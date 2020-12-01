#include "verifier.h"

#include <cstring>
#include <string>
#include <fstream>
#include <filesystem>
#include <iostream>
#include <cerrno>

#include <nx/kit/debug.h>

#include "parse_exception.h"
#include "io_exception.h"

namespace fs = std::filesystem;

namespace verify_globs {

// File parsing constants.
constexpr const char* kGlobLineStart = "file(GLOB";
constexpr const char* kFileLineStart = "  \"";

void Verifier::loadCmakeFile(const std::string& fileName)
{
    m_fileContents.clear();

    const fs::path cmakeFilePath = fs::absolute(
        fs::path(m_buildDirectoryName) / fs::path(fileName));
    m_verifierGlobsFileName = cmakeFilePath.string();
    m_currentParsedLineNumber = 0;

    std::ifstream file(cmakeFilePath);
    if (!file.is_open() || !file.good())
    {
        const char* errorStr = strerror(errno);
        const std::string message = "Can't read file " + m_verifierGlobsFileName + ": " + errorStr;
        throw IOException(message.c_str());
    }

    std::string line;
    while (std::getline(file, line))
        m_fileContents.push_back(line);
}

bool Verifier::hasChangedGlobs()
{
    std::unique_ptr<DirectoryScanner> directoryScanner = std::make_unique<DirectoryScanner>();
    std::unique_ptr<GlobContext> globContext;
    std::set<std::string> actualFilesForGlob;
    bool inFileList = false;

    m_currentParsedLineNumber = 0;
    for (const std::string line: m_fileContents)
    {
        ++m_currentParsedLineNumber;

        LineType lineType = getLineTypeCheckingContext(line, inFileList);
        if (lineType == LineType::glob)
        {
            if (inFileList)
                throw ParseException("Unexpected \"glob\" line found: " + line);
            if (hasUnlistedFiles(actualFilesForGlob, globContext.get()))
            {
                outputUnlistedFiles(actualFilesForGlob);
                return true;
            }
            actualFilesForGlob.clear();
            globContext = createGlobContextFromGlobLine(line);
            setupDirectoryScaner(directoryScanner.get(), globContext.get());
            actualFilesForGlob = directoryScanner->ScanDirectory();
        }
        else if (lineType == LineType::file)
        {
            if (!inFileList)
                throw ParseException("Unexpected \"file\" line found: " + line);
            const std::string fileName = getFileNameFromFileLine(line);
            if (!removeFileFromFileList(fileName, &actualFilesForGlob))
            {
                outputMissingFile(fileName);
                return true;
            }
        }
        else if (lineType == LineType::fileListStart)
        {
            inFileList = true;
        }
        else if (lineType == LineType::fileListEnd)
        {
            inFileList = false;
        }
    }

    return false;
}

void Verifier::outputUnlistedFiles(const std::set<std::string>& filenames)
{
    if (!m_isVerbose)
        return;

    std::string filenamesList = "";
    for (const std::string filename: filenames)
    {
        std::string delimiter = filenamesList.length() ? "" : "\n    ";
        filenamesList += filename;
    }
    std::cerr << 1 + (const char*)
R"(
Unlisted files:
    )" + filenamesList + R"(

)";
}

void Verifier::outputMissingFile(const std::string& filename)
{
    if (!m_isVerbose)
        return;

    std::cerr << 1 + (const char*)
R"(
Missing file:
    )" + filename + R"(

)";
}

bool Verifier::hasUnlistedFiles(std::set<std::string> filenames, GlobContext const* context)
{
    if (filenames.empty())
        return false;

    if (!NX_KIT_ASSERT(context))
        return false;

    // If there are entries in the directory that are not listed in OLD_GLOB list, and directories
    // were included to the OLD_GLOB list ("LIST_DIRECTORIES true"), then the OLD_GLOB list and the
    // list produced by the directory scanner should be the same. Thus, after processing all
    // entries returned by the directory scanner, the resulting list should be empty. If it is not
    // empty, then the GLOB results are different.
    if (context->m_listDirectories)
        return true;

    // If the directories weren't included to the OLD_GLOB list ("LIST_DIRECTORIES false"), then
    // the difference between the OLD_GLOB list and the list produced by the directory scanner
    // should be the list, containinng directories. So, if we have anything but directory in the
    // resulting list, then the GLOB results are different.
    for (const std::string& fileName: filenames)
    {
        const fs::path filePath = !context->m_relativeDirectory.empty() ?
            (context->m_relativeDirectory / fs::path(fileName)) : fs::path(fileName);
        if (!fs::is_directory(filePath))
            return true;
    }

    return false;
}

