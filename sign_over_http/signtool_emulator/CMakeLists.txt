cmake_minimum_required(VERSION 3.15)

project(signtool_emulator LANGUAGES CXX)

set(source_files
    src/main.cpp
)

add_executable(${PROJECT_NAME} ${source_files})
set_target_properties(${PROJECT_NAME} PROPERTIES
    OUTPUT_NAME signtool
    MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
