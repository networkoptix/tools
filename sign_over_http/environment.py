import subprocess
import os


def print_command(command):
    print('>> {0}'.format(subprocess.list2cmdline(command)))


def execute_command(command, verbose=False, working_directory=None):
    if verbose:
        print_command(command)
    try:
        current_directory = os.getcwd()
        if working_directory:
            os.chdir(working_directory)
        subprocess.check_output(command, stderr=subprocess.STDOUT)
        if working_directory:
            os.chdir(current_directory)
    except Exception as e:
        if not verbose:
            print_command(command)
        print("Error: {0}".format(e.output))
        raise