std::unique_ptr<Verifier::GlobContext> Verifier::createGlobContextFromGlobLine(
    const std::string& line)
{
    auto result = std::make_unique<GlobContext>();
    int parseCursorPosition = 0;

    result->m_isRecursive = getRecursiveFlagFromLineMovingCursor(line, &parseCursorPosition);
    result->m_listDirectories = getListDirectoriesFromLineMovingCursor(
        line, result->m_isRecursive, &parseCursorPosition);
    result->m_relativeDirectory = getRelativeDirectoryFromLineMovingCursor(
        line, result->m_listDirectories, &parseCursorPosition);
    result->m_globDirectory = getGlobDirectoryFromLineMovingCursor(line, &parseCursorPosition);
    result->m_pattern = getGlobPatternFromLine(line, parseCursorPosition);

    return result;
}

bool Verifier::getRecursiveFlagFromLineMovingCursor(const std::string& line, int *cursor)
{
    // File parsing constant.
    static const int kFileLineBeginPathIndex = (int) strlen(kGlobLineStart);

    *cursor = kFileLineBeginPathIndex;
    const char& globTypeDefiningToken = line[*cursor];

    if (globTypeDefiningToken == '_')
        return true;

    if (globTypeDefiningToken == ' ')
        return false;

    throw ParseException("Can't determine glob type. Line: " + line);
}

bool Verifier::getListDirectoriesFromLineMovingCursor(
    const std::string& line, const bool isRecursive, int *cursor)
{
    // File parsing constants.
    static const int kListDirectoriesFlagIndexDelta = 27;
    static const int kGlobRecurseAddedLen = (int) strlen("_RECURSE");

    *cursor += kListDirectoriesFlagIndexDelta + (isRecursive ? kGlobRecurseAddedLen : 0);
    const char& listDirectoriesDefiningToken = line[*cursor];

    if (listDirectoriesDefiningToken == 't')
        return true;

    if (listDirectoriesDefiningToken == 'f')
        return false;

    throw ParseException("Can't determine LIST_DIRECTORIES flag value. Line: " + line);
}

std::string Verifier::getRelativeDirectoryFromLineMovingCursor(
    const std::string& line, const bool listDirectories, int *cursor)
{
    // File parsing constants.
    static const int kListDirectoriesTrueLenDelta = (int) strlen("true");
    static const int kListDirectoriesFalseLenDelta = (int) strlen("false");
    constexpr const char* kRelativeToken = " RELATIVE ";
    static const int kRelativeTokenLen = (int) strlen(kRelativeToken);
    static const int kRelativeDirToGlobStringDelta = 3;
    static const int kListDirectoriesFlagToGlobStringDelta = 2;

    *cursor += listDirectories ? kListDirectoriesTrueLenDelta : kListDirectoriesFalseLenDelta;
    if (line.substr(*cursor, kRelativeTokenLen) == kRelativeToken)
    {
        const int relativeDirectoryBeginIndex = *cursor + kRelativeTokenLen + (int) strlen("\"");
        const int relativeDirectoryEndIndex = (int) line.find('"', relativeDirectoryBeginIndex);
        *cursor = relativeDirectoryEndIndex + kRelativeDirToGlobStringDelta;
        return line.substr(relativeDirectoryBeginIndex,
            relativeDirectoryEndIndex - relativeDirectoryBeginIndex);
    }

    *cursor += kListDirectoriesFlagToGlobStringDelta;
    return "";
}

std::string Verifier::getGlobDirectoryFromLineMovingCursor(const std::string& line, int *cursor)
{
    const int globDirectoryEndIndex = (int) line.rfind('/');
    if (globDirectoryEndIndex == std::string::npos)
        throw ParseException("Glob directory not found. Line: " + line);

    const int globDirectoryBeginIndex = *cursor;
    *cursor = globDirectoryEndIndex + 1;
    return line.substr(globDirectoryBeginIndex, globDirectoryEndIndex - globDirectoryBeginIndex);
}

