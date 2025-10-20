import os
import re
import argparse
import sys
from pathlib import Path

# Directories to skip during indexing (only directories that might contain .go files)
SKIP_DIRS = {
    # Dependencies (contain library .go files we don't want to index)
    'vendor', 'third_party', 'node_modules',
    # Version control
    '.git', '.svn', '.hg',
    # Build outputs (contain compiled/generated files)
    'dist', 'build', 'bin', 'pkg',
    # Testing output
    'coverage', 'testdata',
    # IDE/Editor directories
    '.vscode', '.idea', '.vs',
    # Claude configuration
    '.claude', 'claude-helpers',
    # Logs and temporary directories
    'logs', 'tmp', 'temp'
}

def extract_go_info(directory):
    """Traverse the directory and extract Go packages, structs, interfaces, functions."""
    codebase_info = {}

    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if file.endswith('.go') and not file.endswith('_test.go'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()

                    codebase_info[file_path] = parse_go(source, file_path)
                except Exception as e:
                    print(f"Error parsing file {file_path}: {e}")

    return codebase_info


def parse_go(source, file_path):
    """Parse Go source to extract package, structs, interfaces, functions, methods."""
    details = {
        "package": "",
        "imports": [],
        "structs": [],
        "interfaces": [],
        "functions": [],
        "methods": [],
        "constants": [],
        "variables": [],
    }

    lines = source.split('\n')

    # Package declaration: package name
    package_pattern = r'^package\s+([a-zA-Z_][a-zA-Z0-9_]*)'

    # Import statements: import "path" or import ( ... )
    import_single_pattern = r'^import\s+"([^"]+)"'
    import_multi_start_pattern = r'^import\s+\('

    # Struct definition: type StructName struct {
    struct_pattern = r'^type\s+([A-Z][a-zA-Z0-9_]*)\s+struct\s*\{'

    # Interface definition: type InterfaceName interface {
    interface_pattern = r'^type\s+([A-Z][a-zA-Z0-9_]*)\s+interface\s*\{'

    # Function definition: func functionName(...) returnType {
    function_pattern = r'^func\s+([a-z][a-zA-Z0-9_]*)\s*\('

    # Method definition: func (receiver Type) methodName(...) returnType {
    method_pattern = r'^func\s+\(([^)]+)\)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('

    # Constant definition: const ConstName = value or const ( ... )
    const_single_pattern = r'^const\s+([A-Z][a-zA-Z0-9_]*)'
    const_multi_start_pattern = r'^const\s+\('

    # Variable definition: var varName type or var ( ... )
    var_single_pattern = r'^var\s+([a-z][a-zA-Z0-9_]*)'
    var_multi_start_pattern = r'^var\s+\('

    in_import_block = False
    in_const_block = False
    in_var_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments
        if stripped.startswith('//'):
            continue

        # Package declaration
        match = re.match(package_pattern, stripped)
        if match:
            details["package"] = match.group(1)
            continue

        # Import handling
        if re.match(import_multi_start_pattern, stripped):
            in_import_block = True
            continue

        if in_import_block:
            if stripped == ')':
                in_import_block = False
                continue
            # Extract import path
            import_match = re.search(r'"([^"]+)"', stripped)
            if import_match:
                details["imports"].append(import_match.group(1))
            continue

        match = re.match(import_single_pattern, stripped)
        if match:
            details["imports"].append(match.group(1))
            continue

        # Const handling
        if re.match(const_multi_start_pattern, stripped):
            in_const_block = True
            continue

        if in_const_block:
            if stripped == ')':
                in_const_block = False
                continue
            const_match = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|[A-Za-z])', stripped)
            if const_match:
                details["constants"].append({
                    "name": const_match.group(1),
                    "line": i
                })
            continue

        match = re.match(const_single_pattern, stripped)
        if match:
            details["constants"].append({
                "name": match.group(1),
                "line": i
            })
            continue

        # Var handling
        if re.match(var_multi_start_pattern, stripped):
            in_var_block = True
            continue

        if in_var_block:
            if stripped == ')':
                in_var_block = False
                continue
            var_match = re.match(r'([a-z][A-Za-z0-9_]*)\s+([A-Za-z*\[\]{}]+)', stripped)
            if var_match:
                details["variables"].append({
                    "name": var_match.group(1),
                    "type": var_match.group(2),
                    "line": i
                })
            continue

        match = re.match(var_single_pattern, stripped)
        if match:
            # Try to extract type
            type_match = re.match(r'var\s+([a-z][a-zA-Z0-9_]*)\s+([A-Za-z*\[\]{}]+)', stripped)
            var_type = type_match.group(2) if type_match else ""
            details["variables"].append({
                "name": match.group(1),
                "type": var_type,
                "line": i
            })
            continue

        # Struct definition
        match = re.match(struct_pattern, stripped)
        if match:
            struct_name = match.group(1)
            fields = extract_struct_fields(source, lines, i)
            details["structs"].append({
                "name": struct_name,
                "line": i,
                "fields": fields
            })
            continue

        # Interface definition
        match = re.match(interface_pattern, stripped)
        if match:
            interface_name = match.group(1)
            methods = extract_interface_methods(source, lines, i)
            details["interfaces"].append({
                "name": interface_name,
                "line": i,
                "methods": methods
            })
            continue

        # Method definition (must check before function)
        match = re.match(method_pattern, stripped)
        if match:
            receiver = match.group(1).strip()
            method_name = match.group(2)
            signature = extract_function_signature(stripped)

            # Extract receiver type
            receiver_match = re.search(r'\s*(\*?)([A-Z][a-zA-Z0-9_]*)', receiver)
            receiver_type = receiver_match.group(2) if receiver_match else receiver
            is_pointer = receiver_match.group(1) == '*' if receiver_match else False

            details["methods"].append({
                "name": method_name,
                "receiver": receiver_type,
                "is_pointer_receiver": is_pointer,
                "signature": signature,
                "line": i
            })
            continue

        # Function definition
        match = re.match(function_pattern, stripped)
        if match:
            func_name = match.group(1)
            signature = extract_function_signature(stripped)
            details["functions"].append({
                "name": func_name,
                "signature": signature,
                "line": i
            })
            continue

    return details


