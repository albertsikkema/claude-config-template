import os
import re
import argparse
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Directories to skip during indexing
SKIP_DIRS = {
    # Build outputs
    'build', 'bin', 'lib', 'out', 'cmake-build-debug', 'cmake-build-release',
    'cmake-build-relwithdebinfo', 'cmake-build-minsizerel', 'Debug', 'Release',
    'x64', 'x86', 'Win32', '.build',
    # Dependencies / Libraries (large C++ frameworks)
    'third_party', 'thirdparty', '3rdparty', 'vendor', 'external', 'deps',
    'dependencies', 'node_modules', 'vcpkg_installed', 'conan',
    'tracktion_engine', 'JUCE', 'juce', 'modules', 'Libs', 'libs',
    # Version control
    '.git', '.svn', '.hg',
    # IDE/Editor directories
    '.vscode', '.idea', '.vs', '.xcode',
    # Claude configuration
    '.claude',
    # Logs and temporary directories
    'logs', 'tmp', 'temp',
    # Memories/documentation (not source code)
    'memories',
    # Generated files
    'generated', 'gen', 'moc', 'ui_', 'qrc_',
    # Package managers
    '_deps', 'packages',
}

# C/C++ file extensions
CPP_EXTENSIONS = {'.cpp', '.cxx', '.cc', '.c++', '.C'}
HEADER_EXTENSIONS = {'.hpp', '.hxx', '.hh', '.h++', '.H', '.h'}
TEMPLATE_EXTENSIONS = {'.ipp', '.inl', '.tpp', '.txx'}
ALL_EXTENSIONS = CPP_EXTENSIONS | HEADER_EXTENSIONS | TEMPLATE_EXTENSIONS

# Test file patterns to skip
TEST_PATTERNS = ['_test.', '_tests.', 'test_', 'tests_', '_unittest.', '_spec.', 'mock_', 'Mock']


def is_test_file(filename):
    """Check if a file is a test file based on naming patterns."""
    for pattern in TEST_PATTERNS:
        if pattern in filename:
            return True
    return False


def extract_cpp_info(directory):
    """Traverse the directory and extract C/C++ classes, structs, functions, etc."""
    codebase_info = {}
    all_sources = {}  # Store source for usage tracking

    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('cmake-build-')]

        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in ALL_EXTENSIONS and not is_test_file(file):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        source = f.read()

                    all_sources[file_path] = source
                    codebase_info[file_path] = parse_cpp(source, file_path)
                except Exception as e:
                    print(f"Error parsing file {file_path}: {e}")

    # Build usage graph
    usage_graph = build_usage_graph(codebase_info, all_sources, directory)

    # Attach usage info to symbols
    for file_path, content in codebase_info.items():
        for cls in content.get("classes", []):
            cls["used_by"] = usage_graph.get(cls["name"], [])
        for struct in content.get("structs", []):
            struct["used_by"] = usage_graph.get(struct["name"], [])
        for func in content.get("functions", []):
            func["used_by"] = usage_graph.get(func["name"], [])
        for enum in content.get("enums", []):
            enum["used_by"] = usage_graph.get(enum["name"], [])

    return codebase_info


def build_usage_graph(codebase_info, all_sources, base_directory):
    """Build a reverse lookup: for each symbol, find where it's used."""
    usage_graph = defaultdict(list)
    base_path = os.path.abspath(base_directory)

    # Collect all exported symbols
    exported_symbols = {}
    for file_path, content in codebase_info.items():
        rel_path = os.path.relpath(file_path, base_path)

        for cls in content.get("classes", []):
            exported_symbols[cls["name"]] = rel_path
        for struct in content.get("structs", []):
            exported_symbols[struct["name"]] = rel_path
        for func in content.get("functions", []):
            # Skip common function names that would cause false positives
            if func["name"] not in {'main', 'get', 'set', 'init', 'reset', 'clear', 'size', 'empty'}:
                exported_symbols[func["name"]] = rel_path
        for enum in content.get("enums", []):
            exported_symbols[enum["name"]] = rel_path

    # Find usages in all files
    for file_path, source in all_sources.items():
        rel_path = os.path.relpath(file_path, base_path)

        for symbol_name, defining_file in exported_symbols.items():
            if defining_file == rel_path:
                continue  # Skip self-references

            # Check for usage patterns
            patterns = [
                rf'\b{re.escape(symbol_name)}\b',  # Direct usage
                rf'\b{re.escape(symbol_name)}\s*[<({{]',  # Template or function call or initializer
                rf'\b{re.escape(symbol_name)}\s*::',  # Namespace/class scope
                rf'::\s*{re.escape(symbol_name)}\b',  # After scope resolution
                rf'new\s+{re.escape(symbol_name)}\b',  # new ClassName
                rf'\*\s*{re.escape(symbol_name)}\b',  # Pointer type
                rf'&\s*{re.escape(symbol_name)}\b',  # Reference type
            ]

            for pattern in patterns:
                try:
                    if re.search(pattern, source):
                        if rel_path not in usage_graph[symbol_name]:
                            usage_graph[symbol_name].append(rel_path)
                        break
                except re.error:
                    continue

    return dict(usage_graph)