std::string Verifier::getGlobPatternFromLine(const std::string& line, const int cursor)
{
    const int patternEndIndex = (int) line.find('"', cursor);
    if (patternEndIndex == std::string::npos)
        throw ParseException("Glob directory has no '\"' on its end. Line: " + line);
    return line.substr(cursor, patternEndIndex - cursor);
}

void Verifier::setupDirectoryScaner(DirectoryScanner* scanner, GlobContext const* context)
{
    if (!NX_KIT_ASSERT(context))
        return;

    scanner->setDirectory(context->m_globDirectory);
    scanner->setRelativeDirectory(context->m_relativeDirectory);
    scanner->m_pattern = context->m_pattern;
    scanner->m_recursive = context->m_isRecursive;
}

std::string Verifier::getFileNameFromFileLine(const std::string& line)
{
    static const int kFileLineBeginPathIndex = (int) strlen(kFileLineStart);

    const int endFileNamePosition = (int) line.find('"', kFileLineBeginPathIndex);
    const auto filePath = fs::path(line.substr(kFileLineBeginPathIndex,
        endFileNamePosition - kFileLineBeginPathIndex));
    return filePath.generic_string();
}

void Verifier::setGlobMismatchFileFlag(const std::string& flagFileName)
{
    const fs::path flagFilePath = fs::absolute(
        fs::path(m_buildDirectoryName) / fs::path(flagFileName));
    std::ofstream file(flagFilePath);
    file.close();
    // The message "--GLOB mismatch!" is the same that the native cmake implementation of
    // VerifyGlob check produces.
    std::cout << "--GLOB mismatch!" << std::endl;
}

bool Verifier::removeFileFromFileList(
    const std::string& filename, std::set<std::string>* filenames)
{
    const auto fileSearchIt = filenames->find(filename);
    if (fileSearchIt == filenames->end())
        return false;
    filenames->erase(fileSearchIt);
    return true;
}

Verifier::LineType Verifier::getLineTypeCheckingContext(
    const std::string& line, const bool inFileList)
{
    // File parsing constants.
    constexpr const char* kCmakePolicyLineStart = "cmake_policy(SET CMP0009 NEW)";
    constexpr const char* kSetOldGlobLineStart = "set(OLD_GLOB";
    constexpr const char* kEndOldGlobLineStart = "  )";
    constexpr const char* kCheckGlobLineStart = "if(NOT \"${NEW_GLOB}\" STREQUAL \"${OLD_GLOB}\")";
    constexpr const char* kMessageLineStart = "  message(\"-- GLOB mismatch!\")";
    constexpr const char* kCmakeFileTouchLineStart = "  file(TOUCH_NOCREATE ";
    constexpr const char* kEndifLineStart = "endif()";

    if (line.rfind(kGlobLineStart, 0) != std::string::npos)
    {
        if (inFileList)
            throw ParseException("Unexpected \"glob\" line found: " + line);
        return LineType::glob;
    }

    if (line.rfind(kFileLineStart, 0) != std::string::npos)
    {
        if (!inFileList)
            throw ParseException("Unexpected \"file\" line found: " + line);
        return LineType::file;
    }

    if (line.rfind(kSetOldGlobLineStart, 0) != std::string::npos)
        return LineType::fileListStart;

    if (line.rfind(kEndOldGlobLineStart, 0) != std::string::npos)
        return LineType::fileListEnd;

    // We don't use these line types for now. Extend "LineType" and rewrite this condition if such
    // need will ever arise.
    if (line.rfind(kCheckGlobLineStart, 0) != std::string::npos
        || line.rfind(kMessageLineStart, 0) != std::string::npos
        || line.rfind(kCmakeFileTouchLineStart, 0) != std::string::npos
        || line.rfind(kEndifLineStart, 0) != std::string::npos
        || line[0] == '#'
        || line.empty()
        || line.rfind(kCmakePolicyLineStart, 0) != std::string::npos)
    {
        return LineType::irrelevant;
    }

    throw ParseException("Unknown line type. Line: " + line);
}

} // namesapace verify_globs