def extract_struct_fields(source, lines, start_line):
    """Extract fields from a struct definition."""
    fields = []
    brace_count = 0
    found_open_brace = False

    # Start from the struct definition line
    for i in range(start_line - 1, len(lines)):
        line = lines[i].strip()

        # Track braces
        if '{' in line:
            brace_count += line.count('{')
            found_open_brace = True
        if '}' in line:
            brace_count -= line.count('}')

        # If we've closed all braces, we're done
        if found_open_brace and brace_count == 0:
            break

        # Skip lines without field definitions
        if not found_open_brace or '{' in line or '}' in line or line.startswith('//'):
            continue

        # Parse field: FieldName Type `tag`
        field_match = re.match(r'([A-Z][a-zA-Z0-9_]*)\s+([^`\n]+)(?:`([^`]*)`)?', line)
        if field_match:
            field_name = field_match.group(1)
            field_type = field_match.group(2).strip()
            field_tag = field_match.group(3) if field_match.group(3) else ""

            fields.append({
                "name": field_name,
                "type": field_type,
                "tag": field_tag
            })

    return fields


def extract_interface_methods(source, lines, start_line):
    """Extract methods from an interface definition."""
    methods = []
    brace_count = 0
    found_open_brace = False

    # Start from the interface definition line
    for i in range(start_line - 1, len(lines)):
        line = lines[i].strip()

        # Track braces
        if '{' in line:
            brace_count += line.count('{')
            found_open_brace = True
        if '}' in line:
            brace_count -= line.count('}')

        # If we've closed all braces, we're done
        if found_open_brace and brace_count == 0:
            break

        # Skip lines without method definitions
        if not found_open_brace or '{' in line or '}' in line or line.startswith('//'):
            continue

        # Parse method signature: MethodName(params) returnType
        method_match = re.match(r'([A-Z][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*(.*)', line)
        if method_match:
            method_name = method_match.group(1)
            params = method_match.group(2).strip()
            return_type = method_match.group(3).strip()

            methods.append({
                "name": method_name,
                "params": params,
                "returns": return_type
            })

    return methods


def extract_function_signature(line):
    """Extract full function signature from a function definition line."""
    # Try to extract parameters and return type
    # func name(params) returnType or func (receiver) name(params) returnType

    # Find the function name's opening paren
    func_match = re.search(r'func\s+(?:\([^)]+\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*(.*?)\s*\{?', line)
    if func_match:
        params = func_match.group(2).strip()
        returns = func_match.group(3).strip()

        if returns:
            return f"({params}) {returns}"
        else:
            return f"({params})"

    return ""


