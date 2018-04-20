# Crash Analyzer

Linux and Windows Crash Report Analyzer

## Requirements

### Ubuntu

- Python 3 and it's PIP: `sudo apt install python3-pip`
- Install required modules: `sudo python3 -m pip install -r requirements.txt`
- NOTE: DMP analisys is not avaliable

### Windows

- Download and install Python 3: <https://www.python.org>
- Install required modules: `python -m pip install -r requirements.txt`
- Install dump tool requirements:
    - *7x* - Free ZIP extractor, download: <https://www.7-zip.org>
    - *dark* - Wix extractor, part of Wix Toolset: <http://wixtoolset.org/releases>
    - *cdb* - Windows Debugger (for report generation), part of Windows SDK: 
      <https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk>
    - *devenv* - Visual Studio (for developers only): <https://www.visualstudio.com>
- Make sure all of them available in environment variable `PATH`:
    - `C:\Program Files\7-Zip`
    - `C:\Program Files (x86)\WiX Toolset v3.11\bin`
    - `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64`
    - `C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\Common7\IDE`

## Run Tests

- Run all unit and functional tests: `python -m pytest`.
- NOTE: Normally all tests take up to 5 minutes to pass.
- NOTE: Internet access to crash server and JIRA is required for `external_api_test.py`.

## Use Dump Tool manually

- See: `python dump_tool.py -h`

## Run Crash Analyzer and Monitor

- Create config, see example in `resources/monitor_example_config.yaml`.
- Run monitor from terminal: `python monitor.py <config>`.
- Keep an eye if it works, check logs from time to time :)
