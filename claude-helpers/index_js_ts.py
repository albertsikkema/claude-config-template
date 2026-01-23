import os
import re
import argparse
import sys
from pathlib import Path
from collections import defaultdict

# Directories to skip during indexing (only directories that might contain .ts/.tsx files)
SKIP_DIRS = {
    # Dependencies (contain library .ts/.tsx files we don't want to index)
    'node_modules', 'jspm_packages', 'bower_components',
    # Version control
    '.git', '.svn', '.hg',
    # Build outputs (contain compiled/generated files)
    'dist', 'build', 'out', '.next', '.nuxt', '.output',
    # SvelteKit build output (CRITICAL - these contain minified/compiled code)
    '.svelte-kit',
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
    'logs', 'tmp', 'temp',
    # Thoughts/documentation (not source code)
    'thoughts'
}

def extract_typescript_info(directory):
    """Traverse the directory and extract TypeScript/TSX components, functions, interfaces, types."""
    codebase_info = {}
    all_sources = {}  # Store source code for second pass

    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            # Skip test files - they add noise and aren't useful for navigation
            if '.test.' in file or '.spec.' in file or file.startswith('test_'):
                continue

            if file.endswith(('.ts', '.tsx', '.js', '.jsx', '.svelte')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()

                    all_sources[file_path] = source
                    codebase_info[file_path] = parse_typescript(source, file_path)
                except Exception as e:
                    print(f"Error parsing file {file_path}: {e}")

    # Second pass: build usage graph (where each symbol is used)
    usage_graph = build_usage_graph(codebase_info, all_sources, directory)

    # Attach usage info to each symbol
    for file_path, content in codebase_info.items():
        for component in content.get("components", []):
            key = f"{component['name']}"
            component["used_by"] = usage_graph.get(key, [])
        for func in content.get("functions", []):
            key = f"{func['name']}"
            func["used_by"] = usage_graph.get(key, [])
        for cls in content.get("classes", []):
            key = f"{cls['name']}"
            cls["used_by"] = usage_graph.get(key, [])

    return codebase_info


def build_usage_graph(codebase_info, all_sources, base_directory):
    """Build a reverse lookup: for each exported symbol, find where it's used."""
    usage_graph = defaultdict(list)
    base_path = os.path.abspath(base_directory)

    # Collect all exported symbols from each file
    exported_symbols = {}  # symbol_name -> defining file
    for file_path, content in codebase_info.items():
        rel_path = os.path.relpath(file_path, base_path)
        for component in content.get("components", []):
            if component.get("exported"):
                exported_symbols[component["name"]] = rel_path
        for func in content.get("functions", []):
            if func.get("exported"):
                exported_symbols[func["name"]] = rel_path
        for cls in content.get("classes", []):
            if cls.get("exported"):
                exported_symbols[cls["name"]] = rel_path

    # For each file, find imports and usages
    for file_path, source in all_sources.items():
        rel_path = os.path.relpath(file_path, base_path)

        # Extract imports: import { X, Y } from './path'
        import_pattern = r"import\s+(?:\{([^}]+)\}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(import_pattern, source):
            named_imports = match.group(1)  # { X, Y }
            default_import = match.group(2)  # X
            import_path = match.group(3)

            imported_names = []
            if named_imports:
                # Parse named imports, handling aliases: { X as Y, Z }
                for item in named_imports.split(','):
                    item = item.strip()
                    if ' as ' in item:
                        original = item.split(' as ')[0].strip()
                        imported_names.append(original)
                    else:
                        imported_names.append(item)
            if default_import:
                imported_names.append(default_import)

            # Record usage for each imported symbol
            for name in imported_names:
                if name in exported_symbols:
                    # Avoid self-references
                    if exported_symbols[name] != rel_path:
                        usage_graph[name].append(rel_path)

        # Also check for direct usage of symbols (component invocations like <ComponentName />)
        for symbol_name in exported_symbols:
            # Check for JSX usage: <ComponentName or <ComponentName>
            jsx_pattern = rf'<{symbol_name}[\s/>]'
            if re.search(jsx_pattern, source):
                if exported_symbols[symbol_name] != rel_path:
                    if rel_path not in usage_graph[symbol_name]:
                        usage_graph[symbol_name].append(rel_path)

            # Check for function calls: symbolName(
            call_pattern = rf'\b{symbol_name}\s*\('
            if re.search(call_pattern, source):
                if exported_symbols[symbol_name] != rel_path:
                    if rel_path not in usage_graph[symbol_name]:
                        usage_graph[symbol_name].append(rel_path)

    return dict(usage_graph)


def extract_jsdoc(source, position):
    """Extract JSDoc comment immediately before a given position."""
    # Look backwards from position to find /** ... */
    before = source[:position]
    # Find the last JSDoc comment
    jsdoc_end = before.rfind('*/')
    if jsdoc_end == -1:
        return None

    jsdoc_start = before.rfind('/**', 0, jsdoc_end)
    if jsdoc_start == -1:
        return None

    # Check there's not much between the comment and the function
    # Only whitespace and 'export' keyword allowed
    between = before[jsdoc_end+2:].strip()
    if len(between) > 20:  # Too far away, probably not related
        return None
    # Make sure it's only whitespace/export between comment and function
    if between and not between in ('export', 'export default', 'async'):
        if not all(c in ' \t\n' for c in between.replace('export', '').replace('async', '')):
            return None

    jsdoc = before[jsdoc_start:jsdoc_end+2]

    # Extract the description (first meaningful line, not @param etc)
    lines = jsdoc.split('\n')
    for line in lines:
        line = line.strip().lstrip('/*').lstrip('*').strip()
        # Skip empty, @ tags, and lines that look like param descriptions
        if not line or line.startswith('@') or line.startswith('-'):
            continue
        # Skip lines that are likely continuations of file-level docs
        if 'configurations' in line.lower() or 'automatically' in line.lower():
            continue
        # Truncate long descriptions
        if len(line) > 80:
            line = line[:80] + "..."
        return line
    return None


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
    # Note: Also detect multi-line signatures by just matching the declaration start
    func_component_pattern = r'(?:export\s+)?(?:const|function)\s+([A-Z][a-zA-Z0-9]*)\s*(?::\s*React\.FC)?(?:<[^>]*>)?\s*=?\s*(?:\([^)]*\))?\s*(?::\s*[^=]+)?\s*(?:=>)?\s*\{'
    # Simpler pattern to catch multi-line function declarations (just the start)
    func_component_start_pattern = r'^(?:export\s+(?:default\s+)?)?function\s+([A-Z][a-zA-Z0-9]*)\s*\('

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
        # First try full pattern (single-line signatures)
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

        # Also try simpler pattern for multi-line function declarations
        matches = re.finditer(func_component_start_pattern, line)
        for match in matches:
            name = match.group(1)
            if name and name not in found_components:
                # Calculate position in source for prop extraction
                pos = sum(len(lines[j]) + 1 for j in range(i-1)) + match.start()
                props = extract_props_from_signature(source, pos)
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
                # Extract JSDoc description
                # Calculate position in source from line number
                pos = sum(len(lines[j]) + 1 for j in range(i-1))
                description = extract_jsdoc(source, pos)
                details["functions"].append({
                    "name": name,
                    "line": i,
                    "signature": signature,
                    "description": description,
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
    """Extract function parameter signature - COMPACT version, just params."""
    # Find the opening parenthesis - but make sure it's close to start_pos
    paren_start = source.find('(', start_pos)
    if paren_start == -1 or paren_start > start_pos + 100:
        return None

    # Find the matching closing parenthesis
    paren_end = find_matching_paren(source, paren_start)
    if paren_end == -1:
        return None

    # Get parameters
    params = source[paren_start+1:paren_end].strip()

    # Skip if it looks like a test body or condition was captured
    if '\n' in params or '{' in params or '||' in params or '&&' in params or 'return' in params:
        return None

    # Skip if params look like they contain comments or descriptions (not actual code)
    if '//' in params or 'per minute' in params or 'List of' in params:
        return None

    # Skip if params start with quotes (likely a string argument, not param definition)
    if params.startswith("'") or params.startswith('"'):
        return None

    # Extract just parameter names (remove types and defaults)
    clean_params = []
    for param in params.split(','):
        param = param.strip()
        if not param:
            continue
        # Handle destructuring { x, y }
        if param.startswith('{'):
            # Extract names from destructuring
            inner = param.strip('{}').strip()
            names = [n.split(':')[0].strip() for n in inner.split(',') if n.strip()]
            clean_params.append('{ ' + ', '.join(names[:3]) + ' }')
            continue
        # Get just the name (before : or =)
        name = param.split(':')[0].split('=')[0].strip()
        # Only accept valid identifier names
        if name and len(name) < 30 and name.replace('_', '').replace('$', '').isalnum():
            clean_params.append(name)

    result = ', '.join(clean_params)
    # Truncate if still too long
    if len(result) > 60:
        result = result[:60] + "..."

    return f"({result})" if result else "()"


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


def extract_file_description(source):
    """Extract file-level description from first JSDoc comment."""
    # Look for file-level JSDoc at the start
    if not source.strip().startswith('/**'):
        return None

    jsdoc_end = source.find('*/')
    if jsdoc_end == -1:
        return None

    jsdoc = source[:jsdoc_end+2]
    lines = jsdoc.split('\n')

    for line in lines:
        line = line.strip().lstrip('/*').lstrip('*').strip()
        if not line or line.startswith('@'):
            continue
        # Truncate and return first meaningful line
        if len(line) > 60:
            line = line[:60] + "..."
        return line
    return None


def generate_markdown(codebase_info, output_file, directory):
    """Generate a Markdown file - balanced between compact and informative."""
    from datetime import datetime

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Codebase Index\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Regenerate with `/index_codebase`*\n\n")

        base_path = os.path.abspath(directory)
        SKIP_FUNCS = {'load', 'actions', 'handle'}
        HTTP_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}

        # === SECTION 1: Quick Reference (most used symbols) ===
        f.write("## Most Used Symbols\n\n")

        all_symbols = []
        # Skip both framework functions AND HTTP methods in Most Used
        skip_in_most_used = SKIP_FUNCS | HTTP_METHODS
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)
            for func in content.get("functions", []):
                if func.get("used_by") and func["name"] not in skip_in_most_used:
                    all_symbols.append({
                        "name": func["name"],
                        "file": rel_path,
                        "line": func["line"],
                        "signature": func.get("signature"),
                        "description": func.get("description"),
                        "used_by": func["used_by"]
                    })
            for component in content.get("components", []):
                # Skip HTTP method components (GET, POST, etc) - they're framework boilerplate
                if component.get("used_by") and component["name"] not in skip_in_most_used:
                    all_symbols.append({
                        "name": component["name"],
                        "file": rel_path,
                        "line": component["line"],
                        "signature": f"({component.get('props', '')})" if component.get('props') else "()",
                        "description": f"{component.get('type', 'function')} component",
                        "used_by": component["used_by"]
                    })

        all_symbols.sort(key=lambda x: len(x["used_by"]), reverse=True)

        for sym in all_symbols[:25]:
            sig = sym.get("signature") or "()"
            desc = f" - {sym['description']}" if sym.get("description") else ""
            refs = len(sym["used_by"])
            f.write(f"- **{sym['name']}**{sig} `{sym['file']}:{sym['line']}`{desc} → {refs} refs\n")
        f.write("\n")

        # === SECTION 2: Library File Index (skip routes - they're boilerplate) ===
        f.write("## Library Files\n\n")

        for file_path in sorted(codebase_info.keys()):
            content = codebase_info[file_path]
            rel_path = os.path.relpath(file_path, base_path)

            # Skip route files - load/actions are boilerplate
            if rel_path.startswith('routes/'):
                continue

            # Collect all exports from this file with details
            has_exports = False
            exports_lines = []

            for fn in content.get("functions", []):
                if fn.get("exported"):
                    has_exports = True
                    sig = fn.get("signature") or "()"
                    desc = f" - {fn['description']}" if fn.get("description") else ""
                    exports_lines.append(f"  - `{fn['name']}`{sig} :{fn['line']}{desc}")
                    if fn.get("used_by"):
                        used_by_list = ', '.join(f'`{u}`' for u in fn['used_by'][:5])
                        more = f" +{len(fn['used_by'])-5} more" if len(fn['used_by']) > 5 else ""
                        exports_lines.append(f"    ↳ used by: {used_by_list}{more}")

            for c in content.get("components", []):
                if c.get("exported"):
                    has_exports = True
                    props = f"({c.get('props', '')})" if c.get('props') else "()"
                    exports_lines.append(f"  - `{c['name']}`{props} :{c['line']} - {c.get('type', 'function')} component")
                    if c.get("used_by"):
                        used_by_list = ', '.join(f'`{u}`' for u in c['used_by'][:5])
                        more = f" +{len(c['used_by'])-5} more" if len(c['used_by']) > 5 else ""
                        exports_lines.append(f"    ↳ used by: {used_by_list}{more}")

            for cls in content.get("classes", []):
                if cls.get("exported"):
                    has_exports = True
                    methods = f" methods: {', '.join(cls.get('methods', []))}" if cls.get('methods') else ""
                    exports_lines.append(f"  - `{cls['name']}` :{cls['line']} - class{methods}")
                    if cls.get("used_by"):
                        used_by_list = ', '.join(f'`{u}`' for u in cls['used_by'][:5])
                        more = f" +{len(cls['used_by'])-5} more" if len(cls['used_by']) > 5 else ""
                        exports_lines.append(f"    ↳ used by: {used_by_list}{more}")

            if has_exports:
                f.write(f"### `{rel_path}`\n")
                f.write("\n".join(exports_lines))
                f.write("\n\n")

        # === SECTION 2b: API Endpoints (generic - works for any framework) ===
        f.write("## API Endpoints\n\n")

        api_endpoints = []
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)
            # Detect API files: routes/api/*, api/*, or files with HTTP method exports
            is_api_file = '/api/' in rel_path or rel_path.startswith('api/')

            if is_api_file:
                # Extract route path from file path
                route = '/' + rel_path
                # Clean up framework-specific patterns
                for pattern in ['/+server.js', '/+server.ts', '.js', '.ts', '/route.js', '/route.ts']:
                    route = route.replace(pattern, '')
                # Convert [param] to :param (generic REST style)
                import re as re_module
                route = re_module.sub(r'\[([^\]]+)\]', r':\1', route)

                # Find HTTP methods in this file
                methods = []
                for fn in content.get("functions", []):
                    if fn["name"] in HTTP_METHODS:
                        methods.append(fn["name"])
                for c in content.get("components", []):
                    if c["name"] in HTTP_METHODS:
                        methods.append(c["name"])

                if methods:
                    for method in sorted(set(methods)):
                        api_endpoints.append((method, route, rel_path))

        if api_endpoints:
            # Group by route for cleaner display
            for method, route, file_path in sorted(api_endpoints, key=lambda x: (x[1], x[0])):
                f.write(f"- **{method}** `{route}` → `{file_path}`\n")
        else:
            f.write("*No API endpoints detected*\n")
        f.write("\n")

        # === SECTION 2c: Page routes (compact list) ===
        f.write("## Pages\n\n")

        routes = []
        for file_path in sorted(codebase_info.keys()):
            rel_path = os.path.relpath(file_path, base_path)
            # Detect page routes (SvelteKit, Next.js, etc)
            if 'routes/' in rel_path and '+page' in rel_path and '/api/' not in rel_path:
                route = rel_path.replace('routes/', '/').replace('/+page.server.js', '').replace('/+page.server.ts', '').replace('/+page.js', '').replace('/+page.ts', '')
                if not route:
                    route = '/'
                routes.append(route)
            elif 'pages/' in rel_path and '/api/' not in rel_path:
                # Next.js style
                route = rel_path.replace('pages/', '/').replace('.tsx', '').replace('.ts', '').replace('.jsx', '').replace('.js', '').replace('/index', '')
                if not route:
                    route = '/'
                routes.append(route)

        if routes:
            for route in sorted(set(routes)):
                f.write(f"- `{route}`\n")
        else:
            f.write("*No page routes detected*\n")
        f.write("\n")

        # === SECTION 3: Dependency Graph ===
        f.write("## Dependency Graph\n\n")
        f.write("*Library files by number of dependents:*\n\n")

        file_dependencies = {}
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)
            if rel_path.startswith('routes/'):
                continue
            users = set()
            for c in content.get("components", []):
                users.update(c.get("used_by", []))
            for fn in content.get("functions", []):
                if fn.get("name") not in SKIP_FUNCS:
                    users.update(fn.get("used_by", []))
            if users:
                file_dependencies[rel_path] = sorted(users)

        sorted_deps = sorted(file_dependencies.items(), key=lambda x: len(x[1]), reverse=True)
        for file, users in sorted_deps[:20]:
            f.write(f"- `{file}` ← {len(users)} files\n")

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
- **Most Used Symbols**: Top functions/components by usage count
- **Library Files**: All exports with descriptions and "used by" references
- **API Endpoints**: All REST API routes
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
                import re
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
    print(f"Indexing TypeScript codebase in: {args.directory}")
    extracted_info = extract_typescript_info(args.directory)

    # Create Markdown file
    generate_markdown(extracted_info, args.output, args.directory)
    print(f"Found {len(extracted_info)} TypeScript files")

    # Update CLAUDE.md
    if not args.no_claude_md:
        update_claude_md(args.output, args.directory)


if __name__ == "__main__":
    main()