def generate_file_tree(directory, codebase_info):
    """Generate a visual tree structure of Go files in the codebase."""
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
                 and e.endswith('.go') and not e.endswith('_test.go')]

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
    """Generate a Markdown file with Go codebase overview."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Go Codebase Overview\n\n")

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

            # Package
            if content["package"]:
                f.write(f"**Package:** `{content['package']}`\n\n")

            # Overview section
            f.write("## Overview\n\n")
            overview_items = []
            if content["structs"]:
                overview_items.append(f"**Structs:** {len(content['structs'])}")
            if content["interfaces"]:
                overview_items.append(f"**Interfaces:** {len(content['interfaces'])}")
            if content["functions"]:
                overview_items.append(f"**Functions:** {len(content['functions'])}")
            if content["methods"]:
                overview_items.append(f"**Methods:** {len(content['methods'])}")
            if content["constants"]:
                overview_items.append(f"**Constants:** {len(content['constants'])}")
            if content["variables"]:
                overview_items.append(f"**Variables:** {len(content['variables'])}")

            if overview_items:
                f.write(" | ".join(overview_items) + "\n\n")
            else:
                f.write("*No exported items found*\n\n")

            # Imports
            if content["imports"]:
                f.write("## Imports\n\n")
                for imp in content["imports"]:
                    f.write(f"- `{imp}`\n")
                f.write("\n")

            # Structs
            if content["structs"]:
                f.write("## Structs\n\n")
                for struct in content["structs"]:
                    f.write(f"### `{struct['name']}`\n\n")
                    f.write(f"- **Line:** {struct['line']}\n")
                    if struct.get('fields'):
                        f.write("- **Fields:**\n")
                        for field in struct['fields']:
                            tag_str = f" `{field['tag']}`" if field['tag'] else ""
                            f.write(f"  - `{field['name']}` `{field['type']}`{tag_str}\n")
                    f.write("\n")

            # Interfaces
            if content["interfaces"]:
                f.write("## Interfaces\n\n")
                for interface in content["interfaces"]:
                    f.write(f"### `{interface['name']}`\n\n")
                    f.write(f"- **Line:** {interface['line']}\n")
                    if interface.get('methods'):
                        f.write("- **Methods:**\n")
                        for method in interface['methods']:
                            f.write(f"  - `{method['name']}({method['params']}) {method['returns']}`\n")
                    f.write("\n")

            # Functions
            if content["functions"]:
                f.write("## Functions\n\n")
                for func in content["functions"]:
                    f.write(f"### `{func['name']}`\n\n")
                    f.write(f"- **Line:** {func['line']}\n")
                    if func.get('signature'):
                        f.write(f"- **Signature:** `func {func['name']}{func['signature']}`\n")
                    f.write("\n")

            # Methods
            if content["methods"]:
                f.write("## Methods\n\n")
                # Group methods by receiver
                methods_by_receiver = {}
                for method in content["methods"]:
                    receiver = method["receiver"]
                    if receiver not in methods_by_receiver:
                        methods_by_receiver[receiver] = []
                    methods_by_receiver[receiver].append(method)

                for receiver in sorted(methods_by_receiver.keys()):
                    f.write(f"### `{receiver}` Methods\n\n")
                    for method in methods_by_receiver[receiver]:
                        pointer_indicator = "*" if method["is_pointer_receiver"] else ""
                        f.write(f"#### `{method['name']}`\n\n")
                        f.write(f"- **Line:** {method['line']}\n")
                        f.write(f"- **Receiver:** `({pointer_indicator}{receiver})`\n")
                        if method.get('signature'):
                            f.write(f"- **Signature:** `func ({pointer_indicator}{receiver}) {method['name']}{method['signature']}`\n")
                        f.write("\n")

            # Constants
            if content["constants"]:
                f.write("## Constants\n\n")
                for const in content["constants"]:
                    f.write(f"- `{const['name']}` (line {const['line']})\n")
                f.write("\n")

            # Variables
            if content["variables"]:
                f.write("## Variables\n\n")
                for var in content["variables"]:
                    var_type = f": `{var['type']}`" if var.get('type') else ""
                    f.write(f"- `{var['name']}`{var_type} (line {var['line']})\n")
                f.write("\n")

            f.write("---\n\n")

    print(f"Markdown documentation generated: {output_file}")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Index Go codebase and generate Markdown documentation.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Scan current directory
  %(prog)s ./src                              # Scan relative path directory
  %(prog)s ./backend/services                 # Scan nested directory
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
        help='Directory to scan for Go files - supports both relative (./dir, ../dir) and absolute paths (default: ./)'
    )

    parser.add_argument(
        '-o', '--output',
        default='codebase_overview_go.md',
        help='Output Markdown file (default: codebase_overview_go.md)'
    )

    args = parser.parse_args()

    # Validate directory exists
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Extract information
    print(f"Indexing Go codebase in: {args.directory}")
    extracted_info = extract_go_info(args.directory)

    # Create Markdown file
    generate_markdown(extracted_info, args.output, args.directory)
    print(f"Found {len(extracted_info)} Go files")


if __name__ == "__main__":
    main()
