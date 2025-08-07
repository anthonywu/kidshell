"""Data loading and management service."""

import json
import logging
import pathlib

from requests.structures import CaseInsensitiveDict

# Set up logging
logger = logging.getLogger(__name__)


class DataService:
    """Load and manage custom data files."""

    @staticmethod
    def load_data_files(data_dir: str = "./data") -> CaseInsensitiveDict:
        """
        Load data files from directory.

        Tries to parse any file as JSON regardless of extension.

        Args:
            data_dir: Directory containing data files

        Returns:
            CaseInsensitiveDict with combined data
        """
        combined_data = CaseInsensitiveDict()
        data_path = pathlib.Path(data_dir)

        if not data_path.exists():
            return combined_data

        # Try all files in the directory
        for data_file in data_path.iterdir():
            if data_file.is_file() and not data_file.name.startswith("."):
                try:
                    with data_file.open(encoding="utf-8") as f:
                        data_part = json.load(f)
                        if isinstance(data_part, dict):
                            combined_data.update(data_part)
                except json.JSONDecodeError:
                    # Not JSON format
                    if data_file.suffix not in [".json", ".data"]:
                        logger.debug(
                            f"File {data_file.name} is not JSON format. Support for other formats may be added later."
                        )
                except OSError as e:
                    logger.error(f"Error loading {data_file}: {e}")
                    continue

        # Create reverse lookup for string values
        reversed_data = CaseInsensitiveDict((v, k) for k, v in combined_data.items() if isinstance(v, str))
        combined_data.update(reversed_data)

        return combined_data

    @staticmethod
    def get_birthday_info(data: CaseInsensitiveDict) -> str | None:
        """
        Extract birthday information from data.

        Args:
            data: Loaded data dictionary

        Returns:
            Birthday string (yyyy.mm.dd) or None
        """
        return data.get("bday")
