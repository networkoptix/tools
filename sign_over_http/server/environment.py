import asyncio
from dataclasses import dataclass
import logging


@dataclass
class ExecuteCommandResult:
    stdout: str
    stderr: str
    returncode: int


async def execute_command_async(command, timeout=0):
    """Run command in subprocess.
     timeout is in seconds.
    """

    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    if timeout == 0:
        stdout, stderr = await process.communicate()
    else:
        # Wait for the subprocess to finish
        try:
            logging.debug(f"Running process with timeout {timeout}")
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            logging.warning("TimeoutError, killing process")
            process.terminate()
            return ExecuteCommandResult("", "Process killed by timeout", 1)

    return ExecuteCommandResult(
        stdout.decode().strip(),
        stderr.decode().strip(),
        process.returncode)
