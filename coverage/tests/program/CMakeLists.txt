
cmake_minimum_required(VERSION 3.0)
project(test_program)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    add_compile_options(-fprofile-instr-generate -fcoverage-mapping)
    add_link_options(-fprofile-instr-generate)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
    add_compile_options(--coverage)
    add_link_options(--coverage)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
    add_link_options(/Profile)
endif()

add_executable(test_program main.cpp)

set_property(TARGET test_program PROPERTY RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_CACHEFILE_DIR}")
