# Dump Tool

A script to analyze windows `dmp` files from VMS Server and Client.

## Requirements

- **Windows 7+ x64** - tested on **Windows 10 Home and Pro**
- **Python 3** - Interpreter for windows: <https://www.python.org>
- **7z** - Free archive extractor: <https://www.7-zip.org>
- **dark** - Wix extractor, part of Wix Toolset: <http://wixtoolset.org/releases>
- **cdb** - Windows Debugger (for report generation), part of Windows SDK:
    <https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk>
- **devenv** - Visual Studio (for developers only): <https://www.visualstudio.com>

Make sure all of them are available on path, e.g. `PATH` contains:

- `C:\Program Files\7-Zip` for `7z`
- `C:\Program Files (x86)\WiX Toolset v3.11\bin` for `dark`
- `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64` for `cdb`
- `C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\Common7\IDE` for `devenv`

## How it works

- Extracts build information from `dmp` file, customization can be specified explicitly by option
  `-c`.
- Downloads and extracts build and PDBs if they are not available in cache directory.
- Runs Visual Studio for `dmp` file or extracts all thread stacks into text file `cdb-bt` (option
  `-g`).

## Usage

See: `python dump_tool.py -h` for more instructions.

NOTES:

- If you have Python 2 installed in path as well, you can rename Python 3 `python.exe` into
    `python3.exe` and use it directly: `python3 ./dump_tool.py -h`.
- If you use `bash` (e.g. cygwin), make sure `python3` is in the path, then use
    `./dump_tool.py -h`. If there already is `python3`, make an alias for windows python and use it
    instead.
- This script uses a temporary directory, which is by default created in current directory.
    This can be changed by `-d` option, so it makes sense to make bat/sh script.
- Argument parsing is performed by python module, which has a known issue: despite the provided
    help, options without arguments should not be followed by non-option arguments.


# Crash Monitor & Analyzer

Linux and Windows Crash Report Monitor and Analyzer.

## Requirements

- Satisfy all requirements for Dump Tool, see *Requirements* section in **Dump Tool** above.
- Install python modules: `python -m pip install -r requirements.txt`.

## Run Tests

- Run all unit and functional tests: `python -m pytest`.
- Normally all tests take up to 5 minutes to pass.
- Internet access to crash server and JIRA is required for `external_api_test.py`.
- Internet access to daily builds is required for `dump_tool_test.py`.
- Use at your own risk if not all of the tests pass!

## How it works

A service works in an infinite loop until it's stopped:

1. Downloads unknown crash reports from crash server in the internet:
- Gets the list of all reports and parses the report name to get initial report information.
- If the name fails to parse, the report is ignored.
- If information does not match requirements in config, the report is also ignored.
- If the report is already downloaded, it is ignored as well.
- Otherwise, the report is downloaded for further analysis.

2. Extracts signal and failure thread call stack:
- If it is a `dmp` file, dump tool is used to produce `cdb-bt`.
- All frames are formatted the same manner `module_name + '!' + function_name`.
- Frames with unresolved function name are dropped.
- All arguments including templates are removed from function signatures.
- Executable name is replaced with `Server` or `Client` accordingly.
- If there are more than 3 nx frames ('nx_', 'Qn', etc), other functions are replaced with `...`.
- If there are no own frames in windows `dmp` (`cdb-bt`), report is dropped.
- If there are no any resolved frames in linux `gdb-bt`, report is dropped as well.
- A hash from signal and stack is saved in local cache for further matching.

3. Groups reports by module+signal+stack and creates Jira issues with attachments:
- If there are more than 2 same reports, an issue is created with stack and other information.
- If the issue exists and is closed and new report versions are greater or equal `fix versions`
    field, issue is reopened otherwise reports are omitted.
- All new reports are attached and versions field is updated according to uploads. `Fix versions`
    field is updated according to config but greater than the attached report versions.
- If there are more attachments than config permits, the oldest ones are deleted.

## Usage

1. Create config, see example in `resources/monitor_example_config.yaml`.
2. Run monitor from terminal: `python monitor.py <config>`.
3. Keep an eye if it works, check logs from time to time:
- WARNING is to be reviewed. Usually indicates a broken distribution or report.
- ERROR is to be fixed. Indicates some problems.
- CRITICAL is to be fixed ASAP! Happens when analysis cycle is broken by exception.

# Crash Monitor Records Restorer

Linux and Windows Crash Monitor Records Restorer which restores records.json file.

## Requirements
See Crash Monitor & Analyzer Requirements.

## How it works
1. Fetches all crash issues from JIRA
2. Parses JIRA issues fields
3. Generates new records.json file

## Usage
Run restorer from terminal: `python restore_records_file.py <config>`.
`config` is the same file as the one  used for the Crash Monitor, but only 'logging' and
 'upload' groups are required.
