"""Guard: domain entity/value-object semantics must inherit Entity/AggregateRoot or ValueObject."""

import dataclasses
import importlib
import inspect
import pkgutil


def _domain_package_names() -> list[str]:
    """Return ['app.shared_kernel.domain', 'app.modules.example.domain', ...]."""
    names = ["app.shared_kernel.domain"]
    try:
        app_modules = importlib.import_module("app.modules")
    except ModuleNotFoundError:
        return names
    for info in pkgutil.iter_modules(app_modules.__path__, prefix="app.modules."):
        if info.ispkg:
            pkg_name = info.name + ".domain"
            try:
                importlib.import_module(pkg_name)
            except ModuleNotFoundError:
                continue
            names.append(pkg_name)
    return names


def _iter_domain_submodules(package_name: str):
    """Yield (module_name, module) for each submodule (excluding package __init__)."""
    pkg = importlib.import_module(package_name)
    for info in pkgutil.walk_packages(pkg.__path__, prefix=package_name + "."):
        if info.ispkg:
            continue
        try:
            mod = importlib.import_module(info.name)
        except Exception:
            continue
        yield info.name, mod


def _has_id(cls: type) -> bool:
    return (
        "id" in getattr(cls, "__annotations__", {})
        or any("id" in getattr(b, "__annotations__", {}) for b in inspect.getmro(cls)[1:])
        or "id" in getattr(cls, "__dataclass_fields__", {})
    )


def _is_frozen_dataclass(cls: type) -> bool:
    params = getattr(cls, "__dataclass_params__", None)
    return bool(params and getattr(params, "frozen", False))


def _is_entity_semantics(cls: type) -> bool:
    """Heuristic: has id and (dataclass not frozen); exclude *Event/*Exception by name."""
    name = cls.__name__
    if name.endswith("Event") or name.endswith("Exception"):
        return False
    if not _has_id(cls):
        return False
    return not (dataclasses.is_dataclass(cls) and _is_frozen_dataclass(cls))


def _is_value_object_semantics(cls: type) -> bool:
    """Heuristic: dataclass frozen, no id, name not *Event/*Exception."""
    name = cls.__name__
    if name.endswith("Event") or name.endswith("Exception"):
        return False
    if not dataclasses.is_dataclass(cls) or not _is_frozen_dataclass(cls):
        return False
    return not _has_id(cls)


def _skip_class(cls: type) -> bool:
    """Exclude base classes, Repository, DomainEvent, Exception."""
    from app.shared_kernel.domain.aggregate_root import AggregateRoot
    from app.shared_kernel.domain.domain_event import DomainEvent
    from app.shared_kernel.domain.entity import Entity
    from app.shared_kernel.domain.repository import Repository
    from app.shared_kernel.domain.value_object import ValueObject

    if cls in (Entity, AggregateRoot, ValueObject, DomainEvent):
        return True
    return (
        issubclass(cls, Repository)
        or issubclass(cls, DomainEvent)
        or issubclass(cls, BaseException)
    )


def _collect_domain_classes():
    """Yield (cls, module_name) for domain classes that are not excluded."""
    for pkg_name in _domain_package_names():
        for mod_name, mod in _iter_domain_submodules(pkg_name):
            for _name, cls in inspect.getmembers(mod, predicate=inspect.isclass):
                if _skip_class(cls):
                    continue
                if cls.__module__ != mod_name:
                    continue
                yield cls, mod_name


def test_entity_semantics_inherit_entity_or_aggregate_root() -> None:
    """Domain classes with entity semantics must inherit Entity or AggregateRoot."""
    from app.shared_kernel.domain.aggregate_root import AggregateRoot
    from app.shared_kernel.domain.entity import Entity

    bad = []
    for cls, mod in _collect_domain_classes():
        if not _is_entity_semantics(cls):
            continue
        if not (issubclass(cls, Entity) or issubclass(cls, AggregateRoot)):
            bad.append((cls, mod))
    msg = (
        "Domain classes with entity semantics (has id, not frozen) must inherit "
        "Entity or AggregateRoot: " + ", ".join(f"{c.__name__} in {m}" for c, m in bad)
    )
    assert not bad, msg


def test_value_object_semantics_inherit_value_object() -> None:
    """Domain classes with value-object semantics must inherit ValueObject."""
    from app.shared_kernel.domain.value_object import ValueObject

    bad = []
    for cls, mod in _collect_domain_classes():
        if not _is_value_object_semantics(cls):
            continue
        if not issubclass(cls, ValueObject):
            bad.append((cls, mod))
    assert not bad, (
        "Domain classes with value-object semantics (frozen, no id) must inherit ValueObject: "
        + ", ".join(f"{c.__name__} in {m}" for c, m in bad)
    )
