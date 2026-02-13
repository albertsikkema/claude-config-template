#!/usr/bin/env python3
"""
fetch-docs.py
Simple documentation fetcher from context7.com

Usage:
    python3 scripts/fetch-docs.py discover           # List packages from project files
    python3 scripts/fetch-docs.py search <query>     # Search and return top 5 results
    python3 scripts/fetch-docs.py get <project> <name>  # Fetch specific project docs
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Configuration
CONTEXT7_API = "https://context7.com/api/search"
DOCS_DIR = "memories/technical_docs"


def http_get(url: str, timeout: int = 10) -> Optional[str]:
    """Make HTTP GET request."""
    try:
        req = Request(url, headers={'User-Agent': 'WorkflowManager-DocFetcher/2.0'})
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8')
    except (HTTPError, URLError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def discover_packages() -> Dict[str, Dict[str, str]]:
    """Discover packages from project configuration files.

    Returns dict of {package_name: {'version': str, 'source': str}}
    """
    packages = {}

    # Check package.json (JavaScript/TypeScript)
    package_json = Path("frontend/package.json")
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding='utf-8'))

            # Combine dependencies and devDependencies
            all_deps = {}
            all_deps.update(data.get('dependencies', {}))
            all_deps.update(data.get('devDependencies', {}))

            for pkg, version in all_deps.items():
                # Clean package name (remove @ and scope)
                clean_name = pkg.lstrip('@').split('/')[-1]
                packages[clean_name] = {
                    'version': version,
                    'source': 'package.json',
                    'original': pkg
                }
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not parse package.json: {e}", file=sys.stderr)

    # Check go.mod (Go)
    go_mod = Path("go.mod")
    if go_mod.exists():
        try:
            content = go_mod.read_text(encoding='utf-8')
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('//') and not line.startswith('module'):
                    # Match lines like: github.com/wailsapp/wails/v2 v2.10.2
                    match = re.match(r'([^\s]+)\s+v?([^\s]+)', line)
                    if match:
                        pkg_path, version = match.groups()
                        if '/' in pkg_path and 'indirect' not in version:
                            # Use last part of path as package name
                            pkg_name = pkg_path.split('/')[-1]
                            # Remove version suffix (e.g., /v2)
                            pkg_name = re.sub(r'/v\d+$', '', pkg_name)
                            if pkg_name:
                                packages[pkg_name] = {
                                    'version': version,
                                    'source': 'go.mod',
                                    'original': pkg_path
                                }
        except IOError as e:
            print(f"Warning: Could not read go.mod: {e}", file=sys.stderr)

    # Check pyproject.toml (Python)
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding='utf-8')

            # Simple regex-based parsing (good enough for dependencies)
            # Matches: package = "^1.0.0" or package = {version = "^1.0.0"}
            dep_pattern = r'^\s*([a-zA-Z0-9_-]+)\s*=\s*(?:"([^"]+)"|{[^}]*version\s*=\s*"([^"]+)")'

            in_dependencies = False
            for line in content.split('\n'):
                # Track if we're in dependencies section
                if re.match(r'^\[tool\.poetry\.dependencies\]|\[project\.dependencies\]', line):
                    in_dependencies = True
                    continue
                elif line.startswith('['):
                    in_dependencies = False
                    continue

                if in_dependencies:
                    match = re.match(dep_pattern, line)
                    if match:
                        pkg_name = match.group(1)
                        version = match.group(2) or match.group(3)
                        if pkg_name and pkg_name != 'python':
                            packages[pkg_name] = {
                                'version': version or 'unknown',
                                'source': 'pyproject.toml',
                                'original': pkg_name
                            }
        except IOError as e:
            print(f"Warning: Could not read pyproject.toml: {e}", file=sys.stderr)

    return packages


def search_context7(query: str, limit: int = 5) -> Optional[List[Dict]]:
    """Search context7 for a package and return top N results.

    Returns list of dicts with simplified info.
    """
    from urllib.parse import quote
    data = http_get(f"{CONTEXT7_API}?query={quote(query)}")
    if not data:
        return None

    try:
        response = json.loads(data)
        results = response.get('results', [])

        # Return top N results with simplified info
        simplified = []
        for i, result in enumerate(results[:limit]):
            settings = result.get('settings', {})
            simplified.append({
                'rank': i + 1,
                'project': settings.get('project', ''),
                'title': settings.get('title', ''),
                'description': settings.get('description', ''),
                'stars': settings.get('stars', 0),
                'trustScore': settings.get('trustScore', 0),
                'vip': settings.get('vip', False),
                'type': settings.get('type', ''),
                'url': f"https://context7.com{settings.get('project', '')}/llms.txt"
            })

        return simplified
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}", file=sys.stderr)
        return None


def get_docs(project_path: str, package_name: str, overwrite: bool = False) -> bool:
    """Fetch llms.txt for a specific project path."""
    url = f"https://context7.com{project_path}/llms.txt"
    output_file = Path(DOCS_DIR) / f"{package_name}.md"

    # Check if file exists
    if output_file.exists() and not overwrite:
        print(f"File already exists: {output_file}", file=sys.stderr)
        print("Use --overwrite flag to replace", file=sys.stderr)
        return False

    content = http_get(url, timeout=30)
    if not content or content.strip() == "Not Found":
        print(f"Failed to fetch documentation from {url}", file=sys.stderr)
        return False

    # Add metadata header
    current_date = datetime.now().strftime('%Y-%m-%d')
    output_content = f"""# {package_name}

