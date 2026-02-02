#!/usr/bin/env python3
"""
Build C4 PlantUML diagrams to PNG/SVG format.

This script:
1. Finds all .puml files in the specified directory
2. Renders them to PNG and/or SVG using the plantuml command
3. Places output files in the same directory as source files
4. Supports both local plantuml installation and Docker fallback

Usage:
    python claude-helpers/build_c4_diagrams.py [OPTIONS]

Options:
    --format FORMAT    Output format: png, svg, or both (default: both)
    --dir PATH         Directory containing .puml files (default: memories/shared/research/c4-diagrams-plantuml)
    --docker           Force use of Docker instead of local plantuml
    --help             Show this help message
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_plantuml_installed() -> bool:
    """Check if plantuml command is available."""
    try:
        subprocess.run(
            ["plantuml", "-version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_docker_installed() -> bool:
    """Check if docker command is available."""
    try:
        subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def build_with_plantuml(puml_files: list[Path], output_format: str) -> bool:
    """Build diagrams using local plantuml installation."""
    format_flag = f"-t{output_format}"

    try:
        for puml_file in puml_files:
            print(f"Building {puml_file.name} to {output_format.upper()}...")
            subprocess.run(
                ["plantuml", format_flag, str(puml_file)],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"  ✅ {puml_file.stem}.{output_format}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error building diagrams: {e.stderr}", file=sys.stderr)
        return False


def build_with_docker(puml_dir: Path, puml_files: list[Path], output_format: str) -> bool:
    """Build diagrams using Docker plantuml image."""
    format_flag = f"-t{output_format}"

    try:
        for puml_file in puml_files:
            print(f"Building {puml_file.name} to {output_format.upper()} (Docker)...")
            subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{puml_dir.absolute()}:/data",
                    "plantuml/plantuml",
                    format_flag,
                    f"/data/{puml_file.name}",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"  ✅ {puml_file.stem}.{output_format}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error building diagrams with Docker: {e.stderr}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Build C4 PlantUML diagrams to PNG/SVG format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--format",
        choices=["png", "svg", "both"],
        default="svg",
        help="Output format (default: svg)",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("memories/shared/research/c4-diagrams-plantuml"),
        help="Directory containing .puml files",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Force use of Docker instead of local plantuml",
    )

    args = parser.parse_args()

    # Validate directory
    if not args.dir.exists():
        print(f"❌ Directory not found: {args.dir}", file=sys.stderr)
        return 1

    # Find all .puml files
    puml_files = list(args.dir.glob("*.puml"))
    if not puml_files:
        print(f"❌ No .puml files found in {args.dir}", file=sys.stderr)
        return 1

    print(f"Found {len(puml_files)} PlantUML file(s):")
    for pf in puml_files:
        print(f"  - {pf.name}")
    print()

    # Determine build method
    use_docker = args.docker
    if not use_docker and not check_plantuml_installed():
        print("⚠️  plantuml not found locally, checking for Docker...")
        if check_docker_installed():
            print("✅ Docker found, using Docker method")
            use_docker = True
        else:
            print("❌ Neither plantuml nor Docker found", file=sys.stderr)
            print("\nInstall options:", file=sys.stderr)
            print("  1. Install plantuml: brew install plantuml", file=sys.stderr)
            print("  2. Install Docker: https://docker.com", file=sys.stderr)
            return 1

    # Build diagrams
    formats = ["png", "svg"] if args.format == "both" else [args.format]
    success = True

    for fmt in formats:
        if use_docker:
            success = build_with_docker(args.dir, puml_files, fmt) and success
        else:
            success = build_with_plantuml(puml_files, fmt) and success

    if success:
        print(f"\n✅ Successfully built {len(puml_files)} diagram(s) to {', '.join(f.upper() for f in formats)}")
        print(f"\nOutput directory: {args.dir.absolute()}")
        return 0
    else:
        print("\n❌ Failed to build some diagrams", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
