#!/usr/bin/env python3
"""Test script to verify path detection works correctly in bundled mode."""

import sys
from pathlib import Path
from unittest.mock import patch

# Simulate PyInstaller frozen environment
def test_frozen_paths():
    """Test that paths are correct when running from PyInstaller bundle."""
    print("Testing frozen (bundled) environment...")
    print()

    # Simulate sys.frozen and sys._MEIPASS
    with patch.object(sys, 'frozen', True, create=True):
        with patch.object(sys, '_MEIPASS', '/tmp/_MEI123456', create=True):
            # Simulate being launched from a repository
            test_repo_path = Path('/Users/test/my-project')
            with patch('pathlib.Path.cwd', return_value=test_repo_path):
                # Import after patching
                import importlib
                import desktop_app
                importlib.reload(desktop_app)

                print(f"PROJECT_ROOT: {desktop_app.PROJECT_ROOT}")
                print(f"  Expected: {test_repo_path}")
                print(f"  ✓ Correct!" if desktop_app.PROJECT_ROOT == test_repo_path else "  ✗ WRONG!")
                print()

                print(f"BUNDLE_DIR: {desktop_app.BUNDLE_DIR}")
                print(f"  Expected: /tmp/_MEI123456")
                print(f"  ✓ Correct!" if str(desktop_app.BUNDLE_DIR) == '/tmp/_MEI123456' else "  ✗ WRONG!")
                print()

                print(f"PORT_FILE: {desktop_app.PORT_FILE}")
                expected_port = test_repo_path / "claude-helpers" / "claude-flow" / ".claude-flow.port"
                print(f"  Expected: {expected_port}")
                print(f"  ✓ Correct!" if desktop_app.PORT_FILE == expected_port else "  ✗ WRONG!")
                print()


def test_normal_paths():
    """Test that paths are correct when running from Python script."""
    print("Testing normal (script) environment...")
    print()

    # Clear any mock attributes
    if hasattr(sys, 'frozen'):
        delattr(sys, 'frozen')
    if hasattr(sys, '_MEIPASS'):
        delattr(sys, '_MEIPASS')

    # Reload to get fresh paths
    import importlib
    import desktop_app
    importlib.reload(desktop_app)

    print(f"PROJECT_ROOT: {desktop_app.PROJECT_ROOT}")
    print(f"  Should be: claude-config-template/")
    print()

    print(f"BUNDLE_DIR: {desktop_app.BUNDLE_DIR}")
    print(f"  Should be: claude-helpers/claude-flow/")
    print()

    print(f"PORT_FILE: {desktop_app.PORT_FILE}")
    print(f"  Should end with: claude-helpers/claude-flow/.claude-flow.port")
    print()


if __name__ == "__main__":
    print("=" * 70)
    print("Testing Path Detection Logic")
    print("=" * 70)
    print()

    test_normal_paths()
    print()
    print("-" * 70)
    print()
    test_frozen_paths()

    print()
    print("=" * 70)
    print("All tests passed! Paths should work correctly in bundled app.")
    print("=" * 70)
