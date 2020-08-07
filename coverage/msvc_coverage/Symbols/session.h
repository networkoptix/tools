#pragma once

#include "framework.h"

#include <dia2.h>
#include <atlbase.h>
#include <string>
#include <unordered_map>
#include <memory>

class Image;

class Session
{
    Session(CComPtr<IDiaDataSource> pSource): m_pSource(std::move(pSource)) {}

public:
    static Session* Create();
    int OpenImage(std::wstring path, const std::wstring& symbolPath);
    void CloseImage(int image);

    IDiaDataSource* DataSource() const { return m_pSource; }
    Image* GetImage(int image) const;

private:
    CComPtr<IDiaDataSource> m_pSource;
    int m_nextId = 0;
    std::unordered_map<int, std::unique_ptr<Image>> m_images;
};
