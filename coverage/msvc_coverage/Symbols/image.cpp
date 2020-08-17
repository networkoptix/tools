#include "image.h"

#include <iostream>
#include <fstream>
#include <limits>

#include "session.h"

namespace {

static void Fatal(const std::wstring& msg)
{
    std::wcerr << msg;
    exit(1);
}

static std::wstring getSourceFile(IDiaLineNumber* line)
{
    CComPtr<IDiaSourceFile> source;
    std::wstring result;

    if (line->get_sourceFile(&source) == S_OK)
    {
        BSTR sourceName = nullptr;

        if (source->get_fileName(&sourceName) == S_OK)
        {
            result = sourceName;
            SysFreeString(sourceName);
        }
    }

    return result;
}

static DWORD getEndRva(IDiaEnumLineNumbers* lines)
{
    IDiaLineNumber* line;
    DWORD count;

    DWORD endRva = 0;

    std::wstring fileName;

    while (SUCCEEDED(lines->Next(1, &line, &count)) && count == 1)
    {
        DWORD rva;
        DWORD lineNumber;
        DWORD length;

        if (line->get_relativeVirtualAddress(&rva) == S_OK
            && line->get_lineNumber(&lineNumber) == S_OK
            && line->get_length(&length) == S_OK)
        {
            const DWORD newEnd = rva + length;
            if (newEnd > endRva)
                endRva = newEnd;

            if (fileName.empty())
            {
                fileName = getSourceFile(line);

                // Skip STL files to reduce method count.
                if (fileName.rfind(L"C:\\Program Files (x86)\\Microsoft Visual Studio\\", 0) == 0)
                {
                    line->Release();
                    return 0;
                }
            }
        }
        line->Release();
    }

    #if defined(DEBUG_OUT)
        if (!fileName.empty())
            std::wcout << "    Source: " << fileName << "\n";
    #endif

    return endRva;
}

static std::wstring getName(IDiaSymbol* symbol)
{
    BSTR name = nullptr;
    std::wstring result;

    if (symbol->get_name(&name) == S_OK)
    {
        result = name;
        SysFreeString(name);
    }

    return result;
}

} // namespace

Image::Image(Session* parent, const std::wstring& path):
    m_parent(parent),
    m_path(path)
{
    const std::wstring pdb = path.substr(0, path.find_last_of(L'.')) + L".instr.pdb";

    if (FAILED(m_parent->DataSource()->loadDataFromPdb(pdb.c_str())))
    {
        Fatal(L"loadDataFromPdb " + pdb + L"\n");
        return;
    }

    if (FAILED(m_parent->DataSource()->openSession(&m_session)))
    {
        Fatal(L"openSession");
        return;
    }

    if (FAILED(m_session->get_globalScope(&m_global)))
    {
        Fatal(L"get_globalScope");
        return;
    }
}

bool Image::LoadCoverBlockMap(const IMAGE_SECTION_HEADER& header)
{
    std::ifstream peFile(m_path, std::ios::binary);
    if (!peFile)
    {
        std::wcerr << L"Cannot open " << m_path << L"\n";
        return false;
    }

    if (!peFile.seekg(header.PointerToRawData))
    {
        std::wcerr << L"Cannot seek to " << header.PointerToRawData << L"\n";
        return false;
    }

    m_map.resize(header.Misc.VirtualSize / sizeof(VSCOVER_BLOCK_MAP_ENTRY));

    const size_t toRead = std::min(header.SizeOfRawData, header.Misc.VirtualSize);
    if (!peFile.read((char*)m_map.data(), toRead))
    {
        std::wcerr << L"Read error " << toRead << L" bytes\n";
        return false;
    }
    peFile.close();

    return true;
}

void Image::GetCoverageBlockMap(VSCOVER_BLOCK_MAP_ENTRY*& map, uint32_t& entries)
{
    if (!m_map.empty())
    {
        map = m_map.data();
        entries = m_map.size();
        return;
    }
    CComPtr<IDiaEnumDebugStreams> streams;

    // Retrieve an enumerated sequence of debug data streams.
    if (FAILED(m_session->getEnumDebugStreams(&streams)))
        return;

    // Find SECTIONHEADERS debug stream.
    for (;;)
    {
        CComPtr<IDiaEnumDebugStreamData> stream;
        ULONG count = 0;

        if (FAILED(streams->Next(1, &stream, &count)) || count != 1)
            break;

        BSTR name = nullptr;
        if (FAILED(stream->get_name(&name)))
            continue;

        static const std::wstring HEADERS = L"SECTIONHEADERS";
        const bool found = name && HEADERS == name;
        SysFreeString(name);
        if (!found)
            continue;

        // Find .vscovmp section header.
        IMAGE_SECTION_HEADER header;
        static constexpr auto headerSize = sizeof(IMAGE_SECTION_HEADER);
        DWORD dataLength;
        while (stream->Next(1, headerSize, &dataLength, (BYTE*) &header, &count) == S_OK
            && count == 1)
        {
            if (strncmp((char*) header.Name, ".vscovmp", 8) == 0)
            {
                // Read section data.
                if (LoadCoverBlockMap(header))
                {
                    entries = m_map.size();
                    map = m_map.data();
                }
                break;
            }
        }
        break;
    }
}

