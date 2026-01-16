import os
import ast
import re
import argparse
import sys
from collections import defaultdict
from datetime import datetime

# Cache ast.unparse availability check at module level
HAS_UNPARSE = hasattr(ast, 'unparse')

# Directories to skip during indexing (only directories that might contain .py files)
SKIP_DIRS = {
    # Virtual environments (contain Python files we don't want to index)
    '.venv', 'venv', 'env', '.env', 'ENV',
    # Dependencies
    'node_modules',
    # Version control
    '.git', '.svn', '.hg',
    # Python cache directories
    '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.pytype', '.pyre',
    # Testing directories
    '.tox', '.nox', 'htmlcov', '.hypothesis',
    # Build/distribution directories (may contain generated .py files)
    'dist', 'build', '.eggs', 'eggs', 'lib', 'lib64', 'sdist', 'wheels',
    # Documentation builds (may contain generated .py files)
    'site',
    # IDE/Editor directories (may contain IDE-specific .py files)
    '.vscode', '.idea', '.vs', '.spyderproject', '.spyproject', '.ropeproject',
    # Claude configuration
    '.claude', 'claude-helpers',
    # Logs and temporary directories
    'logs', 'tmp', 'temp',
    # Thoughts/documentation (not source code)
    'thoughts',
    # Test directories
    'tests', 'test',
    # Database migrations (auto-generated)
    'alembic', 'migrations'
}

# HTTP methods for API endpoint detection
HTTP_METHODS = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options'}

# Framework-specific route decorators
ROUTE_DECORATORS = {'route', 'get', 'post', 'put', 'delete', 'patch', 'api_view'}

def safe_unparse(node):
    """Safely unparse an AST node with fallback to str()."""
    return ast.unparse(node) if HAS_UNPARSE else str(node)

def extract_codebase_info(directory):
    """Traverse the directory and extract functions, classes, variables."""
    codebase_info = {}

    # Single pass: extract structure and track calls in one go
    # Store AST trees for call tracking
    ast_trees = {}

    for root, dirs, files in os.walk(directory):
        # Skip excluded directories (modify dirs in-place)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith('.egg-info')]

        for file in files:
            # Skip test files - they add noise and aren't useful for navigation
            if file.startswith('test_') or file.endswith('_test.py') or 'conftest' in file:
                continue

            if file.endswith('.py'):  # Process Python files only
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()  # Read file only once

                    # Parse the AST of the file
                    tree = ast.parse(source)
                    codebase_info[file_path] = parse_ast(tree, file_path)
                    ast_trees[file_path] = tree  # Store for call tracking
                except Exception as e:
                    print(f"Error parsing file {file_path}: {e}")

    # Build index for O(1) lookups during call tracking
    name_index = build_name_index(codebase_info)

    # Track calls using pre-parsed AST trees and index
    for file_path, tree in ast_trees.items():
        try:
            track_calls(tree, file_path, name_index)
        except Exception as e:
            print(f"Error tracking calls in {file_path}: {e}")

    return codebase_info


def build_name_index(codebase_info):
    """Build an index mapping names to their definitions for O(1) lookup."""
    name_index = {}

    for file_path, content in codebase_info.items():
        # Index functions
        for func in content["functions"]:
            name = func["name"]
            if name not in name_index:
                name_index[name] = []
            name_index[name].append(func)

        # Index classes
        for cls in content["classes"]:
            name = cls["name"]
            if name not in name_index:
                name_index[name] = []
            name_index[name].append(cls)

        # Index models
        for model in content["models"]:
            name = model["name"]
            if name not in name_index:
                name_index[name] = []
            name_index[name].append(model)

    return name_index


def extract_short_docstring(docstring):
    """Extract just the first line/sentence of a docstring."""
    if not docstring:
        return None
    # Get first line
    first_line = docstring.split('\n')[0].strip()
    # Truncate if too long
    if len(first_line) > 80:
        first_line = first_line[:80] + "..."
    return first_line


def extract_route_info(decorators):
    """Extract route information from function decorators."""
    routes = []
    for decorator in decorators:
        # Handle @app.route('/path') or @router.get('/path')
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                method = decorator.func.attr.lower()
                if method in HTTP_METHODS or method in ROUTE_DECORATORS:
                    # Extract route path from first argument
                    if decorator.args:
                        if isinstance(decorator.args[0], ast.Constant):
                            route_path = decorator.args[0].value
                            http_method = method.upper() if method in HTTP_METHODS else 'GET'
                            routes.append({'method': http_method, 'path': route_path})
            elif isinstance(decorator.func, ast.Name):
                method = decorator.func.id.lower()
                if method in ROUTE_DECORATORS:
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        routes.append({'method': 'GET', 'path': decorator.args[0].value})
        # Handle @get, @post etc (without call)
        elif isinstance(decorator, ast.Attribute):
            method = decorator.attr.lower()
            if method in HTTP_METHODS:
                routes.append({'method': method.upper(), 'path': None})
    return routes


