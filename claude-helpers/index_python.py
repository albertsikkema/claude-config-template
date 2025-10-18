import os
import ast
import argparse
import sys

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
    'logs', 'tmp', 'temp'
}

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


def parse_ast(tree, file_path):
    """Parse AST to extract classes, functions, and global variables."""
    details = {
        "classes": [],
        "functions": [],
        "variables": [],
        "models": [],
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
                "methods": [],
                "docstring": ast.get_docstring(node),
                "is_model": is_model,
                "fields": [] if is_model else None,
                "called_from": [],
            }

            for class_child in node.body:
                if isinstance(class_child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_info = {
                        "name": class_child.name,
                        "docstring": ast.get_docstring(class_child),
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
            details["functions"].append({
                "name": node.name,
                "docstring": ast.get_docstring(node),
                "parameters": extract_function_signature(node),
                "return_type": extract_return_type(node),
                "called_from": [],
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


def generate_markdown(codebase_info, output_file, directory):
    """Generate a Markdown file with per-page overview format."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Python Codebase Overview\n\n")

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
            if content["models"]:
                overview_items.append(f"**Models:** {len(content['models'])}")
            if content["classes"]:
                overview_items.append(f"**Classes:** {len(content['classes'])}")
            if content["functions"]:
                overview_items.append(f"**Functions:** {len(content['functions'])}")
            if content["variables"]:
                overview_items.append(f"**Variables:** {len(content['variables'])}")
            f.write(" | ".join(overview_items) + "\n\n")

            # Models (Pydantic BaseModel classes)
            if content["models"]:
                f.write("## Models\n\n")
                for model in content["models"]:
                    f.write(f"### `{model['name']}`\n")
                    if model['docstring']:
                        f.write(f"> {model['docstring']}\n\n")

                    if model['fields']:
                        f.write("**Fields:**\n")
                        for field in model['fields']:
                            f.write(f"- `{field['name']}`: `{field['type']}`\n")
                        f.write("\n")

                    if model['methods']:
                        f.write("**Methods:**\n")
                        for method in model['methods']:
                            params_str = format_parameters(method['parameters'])
                            return_str = f" -> `{method['return_type']}`" if method['return_type'] else ""
                            f.write(f"- `{method['name']}({params_str}){return_str}`\n")
                            if method['docstring']:
                                f.write(f"  - {method['docstring']}\n")
                        f.write("\n")

                    if model['called_from']:
                        f.write("**Called from:**\n")
                        for caller in model['called_from']:
                            f.write(f"- `{caller}`\n")
                        f.write("\n")

            # Classes
            if content["classes"]:
                f.write("## Classes\n\n")
                for cls in content["classes"]:
                    f.write(f"### `{cls['name']}`\n")
                    if cls['docstring']:
                        f.write(f"> {cls['docstring']}\n\n")

                    if cls['methods']:
                        f.write("**Methods:**\n")
                        for method in cls["methods"]:
                            params_str = format_parameters(method['parameters'])
                            return_str = f" -> `{method['return_type']}`" if method['return_type'] else ""
                            f.write(f"- `{method['name']}({params_str}){return_str}`\n")
                            if method['docstring']:
                                f.write(f"  - {method['docstring']}\n")
                        f.write("\n")

                    if cls['called_from']:
                        f.write("**Called from:**\n")
                        for caller in cls['called_from']:
                            f.write(f"- `{caller}`\n")
                        f.write("\n")

            # Functions
            if content["functions"]:
                f.write("## Functions\n\n")
                for func in content["functions"]:
                    params_str = format_parameters(func['parameters'])
                    return_str = f" -> `{func['return_type']}`" if func['return_type'] else ""
                    f.write(f"### `{func['name']}({params_str}){return_str}`\n")
                    if func['docstring']:
                        f.write(f"> {func['docstring']}\n\n")
                    else:
                        f.write("\n")

                    if func['parameters']:
                        f.write("**Input:**\n")
                        for param in func['parameters']:
                            param_type = f": `{param['type']}`" if 'type' in param else ""
                            f.write(f"- `{param['name']}`{param_type}\n")
                        f.write("\n")

                    if func['return_type']:
                        f.write(f"**Output:** `{func['return_type']}`\n\n")

                    if func['called_from']:
                        f.write("**Called from:**\n")
                        for caller in func['called_from']:
                            f.write(f"- `{caller}`\n")
                        f.write("\n")

            # Variables
            if content["variables"]:
                f.write("## Variables\n\n")
                for var in content["variables"]:
                    var_type = f": `{var['type']}`" if 'type' in var else ""
                    var_value = f" = `{var['value']}`" if var.get('value') else ""
                    f.write(f"- `{var['name']}`{var_type}{var_value}\n")
                f.write("\n")

            f.write("---\n\n")

    print(f"Markdown documentation generated: {output_file}")


def format_parameters(params):
    """Format function parameters for display."""
    if not params:
        return ""

    formatted = []
    for param in params:
        if 'type' in param:
            formatted.append(f"{param['name']}: {param['type']}")
        else:
            formatted.append(param['name'])

    return ", ".join(formatted)


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


if __name__ == "__main__":
    main()