#include "session.h"
#include "image.h"

Session* Session::Create()
{
    CComPtr<IDiaDataSource> pSource;
    const HRESULT hr = CoCreateInstance(CLSID_DiaSource,
        nullptr,
        CLSCTX_INPROC_SERVER,
        __uuidof(IDiaDataSource),
        (void**)&pSource);

    if (FAILED(hr))
        return nullptr;

    return new Session(std::move(pSource));
}

int Session::OpenImage(std::wstring path, const std::wstring& symbolPath)
{
    auto image = std::make_unique<Image>(this, path);
    if (!image->SymbolsLoaded())
        return -1;

    const auto id = m_nextId++;
    m_images[id] = std::move(image);
    return id;
}

void Session::CloseImage(int image)
{
    m_images.erase(image);
}

Image* Session::GetImage(int image) const
{
    const auto it = m_images.find(image);
    if (it == m_images.end())
        return nullptr;
    return it->second.get();
}
