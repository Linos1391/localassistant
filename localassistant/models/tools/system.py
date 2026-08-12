"""OS tools that alternate for llama.cpp tools"""
from datetime import datetime
import re
import glob

from haystack.tools.from_function import create_tool_from_function

# TODO - exec_shell_command, write_file, edit_file - After Human in the loop done.

class SystemTool():
    """Alternative for llama.cpp tools - For human in the loop."""
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
    def read_file(file_path: str):
        """Read the provided file.

        Args:
            file_path (str): Path to file.

        Returns:
            str: File's content.
        """
        content: str = ""
        with open(file_path, 'r', encoding="utf-8") as file:
            content = file.read()
            file.close()
        return content

    @staticmethod
    def get_tools():
        """Get the correlated tools."""
        system = SystemTool()
        return [
            create_tool_from_function(system.get_datetime),
            create_tool_from_function(system.file_glob_search),
            create_tool_from_function(system.grep_search),
            create_tool_from_function(system.read_file)
        ]
