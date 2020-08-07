project(Converter LANGUAGES CSharp)

set(CMAKE_CSharp_FLAGS "/platform:x86")

add_executable(Converter Program.cs)

set_property(TARGET Converter PROPERTY RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/..")

set(VS_TESTPLATFORM "${VSINSTALLDIR}/Common7/IDE/Extensions/TestPlatform")

set(analysis_dll "${VS_TESTPLATFORM}/Microsoft.VisualStudio.Coverage.Analysis.dll")
set(interop_dll "${VS_TESTPLATFORM}/Microsoft.VisualStudio.Coverage.Interop.dll")

# Match target framework version with Visual Studio assemblies.
execute_process(
    COMMAND powershell -ExecutionPolicy Bypass -File ${CMAKE_CURRENT_SOURCE_DIR}/frameworkVersion.ps1 ${analysis_dll}
    OUTPUT_VARIABLE frameworkOut
    OUTPUT_STRIP_TRAILING_WHITESPACE)
string(REGEX REPLACE "^\\.NETFramework,Version=" "" frameworkVersion ${frameworkOut})
message(STATUS "Target .NET Framework: ${frameworkVersion}")

set_property(TARGET Converter PROPERTY VS_DOTNET_TARGET_FRAMEWORK_VERSION ${frameworkVersion})

# Add references
set_property(TARGET Converter PROPERTY VS_DOTNET_REFERENCES
    "System"
    "System.Data"
    "System.Xml"
    ${analysis_dll}
    ${interop_dll}
)

file(COPY ${analysis_dll} ${interop_dll} DESTINATION  "${PROJECT_BINARY_DIR}/..")