def parse_ast(tree, file_path):
    """Parse AST to extract classes, functions, and global variables."""
    details = {
        "classes": [],
        "functions": [],
        "variables": [],
        "models": [],
        "api_routes": [],
    }

    # Use iter_child_nodes to avoid nested functions/classes
    for node in ast.iter_child_nodes(tree):
        # Extract class definitions
        if isinstance(node, ast.ClassDef):
            # Check if it's a Pydantic model or regular class
            is_model = any(
                (isinstance(base, ast.Name) and base.id == 'BaseModel') or
                (isinstance(base, ast.Attribute) and base.attr == 'BaseModel')
                for base in node.bases
            )

            class_info = {
                "name": node.name,
                "line": node.lineno,
                "methods": [],
                "docstring": extract_short_docstring(ast.get_docstring(node)),
                "is_model": is_model,
                "fields": [] if is_model else None,
                "called_from": [],
            }

            for class_child in node.body:
                if isinstance(class_child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_info = {
                        "name": class_child.name,
                        "docstring": extract_short_docstring(ast.get_docstring(class_child)),
                        "parameters": extract_function_signature(class_child),
                        "return_type": extract_return_type(class_child),
                    }
                    class_info["methods"].append(method_info)
                elif isinstance(class_child, ast.AnnAssign) and is_model:
                    # Extract Pydantic model fields
                    field_name = class_child.target.id if isinstance(class_child.target, ast.Name) else None
                    field_type = safe_unparse(class_child.annotation)
                    if field_name:
                        class_info["fields"].append({
                            "name": field_name,
                            "type": field_type,
                        })

            if is_model:
                details["models"].append(class_info)
            else:
                details["classes"].append(class_info)

        # Extract function definitions (only top-level)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Check for route decorators
            routes = extract_route_info(node.decorator_list)
            for route in routes:
                route['function'] = node.name
                details["api_routes"].append(route)

            details["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "docstring": extract_short_docstring(ast.get_docstring(node)),
                "parameters": extract_function_signature(node),
                "return_type": extract_return_type(node),
                "called_from": [],
                "is_route": len(routes) > 0,
            })

        # Extract global variables
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    details["variables"].append({
                        "name": target.id,
                        "value": safe_unparse(node.value) if HAS_UNPARSE else None
                    })
        elif isinstance(node, ast.AnnAssign):
            # Extract annotated assignments
            var_name = node.target.id if isinstance(node.target, ast.Name) else None
            var_type = safe_unparse(node.annotation)
            var_value = safe_unparse(node.value) if node.value else None
            if var_name:
                details["variables"].append({
                    "name": var_name,
                    "type": var_type,
                    "value": var_value,
                })

    return details


def extract_function_signature(func_node):
    """Extract function parameters with type annotations."""
    params = []
    args = func_node.args

    # Regular arguments
    for arg in args.args:
        param_info = {"name": arg.arg}
        if arg.annotation:
            param_info["type"] = safe_unparse(arg.annotation)
        params.append(param_info)

    # *args
    if args.vararg:
        param_info = {"name": f"*{args.vararg.arg}"}
        if args.vararg.annotation:
            param_info["type"] = safe_unparse(args.vararg.annotation)
        params.append(param_info)

    # **kwargs
    if args.kwarg:
        param_info = {"name": f"**{args.kwarg.arg}"}
        if args.kwarg.annotation:
            param_info["type"] = safe_unparse(args.kwarg.annotation)
        params.append(param_info)

    return params


def extract_return_type(func_node):
    """Extract function return type annotation."""
    if func_node.returns:
        return safe_unparse(func_node.returns)
    return None


