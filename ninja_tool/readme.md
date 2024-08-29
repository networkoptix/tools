# Ninja Tool - tool for patching files produced by CMake for Ninja build system

// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

## Introduction

In some cases, the out-of-the-box abilities of CMake are insufficient. For instance, it can be
useful to execute certain actions between the CMake generation stage and the build stage.
Also, the CMake dependency graph may not accurately reflect all nuances, particularly for files
generated by the `add_custom_command` CMake command. To address these situations, `ninja_tool.py`
was introduced. It is especially useful for incremental builds.

`ninja_tool.py` is a utility designed to work with CMake when using the Ninja generator and
out-of-source build. It supports both Unix-based and Windows systems. This tool should be run
after the CMake generation stage and before the build starts. The file `ninja_tool.cmake`
provided in this repository demonstrates how to automate this process using the function
`nx_setup_ninja_preprocessor()`. Additionally, this file contains other functions for creating
commands for `ninja_tool.py` to give users an idea of how the tool should be utilized.

**ATTENTION**: This tool relies on certain presuppositions about the format of files generated by
CMake for Ninja build systems. Therefore, if future CMake versions introduce breaking changes
concerning these presuppositions, the result of `ninja_tool.py` execution could be unpredictable.
Currently supported versions are CMake up to version 3.25 and Ninja up to version 1.10.2.

## How to Run ninja_tool.py

`ninja_tool.py` can operate in the command-line or batch mode.

Command-line mode: The tool executes the command passed using the `--execute` command-line
parameter and exits immediately.

Batch mode: The tool reads commands from a file named `pre_build.ninja_tool `residing in the
project's build directory.

For a detailed description of command-line arguments, run the tool with the `--help` parameter.

## Supported commands

### clean

This command cleans the build directory by removing all files except some hardcoded ones, used by
CMake and Conan package manager, as well as the files listed in `known_files.txt` and
`persistent_known_files.txt`. The key difference between these two files is that the latter one is
created and updated by `ninja_tool.py` itself, while the former one is created and updated by
the user (typically, this is done by the CMake scripts).

Parameters: None

### list_unknown_files

This command generates a list of files that will be deleted by the `clean` command.

Parameters: None

### generate_affected_targets_list

This command parses the `build.ninja` file and generates a list of targets that depend on the
files specified in the input.

Parameters:
- Absolute path to the source directory.
- File containing the list of files for which we want to know the dependent targets (one file per
    line, relative to the source tree root).
- Name of the file containing the dependent targets.

### add_directories_to_known_files

This command adds all files in the specified directory to the list of known files (file
`persistent_known_files.txt`).

Parameters:
- Name of the directory to process.

### strengthen

This command adds all transitive dependencies (dependencies of targets that are dependencies of
the given target) as implicit dependencies of the given target.

Parameters:
- List of targets to process.

### run

This command executes an arbitrary program before the actual build starts.

Parameters:
- Path to the executable file and its command-line arguments.