project(Symbols LANGUAGES CXX)

add_library(Symbols SHARED symbols.cpp session.cpp image.cpp)

set_target_properties(Symbols PROPERTIES LINK_FLAGS "/MACHINE:X86")
set_target_properties(Symbols PROPERTIES OUTPUT_NAME "Microsoft.VisualStudio.Coverage.Symbols")
set_property(TARGET Symbols PROPERTY RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/..")

add_library(
    diaguids
    STATIC IMPORTED
)

set_property(TARGET diaguids PROPERTY IMPORTED_LOCATION "${VSINSTALLDIR}/DIA SDK/lib/diaguids.lib")

target_include_directories(
    diaguids
    INTERFACE
    "${VSINSTALLDIR}/DIA SDK/include"
)

target_link_libraries(Symbols diaguids)
