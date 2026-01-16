import os
import re
import argparse
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

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
    'logs', 'tmp', 'temp',
    # Thoughts/documentation (not source code)
    'thoughts',
    # Database migrations
    'migrations'
}

# HTTP handler patterns for API endpoint detection
HTTP_HANDLER_PATTERNS = [
    r'\.HandleFunc\s*\(\s*"([^"]+)"',  # http.HandleFunc("/path", ...)
    r'\.Handle\s*\(\s*"([^"]+)"',       # mux.Handle("/path", ...)
    r'\.GET\s*\(\s*"([^"]+)"',          # router.GET("/path", ...)
    r'\.POST\s*\(\s*"([^"]+)"',
    r'\.PUT\s*\(\s*"([^"]+)"',
    r'\.DELETE\s*\(\s*"([^"]+)"',
    r'\.PATCH\s*\(\s*"([^"]+)"',
]

def extract_go_info(directory):
    """Traverse the directory and extract Go packages, structs, interfaces, functions."""
    codebase_info = {}
    all_sources = {}  # Store source for usage tracking

    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if file.endswith('.go') and not file.endswith('_test.go'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()

                    all_sources[file_path] = source
                    codebase_info[file_path] = parse_go(source, file_path)
                except Exception as e:
                    print(f"Error parsing file {file_path}: {e}")

    # Build usage graph
    usage_graph = build_usage_graph(codebase_info, all_sources, directory)

    # Attach usage info to symbols
    for file_path, content in codebase_info.items():
        for struct in content.get("structs", []):
            struct["used_by"] = usage_graph.get(struct["name"], [])
        for iface in content.get("interfaces", []):
            iface["used_by"] = usage_graph.get(iface["name"], [])
        for func in content.get("functions", []):
            func["used_by"] = usage_graph.get(func["name"], [])

    return codebase_info


def build_usage_graph(codebase_info, all_sources, base_directory):
    """Build a reverse lookup: for each exported symbol, find where it's used."""
    usage_graph = defaultdict(list)
    base_path = os.path.abspath(base_directory)

    # Collect all exported symbols (capitalized names in Go)
    exported_symbols = {}
    for file_path, content in codebase_info.items():
        rel_path = os.path.relpath(file_path, base_path)
        pkg = content.get("package", "")

        for struct in content.get("structs", []):
            if struct["name"][0].isupper():
                exported_symbols[struct["name"]] = rel_path
        for iface in content.get("interfaces", []):
            if iface["name"][0].isupper():
                exported_symbols[iface["name"]] = rel_path
        for func in content.get("functions", []):
            if func["name"][0].isupper():
                exported_symbols[func["name"]] = rel_path

    # Find usages in all files
    for file_path, source in all_sources.items():
        rel_path = os.path.relpath(file_path, base_path)

        for symbol_name, defining_file in exported_symbols.items():
            if defining_file == rel_path:
                continue  # Skip self-references

            # Check for usage: TypeName, pkg.TypeName, &TypeName, *TypeName
            patterns = [
                rf'\b{symbol_name}\b',  # Direct usage
                rf'\b{symbol_name}\{{',  # Struct literal
                rf'\*{symbol_name}\b',  # Pointer type
                rf'&{symbol_name}\{{',  # Address of struct literal
            ]

            for pattern in patterns:
                if re.search(pattern, source):
                    if rel_path not in usage_graph[symbol_name]:
                        usage_graph[symbol_name].append(rel_path)
                    break

    return dict(usage_graph)


def extract_go_doc(lines, line_num):
    """Extract Go doc comment immediately before a declaration."""
    if line_num <= 1:
        return None

    doc_lines = []
    # Go back from the line before the declaration
    for i in range(line_num - 2, -1, -1):
        line = lines[i].strip()
        if line.startswith('//'):
            # Strip // and leading space
            comment = line[2:].strip()
            doc_lines.insert(0, comment)
        elif not line:
            # Empty line - continue looking
            continue
        else:
            # Non-comment, non-empty line - stop
            break

    if not doc_lines:
        return None

    # Return first meaningful line
    for line in doc_lines:
        if line and not line.startswith('@'):
            if len(line) > 80:
                line = line[:80] + "..."
            return line
    return None


def extract_api_endpoints(source, file_path):
    """Extract HTTP API endpoints from Go source."""
    endpoints = []

    for pattern in HTTP_HANDLER_PATTERNS:
        for match in re.finditer(pattern, source):
            path = match.group(1)
            # Determine HTTP method from pattern
            method = 'GET'
            if '.POST' in pattern:
                method = 'POST'
            elif '.PUT' in pattern:
                method = 'PUT'
            elif '.DELETE' in pattern:
                method = 'DELETE'
            elif '.PATCH' in pattern:
                method = 'PATCH'

            endpoints.append({
                'method': method,
                'path': path,
                'file': file_path
            })

    return endpoints


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
        "api_endpoints": extract_api_endpoints(source, file_path),
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
            doc = extract_go_doc(lines, i)
            details["structs"].append({
                "name": struct_name,
                "line": i,
                "fields": fields,
                "doc": doc
            })
            continue

        # Interface definition
        match = re.match(interface_pattern, stripped)
        if match:
            interface_name = match.group(1)
            methods = extract_interface_methods(source, lines, i)
            doc = extract_go_doc(lines, i)
            details["interfaces"].append({
                "name": interface_name,
                "line": i,
                "methods": methods,
                "doc": doc
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
            doc = extract_go_doc(lines, i)
            details["functions"].append({
                "name": func_name,
                "signature": signature,
                "line": i,
                "doc": doc
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


def format_go_signature(signature):
    """Format Go function signature - extract just parameter names."""
    if not signature:
        return "()"

    # Extract params from signature like "(ctx context.Context, id string) error"
    match = re.match(r'\(([^)]*)\)', signature)
    if not match:
        return "()"

    params_str = match.group(1).strip()
    if not params_str:
        return "()"

    # Extract just parameter names
    param_names = []
    for param in params_str.split(','):
        param = param.strip()
        if not param:
            continue
        # Get just the name (first word before space or type)
        parts = param.split()
        if parts:
            name = parts[0]
            # Skip if it looks like a type (starts with capital or *)
            if not name[0].isupper() and not name.startswith('*'):
                param_names.append(name)

    result = ', '.join(param_names)
    if len(result) > 40:
        result = result[:40] + "..."
    return f"({result})"


def generate_markdown(codebase_info, output_file, directory):
    """Generate a Markdown file - compact format matching JS/TS and Python indexers."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Codebase Index\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Regenerate with `/index_codebase`*\n\n")

        base_path = os.path.abspath(directory)

        # === SECTION 1: Most Used Symbols ===
        f.write("## Most Used Symbols\n\n")

        all_symbols = []
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)

            # Exported structs (capitalized)
            for struct in content.get("structs", []):
                if struct["name"][0].isupper() and struct.get("used_by"):
                    all_symbols.append({
                        "name": struct["name"],
                        "file": rel_path,
                        "line": struct["line"],
                        "signature": "",
                        "description": struct.get("doc"),
                        "type": "struct",
                        "refs": len(struct["used_by"])
                    })

            # Exported interfaces
            for iface in content.get("interfaces", []):
                if iface["name"][0].isupper() and iface.get("used_by"):
                    all_symbols.append({
                        "name": iface["name"],
                        "file": rel_path,
                        "line": iface["line"],
                        "signature": "",
                        "description": iface.get("doc"),
                        "type": "interface",
                        "refs": len(iface["used_by"])
                    })

            # Exported functions
            for func in content.get("functions", []):
                if func["name"][0].isupper() and func.get("used_by"):
                    sig = format_go_signature(func.get("signature", ""))
                    all_symbols.append({
                        "name": func["name"],
                        "file": rel_path,
                        "line": func["line"],
                        "signature": sig,
                        "description": func.get("doc"),
                        "type": "func",
                        "refs": len(func["used_by"])
                    })

        all_symbols.sort(key=lambda x: x["refs"], reverse=True)

        for sym in all_symbols[:25]:
            desc = f" - {sym['description']}" if sym.get("description") else ""
            f.write(f"- **{sym['name']}**{sym['signature']} `{sym['file']}:{sym['line']}`{desc} → {sym['refs']} refs\n")
        f.write("\n")

        # === SECTION 2: Library Files ===
        f.write("## Library Files\n\n")

        for file_path in sorted(codebase_info.keys()):
            content = codebase_info[file_path]
            rel_path = os.path.relpath(file_path, base_path)
            pkg = content.get("package", "")

            exports_lines = []

            # Exported Structs
            for struct in content.get("structs", []):
                if struct["name"][0].isupper():
                    fields = [f['name'] for f in struct.get('fields', [])][:4]
                    fields_str = f" fields: {', '.join(fields)}" if fields else ""
                    desc = f" - {struct['doc']}" if struct.get("doc") else ""
                    exports_lines.append(f"  - `{struct['name']}`:{struct['line']} - struct{fields_str}{desc}")
                    if struct.get("used_by"):
                        used_by = ', '.join(f'`{u}`' for u in struct['used_by'][:5])
                        more = f" +{len(struct['used_by'])-5} more" if len(struct['used_by']) > 5 else ""
                        exports_lines.append(f"    ↳ used by: {used_by}{more}")

            # Exported Interfaces
            for iface in content.get("interfaces", []):
                if iface["name"][0].isupper():
                    methods = [m['name'] for m in iface.get('methods', [])][:4]
                    methods_str = f" methods: {', '.join(methods)}" if methods else ""
                    desc = f" - {iface['doc']}" if iface.get("doc") else ""
                    exports_lines.append(f"  - `{iface['name']}`:{iface['line']} - interface{methods_str}{desc}")
                    if iface.get("used_by"):
                        used_by = ', '.join(f'`{u}`' for u in iface['used_by'][:5])
                        more = f" +{len(iface['used_by'])-5} more" if len(iface['used_by']) > 5 else ""
                        exports_lines.append(f"    ↳ used by: {used_by}{more}")

            # Exported Functions
            for func in content.get("functions", []):
                if func["name"][0].isupper():
                    sig = format_go_signature(func.get("signature", ""))
                    desc = f" - {func['doc']}" if func.get("doc") else ""
                    exports_lines.append(f"  - `{func['name']}`{sig}:{func['line']}{desc}")
                    if func.get("used_by"):
                        used_by = ', '.join(f'`{u}`' for u in func['used_by'][:5])
                        more = f" +{len(func['used_by'])-5} more" if len(func['used_by']) > 5 else ""
                        exports_lines.append(f"    ↳ used by: {used_by}{more}")

            # Methods grouped by receiver
            methods_by_receiver = {}
            for method in content.get("methods", []):
                if method["name"][0].isupper():
                    receiver = method["receiver"]
                    if receiver not in methods_by_receiver:
                        methods_by_receiver[receiver] = []
                    methods_by_receiver[receiver].append(method)

            for receiver, methods in methods_by_receiver.items():
                method_names = ', '.join(m['name'] for m in methods[:5])
                more = f" +{len(methods)-5} more" if len(methods) > 5 else ""
                exports_lines.append(f"  - `{receiver}` methods: {method_names}{more}")

            if exports_lines:
                pkg_str = f" (pkg: {pkg})" if pkg else ""
                f.write(f"### `{rel_path}`{pkg_str}\n")
                f.write("\n".join(exports_lines))
                f.write("\n\n")

        # === SECTION 3: API Endpoints ===
        f.write("## API Endpoints\n\n")

        api_endpoints = []
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)
            for ep in content.get("api_endpoints", []):
                api_endpoints.append({
                    'method': ep['method'],
                    'path': ep['path'],
                    'file': rel_path
                })

        if api_endpoints:
            for ep in sorted(api_endpoints, key=lambda x: (x['path'], x['method'])):
                f.write(f"- **{ep['method']}** `{ep['path']}` → `{ep['file']}`\n")
        else:
            f.write("*No API endpoints detected*\n")
        f.write("\n")

        # === SECTION 4: Dependency Graph ===
        f.write("## Dependency Graph\n\n")
        f.write("*Files by number of dependents:*\n\n")

        file_dependencies = {}
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)
            users = set()
            for struct in content.get("structs", []):
                users.update(struct.get("used_by", []))
            for iface in content.get("interfaces", []):
                users.update(iface.get("used_by", []))
            for func in content.get("functions", []):
                users.update(func.get("used_by", []))
            if users:
                file_dependencies[rel_path] = len(users)

        sorted_deps = sorted(file_dependencies.items(), key=lambda x: x[1], reverse=True)
        for file, count in sorted_deps[:20]:
            f.write(f"- `{file}` ← {count} files\n")

        f.write("\n")

    print(f"Markdown documentation generated: {output_file}")


def update_claude_md(output_file, directory):
    """Update CLAUDE.md to reference the codebase index file."""
    # Find project root - look for CLAUDE.md or .git directory
    project_root = os.getcwd()

    # Walk up to find project root (where .git or CLAUDE.md exists)
    check_dir = os.path.dirname(os.path.abspath(output_file))
    for _ in range(5):  # Max 5 levels up
        if os.path.exists(os.path.join(check_dir, '.git')) or os.path.exists(os.path.join(check_dir, 'CLAUDE.md')):
            project_root = check_dir
            break
        parent = os.path.dirname(check_dir)
        if parent == check_dir:
            break
        check_dir = parent

    claude_md_path = os.path.join(project_root, 'CLAUDE.md')

    # The section we want to add/update
    index_section = f"""## Codebase Index

**IMPORTANT**: Before searching the codebase with Grep, Glob, or Explore, first read the codebase index:

**`{os.path.relpath(output_file, project_root)}`**

This index contains:
- **Most Used Symbols**: Top structs/interfaces/functions by usage count
- **Library Files**: All exports with descriptions and "used by" references
- **API Endpoints**: All HTTP routes
- **Dependency Graph**: Which files are most imported

Reading the index first saves tokens and improves accuracy.
"""

    try:
        if os.path.exists(claude_md_path):
            with open(claude_md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if section already exists
            if '## Codebase Index' in content:
                # Update existing section
                pattern = r'## Codebase Index.*?(?=\n## |\n# |\Z)'
                content = re.sub(pattern, index_section.strip() + '\n\n', content, flags=re.DOTALL)
            else:
                # Add after first heading or at the end
                if '\n## ' in content:
                    # Insert before second section
                    first_section_end = content.find('\n## ')
                    content = content[:first_section_end] + '\n\n' + index_section + content[first_section_end:]
                else:
                    # Append
                    content = content.rstrip() + '\n\n' + index_section

            with open(claude_md_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated CLAUDE.md with codebase index reference")
        else:
            # Create new CLAUDE.md
            with open(claude_md_path, 'w', encoding='utf-8') as f:
                f.write(f"# Project Configuration\n\n{index_section}")
            print(f"Created CLAUDE.md with codebase index reference")

    except Exception as e:
        print(f"Warning: Could not update CLAUDE.md: {e}")


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

    parser.add_argument(
        '--no-claude-md',
        action='store_true',
        help='Skip updating CLAUDE.md'
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

    # Update CLAUDE.md
    if not args.no_claude_md:
        update_claude_md(args.output, args.directory)


if __name__ == "__main__":
    main()
