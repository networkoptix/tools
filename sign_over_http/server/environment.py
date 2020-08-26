import asyncio
import logging
import os

from dataclasses import dataclass
from pathlib import Path


CONFIG_PATH = Path(os.path.realpath(__file__)).parent / 'config'


@dataclass
class ExecuteCommandResult:
    stdout: bytes
    stderr: bytes
    returncode: int

    def __str__(self):
        text = str(self.returncode)
        if self.stdout:
            text += '\n' + self.stdout.decode().strip()
        if self.stderr:
            text += '\n' + self.stderr.decode().strip()
        return text

    def success(self):
        return self.returncode == 0


async def execute_command_async(command, timeout_sec=0):
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        if timeout_sec == 0:
            stdout, stderr = await process.communicate()
        else:
            # Wait for the subprocess to finish
            logging.debug(f"Running process with timeout {timeout_sec} seconds")
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_sec)

    except FileNotFoundError as e:
        logging.warning(e)
        return ExecuteCommandResult(b"", b"File was not found", 1)

    except asyncio.TimeoutError:
        logging.warning("TimeoutError, killing process")
        process.terminate()
        return ExecuteCommandResult(b"", b"Process killed by timeout", 2)

    return ExecuteCommandResult(stdout, stderr, process.returncode)


