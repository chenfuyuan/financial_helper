#!/usr/bin/env python3
"""从 example 模块复制并重命名，生成新业务模块脚手架。

用法:
    python scripts/new_module.py <module_slug> [--aggregate NAME]
    make new-module name=<module_slug>

示例:
    python scripts/new_module.py product
    python scripts/new_module.py order --aggregate Order

生成后需手动:
  1. 在 app/interfaces/main.py 中注册 router 与 lifespan 中的 handlers
  2. 在 tests/api/conftest.py 的 _register_handlers 中注册新模块的 handlers
  3. 按需修改聚合字段、表名、路由前缀
  4. 运行 make migrate-create msg="add <module> tables"
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = "example"
SOURCE_DIRS = [
    ROOT / "src" / "app" / "modules" / EXAMPLE,
    ROOT / "tests" / "unit" / "modules" / EXAMPLE,
    ROOT / "tests" / "api" / "modules" / EXAMPLE,
]


def slug_to_pascal(slug: str) -> str:
    """product -> Product, order-item -> OrderItem."""
    return "".join(part.capitalize() for part in slug.replace("-", "_").split("_"))


def main() -> int:
    parser = argparse.ArgumentParser(description="New DDD module scaffold from example")
    parser.add_argument(
        "name",
        metavar="MODULE_SLUG",
        help="Module directory name (e.g. product, order)",
    )
    parser.add_argument(
        "--aggregate",
        default=None,
        help="Aggregate name in PascalCase (default: capitalize MODULE_SLUG)",
    )
    args = parser.parse_args()

    module_slug = args.name.strip().lower().replace(" ", "-")
    if not re.match(r"^[a-z][a-z0-9_-]*$", module_slug):
        print(
            "Error: MODULE_SLUG must be lowercase letters, numbers, hyphen/underscore.",
            file=sys.stderr,
        )
        return 1
    if module_slug == EXAMPLE:
        print("Error: MODULE_SLUG cannot be 'example'.", file=sys.stderr)
        return 1

    aggregate_name = args.aggregate.strip() if args.aggregate else slug_to_pascal(module_slug)
    aggregate_slug = aggregate_name.lower()
    plural = module_slug + "s"  # naive plural; adjust in code if needed

    # Replacements (order: longer / specific first to avoid double-replace)
    replacements = [
        ("app.modules." + EXAMPLE, "app.modules." + module_slug),
        ("Note", aggregate_name),
        ("notes", plural),
        ("note", aggregate_slug),
    ]

    for src_dir in SOURCE_DIRS:
        if not src_dir.exists():
            print(f"Error: template dir not found: {src_dir}", file=sys.stderr)
            return 1
        dest_dir = src_dir.parent / module_slug
        if dest_dir.exists():
            print(f"Error: target already exists: {dest_dir}", file=sys.stderr)
            return 1

    for src_dir in SOURCE_DIRS:
        dest_dir = src_dir.parent / module_slug
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=False)

        # Rename files: any filename containing "note" -> aggregate_slug
        for path in sorted(dest_dir.rglob("*"), key=lambda p: (-len(p.parts), p)):
            if path.is_file() and "note" in path.name:
                new_name = path.name.replace("note", aggregate_slug)
                if new_name != path.name:
                    new_path = path.parent / new_name
                    path.rename(new_path)
                    path = new_path

        # Replace content in .py files
        for py_path in dest_dir.rglob("*.py"):
            text = py_path.read_text(encoding="utf-8")
            for old, new in replacements:
                text = text.replace(old, new)
            py_path.write_text(text, encoding="utf-8")

    print(f"Scaffolded module: {module_slug} (aggregate: {aggregate_name})")
    print("Next steps:")
    print("  1. Register router and handlers in app/interfaces/main.py")
    print("  2. Register handlers in tests/api/conftest.py _register_handlers()")
    print("  3. Adjust aggregate fields, table name, route prefix if needed")
    print('  4. make migrate-create msg="add ' + module_slug + ' tables"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
