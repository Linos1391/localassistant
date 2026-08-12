"""OS tools that alternate for llama.cpp tools"""
from datetime import datetime
import re
import subprocess
from pathlib import Path
import glob
import sys
from threading import Thread

from haystack.tools.from_function import create_tool_from_function

class SystemTool():
    """Alternative for llama.cpp tools - For human in the loop."""
    def __init__(self, backup: bool) -> None:
        self.backup: bool = backup
    
    @staticmethod
    def get_datetime():
        """Get the current time on the local machine.

        Returns:
            str: The current time.
        """
        timezone = datetime.now().astimezone().tzname()
        return datetime.now().strftime(f"%Y-%m-%d %H:%M:%S {timezone}")

    @staticmethod
    def file_glob_search(
        glob_pattern: str,
        root_dir: str,
        recursive: bool = False,
        include_hidden: bool = False
    ):
        """Glob search through directory.

        Args:
            glob_pattern (str): The glob pattern to find.
            root_dir (str, optional): Target directory to glob search.
            recursive (bool, optional): Recursive through to file or not.
            include_hidden (bool, optional): To include hidden files or directories.
        """
        return glob.glob(glob_pattern, root_dir=root_dir, recursive=recursive,
                         include_hidden=include_hidden)

    @staticmethod
    def grep_search(file_path: str, pattern: str):
        """Grep search within a file.

        Args:
            file_path (str): Path to file.
            pattern (str): Pattern in regex.

        Returns:
            list[str]: List of result in format: 'Line ...: ...'
        """
        searches: list[str] = []
        with open(file_path, 'r', encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if re.search(pattern, line):
                    searches.append(f"Line {line_number}: {line.strip()}")
        return searches

    @staticmethod
    def read_file(file_path: str, start: int = 0, end: int | None = None):
        """Read the provided file. Functioning same as python slicing.

        Args:
            file_path (str): Path to file.
            start (int): Line to start, must be positive, default to the start of the file.
            end (int | None): Line to end, must be positive, default to None as the end of file.

        Returns:
            list[str]: File's content in multiples lines.
        """
        content: list[str] = []
        with open(file_path, 'r', encoding="utf-8") as file:
            for line_number, line in enumerate(file):
                if end and line_number >= end:
                    break
                if line_number >= start:
                    content.append(line.strip())
            file.close()
        return content

    def write_file(self, file_path: str, contents: list[str]) -> bool:
        """Write to the provided file the contents provided.

        Args:
            file_path (str): Path to file.
            contents (list[str]): List of line to write to file.

        Returns:
            bool: Return True if success.
        """
        path: Path = Path(file_path)
        if self.backup:
            path.copy(path.parent / f"{path.stem}.bak")

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'x', encoding="utf-8") as file:
            file.writelines(contents)
            file.close()
        return True

    def edit_file(self, file_path: str, contents: list[str],
                  start: int = 0, end: int | None = None) -> bool:
        """Edit to the provided file the contents provided. Functioning same as python slicing.

        Args:
            file_path (str): Path to file.
            contents (list[str]): List of line to write to file.
            start (int): Line to start, must be positive, default to the start of the file.
            end (int | None): Line to end, must be positive, default to None as the end of file.

        Returns:
            bool: Return True if success.
        """
        path: Path = Path(file_path)
        if self.backup:
            path.copy(path.parent / f"{path.stem}.bak")

        prefix_contents = suffix_contents = []
        if start:
            prefix_contents: list[str] = self.read_file(file_path, 0, start)
        if end:
            suffix_contents: list[str] = self.read_file(file_path, end)

        with open(file_path, 'w', encoding="utf-8") as file:
            for content in (prefix_contents, contents, suffix_contents):
                file.writelines(content)
            file.close()
        return True

    @staticmethod
    def _stream_output(proc: subprocess.Popen, output: list[str]):
        if proc.stdout:
            for line in proc.stdout:
                output.append(line)
                sys.stdout.flush()

    @staticmethod
    def exec_shell_command(commands: list[str], timeout: float | None = None):
        """Via Popen, execute shell commands.

        Args:
            commands (list[str]): Each of commands within Popen.
            timeout (float | None, optional): Timeout to escape, default to wait until finished.

        Returns:
            list[str]: Both stdout and stderr line by line.
        """

        proc = subprocess.Popen(
            commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        captured_output: list[str] = []

        t = Thread(target=SystemTool._stream_output, args=(proc, captured_output))
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            captured_output.append(f"[Timeout after {timeout}s] Terminating process...")
            proc.kill()
            proc.wait()
            t.join()
        return captured_output

    @staticmethod
    def get_tools(backup: bool = False):
        """Get the correlated tools."""
        system = SystemTool(backup=backup)
        return [
            create_tool_from_function(system.get_datetime),
            create_tool_from_function(system.file_glob_search),
            create_tool_from_function(system.grep_search),
            create_tool_from_function(system.read_file),
            create_tool_from_function(system.write_file),
            create_tool_from_function(system.edit_file),
            create_tool_from_function(system.exec_shell_command)
        ]
