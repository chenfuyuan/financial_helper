"""Guard: CommandHandler in application/commands/, QueryHandler in application/queries/."""

import importlib
import inspect
import pkgutil

from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.application.query_handler import QueryHandler


def _application_package_names() -> list[str]:
    """Return ['app.shared_kernel.application', 'app.modules.example.application', ...]."""
    names = ["app.shared_kernel.application"]
    try:
        app_modules = importlib.import_module("app.modules")
    except ModuleNotFoundError:
        return names
    for info in pkgutil.iter_modules(app_modules.__path__, prefix="app.modules."):
        if info.ispkg:
            pkg_name = info.name + ".application"
            try:
                importlib.import_module(pkg_name)
            except ModuleNotFoundError:
                continue
            names.append(pkg_name)
    return names


def _iter_application_submodules(package_name: str):
    """Yield (module_name, module) for each submodule of the given application package."""
    pkg = importlib.import_module(package_name)
    for info in pkgutil.walk_packages(pkg.__path__, prefix=package_name + "."):
        if info.ispkg:
            continue
        try:
            mod = importlib.import_module(info.name)
        except Exception:
            continue
        yield info.name, mod


def _collect_handler_classes():
    """Collect (class, handler_type) for all CommandHandler/QueryHandler subclasses."""
    command_handlers: list[tuple[type, str]] = []
    query_handlers: list[tuple[type, str]] = []
    for pkg_name in _application_package_names():
        for _mod_name, mod in _iter_application_submodules(pkg_name):
            for _name, cls in inspect.getmembers(mod, predicate=inspect.isclass):
                if not inspect.getmro(cls):
                    continue
                if issubclass(cls, CommandHandler) and cls is not CommandHandler:
                    command_handlers.append((cls, cls.__module__))
                if issubclass(cls, QueryHandler) and cls is not QueryHandler:
                    query_handlers.append((cls, cls.__module__))
    return command_handlers, query_handlers


def test_command_handlers_live_in_commands_dir() -> None:
    """CommandHandler subclasses must live under application/commands/."""
    command_handlers, _ = _collect_handler_classes()
    bad = [c for c, mod in command_handlers if ".commands." not in mod]
    assert not bad, "CommandHandler subclasses must live in application/commands/: " + ", ".join(
        f"{cls.__name__} ({mod})" for cls, mod in bad
    )


def test_query_handlers_live_in_queries_dir() -> None:
    """QueryHandler subclasses must live under application/queries/."""
    _, query_handlers = _collect_handler_classes()
    bad = [c for c, mod in query_handlers if ".queries." not in mod]
    assert not bad, "QueryHandler subclasses must live in application/queries/: " + ", ".join(
        f"{cls.__name__} ({mod})" for cls, mod in bad
    )
