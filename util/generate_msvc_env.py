#!/usr/bin/env python3
"""
TODO: Launch vcvars64.bat automatically, after capturing the original env var names, and compare it
to the resulting env var set to automatically deduce the env vars needed for MSVC.
"""

import sys
import re
import os
from typing import List, Dict


vcvars_script = \
"\"C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat\""


env_var_names = [
    "CommandPromptType",
    "DevEnvDir",
    "ExtensionSdkDir",
    "Framework40Version",
    "FrameworkDIR64",
    "FrameworkDir",
    "FrameworkVersion64",
    "FrameworkVersion",
    "IFCPATH",
    "NETFXSDKDir",
    "Platform",
    "UCRTVersion",
    "UniversalCRTSdkDir",
    "VCIDEInstallDir",
    "VCINSTALLDIR",
    "VCToolsInstallDir",
    "VCToolsRedistDir",
    "VCToolsVersion",
    "VS160COMNTOOLS",
    "VSCMD_ARG_HOST_ARCH",
    "VSCMD_ARG_TGT_ARCH",
    "VSCMD_ARG_app_plat",
    "VSCMD_VER",
    "VSINSTALLDIR",
    "VisualStudioVersion",
    "WindowsSDKLibVersion",
    "WindowsSDKVersion",
    "WindowsSDK_ExecutablePath_x64",
    "WindowsSDK_ExecutablePath_x86",
    "WindowsSdkBinPath",
    "WindowsSdkDir",
    "WindowsSdkVerBinPath",
    "__DOTNET_ADD_64BIT",
    "__DOTNET_PREFERRED_BITNESS",
    "__VSCMD_script_err_count",
    "WindowsLibPath",
    "__VSCMD_PREINIT_PATH",
    "INCLUDE",
    "LIB",
    "LIBPATH",
]


def error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def escape_backslashes(s: str) -> str:
    return s.replace('\\', '\\\\')


def read_env_var(name: str) -> str:
    assert re.compile('^[A-Za-z_0-9]+$').match(name), f"Env var {name!r} has invalid name"
    value: str = os.getenv(name)
    if value is None:
        error(
f"""\
Env var {name!r} not found.

Run this script from a cmd.exe console after executing the following MSVC script:

{vcvars_script}

ATTENTION: Do not run this script in the Developer Command Prompt because it sets env vars for a
32-bit MSVC toolsrather than 64-bit.\
""")
            
    if value == "":
        error(f"Env var {name!r} is empty.")
    return value
    
        
def obtain_path_items() -> List[str]:
    path: str = read_env_var('PATH')
    items = path.split(';')
    if not items:
        error(f"PATH env var contains no items: {path!r}")
    
    items = [item[:-1] if item.endswith('\\') else item for item in items]  # Remove trailing `\`.
    items = [item.replace('\\\\', '\\') for item in items]  # Remove duplicate `\`.
    items = list(set(items))  # Remove duplicates.
    items.sort()

    # Keep only MSVC-related items.
    items = [item for item in items if (
        ("\\Microsoft SDKs\\" in item) or
        ("\\Microsoft Visual Studio\\" in item) or
        ("\\Windows Kits\\" in item) or
        ("\\Microsoft.NET\\" in item)
    )]

    return items


def build_path_lines_for_sh() -> str:
    result: str = ""
    for item in obtain_path_items():
            item = item.replace('C:', '/cygdrive/c');
            item = item.replace('\\', '/')
            result += ":" + item + "\\\n"
    
    result = result[:-1]  # Remove the last newline.
    return result
    
    
def generate_sh(env_vars: Dict[str, str], file) -> None:
    file.write(
f"""\
#!/bin/bash

# Env vars obtained via the MSVC script:
# {vcvars_script}

export PATH="$PATH\\
{build_path_lines_for_sh()}
"

""")

    for name, value in env_vars.items():
        file.write(f"export {name}=\"")
        components = value.split(';')
        if len(components) <= 1:
            file.write(f"{escape_backslashes(value)}\"\n")
        else:
            file.write("\\\n")
            for component in components:
                if component != "":
                    file.write(f"{escape_backslashes(component)};\\\n")  # some\\value;\
            file.write("\"\n")
   

def generate_bat(env_vars: Dict[str, str], out_file) -> None:
    assert False, "Generating .bat files not implemented yet"


def main():
    if len(sys.argv) != 2 or (len(sys.argv) > 1 and (
            sys.argv[1] == '-h' or sys.argv[1] == '--help' or sys.argv[1] == '/?')):
        print(
f"""\
This is a Windows tool which generates .bat or .sh (for Cygwin environment) script that sets
all needed env vars for 64-bit MSVC, like its script does:
{vcvars_script}

ATTENTION: The Developer Command Prompt would set the env vars for the 32-bit MSVC rather than
64-bit, as opposed to the above mentioned vcvars64.bat.

NOTE: This script only processes the hard-coded set of env vars, so it may need to be updated in
case some newer MSVC starts using a new env var.

Usage: {sys.argv[0]} msvc_env(.sh|.bat)\
""")
        sys.exit(0)
            
    out_filename = sys.argv[1]
    
    out_file = open(out_filename, "w", newline='\n')
    
    env_vars: Dict[str, str] = {}
    
    for env_var_name in env_var_names:
        env_vars[env_var_name] = read_env_var(env_var_name)
    
    if out_filename.endswith(".sh"):
        print(f"Generating .sh script {out_filename}")
        generate_sh(env_vars, out_file)
    elif out_filename.endswith(".bat"):
        print(f"Generating .bat script {out_filename}")
        generate_bat(env_vars, out_file)        
    else:
        error("Output file have one of the two suffixes: .sh or .bat")

    out_file.close()
    

if __name__ == '__main__':
    main()