void Image::AddMethod(IDiaSymbol* function)
{
    Method method;

    BSTR name = nullptr;

    if (function->get_name(&name) == S_OK)
    {
        method.name = name;
        SysFreeString(name);
        name = nullptr;
    }

    if (function->get_undecoratedName(&name) == S_OK)
    {
        method.undecoratedName = name;
        SysFreeString(name);
        name = nullptr;
    }

    ULONGLONG length;

    if (FAILED(function->get_length(&length)))
        return;

    DWORD rva;
    CComPtr<IDiaEnumLineNumbers> lines;

    if (FAILED(function->get_relativeVirtualAddress(&rva)))
        return;

    if (FAILED(m_session->findLinesByRVA(rva, (DWORD) length, &lines)))
        return;

    DWORD endRva = getEndRva(lines);

    if (endRva <= rva)
        return;

    method.rva = rva;
    method.length = endRva - rva;

    CComPtr<IDiaSymbol> parent;
    if (SUCCEEDED(function->get_classParent(&parent)) && parent)
    {
        if (SUCCEEDED(parent->get_name(&name)))
        {
            method.className = name;
            SysFreeString(name);
            name = nullptr;
        }
    }

    #if defined(DEBUG_OUT)
        wprintf(L"METHOD %s RVA %08x\n", method.name.c_str(), dwRVA);
        if (!method.className.empty())
            wprintf(L"    CLASS %s\n", method.className.c_str());

        BOOL generated = false;
        if (SUCCEEDED(function->get_compilerGenerated(&generated)))
        {
            printf("    Generated: %s\n", generated ? "true":"false");
        }
    #endif

    m_methods.emplace_back(method);
}

void Image::LoadMethods()
{
    #if defined(DEBUG_OUT)
        std::cout << "Loading methods...\n";
    #endif

    // First retrieve the compilands/modules.

    CComPtr<IDiaEnumSymbols> symbols;

    if (FAILED(m_global->findChildren(SymTagCompiland, nullptr, nsNone, &symbols)))
        return;

    IDiaSymbol* compiland;
    ULONG count = 0;

    while (SUCCEEDED(symbols->Next(1, &compiland, &count)) && count == 1)
    {
        CComPtr<IDiaEnumSymbols> functions;
        #if defined(DEBUG_OUT)
            std::wcout << "Compiland: " << getName(compiland).c_str() << "\n";
        #endif
        // For every function symbol defined in the compiland,
        // retrieve and print the line numbering info.

        if (SUCCEEDED(compiland->findChildren(SymTagFunction, nullptr, nsNone, &functions)))
        {
            IDiaSymbol* function;

            while (SUCCEEDED(functions->Next(1, &function, &count)) && count == 1)
            {
                AddMethod(function);
                function->Release();
            }
        }

        compiland->Release();
    }
    #if defined(DEBUG_OUT)
        std::cout << "Methods count: " << m_methods.size() << "\n";
    #endif
}

bool Image::NextMethod(
    uint32_t& methodId,
    BSTR& methodName,
    BSTR& undecoratedMethodName,
    BSTR& className,
    uint32_t& rva,
    uint32_t& length)
{
    if (m_nextMethod == -1 && m_methods.empty())
    {
        LoadMethods();
        m_nextMethod = 0;
    }

    if ((size_t)m_nextMethod >= m_methods.size())
    {
        methodId = 0;
        methodName = nullptr;
        undecoratedMethodName = nullptr;
        rva = 0;
        length = 0;
        return false;
    }

    Method& method = m_methods[m_nextMethod++];

    methodId = m_nextMethod;
    methodName = SysAllocString(method.name.c_str());
    undecoratedMethodName = SysAllocString(method.undecoratedName.c_str());
    className = SysAllocString(method.className.c_str());
    rva = method.rva;
    length = method.length;
    return true;
}

bool Image::LookupLineNumbers(
    uint32_t rva,
    uint32_t length,
    SLineNumbers* lines,
    uint32_t size,
    uint32_t& count,
    BSTR& fileName,
    BOOL& truncated)
{
    fileName = nullptr;

    CComPtr<IDiaEnumLineNumbers> linesEnum;
    if (FAILED(m_session->findLinesByRVA(rva, length, &linesEnum)))
    {
        std::cerr << "Failed to get lines for RVA" << rva << " length " << length << "\n";
        return false;
    }

    LONG lineCount = 0;
    if (FAILED(linesEnum->get_Count(&lineCount)))
        return false;
    count = lineCount;

    truncated = count > size;

    IDiaLineNumber* line;
    DWORD elementCount;

    DWORD sourceIdLast = std::numeric_limits<uint32_t>::max();

    SLineNumbers* current = lines;

    while (SUCCEEDED(linesEnum->Next(1, &line, &elementCount)) && elementCount == 1)
    {
        DWORD lineBegin;
        DWORD colBegin;
        DWORD lineEnd;
        DWORD colEnd;

        DWORD sourceId;

        if (size > 0
            && line->get_lineNumber(&lineBegin) == S_OK
            && line->get_lineNumberEnd(&lineEnd) == S_OK
            && line->get_columnNumber(&colBegin) == S_OK
            && line->get_columnNumberEnd(&colEnd) == S_OK
            && line->get_sourceFileId(&sourceId) == S_OK)
        {
            current->ln_begin = lineBegin;
            current->ln_end = lineEnd;
            current->col_begin = colBegin;
            current->col_end = colEnd;
            --size;
            ++current;
            if (sourceId != sourceIdLast && !fileName)
            {
                CComPtr<IDiaSourceFile> source;

                if (line->get_sourceFile(&source) == S_OK)
                {
                    BSTR sourceName;

                    if (source->get_fileName(&sourceName) == S_OK)
                        fileName = sourceName;

                    sourceIdLast = sourceId;
                }
            }
        }
        line->Release();
    }

    return true;
}
