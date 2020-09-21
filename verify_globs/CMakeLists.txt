cmake_minimum_required(VERSION 3.8)

project(verify_globs)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

add_executable(verify_globs exe/src/verify_globs.cpp)

add_subdirectory(lib)

target_link_libraries(verify_globs PRIVATE lib_verify_globs)
target_include_directories(verify_globs PRIVATE ${PROJECT_BINARY_DIR})