def track_calls(tree, current_file, name_index):
    """Track where functions, classes, and models are called from using indexed lookup."""

    class CallTracker(ast.NodeVisitor):
        def __init__(self, name_index):
            self.current_function = None
            self.current_class = None
            self.name_index = name_index

        def visit_FunctionDef(self, node):
            old_function = self.current_function
            self.current_function = node.name
            self.generic_visit(node)
            self.current_function = old_function

        def visit_AsyncFunctionDef(self, node):
            # Handle async functions the same as regular functions
            old_function = self.current_function
            self.current_function = node.name
            self.generic_visit(node)
            self.current_function = old_function

        def visit_ClassDef(self, node):
            old_class = self.current_class
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = old_class

        def visit_Call(self, node):
            """Track function calls and class/model instantiations."""
            called_name = None

            # Direct function/class call: foo()
            if isinstance(node.func, ast.Name):
                called_name = node.func.id
            # Method call: obj.method() - we track the method name
            elif isinstance(node.func, ast.Attribute):
                called_name = node.func.attr

            if called_name:
                # Determine the context (where it's called from)
                if self.current_function:
                    if self.current_class:
                        context = f"{current_file}::{self.current_class}.{self.current_function}"
                    else:
                        context = f"{current_file}::{self.current_function}"
                elif self.current_class:
                    context = f"{current_file}::{self.current_class}"
                else:
                    context = f"{current_file}::module-level"

                # O(1) lookup using name index instead of nested loops
                if called_name in self.name_index:
                    for item in self.name_index[called_name]:
                        if context not in item["called_from"]:
                            item["called_from"].append(context)

            self.generic_visit(node)

    tracker = CallTracker(name_index)
    tracker.visit(tree)


def generate_file_tree(directory, codebase_info):
    """Generate a visual tree structure of Python files in the codebase."""
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
                and e not in SKIP_DIRS and not e.endswith('.egg-info')]
        files = [e for e in entries if os.path.isfile(os.path.join(current_dir, e))
                 and e.endswith('.py')]

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


def simplify_caller(caller_path, base_path):
    """Simplify a caller path for display (extract just the file path)."""
    # Format is: /path/to/file.py::function or /path/to/file.py::Class.method
    if '::' in caller_path:
        file_part = caller_path.split('::')[0]
    else:
        file_part = caller_path

    # Make relative if possible
    try:
        return os.path.relpath(file_part, base_path)
    except ValueError:
        return file_part


