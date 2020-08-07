# MSVC coverage converter

Reads VStest binary code coverage data, and outputs it in XML or LCOV format.

## Build

You will need Visual Studio C++ Profiling Tools, DIA SDK and necessary .NET Framework tools.

```
mkdir build
cd build
cmake -G "Visual Studio 16 2019" -A win32 ..
cmake --build .
```

## Run

```
.\Debug\Converter.exe lcov.info default.coverage
```