def extract_doxygen_doc(lines, line_num):
    """Extract Doxygen/doc comment immediately before a declaration."""
    if line_num <= 1:
        return None

    doc_lines = []
    in_block_comment = False

    # Go back from the line before the declaration
    for i in range(line_num - 2, max(-1, line_num - 20), -1):
        line = lines[i].strip()

        # Check for end of block comment (we're going backwards)
        if line.endswith('*/'):
            in_block_comment = True
            # Get content on this line before */
            content = line[:-2].strip()
            if content and not content.startswith('/*'):
                # Remove leading * if present
                if content.startswith('*'):
                    content = content[1:].strip()
                if content:
                    doc_lines.insert(0, content)
            continue

        # Check for start of block comment
        if in_block_comment:
            if line.startswith('/**') or line.startswith('/*!') or line.startswith('/*'):
                # Get content after /**
                content = line[3:].strip() if line.startswith('/**') or line.startswith('/*!') else line[2:].strip()
                if content:
                    doc_lines.insert(0, content)
                break
            else:
                # Middle of block comment - remove leading *
                content = line
                if content.startswith('*'):
                    content = content[1:].strip()
                if content and not content.startswith('@'):
                    doc_lines.insert(0, content)
            continue

        # Single line doc comments: /// or //!
        if line.startswith('///') or line.startswith('//!'):
            comment = line[3:].strip()
            if comment and not comment.startswith('@'):
                doc_lines.insert(0, comment)
            continue

        # Regular // comments can also be docs if immediately before
        if line.startswith('//') and not line.startswith('///'):
            if not doc_lines:  # Only if we haven't found doc comments yet
                comment = line[2:].strip()
                if comment:
                    doc_lines.insert(0, comment)
            continue

        # Empty line - stop if we have content, continue if not
        if not line:
            if doc_lines:
                break
            continue

        # Non-comment, non-empty line - stop
        break

    if not doc_lines:
        return None

    # Return first meaningful line
    for line in doc_lines:
        # Skip empty, annotation, and separator lines
        if not line:
            continue
        if line.startswith('@') or line.startswith('\\'):
            continue
        # Skip separator lines (==== or ---- or ****)
        if len(line) > 5 and len(set(line.replace(' ', ''))) <= 2:
            continue
        if len(line) > 80:
            line = line[:80] + "..."
        return line
    return None


