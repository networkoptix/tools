#include "symbols.h"
#include "session.h"
#include "image.h"

Session* CreateSession()
{
    return Session::Create();
}

void CloseSession(Session* session)
{
    if (session)
        delete session;
}

int32_t OpenSessionImage(
    Session* session,
    LPWSTR path,
    LPWSTR symbolPath,
    uint32_t imageSize,
    uint32_t linkTime)
{
    return session->OpenImage(path, symbolPath);
}

void CloseSessionImage(Session* session, int32_t image)
{
    session->CloseImage(image);
}

BOOL ImageSymbolsLoaded(Session* session, int32_t image)
{
    const auto sessionImage = session->GetImage(image);
    return sessionImage && sessionImage->SymbolsLoaded();
}

void GetCoverageBlockMap(
    Session* session,
    int32_t image,
    VSCOVER_BLOCK_MAP_ENTRY*& map,
    uint32_t& entries)
{
    auto sessionImage = session->GetImage(image);
    if (!sessionImage)
        return;
    sessionImage->GetCoverageBlockMap(map, entries);
}

BOOL LookupNextImageMethod(
    Session* session,
    int32_t image,
    uint32_t& methodId,
    BSTR& methodName,
    BSTR& undecoratedMethodName,
    BSTR& className,
    BSTR& namespaceName,
    uint32_t& rva,
    uint32_t& length)
{
    auto sessionImage = session->GetImage(image);
    if (!sessionImage)
        return false;

    namespaceName = nullptr;

    return sessionImage->NextMethod(
        methodId, methodName, undecoratedMethodName, className, rva, length);
}

bool LookupLineNumbers(
    Session* session,
    int32_t image,
    uint32_t rva,
    uint32_t length,
    SLineNumbers* lines,
    uint32_t size,
    uint32_t& count,
    BSTR& fileName,
    BOOL& truncated)
{
    auto sessionImage = session->GetImage(image);
    if (!sessionImage)
        return false;
    return sessionImage->LookupLineNumbers(rva, length, lines, size, count, fileName, truncated);
}
