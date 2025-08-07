"""
Entry point for KidShell Textual web app.
Run this with textual-web to serve KidShell in a browser.
"""

import os

from kidshell.frontends.textual_app import KidShellTextualApp


def main():
    """Run the Textual app."""
    if "KIDSHELL_PREVIEW" in os.environ:
        app = KidShellTextualApp()
        app.run()
    else:
        print("⏳ Coming soon!")


if __name__ == "__main__":
    main()
