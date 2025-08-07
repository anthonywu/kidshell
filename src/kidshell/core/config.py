"""Configuration management using platformdirs."""

import json
import logging
import os
import pathlib
import subprocess
import sys
from typing import Any

import platformdirs
from requests.structures import CaseInsensitiveDict

# Set up logging
logger = logging.getLogger(__name__)


class ConfigManager:
    """Manage kidshell configuration using platform-specific directories."""

    def __init__(self, app_name: str = "kidshell"):
        """
        Initialize configuration manager.

        Args:
            app_name: Application name for directory creation
        """
        self.app_name = app_name
        self.config_dir = pathlib.Path(platformdirs.user_config_dir(app_name))
        self.data_dir = pathlib.Path(platformdirs.user_data_dir(app_name))

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Default config file
        self.config_file = self.config_dir / "config.json"

        # Example data file for custom lookups
        self.example_data_file = self.data_dir / "example.json"

        # Initialize with example if needed
        self._initialize_example_data()

    def _initialize_example_data(self):
        """Create example data file if it doesn't exist."""
        if not self.example_data_file.exists():
            example_data = {
                "title": "Example Custom Data",
                "description": "Add your custom input->output mappings here",
                "hello": "👋",
                "world": "🌍",
                "cat": "🐱",
                "dog": "🐕",
            }
            self.example_data_file.write_text(json.dumps(example_data, indent=2))

    def load_data_files(self) -> CaseInsensitiveDict:
        """
        Load all data files from the data directory.

        Tries to parse any file as JSON regardless of extension.

        Returns:
            CaseInsensitiveDict with combined data from all files
        """
        combined_data = CaseInsensitiveDict()

        # Try all files in the data directory
        for data_file in self.data_dir.iterdir():
            if data_file.is_file() and not data_file.name.startswith("."):
                try:
                    with data_file.open(encoding="utf-8") as f:
                        data_part = json.load(f)
                        if isinstance(data_part, dict):
                            combined_data.update(data_part)
                            if "title" in data_part:
                                logger.debug(f"Loaded: {data_part['title']} from {data_file.name}")
                except json.JSONDecodeError:
                    # Not JSON format
                    if data_file.suffix not in [".json", ".data"]:
                        logger.debug(
                            f"File {data_file.name} is not JSON format. Support for other formats may be added later."
                        )
                except OSError as e:
                    logger.error(f"Error reading {data_file}: {e}")
                    continue

        # Create reverse lookup for string values
        reversed_data = CaseInsensitiveDict((v, k) for k, v in combined_data.items() if isinstance(v, str))
        combined_data.update(reversed_data)

        return combined_data

    def edit_config(self, file_name: str | None = None):
        """
        Open configuration file in the default editor.

        Args:
            file_name: Specific file to edit, or None for default example.json
        """
        if file_name:
            # Validate file name to prevent path traversal
            # Check for .., absolute paths, and Windows drive letters
            if (
                ".." in file_name
                or file_name.startswith(("/", "\\"))
                or (len(file_name) >= 2 and file_name[1] == ":" and file_name[0].isalpha())
            ):
                print(
                    f"Error: Invalid file name '{file_name}'. File names cannot contain '..', start with path separators, or contain drive letters."
                )
                return

            # Additional validation: ensure the resolved path stays within data_dir
            file_path = self.data_dir / file_name
            try:
                # Resolve to absolute paths and check containment
                resolved_path = file_path.resolve()
                data_dir_resolved = self.data_dir.resolve()

                # Use try/except with relative_to for robust path containment check
                # This works correctly across all platforms and handles edge cases
                try:
                    # If this succeeds, resolved_path is within data_dir_resolved
                    resolved_path.relative_to(data_dir_resolved)
                except ValueError:
                    # Path is outside the data directory
                    print(f"Error: File path '{file_name}' would escape the data directory.")
                    return
            except (OSError, RuntimeError) as e:
                # OSError: file system errors, RuntimeError: symlink loops
                print(f"Error: Invalid file path '{file_name}': {e}")
                return
        else:
            file_path = self.example_data_file

        # Ensure file exists
        if not file_path.exists():
            # Create parent directories if needed (only for files within data_dir)
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                # Create empty JSON file for any extension
                file_path.write_text("{}")
            except (OSError, PermissionError) as e:
                print(f"Error: Could not create file '{file_path.name}': {e}")
                return

        # Get editor from environment
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", None))

        if not editor:
            # Try common editors
            for try_editor in ["nano", "vim", "vi", "emacs", "code", "subl"]:
                if subprocess.run(["which", try_editor], check=False, capture_output=True, text=True).returncode == 0:
                    editor = try_editor
                    break

        if not editor:
            print("No editor found. Please set EDITOR environment variable.")
            print(f"Config location: {file_path}")
            return

        print(f"Opening {file_path} with {editor}...")
        try:
            subprocess.run([editor, str(file_path)], check=False)
        except Exception as e:
            print(f"Error opening editor: {e}")
            print(f"Config location: {file_path}")

    def list_data_files(self) -> list[pathlib.Path]:
        """
        List all data files in the data directory.

        Returns:
            List of data file paths
        """
        return [f for f in self.data_dir.iterdir() if f.is_file() and not f.name.startswith(".")]

    def get_config_info(self) -> dict[str, Any]:
        """
        Get information about configuration directories.

        Returns:
            Dictionary with config paths and info
        """
        return {
            "config_dir": str(self.config_dir),
            "data_dir": str(self.data_dir),
            "data_files": [f.name for f in self.list_data_files()],
            "platform": sys.platform,
        }


# Global instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get or create the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
