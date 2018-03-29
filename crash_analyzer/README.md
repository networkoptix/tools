# Crash Analyzer

Linux and Windows crash report analyzer.


## Requirements

### Ubuntu

- Python 3 and it's PIP: `sudo apt install python3-pip`.
- Install required modules: `sudo python3 -m pip install -r requirements.txt`.
- NOTE: DMP analisys is not avaliable.

### Windows

- Download and install python 3 from [https://www.python.org/]().
- Install required modules `python.exe -m pip install -r requirements.txt`.
- Install dumtool requirements:
    - *7x* - Free ZIP extractor, download: [https://www.7-zip.org/]()
    - *dark* - Wix extractor, part of Wix Toolset: [http://http://wixtoolset.org/releases/]()
    - *cdb* - Windows debugger, part of Windows SDK: 
      [https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk]()
- Make sure all of them available in environment variable `PATH`.

## Run Tests

- Run all unit and functional tests: `python3 -m pytest`.
- NOTE: Internet access to crash server and JIRA is required for `external_api_test.py`.

## Use Dump Tool manually

- See: `python.exe dumptool.py -h`

## Run Crash Analyzer and Monitor

- Create config, see example in `resources/monitor_example_config.yaml`.
- Run monitor from terminal: `python3 monitor.py <config>`.
- Keep an eye if it works, check logs from time to time :)
