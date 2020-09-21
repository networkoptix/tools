#pragma once

#include <set>
#include <string>
#include <filesystem>

namespace fs = std::filesystem;

namespace verify_globs {

class DirectoryScanner
{
public:
    DirectoryScanner(bool followSymlniks = false): m_followSymlinks(followSymlniks) {}

    std::set<std::string> ScanDirectory(
        const fs::path& directory, const std::string& pattern = "");
    std::set<std::string> ScanDirectory() { return ScanDirectory(m_directory, m_pattern); }
    void setDirectory(const std::string& directory);
    void setRelativeDirectory(const std::string& directory);

    bool m_recursive = false;
    std::string m_pattern;

private:
    bool m_followSymlinks;
    fs::path m_relativeDirectory;
    fs::path m_directory;

    static bool fileNameMatchesPattern(const std::string& filePath, const std::string& pattern);
};

} // namespace verify_globs
