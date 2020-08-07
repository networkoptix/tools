#pragma once

#include "framework.h"

#include <atlbase.h>

#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * SymbolInterop API.
 */

struct VSCOVER_BLOCK_MAP_ENTRY
{
    uint32_t Rva = 0;
    uint16_t SizeOfBlock = 0;
    int8_t DeltaFromOriginalBlock = 0;
    uint8_t SizeOfProbe = 0;
};

struct SLineNumbers
{
    uint32_t ln_begin;
    uint32_t col_begin;
    uint32_t ln_end;
    uint32_t col_end;
};

class Session;

__declspec(dllexport) Session* CreateSession();
__declspec(dllexport) void CloseSession(Session* session);
__declspec(dllexport) int32_t OpenSessionImage(
    Session* session,
    LPWSTR path,
    LPWSTR symbolPath,
    uint32_t imageSize,
    uint32_t linkTime);
__declspec(dllexport) void CloseSessionImage(Session* session, int32_t image);

__declspec(dllexport) BOOL ImageSymbolsLoaded(Session* session, int32_t image);

__declspec(dllexport) void GetCoverageBlockMap(
    Session* session,
    int32_t image,
    VSCOVER_BLOCK_MAP_ENTRY*& map,
    uint32_t& entries);

__declspec(dllexport) BOOL LookupNextImageMethod(
    Session* session,
    int32_t image,
    uint32_t& methodId,
    BSTR& methodName,
    BSTR& undecoratedMethodName,
    BSTR& className,
    BSTR& namespaceName,
    uint32_t& rva,
    uint32_t& length);

__declspec(dllexport) bool LookupLineNumbers(
    Session* session,
    int32_t image,
    uint32_t rva,
    uint32_t length,
    SLineNumbers* lines,
    uint32_t size,
    uint32_t& count,
    BSTR& fileName,
    BOOL& truncated);

#ifdef __cplusplus
}
#endif
