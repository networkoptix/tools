#include "directory_scanner.h"
#if !defined(WIN32)

#include <set>
#include <cstring>
#include <string>
#include <filesystem>
#include <iostream>

namespace fs = std::filesystem;

namespace verify_globs {

std::set<std::string> DirectoryScanner::ScanDirectory(
    const fs::path& directory, const std::string& pattern)
{
    std::set<std::string> result;

    const auto options = fs::directory_options::skip_permission_denied |
        (m_followSymlinks
            ? fs::directory_options::follow_directory_symlink
            : fs::directory_options::none);
    const fs::path directoryPath = fs::absolute(fs::path(directory)).lexically_normal();

    try
    {
        for (auto directoryEntryIt = fs::recursive_directory_iterator(directoryPath, options);
            directoryEntryIt != fs::recursive_directory_iterator();
            ++directoryEntryIt)
        {
            if (!m_recursive)
                directoryEntryIt.disable_recursion_pending();

            const fs::path path = directoryEntryIt->path();
            if (!fileNameMatchesPattern(path.filename().generic_string(), pattern))
                continue;

            if (!m_relativeDirectory.empty())
            {
                const fs::path relativePath = path.lexically_relative(m_relativeDirectory);
                result.emplace(relativePath.generic_string());
            }
            else
            {
                result.emplace(path.generic_string());
            }
        }
    }
    catch (const fs::filesystem_error& e)
    {
        if (e.code() == std::errc::no_such_file_or_directory)
            std::cerr << "verify_globs: WARNING: Can't find directory " << e.path1()
                << "; possible error in CMake file." << std::endl;
        else
            throw;
    }
    return result;
}

} // namespace verify_globs

#endif // !defined(WIN32)
