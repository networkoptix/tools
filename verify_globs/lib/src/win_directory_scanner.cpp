#include "directory_scanner.h"
#if defined(WIN32)

#include <set>
#include <cstring>
#include <string>
#include <filesystem>
#include <iostream>

#include <windows.h>
#include <tchar.h>
#include <strsafe.h>

#include "io_exception.h"

namespace fs = std::filesystem;

namespace verify_globs {

std::set<std::string> DirectoryScanner::ScanDirectory(
    const fs::path& directory, const std::string& pattern)
{
    std::set<std::string> result;
    const std::string glob = directory.string() + "/*";

    WIN32_FIND_DATA findData;
    HANDLE findHandle = INVALID_HANDLE_VALUE;
    findHandle = FindFirstFileA(glob.c_str(), &findData);
    if (findHandle == INVALID_HANDLE_VALUE)
    {
        const DWORD lastError = GetLastError();
        if (lastError == ERROR_FILE_NOT_FOUND)
            return result;
        if (lastError == ERROR_PATH_NOT_FOUND)
        {
            std::cerr << "verify_globs: WARNING: Can't find directory \""
                << directory.string() << "\"" << "; possible error in CMake file." << std::endl;
            return result;
        }
        throw IOException(std::string("Error ") + std::to_string(lastError) +
            " while trying to find the first file in directory " + directory.string());
    }

    for (bool hasUncheckedFiles = true;
        hasUncheckedFiles;
        hasUncheckedFiles = (FindNextFileA(findHandle, &findData) != 0))
    {
        if (strcmp(findData.cFileName, ".") == 0 || strcmp(findData.cFileName, "..") == 0)
            continue;

        const auto pathFileName = fs::path(findData.cFileName);
        const fs::path fullPath = (directory / pathFileName).lexically_normal();
        if (findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
        {
            if (m_recursive)
            {
                const std::set<std::string> subdirectoryResult = ScanDirectory(fullPath, pattern);
                result.insert(subdirectoryResult.begin(), subdirectoryResult.end());
            }
        }

        if (!fileNameMatchesPattern(pathFileName.generic_string(), pattern))
            continue;

        if (!m_relativeDirectory.empty())
        {
            const fs::path relativePath = fullPath.lexically_relative(m_relativeDirectory);
            result.emplace(relativePath.generic_string());
        }
        else
        {
            result.emplace(fullPath.generic_string());
        }
    }

    const DWORD lastError = GetLastError();
    if (lastError != ERROR_NO_MORE_FILES)
    {
        FindClose(findHandle);
        throw IOException(
            std::string("Error ") + std::to_string(lastError)
            + " trying to find the next entry in the directory " + directory.string());
    }

    FindClose(findHandle);
    return result;
}

} // namespace verify_globs

#endif // defined(WIN32)
