#pragma once

#include "framework.h"

#include <dia2.h>
#include <atlbase.h>
#include <string>
#include <vector>
#include <memory>

#include "symbols.h"

class Session;

class Image
{
public:
    Image(Session* parent, const std::wstring& path);

    bool SymbolsLoaded() const { return m_pGlobal; }
    void GetCoverageBlockMap(VSCOVER_BLOCK_MAP_ENTRY*& map, uint32_t& entries);

    bool NextMethod(
        uint32_t& methodId,
        BSTR& methodName,
        BSTR& undecoratedMethodName,
        BSTR& className,
        uint32_t& rva,
        uint32_t& length);

    bool LookupLineNumbers(
        uint32_t rva,
        uint32_t length,
        SLineNumbers* lines,
        uint32_t size,
        uint32_t& count,
        BSTR& fileName,
        BOOL& truncated);

private:
    bool LoadCoverBlockMap(const IMAGE_SECTION_HEADER& header);
    void LoadMethods();
    void AddMethod(IDiaSymbol* pFunction);

    struct Method
    {
        std::wstring name;
        std::wstring undecoratedName;
        std::wstring className;
        DWORD length;
        DWORD rva;
    };

    Session* m_parent;
    std::wstring m_path;
    CComPtr<IDiaSession> m_pSession;
    CComPtr<IDiaSymbol> m_pGlobal;

    std::vector<Method> m_methods;
    int m_nextMethod = -1;

    std::vector<VSCOVER_BLOCK_MAP_ENTRY> m_map;
};
