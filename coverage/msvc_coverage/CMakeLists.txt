cmake_minimum_required(VERSION 3.0)
project(CoverageConverter)

get_filename_component(MSBUILDDIR ${CMAKE_VS_MSBUILD_COMMAND} DIRECTORY)
get_filename_component(VSINSTALLDIR "${MSBUILDDIR}/../../.." ABSOLUTE)

add_subdirectory(Symbols)
add_subdirectory(Converter)
