import os
import re
import argparse
import sys
from pathlib import Path

# Directories to skip during indexing (only directories that might contain .ts/.tsx files)
SKIP_DIRS = {
    # Dependencies (contain library .ts/.tsx files we don't want to index)
    'node_modules', 'jspm_packages', 'bower_components',
    # Version control
    '.git', '.svn', '.hg',
    # Build outputs (contain compiled/generated files)
    'dist', 'build', 'out', '.next', '.nuxt', '.output',
    # Cache directories
    '.cache', '.parcel-cache', '.turbo',
    # Testing output
    'coverage',
    # Framework specific build directories
    '.docusaurus', '.serverless',
    # IDE/Editor directories
    '.vscode', '.idea', '.vs',
    # Claude configuration
    '.claude', 'claude-helpers',
    # Logs and temporary directories
    'logs', 'tmp', 'temp'
}

def extract_typescript_info(directory):
    """Traverse the directory and extract TypeScript/TSX components, functions, interfaces, types."""
    codebase_info = {}

    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if file.endswith(('.ts', '.tsx', '.js', '.jsx')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()

                    codebase_info[file_path] = parse_typescript(source, file_path)
                except Exception as e:
                    print(f"Error parsing file {file_path}: {e}")

    return codebase_info


def parse_typescript(source, file_path):
    """Parse TypeScript/TSX source to extract components, functions, interfaces, types."""
    details = {
        "components": [],
        "functions": [],
        "interfaces": [],
        "types": [],
        "classes": [],
        "exports": [],
    }

    lines = source.split('\n')

    # Extract React components (function components and class components)
    # Function components: export const ComponentName = () => { or function ComponentName() {
    func_component_pattern = r'(?:export\s+)?(?:const|function)\s+([A-Z][a-zA-Z0-9]*)\s*(?::\s*React\.FC)?(?:<[^>]*>)?\s*=?\s*(?:\([^)]*\))?\s*(?::\s*[^=]+)?\s*(?:=>)?\s*\{'

    # Class components: class ComponentName extends React.Component
    class_component_pattern = r'(?:export\s+)?class\s+([A-Z][a-zA-Z0-9]*)\s+extends\s+(?:React\.)?(?:Component|PureComponent)'

    # Regular functions: function functionName() or const functionName = () =>
    function_pattern = r'(?:export\s+)?(?:const|function)\s+([a-z][a-zA-Z0-9]*)\s*(?::\s*[^=]+)?\s*=?\s*(?:\([^)]*\))?\s*(?::\s*[^=]+)?\s*(?:=>)?\s*\{'

    # Interfaces: interface InterfaceName {
    interface_pattern = r'(?:export\s+)?interface\s+([A-Z][a-zA-Z0-9]*)\s*(?:<[^>]*>)?\s*(?:extends\s+[^{]+)?\s*\{'

    # Type aliases: type TypeName = ...
    type_pattern = r'(?:export\s+)?type\s+([A-Z][a-zA-Z0-9]*)\s*(?:<[^>]*>)?\s*=\s*(.+?)(?:;|\n)'

    # Classes: class ClassName {
    class_pattern = r'(?:export\s+)?class\s+([A-Z][a-zA-Z0-9]*)\s*(?:<[^>]*>)?\s*(?:extends\s+[^{]+)?\s*\{'

    # Exports: export { ... }
    export_pattern = r'export\s+\{([^}]+)\}'

    # Track what we've already found to avoid duplicates
    found_components = set()
    found_functions = set()
    found_classes = set()

    for i, line in enumerate(lines, 1):
        # React Function Components (capitalized names)
        matches = re.finditer(func_component_pattern, line)
        for match in matches:
            name = match.group(1)
            if name and name not in found_components:
                # Extract props from the function signature
                props = extract_props_from_signature(source, match.start())
                details["components"].append({
                    "name": name,
                    "type": "function",
                    "line": i,
                    "props": props,
                    "exported": "export" in line,
                })
                found_components.add(name)

        # React Class Components
        matches = re.finditer(class_component_pattern, line)
        for match in matches:
            name = match.group(1)
            if name and name not in found_components:
                details["components"].append({
                    "name": name,
                    "type": "class",
                    "line": i,
                    "exported": "export" in line,
                })
                found_components.add(name)

        # Regular Functions (lowercase names)
        matches = re.finditer(function_pattern, line)
        for match in matches:
            name = match.group(1)
            if name and name not in found_functions and name not in found_components:
                # Extract function signature
                signature = extract_function_signature(source, match.start())
                details["functions"].append({
                    "name": name,
                    "line": i,
                    "signature": signature,
                    "exported": "export" in line,
                })
                found_functions.add(name)

        # Interfaces
        matches = re.finditer(interface_pattern, line)
        for match in matches:
            name = match.group(1)
            if name:
                # Extract interface fields
                fields = extract_interface_fields(source, match.end(), lines, i)
                details["interfaces"].append({
                    "name": name,
                    "line": i,
                    "fields": fields,
                    "exported": "export" in line,
                })

        # Type Aliases
        matches = re.finditer(type_pattern, line)
        for match in matches:
            name = match.group(1)
            definition = match.group(2).strip()
            if name:
                details["types"].append({
                    "name": name,
                    "line": i,
                    "definition": definition,
                    "exported": "export" in line,
                })

        # Classes (non-React)
        matches = re.finditer(class_pattern, line)
        for match in matches:
            name = match.group(1)
            if name and name not in found_classes and name not in found_components:
                # Extract class methods
                methods = extract_class_methods(source, match.end(), lines, i)
                details["classes"].append({
                    "name": name,
                    "line": i,
                    "methods": methods,
                    "exported": "export" in line,
                })
                found_classes.add(name)

        # Exports
        matches = re.finditer(export_pattern, line)
        for match in matches:
            exports = [e.strip() for e in match.group(1).split(',')]
            details["exports"].extend(exports)

    return details


def extract_props_from_signature(source, start_pos):
    """Extract props from React component function signature."""
    # Find the opening parenthesis
    paren_start = source.find('(', start_pos)
    if paren_start == -1:
        return None

    # Find the matching closing parenthesis
    paren_end = find_matching_paren(source, paren_start)
    if paren_end == -1:
        return None

    props_sig = source[paren_start+1:paren_end].strip()

    # Handle destructured props: { prop1, prop2 }: PropsType
    if ':' in props_sig:
        props_type = props_sig.split(':')[-1].strip()
        return props_type

    return props_sig if props_sig else None


def extract_function_signature(source, start_pos):
    """Extract function parameter signature."""
    # Find the opening parenthesis
    paren_start = source.find('(', start_pos)
    if paren_start == -1:
        return None

    # Find the matching closing parenthesis
    paren_end = find_matching_paren(source, paren_start)
    if paren_end == -1:
        return None

    # Get parameters
    params = source[paren_start+1:paren_end].strip()

    # Try to find return type after the closing paren
    arrow_pos = source.find('=>', paren_end)
    colon_pos = source.find(':', paren_end)

    return_type = None
    if colon_pos != -1 and (arrow_pos == -1 or colon_pos < arrow_pos):
        # Find the end of the return type (before => or {)
        end_markers = ['=>', '{']
        end_pos = len(source)
        for marker in end_markers:
            marker_pos = source.find(marker, colon_pos)
            if marker_pos != -1:
                end_pos = min(end_pos, marker_pos)
        return_type = source[colon_pos+1:end_pos].strip()

    if return_type:
        return f"({params}): {return_type}"
    return f"({params})"


def extract_interface_fields(source, start_pos, lines, line_num):
    """Extract fields from an interface definition."""
    fields = []
    brace_count = 1
    current_pos = start_pos

    while brace_count > 0 and current_pos < len(source):
        char = source[current_pos]
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        current_pos += 1

    # Extract the content between braces
    interface_body = source[start_pos:current_pos-1].strip()

    # Parse fields (simple version - can be improved)
    for line in interface_body.split('\n'):
        line = line.strip()
        if line and not line.startswith('//'):
            # Remove trailing comma or semicolon
            line = line.rstrip(',;')
            if ':' in line:
                field_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_?]*)\s*:\s*(.+)', line)
                if field_match:
                    fields.append({
                        "name": field_match.group(1),
                        "type": field_match.group(2).strip()
                    })

    return fields


