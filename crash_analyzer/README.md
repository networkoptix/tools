# Crash Analyzer

Linux and Windows crash report analyzer.


## Requirements

### Ubuntu

- Python 3 and it's PIP: `sudo apt install python3-pip`.
- Install required modules: `sudo python3 -m pip install -r requirements.txt`.

NOTE: DMP analisys is not avaliable.

### Windows

- Download and install python 3 from [https://www.python.org/]().
- Install required modules `python.exe -m pip install -r requirements.txt`.

TODO: Refactor and integration + setup instructions.

## Run Tests

- Run all unit and functional tests: `python3 -m pytest`.

NOTE: internet access is required for `external_api_test.py`.

## Run Crash Analyzer & Monitor

- Create config, see example in `resources/monitor_example_config.yaml`.
- Run monitor from terminal: `python3 monitor.py <config>`.
- Keep an eye if it works, check logs from time to time :)