**Source**: context7.com{project_path}
**Last Updated**: {current_date}
**URL**: {url}

---

{content}
"""

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(output_content, encoding='utf-8')

    return True


def cmd_discover() -> int:
    """Discover and output packages as JSON."""
    packages = discover_packages()

    # Output as JSON for easy parsing
    output = {
        'total': len(packages),
        'packages': packages
    }

    print(json.dumps(output, indent=2))
    return 0


def cmd_search(query: str, limit: int = 5) -> int:
    """Search for a package and output top N results as JSON."""
    results = search_context7(query, limit)

    if results is None:
        print(json.dumps({'error': 'Search failed'}), file=sys.stderr)
        return 1

    if not results:
        print(json.dumps({'error': 'No results found'}), file=sys.stderr)
        return 1

    output = {
        'query': query,
        'count': len(results),
        'results': results
    }

    print(json.dumps(output, indent=2))
    return 0


def cmd_get(project_path: str, package_name: str, overwrite: bool = False) -> int:
    """Get documentation for a specific project."""
    if not project_path.startswith('/'):
        project_path = '/' + project_path

    output_file = Path(DOCS_DIR) / f"{package_name}.md"

    if get_docs(project_path, package_name, overwrite):
        result = {
            'success': True,
            'project': project_path,
            'package': package_name,
            'file': str(output_file)
        }
        print(json.dumps(result, indent=2))
        return 0
    else:
        result = {
            'success': False,
            'project': project_path,
            'package': package_name
        }
        print(json.dumps(result, indent=2))
        return 1


def show_help():
    """Show help message."""
    help_text = """
Context7 Documentation Fetcher v2.0

USAGE:
    python3 scripts/fetch-docs.py <command> [args]

COMMANDS:
    discover                    List all packages from project files (JSON output)
    search <query> [limit]      Search context7 and return top N results (default: 5)
    get <project> <name> [--overwrite]  Fetch docs for specific project

EXAMPLES:
    # Discover packages
    python3 scripts/fetch-docs.py discover

    # Search for a package (returns top 5 as JSON)
    python3 scripts/fetch-docs.py search svelte

    # Search with custom limit
    python3 scripts/fetch-docs.py search vite 10

    # Get docs for specific project
    python3 scripts/fetch-docs.py get /sveltejs/svelte svelte

    # Get docs and overwrite existing file
    python3 scripts/fetch-docs.py get /sveltejs/kit sveltekit --overwrite

OUTPUT:
    All commands output JSON for easy parsing by other tools.
"""
    print(help_text)


def main() -> int:
    """Main entry point."""
    # Ensure we're in project root
    if Path(__file__).parent.name == 'scripts':
        project_root = Path(__file__).parent.parent
        os.chdir(project_root)

    if len(sys.argv) < 2:
        show_help()
        return 1

    command = sys.argv[1].lower()

    if command in ['help', '--help', '-h']:
        show_help()
        return 0

    elif command == 'discover':
        return cmd_discover()

    elif command == 'search':
        if len(sys.argv) < 3:
            print(json.dumps({'error': 'search requires a query argument'}), file=sys.stderr)
            return 1
        query = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        return cmd_search(query, limit)

    elif command == 'get':
        if len(sys.argv) < 4:
            print(json.dumps({'error': 'get requires <project> and <name> arguments'}), file=sys.stderr)
            return 1
        project_path = sys.argv[2]
        package_name = sys.argv[3]
        overwrite = '--overwrite' in sys.argv or '-f' in sys.argv
        return cmd_get(project_path, package_name, overwrite)

    else:
        print(json.dumps({'error': f"Unknown command: {command}"}), file=sys.stderr)
        show_help()
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(json.dumps({'error': 'Interrupted by user'}), file=sys.stderr)
        sys.exit(130)
