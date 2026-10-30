"""Adds a Voice Studio icon to your desktop and app menu. Run: python create_shortcut.py"""
import sys

from app import shortcut

if __name__ == "__main__":
    try:
        result = shortcut.create()
    except Exception as exc:
        print(f"Could not create the shortcut: {exc}")
        sys.exit(1)
    print("Shortcut created:")
    for path in result["created"]:
        print("  ", path)
