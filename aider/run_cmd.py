import os
import platform
import subprocess
import sys
from io import BytesIO

import pexpect


def run_cmd(command, verbose=False):
    import sys

    if sys.stdin.isatty() and hasattr(pexpect, "spawn") and platform.system() != "Windows":
        return run_cmd_pexpect(command, verbose)

    return run_cmd_subprocess(command, verbose)


def run_cmd_subprocess(command, verbose=False):
    if verbose:
        print("run_cmd_subprocess:", command)
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            encoding=sys.stdout.encoding,
            errors="replace",
            bufsize=1,
            universal_newlines=True,
        )

        output = []
        for line in process.stdout:
            print(line, end="")  # Print the line in real-time
            output.append(line)  # Store the line for later use

        process.wait()
        return process.returncode, "".join(output)
    except Exception as e:
        return 1, str(e)


def run_cmd_pexpect(command, verbose=False):
    """
    Run a shell command interactively using pexpect, capturing all output.

    :param command: The command to run as a string.
    :param verbose: If True, print output in real-time.
    :return: A tuple containing (exit_status, output)
    """
    if verbose:
        print("run_cmd_pexpect:", command)

    output = BytesIO()

    def output_callback(b):
        output.write(b)
        return b

    try:
        # Use the SHELL environment variable, falling back to /bin/sh if not set
        shell = os.environ.get("SHELL", "/bin/sh")
        if verbose:
            print("shell:", shell)

        if os.path.exists(shell):
            # Use the shell from SHELL environment variable
            if verbose:
                print("pexpect.spawn with shell:", shell)
            child = pexpect.spawn(shell, args=["-c", command], encoding="utf-8")
        else:
            # Fall back to spawning the command directly
            if verbose:
                print("pexpect.spawn without shell")
            child = pexpect.spawn(command, encoding="utf-8")

        # Transfer control to the user, capturing output
        child.interact(output_filter=output_callback)

        # Wait for the command to finish and get the exit status
        child.close()
        return child.exitstatus, output.getvalue().decode("utf-8", errors="replace")

    except pexpect.ExceptionPexpect as e:
        error_msg = f"Error running command: {e}"
        return 1, error_msg
