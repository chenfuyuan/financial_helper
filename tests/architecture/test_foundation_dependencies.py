"""Guard: foundation 模块不应依赖业务模块。"""

import ast
import importlib
import pkgutil
from pathlib import Path


def _get_foundation_modules() -> list[str]:
    """获取 foundation 模块下所有子模块。"""
    modules = []
    try:
        foundation_pkg = importlib.import_module("app.modules.foundation")
    except ModuleNotFoundError:
        return modules

    for info in pkgutil.walk_packages(foundation_pkg.__path__, prefix="app.modules.foundation."):
        if info.ispkg:
            continue
        modules.append(info.name)
    return modules


def _get_imports_from_file(file_path: Path) -> list[str]:
    """解析文件中的所有 import 语句，返回导入的模块名列表。"""
    imports = []
    try:
        content = file_path.read_text()
        tree = ast.parse(content)
    except (SyntaxError, FileNotFoundError):
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def test_foundation_does_not_import_business_modules() -> None:
    """验证 foundation 模块不 import 任何业务模块。"""
    foundation_path = Path(__file__).parent.parent.parent / "src" / "app" / "modules" / "foundation"

    if not foundation_path.exists():
        # 如果 foundation 目录不存在，测试跳过
        return

    business_module_prefixes = ["app.modules.data_engineering", "app.modules."]
    violations = []

    for py_file in foundation_path.rglob("*.py"):
        imports = _get_imports_from_file(py_file)
        for imp in imports:
            for prefix in business_module_prefixes:
                if imp.startswith(prefix) and not imp.startswith("app.modules.foundation"):
                    violations.append(f"{py_file.relative_to(foundation_path.parent.parent.parent)}: import {imp}")

    assert not violations, (
        "Foundation module should not import business modules. "
        "Violations found:\n" + "\n".join(violations)
    )