def generate_markdown(codebase_info, output_file, directory):
    """Generate a Markdown file - compact format matching JS/TS indexer."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Codebase Index\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Regenerate with `/index_codebase`*\n\n")

        base_path = os.path.abspath(directory)

        # === SECTION 1: Most Used Symbols ===
        f.write("## Most Used Symbols\n\n")

        all_symbols = []
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)

            # Functions
            for func in content.get("functions", []):
                if func.get("called_from"):
                    params_str = format_parameters(func['parameters'])
                    all_symbols.append({
                        "name": func["name"],
                        "file": rel_path,
                        "line": func.get("line", 0),
                        "signature": f"({params_str})" if params_str else "()",
                        "description": func.get("docstring"),
                        "refs": len(func["called_from"])
                    })

            # Classes
            for cls in content.get("classes", []):
                if cls.get("called_from"):
                    all_symbols.append({
                        "name": cls["name"],
                        "file": rel_path,
                        "line": cls.get("line", 0),
                        "signature": "",
                        "description": cls.get("docstring"),
                        "refs": len(cls["called_from"])
                    })

            # Models
            for model in content.get("models", []):
                if model.get("called_from"):
                    all_symbols.append({
                        "name": model["name"],
                        "file": rel_path,
                        "line": model.get("line", 0),
                        "signature": "",
                        "description": model.get("docstring"),
                        "refs": len(model["called_from"])
                    })

        all_symbols.sort(key=lambda x: x["refs"], reverse=True)

        for sym in all_symbols[:25]:
            desc = f" - {sym['description']}" if sym.get("description") else ""
            line_ref = f":{sym['line']}" if sym.get('line') else ""
            f.write(f"- **{sym['name']}**{sym['signature']} `{sym['file']}{line_ref}`{desc} → {sym['refs']} refs\n")
        f.write("\n")

        # === SECTION 2: Library Files ===
        f.write("## Library Files\n\n")

        for file_path in sorted(codebase_info.keys()):
            content = codebase_info[file_path]
            rel_path = os.path.relpath(file_path, base_path)

            # Collect exports
            has_exports = False
            exports_lines = []

            # Functions (skip routes - they're listed in API Endpoints)
            for func in content.get("functions", []):
                if func.get("is_route"):
                    continue
                has_exports = True
                params_str = format_parameters(func['parameters'])
                sig = f"({params_str})" if params_str else "()"
                desc = f" - {func['docstring']}" if func.get("docstring") else ""
                line_ref = f":{func.get('line', '')}" if func.get('line') else ""
                exports_lines.append(f"  - `{func['name']}`{sig}{line_ref}{desc}")
                if func.get("called_from"):
                    callers = [simplify_caller(c, base_path) for c in func['called_from'][:5]]
                    more = f" +{len(func['called_from'])-5} more" if len(func['called_from']) > 5 else ""
                    exports_lines.append(f"    ↳ used by: {', '.join(f'`{c}`' for c in callers)}{more}")

            # Classes
            for cls in content.get("classes", []):
                has_exports = True
                methods = [m['name'] for m in cls.get('methods', []) if not m['name'].startswith('_')][:5]
                methods_str = f" methods: {', '.join(methods)}" if methods else ""
                desc = f" - {cls['docstring']}" if cls.get("docstring") else ""
                line_ref = f":{cls.get('line', '')}" if cls.get('line') else ""
                exports_lines.append(f"  - `{cls['name']}`{line_ref} - class{methods_str}{desc}")
                if cls.get("called_from"):
                    callers = [simplify_caller(c, base_path) for c in cls['called_from'][:5]]
                    more = f" +{len(cls['called_from'])-5} more" if len(cls['called_from']) > 5 else ""
                    exports_lines.append(f"    ↳ used by: {', '.join(f'`{c}`' for c in callers)}{more}")

            # Models (Pydantic)
            for model in content.get("models", []):
                has_exports = True
                fields = [f['name'] for f in model.get('fields', [])][:5]
                fields_str = f" fields: {', '.join(fields)}" if fields else ""
                desc = f" - {model['docstring']}" if model.get("docstring") else ""
                line_ref = f":{model.get('line', '')}" if model.get('line') else ""
                exports_lines.append(f"  - `{model['name']}`{line_ref} - model{fields_str}{desc}")
                if model.get("called_from"):
                    callers = [simplify_caller(c, base_path) for c in model['called_from'][:5]]
                    more = f" +{len(model['called_from'])-5} more" if len(model['called_from']) > 5 else ""
                    exports_lines.append(f"    ↳ used by: {', '.join(f'`{c}`' for c in callers)}{more}")

            if has_exports:
                f.write(f"### `{rel_path}`\n")
                f.write("\n".join(exports_lines))
                f.write("\n\n")

        # === SECTION 3: API Endpoints ===
        f.write("## API Endpoints\n\n")

        api_endpoints = []
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)
            for route in content.get("api_routes", []):
                api_endpoints.append({
                    'method': route['method'],
                    'path': route.get('path', '/'),
                    'function': route.get('function'),
                    'file': rel_path
                })

        if api_endpoints:
            for ep in sorted(api_endpoints, key=lambda x: (x['path'] or '', x['method'])):
                f.write(f"- **{ep['method']}** `{ep['path']}` → `{ep['file']}:{ep['function']}`\n")
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
            for func in content.get("functions", []):
                for caller in func.get("called_from", []):
                    users.add(simplify_caller(caller, base_path))
            for cls in content.get("classes", []):
                for caller in cls.get("called_from", []):
                    users.add(simplify_caller(caller, base_path))
            for model in content.get("models", []):
                for caller in model.get("called_from", []):
                    users.add(simplify_caller(caller, base_path))
            if users:
                file_dependencies[rel_path] = len(users)

        sorted_deps = sorted(file_dependencies.items(), key=lambda x: x[1], reverse=True)
        for file, count in sorted_deps[:20]:
            f.write(f"- `{file}` ← {count} files\n")

        f.write("\n")

    print(f"Markdown documentation generated: {output_file}")


def format_parameters(params, include_types=False):
    """Format function parameters for display - names only by default."""
    if not params:
        return ""

    formatted = []
    for param in params:
        name = param['name']
        # Skip 'self' and 'cls' params
        if name in ('self', 'cls'):
            continue
        if include_types and 'type' in param:
            formatted.append(f"{name}: {param['type']}")
        else:
            formatted.append(name)

    result = ", ".join(formatted)
    # Truncate if too long
    if len(result) > 50:
        result = result[:50] + "..."
    return result


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
- **Most Used Symbols**: Top functions/classes by usage count
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
        description='Index Python codebase and generate Markdown documentation.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Scan current directory
  %(prog)s ./src                              # Scan relative path directory
  %(prog)s ./cc_wrapper/backend               # Scan nested directory
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
        help='Directory to scan for Python files - supports both relative (./dir, ../dir) and absolute paths (default: ./)'
    )

    parser.add_argument(
        '-o', '--output',
        default='codebase_overview.md',
        help='Output Markdown file (default: codebase_overview.md)'
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
    print(f"Indexing Python codebase in: {args.directory}")
    extracted_info = extract_codebase_info(args.directory)

    # Create Markdown file
    generate_markdown(extracted_info, args.output, args.directory)
    print(f"Found {len(extracted_info)} Python files")

    # Update CLAUDE.md
    if not args.no_claude_md:
        update_claude_md(args.output, args.directory)


if __name__ == "__main__":
    main()