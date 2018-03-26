# Crash Analyzer

Linux and Windows crash report analyzer.


## Requirements

### Ubuntu

Limitations: DMP analisys is not avaliable.
```
apt install python3-pip             # Python 3 and it's PIP.
python3 -m pip install pyaml jira   #< Required modules.
```

### Windows

TODO: Dumptool refactor and integration + setup instructions.

## Run Tests
```
./crash_info_test.py      # Crash report stack extraction.
./external_api_test.py    # External server API (requires internet).
./monitor_test.py         # Monitoring system.
```

## Run Crash Analyzer & Monitor

1. Create config, see example in `resources/monitor_config.yaml`
2. Run monitor from terminal: `python3 monitor.py <config>`
3. Keep an eye if it works, check logs from time to time :)
