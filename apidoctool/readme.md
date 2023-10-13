# Apidoctool - generator of HTTP API documentation from C++ code

// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

---------------------------------------------------------------------------------------------------
## Introduction

Apidoctool is a command-line utility that parses C++ comments and code, and generates JSON files
with the HTTP API documentation.

Currently, the documentation is created in the OpenAPI format intended to be visualized by
[Swagger](https://swagger.io/).

See the command-line help invoked via `-h` for the usage details.

Apidoctool is written in Java 8, and can be compiled and run with any later Java version.

Most of the source code and other files are licensed under the terms of Mozilla Public License 2.0
(unless specified otherwise in the files) which can be found in the `license_mpl2.md` file in the
`licenses/` directory in the root directory of the repository.

Apidoctool has no external dependencies, but includes the source code of some open-source libraries
in the `apidoctool/artifacts/` directory together with their licenses.

---------------------------------------------------------------------------------------------------
## API documentation source

Apidoctool parses C++ code in order to collect information about API endpoints and their input and
output data structures. The source code files to be parsed are defined via parameters either passed
on the command line as `-Dparam=value` or collated into some `apidoctool.properties` file which
path is passed on the command line as `-config=`.

In apidoctool, HTTP API endpoints are called Functions; they can be grouped into Groups.

An ad-hoc regex-based parser is implemented for parsing C++ constructs such as structs, enums, C++
function calls which register HTTP API endpoints (handlers). The code is assumed to use the Nx
Coding Style - not every formatting accepted by a C++ compiler will be accepted by apidoctool.

The main API documentation for the Function is considered to be located in the Apidoc comment
attributed to the Function registration in the C++ code. Also Apidoc comments can be located at
C++ enums, structs and their fields; such information is considered to form a cascaded hierarchy,
e.g. the main Apidoc comment can override the comments for the particular struct fields.

In addition to the C++ entities, the tool parses comments explicitly intended for it - they
resemble Javadoc/Doxygen comments but use `%` instead of `@` and start with `%apidoc`. Their syntax
is described in Java comments in `src/com/nx/apidoc/ApidocComment.java`. Such comments are called
Apidoc comments.

Unit tests demonstrate all features of Apidoc comments - mock C++ code with them can be found in
`test/nx_vms`.

---------------------------------------------------------------------------------------------------
## Architecture

### Package structure

- `src/com/nx/util/` contains generic utilities which are not related to the apidoctool domain,
    such as saving strings to files, and parsing text files.

- `src/com/nx/apidoc/` contains classes which represent the knowledge about Apidoc comments and C++
    entities like structs and enums which are parsed by the tool.

- `src/com/nx/apidoctool/` contains classes which perform the main tasks of the apidoctool - they
    encapsulate the knowledge about the command-line paramaters and tool configuration files, as
    well as the specifics of the C++ code for HTTP API endpoint registration.

### Processing workflow

`com.nx.apidoctool.Main` parses command-line arguments via `com.nx.apidoctool.Params` and
determines which activity needs to be performed - show help, run unit tests, or run the respective
descendant of `com.nx.apidoctool.Executor`:
    - `com.nx.apidoctool.VmsCodeToJsonExecutor` - generating one OpenAPI `.json` file from the
        information parsed out of the C++ source code.
    - `com.nx.apidoctool.PrintDepsExecutor` - printing the list of all used C++ source files;
        helpful for the C++ build scripts/tools like CMake.

`com.nx.utils.SourceCode` is a data object which stores the exact contents of a text file.

`com.nx.apidoc.Apidoc` is a data object which holds the information about all API Functions that
will be used for generating the particular `.json` OpenAPI Schema - it contains the structured
information about each Function, its input and output data (JSON body/response and URL parameters
of an HTTP endpoint), and the documentation texts for all these entities.

`com.nx.apidoc.TypeManager` is a data object and a parser which parses and holds the information
about C++ entities like structures and enums - their items and fields with their C++ types.

`com.nx.apidoctool.VmsCodeToJsonExecutor` loads all necessary C++ source code files into memory
via `com.nx.utils.SourceCode`. Then it parses the files with C++ types (structs and enums) via
`com.nx.apidoc.TypeManager`, and parses the files with the API Function registration lines via
`com.nx.apidoc.SourceCodeParser` which populates the instance of `com.nx.apidoc.Apidoc`. Then it
calls `com.nx.apidoc.OpenApiSerializer` to generate the OpenAPI `.json` file from the populated
`com.nx.apidoc.Apidoc` with the help of `com.nx.utils.JsonSerializer`.

### Unit tests

Since apidoctool uses no external dependencies, its unit tests are written using its own
rudimentary unit test framework `com.nx.utils.TestBase`.

The unit test code is located in `com.nx.apidoctool.Tests`, and is called using the respective
command-line argument.

The data for the unit tests - mock C++ source code files, expected generated files, configuration
files and the like - is located in the `test/` directory.
