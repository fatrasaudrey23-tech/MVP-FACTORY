import os
import sys
import ast
import argparse
from pathlib import Path
from typing import List, Dict, Union, Optional, Any

# --- Utility AST Visitors ---

class CompatibilityVisitor(ast.NodeVisitor):
    """
    AST visitor to check for Python 3.9 compatibility issues.
    """
    def __init__(self) -> None:
        self.issues: List[str] = []

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check for 'sys.gettotalrefcount'
        if isinstance(node.value, ast.Name) and node.value.id == "sys" and node.attr == "gettotalrefcount":
            self.issues.append(
                f"Line {node.lineno}: Usage of 'sys.gettotalrefcount' is deprecated in Python 3.8 "
                f"and removed in Python 3.9. Consider alternative profiling tools."
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check for asyncio functions with 'loop' parameter
        if isinstance(node.func, ast.Attribute) and \
           isinstance(node.func.value, ast.Name) and \
           node.func.value.id == "asyncio" and \
           node.func.attr in ("create_task", "ensure_future", "gather"):
            for keyword in node.keywords:
                if keyword.arg == "loop":
                    self.issues.append(
                        f"Line {node.lineno}: Usage of 'loop' parameter in 'asyncio.{node.func.attr}' "
                        f"is deprecated since Python 3.8 and removed in 3.10. "
                        f"It's not needed in Python 3.9+. Remove it."
                    )
        
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # Check for deprecated generic type hinting (PEP 585, introduced in 3.9)
        # e.g., typing.List[str] -> list[str]
        if isinstance(node.value, ast.Attribute) and \
           isinstance(node.value.value, ast.Name) and \
           node.value.value.id == "typing":
            if node.value.attr in ("List", "Dict", "Tuple", "Set", "FrozenSet", "Type"):
                self.issues.append(
                    f"Line {node.lineno}: Usage of 'typing.{node.value.attr}' is deprecated in Python 3.9 "
                    f"in favor of built-in generics (e.g., '{node.value.attr.lower()}[...]')."
                )
        self.generic_visit(node)

class AutonomyVisitor(ast.NodeVisitor):
    """
    AST visitor to check for file autonomy issues.
    """
    def __init__(self) -> None:
        self.issues: List[str] = []
        self.imported_names: Dict[str, List[int]] = {}  # name -> [lineno, ...]
        self.used_names: Dict[str, List[int]] = {}      # name -> [lineno, ...]
        self.function_defs: List[Union[ast.FunctionDef, ast.AsyncFunctionDef]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            # Store top-level module name for simplicity in unused import check
            self.imported_names.setdefault(name.split('.')[0], []).append(node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names.setdefault(name, []).append(node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Load, ast.Store, ast.Del)): # Only consider actual uses
            self.used_names.setdefault(node.id, []).append(node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_defs.append(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_defs.append(node)
        self.generic_visit(node)

    def finalize_checks(self) -> None:
        # Check for unused imports
        for imported_name, lines in self.imported_names.items():
            if imported_name not in self.used_names:
                for line in lines:
                    self.issues.append(f"Line {line}: Imported name '{imported_name}' appears to be unused.")

        # Check function interfaces
        for node in self.function_defs:
            if not node.args.args and not node.args.kwonlyargs and not node.args.posonlyargs:
                if not node.name.startswith('_'): # Exclude private/internal functions by convention
                    self.issues.append(
                        f"Line {node.lineno}: Function '{node.name}' has no explicit arguments. "
                        "Consider defining clear interfaces."
                    )
            # QA Correction 2: Detect absence of return type annotations
            if node.returns is None:
                self.issues.append(
                    f"Line {node.lineno}: Function '{node.name}' has no explicit return type annotation. "
                    "Consider adding return type hints for clarity."
                )
        
class GlobalVariableCollector(ast.NodeVisitor):
    """
    AST visitor to collect global variables defined or modified at module level.
    """
    def __init__(self) -> None:
        self.global_variables: List[Dict[str, Union[str, int]]] = []
        self._defined_vars: Dict[str, bool] = {} # To track if a var is globally defined

    def visit_Assign(self, node: ast.Assign) -> None:
        # Check if assignment is at module level (not inside a function/class)
        # This visitor is expected to be run on the top-level AST
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id not in self._defined_vars:
                self.global_variables.append({"name": target.id, "line": node.lineno, "type": "definition"})
                self._defined_vars[target.id] = True
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            if name not in self._defined_vars: # If declared global but not yet assigned, still flag
                self.global_variables.append({"name": name, "line": node.lineno, "type": "global_declaration"})
                self._defined_vars[name] = True
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Stop visiting into functions to only collect module-level globals
        pass

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Stop visiting into classes to only collect module-level globals
        pass

class MainBlockChecker(ast.NodeVisitor):
    """
    AST visitor to check for the presence of `if __name__ == "__main__":` block.
    """
    def __init__(self) -> None:
        self.has_main_block: bool = False

    def visit_If(self, node: ast.If) -> None:
        if isinstance(node.test, ast.Compare):
            left = node.test.left
            ops = node.test.ops
            comparators = node.test.comparators

            if (isinstance(left, ast.Name) and left.id == "__name__" and
                len(ops) == 1 and isinstance(ops[0], ast.Eq) and
                len(comparators) == 1 and isinstance(comparators[0], ast.Constant) and
                comparators[0].value == "__main__"):
                self.has_main_block = True
        self.generic_visit(node)


# --- Core Audit Functions ---

def _parse_python_file_to_ast(file_path: Path) -> Optional[ast.Module]:
    """
    Utility function to read a Python file and convert it into its Abstract Syntax Tree.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content, filename=str(file_path))
        return tree
    except SyntaxError as e:
        print(f"Error: Syntax error in {file_path} at line {e.lineno}, column {e.offset}: {e.msg}")
        return None
    except IOError as e:
        print(f"Error: Could not read file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while parsing {file_path}: {e}")
        return None

def _collect_global_variables(tree: ast.Module) -> List[Dict[str, Union[str, int]]]:
    """
    Internal utility to visit the AST and identify global variables defined or modified.
    """
    visitor = GlobalVariableCollector()
    visitor.visit(tree)
    return visitor.global_variables

def _check_main_execution_block(tree: ast.Module) -> bool:
    """
    Internal utility to check for the presence of the `if __name__ == "__main__":` block.
    """
    visitor = MainBlockChecker()
    visitor.visit(tree)
    return visitor.has_main_block

def analyze_python_39_compatibility(tree: ast.Module, file_path: Path) -> List[str]:
    """
    Analyzes the AST of a file for potential compatibility issues with Python 3.9.
    """
    visitor = CompatibilityVisitor()
    visitor.visit(tree)
    return visitor.issues

def analyze_file_autonomy(tree: ast.Module, file_path: Path) -> List[str]:
    """
    Evaluates the degree of autonomy and encapsulation of code within a file.
    """
    issues: List[str] = []

    # Check for __name__ == "__main__" block
    if not _check_main_execution_block(tree):
        issues.append("Missing 'if __name__ == \"__main__\":' block. File may not be designed for autonomous execution.")

    # Identify global variables
    global_vars = _collect_global_variables(tree)
    for var_info in global_vars:
        issues.append(
            f"Line {var_info['line']}: Global variable '{var_info['name']}' detected. "
            "Excessive use of global variables can reduce autonomy and testability."
        )

    # Check clarity of interfaces and unused imports
    visitor = AutonomyVisitor()
    visitor.visit(tree)
    visitor.finalize_checks() # Run post-traversal checks
    issues.extend(visitor.issues)

    return issues

def audit_python_file(file_path: Path) -> Dict[str, Any]:
    """
    Performs a complete audit (3.9 compatibility and autonomy) on a single Python file.
    """
    results: Dict[str, Any] = {
        "file": str(file_path),
        "compat_issues": [],
        "autonomy_issues": [],
        "parse_error": False
    }

    tree = _parse_python_file_to_ast(file_path)
    if tree is None:
        results["parse_error"] = True
        results["compat_issues"].append("File could not be parsed due to syntax errors or I/O issues.")
        results["autonomy_issues"].append("File could not be parsed, autonomy checks skipped.")
        return results

    results["compat_issues"] = analyze_python_39_compatibility(tree, file_path)
    results["autonomy_issues"] = analyze_file_autonomy(tree, file_path)

    return results

def traverse_and_audit_codebase(root_dir: Path) -> Dict[str, Any]:
    """
    Traverses a given directory, identifies all Python files, and launches an audit for each.
    """
    codebase_results: Dict[str, Any] = {
        "summary": {
            "total_files_audited": 0,
            "files_with_compat_issues": 0,
            "files_with_autonomy_issues": 0,
            "files_with_parse_errors": 0,
            "total_compat_issues": 0,
            "total_autonomy_issues": 0
        },
        "file_audits": []
    }

    if not root_dir.is_dir():
        print(f"Error: Directory not found: {root_dir}")
        return codebase_results

    print(f"Starting audit of codebase in: {root_dir}")
    for file_path in root_dir.rglob('*.py'):
        if file_path.is_file():
            codebase_results["summary"]["total_files_audited"] += 1
            print(f"  Auditing {file_path.relative_to(root_dir)}...")
            file_audit_results = audit_python_file(file_path)
            codebase_results["file_audits"].append(file_audit_results)

            if file_audit_results["parse_error"]:
                codebase_results["summary"]["files_with_parse_errors"] += 1
            if file_audit_results["compat_issues"]:
                codebase_results["summary"]["files_with_compat_issues"] += 1
                codebase_results["summary"]["total_compat_issues"] += len(file_audit_results["compat_issues"])
            if file_audit_results["autonomy_issues"]:
                codebase_results["summary"]["files_with_autonomy_issues"] += 1
                codebase_results["summary"]["total_autonomy_issues"] += len(file_audit_results["autonomy_issues"])
    
    print("Audit complete.")
    return codebase_results

def main(args: argparse.Namespace) -> None:
    """
    Main entry point of the script.
    """
    root_dir = Path(args.path)

    audit_results = traverse_and_audit_codebase(root_dir)

    print("\n--- Audit Summary ---")
    summary = audit_results["summary"]
    print(f"Total Python files audited: {summary['total_files_audited']}")
    print(f"Files with parsing errors: {summary['files_with_parse_errors']}")
    print(f"Files with compatibility issues (Python 3.9): {summary['files_with_compat_issues']} ({summary['total_compat_issues']} issues)")
    print(f"Files with autonomy issues: {summary['files_with_autonomy_issues']} ({summary['total_autonomy_issues']} issues)")

    print("\n--- Detailed Audit Results ---")
    found_issues = False
    for file_audit in audit_results["file_audits"]:
        if file_audit["parse_error"] or file_audit["compat_issues"] or file_audit["autonomy_issues"]:
            found_issues = True
            print(f"\nFile: {file_audit['file']}")
            if file_audit["parse_error"]:
                print("  [ERROR] Parsing failed.")
            if file_audit["compat_issues"]:
                print("  Python 3.9 Compatibility Issues:")
                for issue in file_audit["compat_issues"]:
                    print(f"    - {issue}")
            if file_audit["autonomy_issues"]:
                print("  Autonomy Issues:")
                for issue in file_audit["autonomy_issues"]:
                    print(f"    - {issue}")
    
    if not found_issues:
        print("No issues found in audited files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Audit Python codebase for Python 3.9 compatibility and file autonomy."
    )
    parser.add_argument(
        "path",
        type=str,
        help="The root directory of the codebase to audit."
    )
    args = parser.parse_args()
    main(args)