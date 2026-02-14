import os
import re
import json
import argparse
import sys
from datetime import datetime
from collections import defaultdict

# Directories to skip during scanning
SKIP_DIRS = {
    '.git', '.svn', '.hg',
    'node_modules',
    '.venv', 'venv', 'env', '.env',
    '__pycache__', '.pytest_cache',
    'dist', 'build',
    '.claude', 'memories',
    '.idea', '.vscode',
}


def find_bruno_collections(directory):
    """Walk tree looking for bruno.json files, skip ignored directories.

    Returns list of dicts with 'path' (directory containing bruno.json)
    and 'config' (parsed bruno.json content).
    """
    collections = []
    abs_dir = os.path.abspath(directory)

    for root, dirs, files in os.walk(abs_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        if 'bruno.json' in files:
            config_path = os.path.join(root, 'bruno.json')
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Could not parse {config_path}: {e}",
                      file=sys.stderr)
                config = {}

            collections.append({
                'path': root,
                'config': config,
            })
            # Don't descend into this collection (nested collections unlikely)
            dirs.clear()

    return collections


def parse_bru_file(file_path):
    """Regex-based extraction of request info from a .bru file.

    Returns dict with: name, method, url, has_tests, has_asserts,
    body_type, has_pre_script, has_post_script.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        return None

    info = {
        'name': os.path.splitext(os.path.basename(file_path))[0],
        'method': None,
        'url': None,
        'has_tests': False,
        'has_asserts': False,
        'body_type': None,
        'has_pre_script': False,
        'has_post_script': False,
    }

    # Extract name from meta block: meta { name: Something }
    meta_match = re.search(
        r'meta\s*\{[^}]*?name:\s*(.+?)[\n,}]', content)
    if meta_match:
        info['name'] = meta_match.group(1).strip()

    # Extract HTTP method and URL from request blocks like:
    # get { url: https://... }  or  post { url: {{baseUrl}}/path }
    method_match = re.search(
        r'^(get|post|put|patch|delete|head|options)\s*\{',
        content, re.MULTILINE | re.IGNORECASE)
    if method_match:
        info['method'] = method_match.group(1).upper()

    url_match = re.search(
        r'url:\s*(.+)', content)
    if url_match:
        info['url'] = url_match.group(1).strip()

    # Check for tests block
    if re.search(r'^tests\s*\{', content, re.MULTILINE):
        info['has_tests'] = True

    # Check for assert block
    if re.search(r'^assert\s*\{', content, re.MULTILINE):
        info['has_asserts'] = True

    # Detect body type
    for body_type in ('body:json', 'body:xml', 'body:form-urlencoded',
                      'body:multipart-form', 'body:text', 'body:graphql'):
        if re.search(rf'^{re.escape(body_type)}\s*\{{', content,
                     re.MULTILINE):
            info['body_type'] = body_type.replace('body:', '')
            break

    # Pre/post request scripts
    if re.search(r'^script:pre-request\s*\{', content, re.MULTILINE):
        info['has_pre_script'] = True
    if re.search(r'^script:post-response\s*\{', content, re.MULTILINE):
        info['has_post_script'] = True

    return info


def find_environment_files(collection_path):
    """Parse environments/*.bru for variable names.

    Returns list of dicts with 'name', 'variables' (list of var names),
    and 'file' (relative path).
    """
    env_dir = os.path.join(collection_path, 'environments')
    if not os.path.isdir(env_dir):
        return []

    environments = []
    for fname in sorted(os.listdir(env_dir)):
        if not fname.endswith('.bru'):
            continue
        env_path = os.path.join(env_dir, fname)
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except OSError:
            continue

        env_name = os.path.splitext(fname)[0]
        # Extract variable names from "vars { key: value }" blocks
        variables = []
        vars_match = re.search(
            r'vars\s*\{(.*?)\}', content, re.DOTALL)
        if vars_match:
            for line in vars_match.group(1).strip().splitlines():
                line = line.strip()
                if ':' in line and not line.startswith('//'):
                    var_name = line.split(':')[0].strip().lstrip('~')
                    if var_name:
                        variables.append(var_name)

        environments.append({
            'name': env_name,
            'variables': variables,
            'file': os.path.join('environments', fname),
        })

    return environments


def scan_collection(collection_path, base_directory):
    """Scan a Bruno collection directory for all .bru request files.

    Groups requests by subfolder and collects stats.

    Returns dict with:
      'name': collection name from bruno.json
      'rel_path': relative path from base_directory
      'environments': list from find_environment_files
      'folders': dict mapping folder_name -> list of request dicts
      'total_requests': int
      'tested_requests': int
      'untested': list of untested request dicts with file paths
    """
    # Read collection name from bruno.json
    config_path = os.path.join(collection_path, 'bruno.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        collection_name = config.get('name', os.path.basename(collection_path))
    except (json.JSONDecodeError, OSError):
        collection_name = os.path.basename(collection_path)

    rel_path = os.path.relpath(collection_path, os.path.abspath(base_directory))
    environments = find_environment_files(collection_path)

    # Find all .bru files (excluding environments)
    folders = defaultdict(list)
    untested = []
    total = 0
    tested = 0

    for root, dirs, files in os.walk(collection_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        # Skip environments folder — those aren't requests
        if os.path.basename(root) == 'environments':
            continue

        bru_files = sorted(f for f in files if f.endswith('.bru'))
        for bru_file in bru_files:
            bru_path = os.path.join(root, bru_file)
            info = parse_bru_file(bru_path)
            if info is None or info['method'] is None:
                continue  # Skip non-request .bru files (e.g., env files)

            # Determine folder name relative to collection root
            rel_to_collection = os.path.relpath(root, collection_path)
            if rel_to_collection == '.':
                folder_name = '(root)'
            else:
                folder_name = rel_to_collection

            info['file'] = os.path.relpath(bru_path,
                                           os.path.abspath(base_directory))
            folders[folder_name].append(info)
            total += 1

            has_testing = info['has_tests'] or info['has_asserts']
            if has_testing:
                tested += 1
            else:
                untested.append(info)

    return {
        'name': collection_name,
        'rel_path': rel_path,
        'environments': environments,
        'folders': dict(folders),
        'total_requests': total,
        'tested_requests': tested,
        'untested': untested,
    }


def generate_markdown(collections_data, output_file, directory):
    """Write the API testing tools index as Markdown."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# API Testing Tools Index\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                f" | Regenerate with `/index_codebase`*\n\n")

        if not collections_data:
            f.write("*No API testing tools (Bruno collections) found.*\n")
            print(f"Markdown documentation generated: {output_file}")
            return

        # Summary
        total_requests = sum(c['total_requests'] for c in collections_data)
        total_tested = sum(c['tested_requests'] for c in collections_data)
        untested_count = total_requests - total_tested
        pct = (total_tested * 100 // total_requests) if total_requests else 0

        f.write("## Summary\n")
        f.write(f"- **Tool**: Bruno\n")
        f.write(f"- **Collections**: {len(collections_data)} found")
        if len(collections_data) == 1:
            f.write(f" at `{collections_data[0]['rel_path']}`")
        f.write("\n")
        f.write(f"- **Total Requests**: {total_requests}"
                f" | **With Tests**: {total_tested} ({pct}%)"
                f" | **Without Tests**: {untested_count}\n\n")

        # Per-collection details
        for coll in collections_data:
            f.write(f"## Collection: {coll['name']}"
                    f" (`{coll['rel_path']}`)\n\n")

            # Environments
            if coll['environments']:
                f.write("### Environments\n")
                for env in coll['environments']:
                    var_count = len(env['variables'])
                    env_file = os.path.join(coll['rel_path'], env['file'])
                    f.write(f"- `{env['name']}` — {var_count} variables"
                            f" (`{env_file}`)\n")
                f.write("\n")

            # Requests by folder
            if coll['folders']:
                f.write("### Requests by Folder\n\n")
                for folder_name in sorted(coll['folders'].keys()):
                    requests = coll['folders'][folder_name]
                    f.write(f"#### {folder_name}/\n")
                    f.write("| Method | Name | URL | Tests |\n")
                    f.write("|--------|------|-----|-------|\n")
                    for req in requests:
                        has_testing = 'yes' if (req['has_tests']
                                                or req['has_asserts']) else 'no'
                        url = req['url'] or '—'
                        f.write(f"| {req['method']} | {req['name']}"
                                f" | {url} | {has_testing} |\n")
                    f.write("\n")

            # Untested requests
            if coll['untested']:
                f.write("### Untested Requests\n")
                for req in coll['untested']:
                    f.write(f"- `{req['method']}` {req['name']}"
                            f" — `{req['file']}`\n")
                f.write("\n")

        # URL → Bruno File Map (cross-reference for planning)
        f.write("## URL → Bruno File Map\n")
        f.write("| URL Pattern | Method | Bruno File |\n")
        f.write("|-------------|--------|------------|\n")

        all_requests = []
        for coll in collections_data:
            for folder_requests in coll['folders'].values():
                all_requests.extend(folder_requests)

        # Sort by URL for easy lookup
        all_requests.sort(key=lambda r: (r.get('url') or '', r['method']))
        for req in all_requests:
            url = req['url'] or '—'
            f.write(f"| {url} | {req['method']} | `{req['file']}` |\n")

        f.write("\n")

    print(f"Markdown documentation generated: {output_file}")


def update_claude_md(output_file, directory):
    """Update CLAUDE.md to reference the API tools index file."""
    project_root = os.getcwd()

    check_dir = os.path.dirname(os.path.abspath(output_file))
    for _ in range(5):
        if (os.path.exists(os.path.join(check_dir, '.git'))
                or os.path.exists(os.path.join(check_dir, 'CLAUDE.md'))):
            project_root = check_dir
            break
        parent = os.path.dirname(check_dir)
        if parent == check_dir:
            break
        check_dir = parent

    claude_md_path = os.path.join(project_root, 'CLAUDE.md')
    rel_output = os.path.relpath(output_file, project_root)

    # We only add a reference line if there's a Codebase Overview section
    # and our file isn't already mentioned.
    try:
        if not os.path.exists(claude_md_path):
            return

        with open(claude_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if rel_output in content:
            # Already referenced
            return

        # Look for the Available Index Files subsection
        marker = '### Available Index Files'
        if marker in content:
            idx = content.index(marker)
            # Find the end of the bullet list under this heading
            lines = content[idx:].split('\n')
            insert_after = idx
            for i, line in enumerate(lines):
                if i == 0:
                    continue
                if line.startswith('- `codebase_overview_'):
                    insert_after = idx + sum(
                        len(l) + 1 for l in lines[:i + 1])
                elif line.strip() == '' and insert_after != idx:
                    break
                elif not line.startswith('- ') and line.strip() and i > 1:
                    break

            if insert_after != idx:
                new_line = (f"- `codebase_overview_*_api_tools.md`"
                            f" - API testing tools (Bruno collections)\n")
                content = (content[:insert_after]
                           + new_line + content[insert_after:])

                with open(claude_md_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print("Updated CLAUDE.md with API tools index reference")

    except Exception as e:
        print(f"Warning: Could not update CLAUDE.md: {e}", file=sys.stderr)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Index API testing tools (Bruno collections) and '
                    'generate Markdown documentation.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Scan current directory
  %(prog)s ./                                 # Scan root directory
  %(prog)s ./api_tools                        # Scan specific directory
  %(prog)s ./ -o memories/codebase/out.md     # Custom output file
  %(prog)s --help                             # Show this help
        """
    )

    parser.add_argument(
        'directory',
        nargs='?',
        default='./',
        help='Directory to scan for Bruno collections '
             '(default: ./)',
    )

    parser.add_argument(
        '-o', '--output',
        default='codebase_overview_api_tools.md',
        help='Output Markdown file '
             '(default: codebase_overview_api_tools.md)',
    )

    parser.add_argument(
        '--no-claude-md',
        action='store_true',
        help='Skip updating CLAUDE.md',
    )

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.",
              file=sys.stderr)
        sys.exit(1)

    print(f"Scanning for Bruno collections in: {args.directory}")
    collections = find_bruno_collections(args.directory)
    print(f"Found {len(collections)} Bruno collection(s)")

    # Scan each collection
    collections_data = []
    for coll in collections:
        data = scan_collection(coll['path'], args.directory)
        collections_data.append(data)

    # Generate output
    generate_markdown(collections_data, args.output, args.directory)

    if not args.no_claude_md:
        update_claude_md(args.output, args.directory)


if __name__ == "__main__":
    main()
