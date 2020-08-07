
#include "image.h"

#include <iostream>
#include <fstream>

#include "session.h"

namespace {

static void Fatal(std::wstring msg)
{
    std::wcerr << msg;
    exit(1);
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

    if (FAILED(m_parent->DataSource()->openSession(&m_pSession)))
    {
        Fatal(L"openSession");
        return;
    }

    if (FAILED(m_pSession->get_globalScope(&m_pGlobal)))
    {
        Fatal(L"get_globalScope");
        return;
    }
}

bool Image::LoadCoverBlockMap(const IMAGE_SECTION_HEADER& header)
{
    std::ifstream pefile(m_path, std::ios::binary);
    if (!pefile)
    {
        std::wcerr << L"Cannot open " << m_path << L"\n";
        return false;
    }

    if (!pefile.seekg(header.PointerToRawData))
    {
        std::wcerr << L"Cannot seek to " << header.PointerToRawData << L"\n";
        return false;
    }

    m_map.resize(header.Misc.VirtualSize / sizeof(VSCOVER_BLOCK_MAP_ENTRY));

    const size_t toRead = min(header.SizeOfRawData, m_map.size() * sizeof(VSCOVER_BLOCK_MAP_ENTRY));
    if (!pefile.read((char*)m_map.data(), toRead))
    {
        std::wcerr << L"Read error " << toRead << L" bytes\n";
        return false;
    }
    pefile.close();

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
    CComPtr<IDiaEnumDebugStreams> pEnumStreams;

    // Retrieve an enumerated sequence of debug data streams
    if (FAILED(m_pSession->getEnumDebugStreams(&pEnumStreams)))
        return;

    // Find SECTIONHEADERS debug stream.
    for (;;)
    {
        CComPtr<IDiaEnumDebugStreamData> pStream;
        ULONG celt = 0;

        if (FAILED(pEnumStreams->Next(1, &pStream, &celt)) || celt != 1)
            break;

        BSTR bstrName = nullptr;
        if (FAILED(pStream->get_name(&bstrName)))
            continue;

        static const std::wstring HEADERS = L"SECTIONHEADERS";
        const bool found = bstrName && HEADERS == bstrName;
        SysFreeString(bstrName);
        if (!found)
            continue;

        // Find .vscovmp section header
        IMAGE_SECTION_HEADER header;
        DWORD cbData;
        while (pStream->Next(1, sizeof(IMAGE_SECTION_HEADER), &cbData, (BYTE*)&header, &celt) == S_OK && celt == 1)
        {
            std::string name((char*)header.Name, 8);

            // Read section data
            if (name == ".vscovmp")
            {
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

std::wstring getSourceFile(IDiaLineNumber* pLine)
{
    CComPtr<IDiaSourceFile> pSource;
    std::wstring result;

    if (pLine->get_sourceFile(&pSource) == S_OK) {
        BSTR bstrSourceName = nullptr;

        if (pSource->get_fileName(&bstrSourceName) == S_OK) {
            result = bstrSourceName;
            SysFreeString(bstrSourceName);
        }
    }
    return result;
}

static DWORD getEndRva(IDiaEnumLineNumbers* pLines)
{
    IDiaLineNumber* pLine;
    DWORD celt;

    DWORD endRVA = 0;

    std::wstring fileName;

    while (SUCCEEDED(pLines->Next(1, &pLine, &celt)) && (celt == 1))
    {
        DWORD dwRVA;
        DWORD dwLinenum;
        DWORD dwLength;

        if ((pLine->get_relativeVirtualAddress(&dwRVA) == S_OK) &&
            (pLine->get_lineNumber(&dwLinenum) == S_OK) &&
            (pLine->get_length(&dwLength) == S_OK))
        {
            const DWORD newEnd = dwRVA + dwLength;
            if (newEnd > endRVA)
                endRVA = newEnd;

            if (fileName.empty())
            {
                fileName = getSourceFile(pLine);

                // Skip STL files to reduce method count.
                if (fileName.find(L"C:\\Program Files (x86)\\Microsoft Visual Studio\\") == 0)
                {
                    pLine->Release();
                    return 0;
                }
            }
        }
        pLine->Release();
    }

    #ifdef DEBUG_OUT
        if (!fileName.empty())
            std::wcout << "    Source: " << fileName << "\n";
    #endif

    return endRVA;
}

std::wstring getName(IDiaSymbol* pSymbol)
{
    BSTR bstrName = nullptr;
    std::wstring result;

    if (pSymbol->get_name(&bstrName) == S_OK)
    {
        result = bstrName;
        SysFreeString(bstrName);
    }
    return result;
}

void Image::AddMethod(IDiaSymbol* pFunction)
{
    Method method;

    BSTR bstrName = nullptr;

    if (pFunction->get_name(&bstrName) == S_OK)
    {
        method.name = bstrName;
        SysFreeString(bstrName);
        bstrName = nullptr;
    }

    if (pFunction->get_undecoratedName(&bstrName) == S_OK)
    {
        method.undecoratedName = bstrName;
        SysFreeString(bstrName);
        bstrName = nullptr;
    }

    ULONGLONG ulLength;

    if (FAILED(pFunction->get_length(&ulLength)))
        return;

    DWORD dwRVA;
    CComPtr<IDiaEnumLineNumbers> pLines;

    if (FAILED(pFunction->get_relativeVirtualAddress(&dwRVA)))
        return;

    if (FAILED(m_pSession->findLinesByRVA(dwRVA, static_cast<DWORD>(ulLength), &pLines)))
        return;

    DWORD endRVA = getEndRva(pLines);

    if (endRVA <= dwRVA)
        return;

    method.rva = dwRVA;
    method.length = endRVA - dwRVA;

    CComPtr<IDiaSymbol> parent;
    if (SUCCEEDED(pFunction->get_classParent(&parent)) && parent)
    {
        if (SUCCEEDED(parent->get_name(&bstrName)))
        {
            method.className = bstrName;
            SysFreeString(bstrName);
            bstrName = nullptr;
        }
    }

    #ifdef DEBUG_OUT
        wprintf(L"METHOD %s RVA %08x\n", method.name.c_str(), dwRVA);
        if (!method.className.empty())
            wprintf(L"    CLASS %s\n", method.className.c_str(), dwRVA);

        BOOL generated = false;
        if (SUCCEEDED(pFunction->get_compilerGenerated(&generated)))
        {
            printf("    Generated: %s\n", (generated ? "true":"false"));
        }
    #endif

    m_methods.emplace_back(method);
}

void Image::LoadMethods()
{
    #ifdef DEBUG_OUT
        std::cout << "Loading methods...\n";
    #endif

    // First retrieve the compilands/modules

    CComPtr<IDiaEnumSymbols> pEnumSymbols;

    if (FAILED(m_pGlobal->findChildren(SymTagCompiland, nullptr, nsNone, &pEnumSymbols)))
        return;

    IDiaSymbol* pCompiland;
    ULONG celt = 0;

    while (SUCCEEDED(pEnumSymbols->Next(1, &pCompiland, &celt)) && (celt == 1))
    {
        CComPtr<IDiaEnumSymbols> pEnumFunction;
        #ifdef DEBUG_OUT
            std::wcout << "Compiland: " << getName(pCompiland).c_str() << "\n";
        #endif
        // For every function symbol defined in the compiland, retrieve and print the line numbering info

        if (SUCCEEDED(pCompiland->findChildren(SymTagFunction, NULL, nsNone, &pEnumFunction)))
        {
            IDiaSymbol* pFunction;

            while (SUCCEEDED(pEnumFunction->Next(1, &pFunction, &celt)) && (celt == 1))
            {
                AddMethod(pFunction);
                pFunction->Release();
            }
        }

        pCompiland->Release();
    }
    #ifdef DEBUG_OUT
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

    CComPtr<IDiaEnumLineNumbers> pLines;
    if (FAILED(m_pSession->findLinesByRVA(rva, length, &pLines)))
    {
        std::cerr << "Failed to get lines for RVA" << rva << " length " << length << "\n";
        return false;
    }

    LONG lCount = 0;
    if (FAILED(pLines->get_Count(&lCount)))
        return false;
    count = lCount;

    truncated = count > size;

    IDiaLineNumber* pLine;
    DWORD celt;

    DWORD dwSrcIdLast = (DWORD)(-1);

    SLineNumbers* current = lines;

    while (SUCCEEDED(pLines->Next(1, &pLine, &celt)) && (celt == 1))
    {
        DWORD lineBegin;
        DWORD colBegin;
        DWORD lineEnd;
        DWORD colEnd;

        DWORD dwSrcId;

        if (size > 0 &&
            (pLine->get_lineNumber(&lineBegin) == S_OK) &&
            (pLine->get_lineNumberEnd(&lineEnd) == S_OK) &&
            (pLine->get_columnNumber(&colBegin) == S_OK) &&
            (pLine->get_columnNumberEnd(&colEnd) == S_OK) &&
            (pLine->get_sourceFileId(&dwSrcId) == S_OK))
        {
            current->ln_begin = lineBegin;
            current->ln_end = lineEnd;
            current->col_begin = colBegin;
            current->col_end = colEnd;
            --size;
            ++current;
            if (dwSrcId != dwSrcIdLast && !fileName)
            {
                CComPtr<IDiaSourceFile> pSource;

                if (pLine->get_sourceFile(&pSource) == S_OK)
                {
                    BSTR bstrSourceName;

                    if (pSource->get_fileName(&bstrSourceName) == S_OK)
                        fileName = bstrSourceName;

                    dwSrcIdLast = dwSrcId;
                }
            }
        }
        pLine->Release();
    }

    return true;
}
