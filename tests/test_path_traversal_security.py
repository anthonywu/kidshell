"""
Test path traversal security in config module.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kidshell.core.config import ConfigManager, get_app_home_dir


class TestPathTraversalSecurity:
    """Test that path traversal attacks are properly prevented."""

    def test_edit_config_blocks_dotdot_traversal(self, capsys):
        """Test that .. sequences are blocked."""
        config = ConfigManager()

        # Try various path traversal attempts
        dangerous_paths = [
            "../../../etc/passwd",
            "../../sensitive.json",
            "../outside.json",
            "subdir/../../escape.json",
            "normal/../../../etc/hosts",
        ]

        for dangerous_path in dangerous_paths:
            config.edit_config(dangerous_path)
            captured = capsys.readouterr()
            assert "Error: Invalid file name" in captured.out
            assert ".." in captured.out

    def test_edit_config_blocks_absolute_paths(self, capsys):
        """Test that absolute paths are blocked."""
        config = ConfigManager()

        dangerous_paths = [
            "/etc/passwd",
            "/root/.ssh/id_rsa",
            "\\windows\\system32\\config.sys",
        ]

        for dangerous_path in dangerous_paths:
            config.edit_config(dangerous_path)
            captured = capsys.readouterr()
            assert "Error: Invalid file name" in captured.out

    def test_edit_config_allows_safe_names(self):
        """Test that legitimate file names are allowed."""
        config = ConfigManager()

        safe_names = [
            "config.json",
            "my-data.json",
            "family_config.json",
            "test123.json",
            "subdir/config.json",  # Subdirectories should be allowed
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            for safe_name in safe_names:
                # Create a mock file so it doesn't try to create it
                expected_path = config.data_dir / safe_name
                expected_path.parent.mkdir(parents=True, exist_ok=True)
                expected_path.write_text("{}")

                # Should not raise an error or print error message
                with patch("builtins.print") as mock_print:
                    config.edit_config(safe_name)
                    # Check that no error message was printed
                    for call in mock_print.call_args_list:
                        if call[0]:
                            assert "Error:" not in str(call[0][0])

                # Clean up
                if expected_path.exists():
                    expected_path.unlink()
                if expected_path.parent != config.data_dir and expected_path.parent.exists():
                    expected_path.parent.rmdir()

    def test_edit_config_symlink_escape_attempt(self, capsys):
        """Test that symlinks cannot be used to escape the data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a custom ConfigManager with a temp data dir
            config = ConfigManager()
            config.data_dir = Path(tmpdir) / "data"
            config.data_dir.mkdir(parents=True, exist_ok=True)

            # Create a symlink that points outside
            outside_dir = Path(tmpdir) / "outside"
            outside_dir.mkdir(parents=True, exist_ok=True)

            symlink_path = config.data_dir / "escape_link"
            try:
                symlink_path.symlink_to(outside_dir)

                # Try to edit a file through the symlink
                config.edit_config("escape_link/../../sensitive.json")
                captured = capsys.readouterr()

                # Should be blocked
                assert "Error:" in captured.out
            except OSError:
                # Skip test if symlinks aren't supported
                pytest.skip("Symlinks not supported on this system")
            finally:
                if symlink_path.exists():
                    symlink_path.unlink()

    def test_resolve_path_validation(self, capsys):
        """Test that path resolution properly validates containment."""
        config = ConfigManager()

        # Test edge cases with path resolution
        tricky_paths = [
            ".",  # Current directory
            "./",  # Current directory with separator
            "subdir/.",  # Subdirectory with dot
            "subdir/./file.json",  # Path with embedded dot
        ]

        for path in tricky_paths:
            # These should be allowed as they stay within data_dir
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                # Create the file so it exists
                full_path = config.data_dir / path
                if path in [".", "./"]:
                    # Skip directory paths
                    continue

                full_path.parent.mkdir(parents=True, exist_ok=True)
                if not full_path.exists():
                    full_path.write_text("{}")

                config.edit_config(path)
                captured = capsys.readouterr()

                # Should not have errors for these safe paths
                if "Error:" in captured.out:
                    # Only error we'd expect is no editor found
                    assert "No editor found" in captured.out

                # Clean up
                if full_path.exists() and full_path.is_file():
                    full_path.unlink()

    def test_kidshell_home_override(self, monkeypatch):
        """Test that KIDSHELL_HOME overrides default ~/.kidshell base path."""
        custom_home = "/tmp/kidshell-test-home"
        monkeypatch.setenv("KIDSHELL_HOME", custom_home)
        assert get_app_home_dir() == Path(custom_home)

    def test_config_info_exposes_base_and_history(self):
        """Test config info includes base, history, and profile paths."""
        config = ConfigManager()
        info = config.get_config_info()
        assert "base_dir" in info
        assert "history_file" in info
        assert "profile_file" in info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