def extract_class_methods(source, start_pos, lines, line_num):
    """Extract methods from a class definition."""
    methods = []
    brace_count = 1
    current_pos = start_pos

    while brace_count > 0 and current_pos < len(source):
        char = source[current_pos]
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        current_pos += 1

    # Extract the class body
    class_body = source[start_pos:current_pos-1]

    # Find method definitions
    method_pattern = r'(?:async\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{'

    for match in re.finditer(method_pattern, class_body):
        method_name = match.group(1)
        # Skip constructor if you want, or keep it
        if method_name not in ['if', 'for', 'while', 'switch']:  # Avoid false positives
            methods.append(method_name)

    return methods


def find_matching_paren(source, start_pos):
    """Find the matching closing parenthesis."""
    count = 1
    pos = start_pos + 1

    while pos < len(source) and count > 0:
        if source[pos] == '(':
            count += 1
        elif source[pos] == ')':
            count -= 1
        pos += 1

    return pos - 1 if count == 0 else -1


def generate_file_tree(directory, codebase_info):
    """Generate a visual tree structure of TypeScript/TSX files in the codebase."""
    tree_lines = []
    base_path = os.path.abspath(directory)
    base_name = os.path.basename(base_path) or base_path

    # Create tree structure
    def build_tree(current_dir, prefix="", is_last=True):
        """Recursively build tree structure."""
        try:
            entries = sorted(os.listdir(current_dir))
        except PermissionError:
            return

        # Filter out SKIP_DIRS
        dirs = [e for e in entries if os.path.isdir(os.path.join(current_dir, e))
                and e not in SKIP_DIRS]
        files = [e for e in entries if os.path.isfile(os.path.join(current_dir, e))
                 and e.endswith(('.ts', '.tsx', '.js', '.jsx'))]

        # Combine and sort: directories first, then files
        all_entries = [(d, True) for d in dirs] + [(f, False) for f in files]

        for idx, (entry, is_dir) in enumerate(all_entries):
            is_last_entry = idx == len(all_entries) - 1
            entry_path = os.path.join(current_dir, entry)

            # Determine connector
            connector = "└── " if is_last_entry else "├── "
            tree_lines.append(f"{prefix}{connector}{entry}{'/' if is_dir else ''}")

            # Recurse into directories
            if is_dir:
                extension = "    " if is_last_entry else "│   "
                build_tree(entry_path, prefix + extension, is_last_entry)

    # Start with root
    tree_lines.append(f"{base_name}/")
    build_tree(base_path, "", True)

    return "\n".join(tree_lines)


