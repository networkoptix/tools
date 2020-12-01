#pragma once

#include <string>
#include <vector>

#include "directory_scanner.h"

namespace verify_globs {

class Verifier
{
public:
    Verifier(std::string buildDirectoryName, bool isVerbose = false):
        m_buildDirectoryName(buildDirectoryName), m_isVerbose(isVerbose) {}

    void loadCmakeFile(const std::string& fileName = "CMakeFiles/VerifyGlobs.cmake");
    bool hasChangedGlobs();
    void setGlobMismatchFileFlag(const std::string& flagFileName = "CMakeFiles/cmake.verify_globs");

    const char* getParsedFileName() const { return m_verifierGlobsFileName.c_str(); }
    int getCurrentParsedLineNumber() const { return m_currentParsedLineNumber; }

private:
    struct GlobContext
    {
        std::string m_relativeDirectory;
        std::string m_globDirectory;
        std::string m_pattern;
        bool m_listDirectories = false;
        bool m_isRecursive = false;
    };

    enum class LineType
    {
        unknown,
        glob,
        file,
        fileListStart,
        fileListEnd,
        irrelevant,
    };

    std::string m_buildDirectoryName;
    std::vector<std::string> m_fileContents;

    bool hasUnlistedFiles(std::set<std::string> filenames, GlobContext const* context);
    void outputUnlistedFiles(const std::set<std::string>& filenames);
    void outputMissingFile(const std::string& filename);
    std::unique_ptr<GlobContext> createGlobContextFromGlobLine(const std::string& line);
    void setupDirectoryScaner(DirectoryScanner* scanner, GlobContext const* context);
    std::string getFileNameFromFileLine(const std::string& line);
    bool removeFileFromFileList(const std::string& filename, std::set<std::string>* filenames);
    LineType getLineTypeCheckingContext(const std::string& line, const bool inFileList);

    bool getRecursiveFlagFromLineMovingCursor(const std::string& line, int *cursor);
    bool getListDirectoriesFromLineMovingCursor(
        const std::string& line, const bool isRecursive, int *cursor);
    std::string getRelativeDirectoryFromLineMovingCursor(
        const std::string& line, const bool listDirectories, int *cursor);
    std::string getGlobDirectoryFromLineMovingCursor(const std::string& line, int *cursor);
    std::string getGlobPatternFromLine(const std::string& line, const int cursor);

    std::string m_verifierGlobsFileName;
    int m_currentParsedLineNumber;
    bool m_isVerbose;
};

} // namesapace verify_globs
