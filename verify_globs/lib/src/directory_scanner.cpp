#include "directory_scanner.h"

#include <cstring>
#include <string>
#include <filesystem>

#include "parse_exception.h"

namespace fs = std::filesystem;

namespace verify_globs {

bool DirectoryScanner::fileNameMatchesPattern(const std::string& fileName, const std::string& pattern)
{
    if (pattern.empty())
        return true;

    std::string::const_iterator fileNameIterator = fileName.begin();
    for (auto patternIt = pattern.begin(); patternIt != pattern.end(); ++patternIt)
    {
        switch (*patternIt)
        {
            case '?':
                if (fileNameIterator == fileName.end())
                    return false;

                ++fileNameIterator;
                break;

            case '*':
            {
                if (patternIt + 1 == pattern.end())
                    return true;

                const int max = (int) strlen(&*fileNameIterator);
                for (int i = 0; i < max; ++i)
                {
                    if (fileNameMatchesPattern(&*(fileNameIterator + i), &*(patternIt + 1)))
                        return true;
                }

                return false;
            }

            case '[':
            case ']':
            {
                throw ParseException("GLOB pattern \"" + pattern
                    + "\" contains unsupported symbol '" + *patternIt + "'");
            }

            default:
                if (fileNameIterator == fileName.end() || *fileNameIterator != *patternIt)
                    return false;

                ++fileNameIterator;
        }
    }

    return fileNameIterator == fileName.end();
}

void DirectoryScanner::setRelativeDirectory(const std::string& directory)
{
    const auto directoryPath = fs::path(directory);
    m_relativeDirectory = directoryPath.empty()
        ? directoryPath
        : fs::absolute(directoryPath).lexically_normal();
}

void DirectoryScanner::setDirectory(const std::string& directory)
{
    m_directory = fs::path(directory);
}

} // namespace verify_globs