def parse_cpp(source, file_path):
    """Parse C/C++ source to extract classes, structs, functions, enums, etc."""
    details = {
        "includes": [],
        "namespaces": [],
        "classes": [],
        "structs": [],
        "functions": [],
        "enums": [],
        "typedefs": [],
        "macros": [],
    }

    lines = source.split('\n')

    # Track current namespace context
    current_namespace = None
    brace_depth = 0
    namespace_depth = 0

    # Patterns
    include_pattern = r'^#include\s*[<"]([^>"]+)[>"]'
    namespace_pattern = r'^namespace\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\{?'
    class_pattern = r'^(?:template\s*<[^>]*>\s*)?class\s+(?:__attribute__\s*\([^)]*\)\s*)?([A-Z][a-zA-Z0-9_]*)\s*(?:final\s*)?(?::\s*(?:public|protected|private)\s+[^{]+)?\s*\{?'
    struct_pattern = r'^(?:template\s*<[^>]*>\s*)?struct\s+([A-Z][a-zA-Z0-9_]*)\s*(?::\s*(?:public|protected|private)\s+[^{]+)?\s*\{?'
    enum_pattern = r'^enum\s+(?:class\s+)?([A-Z][a-zA-Z0-9_]*)\s*(?::\s*[a-zA-Z_][a-zA-Z0-9_:]*)?\s*\{?'
    typedef_pattern = r'^typedef\s+.+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;'
    using_type_pattern = r'^using\s+([A-Z][a-zA-Z0-9_]*)\s*='
    macro_pattern = r'^#define\s+([A-Z][A-Z0-9_]*)\s*(?:\(|[^(])'

    # Function patterns - more permissive
    # Matches: ReturnType FunctionName(params) or ReturnType ClassName::FunctionName(params)
    function_pattern = r'^(?:(?:static|inline|virtual|explicit|constexpr|const|extern|friend|override)\s+)*([a-zA-Z_][a-zA-Z0-9_:<>,\s\*&]*?)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*(?:const|override|final|noexcept|\s)*(?:\{|;|$)'

    # Method definition with class scope
    method_def_pattern = r'^(?:(?:static|inline|virtual|explicit|constexpr|const)\s+)*([a-zA-Z_][a-zA-Z0-9_:<>,\s\*&]*?)\s+([a-zA-Z_][a-zA-Z0-9_]+)::([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)'

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip empty lines and pure comment lines for main parsing
        if not stripped or stripped.startswith('//'):
            continue

        # Include statements
        match = re.match(include_pattern, stripped)
        if match:
            details["includes"].append(match.group(1))
            continue

        # Namespace
        match = re.match(namespace_pattern, stripped)
        if match:
            ns_name = match.group(1)
            if ns_name not in ['std', 'detail', 'internal', 'impl']:
                details["namespaces"].append({
                    "name": ns_name,
                    "line": i
                })
            continue

        # Macros (only uppercase macros, likely constants or important macros)
        match = re.match(macro_pattern, stripped)
        if match:
            macro_name = match.group(1)
            # Skip common/unimportant macros
            if macro_name not in {'NDEBUG', 'DEBUG', 'NULL', 'TRUE', 'FALSE'}:
                details["macros"].append({
                    "name": macro_name,
                    "line": i
                })
            continue

        # Typedef
        match = re.match(typedef_pattern, stripped)
        if match:
            details["typedefs"].append({
                "name": match.group(1),
                "line": i
            })
            continue

        # Using type alias
        match = re.match(using_type_pattern, stripped)
        if match:
            details["typedefs"].append({
                "name": match.group(1),
                "line": i
            })
            continue

        # Class definition
        match = re.match(class_pattern, stripped)
        if match:
            class_name = match.group(1)
            # Skip forward declarations
            if not stripped.endswith(';') or '{' in stripped:
                members = extract_class_members(lines, i)
                doc = extract_doxygen_doc(lines, i)
                details["classes"].append({
                    "name": class_name,
                    "line": i,
                    "methods": members.get("methods", []),
                    "members": members.get("members", []),
                    "doc": doc
                })
            continue

        # Struct definition
        match = re.match(struct_pattern, stripped)
        if match:
            struct_name = match.group(1)
            # Skip forward declarations
            if not stripped.endswith(';') or '{' in stripped:
                members = extract_class_members(lines, i)
                doc = extract_doxygen_doc(lines, i)
                details["structs"].append({
                    "name": struct_name,
                    "line": i,
                    "methods": members.get("methods", []),
                    "members": members.get("members", []),
                    "doc": doc
                })
            continue

        # Enum definition
        match = re.match(enum_pattern, stripped)
        if match:
            enum_name = match.group(1)
            values = extract_enum_values(lines, i)
            doc = extract_doxygen_doc(lines, i)
            details["enums"].append({
                "name": enum_name,
                "line": i,
                "values": values,
                "doc": doc
            })
            continue

        # Method definition (ClassName::methodName)
        match = re.match(method_def_pattern, stripped)
        if match:
            # This is a method implementation, we track it differently
            # but we don't add it as a standalone function
            continue

        # Function definition (top-level)
        match = re.match(function_pattern, stripped)
        if match:
            return_type = match.group(1).strip()
            func_name = match.group(2)
            params = match.group(3).strip()

            # Skip if it looks like a method (contains ::)
            if '::' in return_type:
                continue

            # Skip constructors/destructors (no return type or name matches common patterns)
            if not return_type or return_type in ['if', 'for', 'while', 'switch', 'return']:
                continue

            # Skip main if it's just a simple main
            if func_name == 'main':
                continue

            doc = extract_doxygen_doc(lines, i)
            signature = format_cpp_signature(params)
            details["functions"].append({
                "name": func_name,
                "return_type": return_type,
                "signature": signature,
                "line": i,
                "doc": doc
            })
            continue

    return details


