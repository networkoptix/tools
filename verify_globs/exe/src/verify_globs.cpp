#include <iostream>
#include <cstring>
#include <string>
#include <memory>

#include <parse_exception.h>
#include <io_exception.h>
#include <directory_scanner.h>
#include <verifier.h>

using namespace verify_globs;

static const std::string kUtilityVersion = "1.0";
static const std::string kUtilityName = "verify_globs";

int main(int argc, char* argv[])
{
    const std::string kUsageMessage = /*suppress newline*/ 1 + (const char*)
R"(
Usage:

 )" + kUtilityName + R"( <build-directory>
 )" + kUtilityName + R"( -h|--help
)";

    if (argc != 2)
    {
        std::cout << kUsageMessage;
        return 1;
    }

    if (strcmp(argv[1], "-h") == 0 || strcmp(argv[1], "--help") == 0)
    {
        const std::string helpMessage = /*suppress newline*/ 1 + (const char*)
R"(
This tool is an interpreter for VerifyGlobs.cmake script. It emulates running cmake in the script
interpretation mode with the VerifyGlobs.cmake file as a parameter:
cmake -P <path-to-VerifyGlobs.cmake>

If the file lists described by the GLOBs found in this file haven't changed, this tool prints
nothing and exits with the exit status 0. If there are some new files or some files a missing, this
tool prints "--GLOB mismatch!", touches the file cmake.verify_globs and exits with the exit status
0. If the file cannot be parsed, e.g. contains something that this tool does not support, this tool
fails with an error. If the script needs such feature, consider extending this tool.

)" + kUsageMessage + R"(
If <build-directory> is specified, then the tool parses VerifyGlobs.cmake file generated by CMake
for this build directory.

If the tools is run with "-h" or "--help" option, it prints this message and exits.
)";
        std::cout << helpMessage;
        return 0;
    }

    auto verifier = std::make_unique<Verifier>(argv[1]);
    try
    {
        verifier->loadCmakeFile();

        if (verifier->hasChangedGlobs())
        {
            verifier->setGlobMismatchFileFlag();
            return 1;
        }
    }
    catch (const ParseException& e)
    {
        std::cerr << kUtilityName << ": Error at "
            << verifier->getParsedFileName() << ":"
            << verifier->getCurrentParsedLineNumber() << ":\n"
            << "  " << e.what() << std::endl;
        return 1;
    }
    catch (const IOException& e)
    {
        std::cerr << kUtilityName << ": IO exception: " << e.what() << std::endl;
        return 1;
    }
    catch (const std::exception& e)
    {
        std::cerr << kUtilityName << ": INTERNAL ERROR: Exception raised: "
            << e.what() << std::endl;
        return 1;
    }
    catch (...)
    {
        std::cerr << kUtilityName << ": INTERNAL ERROR: Unknown exception raised." << std::endl;
        return 1;
    }
}
