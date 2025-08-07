"""CLI command handler for configuration management."""

import argparse
import sys

from kidshell.core.config import get_config_manager


def config_command(args: list[str] | None = None):
    """
    Handle the 'kidshell config' command.

    Args:
        args: Command line arguments
    """
    parser = argparse.ArgumentParser(
        prog="kidshell config",
        description="Manage kidshell configuration files",
    )

    subparsers = parser.add_subparsers(dest="command", help="Config commands")

    # Edit command
    edit_parser = subparsers.add_parser("edit", help="Edit a configuration file")
    edit_parser.add_argument(
        "file",
        nargs="?",
        default="example.json",
        help="File to edit (default: example.json)",
    )

    # List command
    subparsers.add_parser("list", help="List all data files")

    # Info command
    subparsers.add_parser("info", help="Show configuration paths")

    # Parse arguments
    if args is None:
        args = sys.argv[2:] if len(sys.argv) > 2 else []

    parsed_args = parser.parse_args(args)

    config_manager = get_config_manager()

    # Default to edit if no subcommand
    if not parsed_args.command:
        config_manager.edit_config()
        return

    if parsed_args.command == "edit":
        config_manager.edit_config(parsed_args.file)
    elif parsed_args.command == "list":
        files = config_manager.list_data_files()
        if files:
            print("Data files:")
            for f in files:
                print(f"  - {f.name}")
        else:
            print("No data files found.")
            print(f"Create them in: {config_manager.data_dir}")
    elif parsed_args.command == "info":
        info = config_manager.get_config_info()
        print("Configuration directories:")
        print(f"  Config: {info['config_dir']}")
        print(f"  Data:   {info['data_dir']}")
        if info["data_files"]:
            print("\nData files:")
            for f in info["data_files"]:
                print(f"  - {f}")


def main():
    """Main entry point for kidshell config command."""
    config_command()


if __name__ == "__main__":
    main()
