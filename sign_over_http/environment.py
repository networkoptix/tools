import subprocess


def print_command(command):
    print('>> {0}'.format(subprocess.list2cmdline(command)))


def execute_command(command, verbose=False):
    if verbose:
        print_command(command)
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT)
    except Exception as e:
        if not verbose:
            print_command(command)
        print("Error: {0}".format(e.output))
        raise
