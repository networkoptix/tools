# Crash Analyzer

Linux and Windows crash report analyzer.


## Requirements

### Ubuntu

1. Python 3 and it's PIP: `sudo apt install python3-pip`
2. Install required modules: `sudo python3 -m pip install -r requirements.txt`

NOTE: DMP analisys is not avaliable.

### Windows

1. Download and install python 3 from https://www.python.org
2. Install required modules `python.exe -m pip install -r requirements.txt`

TODO: Dumptool refactor and integration + setup instructions.

## Run Tests
```
./crash_info_test.py      # Crash report stack extraction.
./external_api_test.py    # External server API (requires internet).
./monitor_test.py         # Monitoring system.
```

## Run Crash Analyzer & Monitor

1. Create config, see example in `resources/monitor_example_config.yaml`
2. Run monitor from terminal: `python3 monitor.py <config>`
3. Keep an eye if it works, check logs from time to time :)