def extract_class_members(lines, start_line):
    """Extract methods and member variables from a class/struct definition."""
    members = {"methods": [], "members": []}
    brace_count = 0
    found_open_brace = False
    current_access = "private"  # Default for class

    # Check if it's a struct (default public) or class (default private)
    if 'struct' in lines[start_line - 1]:
        current_access = "public"

    # Method pattern inside class
    method_pattern = r'^\s*(?:(?:static|inline|virtual|explicit|constexpr|const)\s+)*([a-zA-Z_][a-zA-Z0-9_:<>,\s\*&]*?)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)'

    # Member variable pattern
    member_pattern = r'^\s*([a-zA-Z_][a-zA-Z0-9_:<>,\s\*&]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|;|\{)'

    for i in range(start_line - 1, min(len(lines), start_line + 200)):
        line = lines[i]
        stripped = line.strip()

        # Track braces
        brace_count += line.count('{') - line.count('}')
        if '{' in line:
            found_open_brace = True

        # If we've closed all braces, we're done
        if found_open_brace and brace_count <= 0:
            break

        # Skip lines before the opening brace
        if not found_open_brace:
            continue

        # Access specifiers
        if stripped in ['public:', 'protected:', 'private:']:
            current_access = stripped[:-1]
            continue

        # Skip comments and empty lines
        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Look for methods (only public ones for documentation)
        if current_access == "public":
            match = re.match(method_pattern, stripped)
            if match:
                return_type = match.group(1).strip()
                method_name = match.group(2)
                params = match.group(3).strip()

                # Skip constructors/destructors and operators
                if return_type and not method_name.startswith('operator') and method_name not in ['if', 'for', 'while']:
                    members["methods"].append({
                        "name": method_name,
                        "return_type": return_type,
                        "params": format_cpp_signature(params)
                    })
                continue

            # Look for member variables (only a few for documentation)
            if len(members["members"]) < 5:
                match = re.match(member_pattern, stripped)
                if match:
                    var_type = match.group(1).strip()
                    var_name = match.group(2)
                    # Skip if it looks like a function
                    if '(' not in var_type and var_name not in ['if', 'for', 'while', 'return']:
                        members["members"].append({
                            "name": var_name,
                            "type": var_type
                        })

    return members


def extract_enum_values(lines, start_line):
    """Extract values from an enum definition."""
    values = []
    brace_count = 0
    found_open_brace = False

    for i in range(start_line - 1, min(len(lines), start_line + 50)):
        line = lines[i]
        stripped = line.strip()

        # Track braces
        if '{' in line:
            brace_count += line.count('{')
            found_open_brace = True
        if '}' in line:
            brace_count -= line.count('}')

        # If we've closed all braces, we're done
        if found_open_brace and brace_count <= 0:
            break

        # Skip lines before/with the opening brace
        if not found_open_brace or '{' in line:
            continue

        # Skip comments
        if stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Extract enum values
        # Remove trailing comma and any assignment
        value_match = re.match(r'([A-Za-z_][A-Za-z0-9_]*)', stripped)
        if value_match:
            values.append(value_match.group(1))

        # Limit to first 10 values
        if len(values) >= 10:
            break

    return values


def format_cpp_signature(params):
    """Format C++ function parameters - extract just parameter names."""
    if not params or params.strip() == 'void':
        return "()"

    # Split by comma (but not commas inside templates)
    param_names = []
    depth = 0
    current_param = ""

    for char in params:
        if char in '<(':
            depth += 1
            current_param += char
        elif char in '>)':
            depth -= 1
            current_param += char
        elif char == ',' and depth == 0:
            # Process current param
            name = extract_param_name(current_param.strip())
            if name:
                param_names.append(name)
            current_param = ""
        else:
            current_param += char

    # Process last param
    if current_param.strip():
        name = extract_param_name(current_param.strip())
        if name:
            param_names.append(name)

    result = ', '.join(param_names)
    if len(result) > 40:
        result = result[:40] + "..."
    return f"({result})"