def generate_markdown(codebase_info, output_file, directory):
    """Generate a Markdown file with TypeScript codebase overview."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# JavaScript/TypeScript/React Codebase Overview\n\n")

        # Generate file tree
        f.write("## File Tree\n\n")
        f.write("```\n")
        tree = generate_file_tree(directory, codebase_info)
        f.write(tree)
        f.write("\n```\n\n")
        f.write("---\n\n")

        # Generate table of contents
        f.write("## Table of Contents\n\n")
        for file_path in sorted(codebase_info.keys()):
            rel_path = file_path.replace(os.getcwd() + '/', '')
            anchor = rel_path.replace('/', '-').replace('.', '')
            f.write(f"- [{rel_path}](#{anchor})\n")
        f.write("\n---\n\n")

        # Generate per-file documentation
        for file_path in sorted(codebase_info.keys()):
            content = codebase_info[file_path]
            rel_path = file_path.replace(os.getcwd() + '/', '')

            f.write(f"# File: `{rel_path}`\n\n")

            # Overview section
            f.write("## Overview\n\n")
            overview_items = []
            if content["components"]:
                overview_items.append(f"**Components:** {len(content['components'])}")
            if content["functions"]:
                overview_items.append(f"**Functions:** {len(content['functions'])}")
            if content["interfaces"]:
                overview_items.append(f"**Interfaces:** {len(content['interfaces'])}")
            if content["types"]:
                overview_items.append(f"**Types:** {len(content['types'])}")
            if content["classes"]:
                overview_items.append(f"**Classes:** {len(content['classes'])}")

            if overview_items:
                f.write(" | ".join(overview_items) + "\n\n")
            else:
                f.write("*No exported items found*\n\n")

            # React Components
            if content["components"]:
                f.write("## React Components\n\n")
                for component in content["components"]:
                    export_badge = "**[exported]**" if component.get("exported") else ""
                    f.write(f"### `{component['name']}` {export_badge}\n\n")
                    f.write(f"- **Type:** {component['type']} component\n")
                    f.write(f"- **Line:** {component['line']}\n")
                    if component.get('props'):
                        f.write(f"- **Props:** `{component['props']}`\n")
                    f.write("\n")

            # Functions
            if content["functions"]:
                f.write("## Functions\n\n")
                for func in content["functions"]:
                    export_badge = "**[exported]**" if func.get("exported") else ""
                    f.write(f"### `{func['name']}` {export_badge}\n\n")
                    f.write(f"- **Line:** {func['line']}\n")
                    if func.get('signature'):
                        f.write(f"- **Signature:** `{func['signature']}`\n")
                    f.write("\n")

            # Interfaces
            if content["interfaces"]:
                f.write("## Interfaces\n\n")
                for interface in content["interfaces"]:
                    export_badge = "**[exported]**" if interface.get("exported") else ""
                    f.write(f"### `{interface['name']}` {export_badge}\n\n")
                    f.write(f"- **Line:** {interface['line']}\n")
                    if interface.get('fields'):
                        f.write("- **Fields:**\n")
                        for field in interface['fields']:
                            f.write(f"  - `{field['name']}`: `{field['type']}`\n")
                    f.write("\n")

            # Type Aliases
            if content["types"]:
                f.write("## Type Aliases\n\n")
                for type_def in content["types"]:
                    export_badge = "**[exported]**" if type_def.get("exported") else ""
                    f.write(f"### `{type_def['name']}` {export_badge}\n\n")
                    f.write(f"- **Line:** {type_def['line']}\n")
                    f.write(f"- **Definition:** `{type_def['definition']}`\n")
                    f.write("\n")

            # Classes
            if content["classes"]:
                f.write("## Classes\n\n")
                for cls in content["classes"]:
                    export_badge = "**[exported]**" if cls.get("exported") else ""
                    f.write(f"### `{cls['name']}` {export_badge}\n\n")
                    f.write(f"- **Line:** {cls['line']}\n")
                    if cls.get('methods'):
                        f.write(f"- **Methods:** {', '.join([f'`{m}`' for m in cls['methods']])}\n")
                    f.write("\n")

            # Exports
            if content["exports"]:
                f.write("## Exports\n\n")
                f.write(", ".join([f"`{e}`" for e in content["exports"]]))
                f.write("\n\n")

            f.write("---\n\n")

    print(f"Markdown documentation generated: {output_file}")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Index TypeScript/React codebase and generate Markdown documentation.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Scan current directory
  %(prog)s ./src                              # Scan relative path directory
  %(prog)s ./cc_wrapper/frontend/src          # Scan nested directory
  %(prog)s /absolute/path/to/project          # Scan absolute path
  %(prog)s ./src -o docs.md                   # Scan directory with custom output file
  %(prog)s --help                             # Show this help message

Note: Both relative paths (./dir, ../dir) and absolute paths (/path/to/dir) are supported.
        """
    )

    parser.add_argument(
        'directory',
        nargs='?',
        default='./',
        help='Directory to scan for TypeScript/TSX files - supports both relative (./dir, ../dir) and absolute paths (default: ./)'
    )

    parser.add_argument(
        '-o', '--output',
        default='codebase_overview_js_ts.md',
        help='Output Markdown file (default: codebase_overview_js_ts.md)'
    )

    args = parser.parse_args()

    # Validate directory exists
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Extract information
    print(f"Indexing TypeScript codebase in: {args.directory}")
    extracted_info = extract_typescript_info(args.directory)

    # Create Markdown file
    generate_markdown(extracted_info, args.output, args.directory)
    print(f"Found {len(extracted_info)} TypeScript files")


if __name__ == "__main__":
    main()
