:: Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

@echo off

if not "%DISABLE_NINJA_TOOL%"=="" GOTO SKIP_NINJA_TOOL_RUN
python "%~dp0\ninja_tool.py" --log-output --stack-trace
:SKIP_NINJA_TOOL_RUN

ninja %*