def extract_param_name(param):
    """Extract parameter name from a C++ parameter declaration."""
    # Remove default value
    if '=' in param:
        param = param[:param.index('=')].strip()

    # Handle common patterns:
    # const Type& name, Type* name, Type name, etc.
    # The name is usually the last identifier

    # Remove array brackets
    param = re.sub(r'\[[^\]]*\]', '', param)

    # Split by common separators and get last word
    parts = re.split(r'[\s\*&]+', param)
    parts = [p for p in parts if p and not p.startswith('const') and p != 'volatile']

    if parts:
        last_part = parts[-1]
        # Check if it's a valid identifier (not a type keyword)
        if re.match(r'^[a-z_][a-zA-Z0-9_]*$', last_part) and last_part not in ['int', 'float', 'double', 'char', 'void', 'bool', 'auto', 'size_t']:
            return last_part

    return None


def generate_markdown(codebase_info, output_file, directory):
    """Generate a Markdown file - compact format matching other indexers."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Codebase Index\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Regenerate with `/index_codebase`*\n\n")

        base_path = os.path.abspath(directory)

        # === SECTION 1: Most Used Symbols ===
        f.write("## Most Used Symbols\n\n")

        all_symbols = []
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)

            # Classes
            for cls in content.get("classes", []):
                if cls.get("used_by"):
                    all_symbols.append({
                        "name": cls["name"],
                        "file": rel_path,
                        "line": cls["line"],
                        "signature": "",
                        "description": cls.get("doc"),
                        "type": "class",
                        "refs": len(cls["used_by"])
                    })

            # Structs
            for struct in content.get("structs", []):
                if struct.get("used_by"):
                    all_symbols.append({
                        "name": struct["name"],
                        "file": rel_path,
                        "line": struct["line"],
                        "signature": "",
                        "description": struct.get("doc"),
                        "type": "struct",
                        "refs": len(struct["used_by"])
                    })

            # Functions
            for func in content.get("functions", []):
                if func.get("used_by"):
                    all_symbols.append({
                        "name": func["name"],
                        "file": rel_path,
                        "line": func["line"],
                        "signature": func.get("signature", "()"),
                        "description": func.get("doc"),
                        "type": "func",
                        "refs": len(func["used_by"])
                    })

            # Enums
            for enum in content.get("enums", []):
                if enum.get("used_by"):
                    all_symbols.append({
                        "name": enum["name"],
                        "file": rel_path,
                        "line": enum["line"],
                        "signature": "",
                        "description": enum.get("doc"),
                        "type": "enum",
                        "refs": len(enum["used_by"])
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

            exports_lines = []

            # Classes
            for cls in content.get("classes", []):
                methods = [m['name'] for m in cls.get('methods', [])][:4]
                methods_str = f" methods: {', '.join(methods)}" if methods else ""
                desc = f" - {cls['doc']}" if cls.get("doc") else ""
                exports_lines.append(f"  - `{cls['name']}`:{cls['line']} - class{methods_str}{desc}")
                if cls.get("used_by"):
                    used_by = ', '.join(f'`{u}`' for u in cls['used_by'][:5])
                    more = f" +{len(cls['used_by'])-5} more" if len(cls['used_by']) > 5 else ""
                    exports_lines.append(f"    ↳ used by: {used_by}{more}")

            # Structs
            for struct in content.get("structs", []):
                members = [m['name'] for m in struct.get('members', [])][:4]
                members_str = f" members: {', '.join(members)}" if members else ""
                desc = f" - {struct['doc']}" if struct.get("doc") else ""
                exports_lines.append(f"  - `{struct['name']}`:{struct['line']} - struct{members_str}{desc}")
                if struct.get("used_by"):
                    used_by = ', '.join(f'`{u}`' for u in struct['used_by'][:5])
                    more = f" +{len(struct['used_by'])-5} more" if len(struct['used_by']) > 5 else ""
                    exports_lines.append(f"    ↳ used by: {used_by}{more}")

            # Enums
            for enum in content.get("enums", []):
                values = enum.get('values', [])[:4]
                values_str = f" values: {', '.join(values)}" if values else ""
                desc = f" - {enum['doc']}" if enum.get("doc") else ""
                exports_lines.append(f"  - `{enum['name']}`:{enum['line']} - enum{values_str}{desc}")
                if enum.get("used_by"):
                    used_by = ', '.join(f'`{u}`' for u in enum['used_by'][:5])
                    more = f" +{len(enum['used_by'])-5} more" if len(enum['used_by']) > 5 else ""
                    exports_lines.append(f"    ↳ used by: {used_by}{more}")

            # Functions
            for func in content.get("functions", []):
                sig = func.get("signature", "()")
                ret = func.get("return_type", "")
                ret_str = f" -> {ret}" if ret else ""
                desc = f" - {func['doc']}" if func.get("doc") else ""
                exports_lines.append(f"  - `{func['name']}`{sig}{ret_str}:{func['line']}{desc}")
                if func.get("used_by"):
                    used_by = ', '.join(f'`{u}`' for u in func['used_by'][:5])
                    more = f" +{len(func['used_by'])-5} more" if len(func['used_by']) > 5 else ""
                    exports_lines.append(f"    ↳ used by: {used_by}{more}")

            if exports_lines:
                f.write(f"### `{rel_path}`\n")
                f.write("\n".join(exports_lines))
                f.write("\n\n")

        # === SECTION 3: Include Dependencies ===
        f.write("## Include Dependencies\n\n")
        f.write("*Most commonly included headers:*\n\n")

        include_counts = defaultdict(int)
        for file_path, content in codebase_info.items():
            for inc in content.get("includes", []):
                include_counts[inc] += 1

        sorted_includes = sorted(include_counts.items(), key=lambda x: x[1], reverse=True)
        for inc, count in sorted_includes[:20]:
            f.write(f"- `{inc}` ← {count} files\n")
        f.write("\n")

        # === SECTION 4: Dependency Graph ===
        f.write("## Dependency Graph\n\n")
        f.write("*Files by number of dependents:*\n\n")

        file_dependencies = {}
        for file_path, content in codebase_info.items():
            rel_path = os.path.relpath(file_path, base_path)
            users = set()
            for cls in content.get("classes", []):
                users.update(cls.get("used_by", []))
            for struct in content.get("structs", []):
                users.update(struct.get("used_by", []))
            for func in content.get("functions", []):
                users.update(func.get("used_by", []))
            for enum in content.get("enums", []):
                users.update(enum.get("used_by", []))
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
- **Most Used Symbols**: Top classes/structs/functions by usage count
- **Library Files**: All exports with descriptions and "used by" references
- **Include Dependencies**: Most commonly included headers
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
        description='Index C/C++ codebase and generate Markdown documentation.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Scan current directory
  %(prog)s ./src                              # Scan relative path directory
  %(prog)s ./backend/services                 # Scan nested directory
  %(prog)s /absolute/path/to/project          # Scan absolute path
  %(prog)s ./src -o docs.md                   # Scan directory with custom output file
  %(prog)s --help                             # Show this help message

Supported file extensions:
  C++: .cpp, .cxx, .cc, .c++, .C
  Headers: .hpp, .hxx, .hh, .h++, .H, .h
  Templates: .ipp, .inl, .tpp, .txx

Note: Both relative paths (./dir, ../dir) and absolute paths (/path/to/dir) are supported.
        """
    )

    parser.add_argument(
        'directory',
        nargs='?',
        default='./',
        help='Directory to scan for C/C++ files - supports both relative (./dir, ../dir) and absolute paths (default: ./)'
    )

    parser.add_argument(
        '-o', '--output',
        default='codebase_overview_cpp.md',
        help='Output Markdown file (default: codebase_overview_cpp.md)'
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
    print(f"Indexing C/C++ codebase in: {args.directory}")
    extracted_info = extract_cpp_info(args.directory)

    # Create Markdown file
    generate_markdown(extracted_info, args.output, args.directory)
    print(f"Found {len(extracted_info)} C/C++ files")

    # Update CLAUDE.md
    if not args.no_claude_md:
        update_claude_md(args.output, args.directory)


if __name__ == "__main__":
    main()
