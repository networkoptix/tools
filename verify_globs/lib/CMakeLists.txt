cmake_minimum_required(VERSION 3.8)

project(lib_verify_globs)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set(GCC_EXPECTED_VERSION 8.1.0)
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS GCC_EXPECTED_VERSION)
        message(FATAL_ERROR
	    "GCC: lib_verify_globs requires version ${GCC_EXPECTED_VERSION} to build but found \
	    ${CMAKE_CXX_COMPILER_VERSION}")
    endif()
endif()

set(nxKitDir "" CACHE PATH "Path to NX Kit library sources.")
if(nxKitDir STREQUAL "")
    set(nxKitDir "${CMAKE_CURRENT_LIST_DIR}/../../../nx/open/artifacts")
    if(NOT EXISTS ${nxKitDir}/nx_kit/src/nx/kit)
        message(FATAL_ERROR
            "Define nxKitDir cache variable to point to NX Kit library source directory.")
    endif()
endif()

set(nxKitLibraryType "STATIC" CACHE STRING "" FORCE)
set(nxKitWithTests "NO" CACHE STRING "" FORCE)
add_subdirectory(${nxKitDir}/nx_kit ${CMAKE_CURRENT_BINARY_DIR}/nx_kit)

add_library(lib_verify_globs STATIC
    src/directory_scanner.cpp
    src/win_directory_scanner.cpp
    src/generic_directory_scanner.cpp
    src/verifier.cpp

    src/directory_scanner.h
    src/verifier.h
    src/parse_exception.h
    src/io_exception.h)

target_include_directories(lib_verify_globs INTERFACE src)
target_link_libraries(lib_verify_globs PRIVATE nx_kit)

if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_link_libraries(lib_verify_globs
        PUBLIC
        "stdc++fs"
        "-Wl,--exclude-libs,ALL")
endif()

if (WIN32)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
endif()
