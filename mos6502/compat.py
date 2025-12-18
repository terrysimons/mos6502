#!/usr/bin/env python3
"""Compatibility module for CPython and MicroPython.

This module provides compatibility shims for modules that are available
in CPython but not in MicroPython.
"""

# typing compatibility - must come first as other modules may need it
try:
    from typing import (
        TYPE_CHECKING,
        Optional,
        List,
        Dict,
        Tuple,
        Union,
        Callable,
        Protocol,
        NamedTuple,
        Literal,
        NoReturn,
        Any,
    )
except ImportError:
    # MicroPython stub for typing
    # TYPE_CHECKING is False at runtime, so conditional imports won't execute
    TYPE_CHECKING = False

    # Generic type hints need to support [] subscript syntax
    # We create a class that returns itself when subscripted
    class _TypingStub:
        """A type stub that can be subscripted with []."""
        def __getitem__(self, item):
            return self

        def __call__(self, *args):
            return self

    # Create instances for each typing construct
    Optional = _TypingStub()
    List = _TypingStub()
    Dict = _TypingStub()
    Tuple = _TypingStub()
    Union = _TypingStub()
    Callable = _TypingStub()
    Literal = _TypingStub()
    NoReturn = _TypingStub()
    Any = _TypingStub()

    # Protocol is just a base class for structural subtyping
    class Protocol:
        pass

    # NamedTuple - For MicroPython, create actual namedtuples using collections.namedtuple
    # The class-based syntax (class Foo(NamedTuple): field: type) doesn't work in MicroPython,
    # so we provide a simple tuple base class as a fallback
    try:
        from collections import namedtuple as _namedtuple
        # MicroPython has namedtuple, but the class inheritance syntax doesn't work
        # Just use tuple as base - classes will work but lose field names
        NamedTuple = tuple
    except ImportError:
        # No namedtuple available - just use tuple
        NamedTuple = tuple


# contextlib compatibility
try:
    import contextlib  # CPython
except ImportError:
    import ucontextlib as contextlib  # MicroPython

# logging compatibility
try:
    import logging
except ImportError:
    # MicroPython stub for logging using print
    import sys as _sys

    class _PrintLogger:
        """Simple logger that uses print() for MicroPython."""

        def __init__(self, name=None):
            self._name = name or "root"

        def debug(self, msg, *args):
            print(f"[DEBUG] {self._name}: {msg}")

        def info(self, msg, *args):
            print(f"[INFO] {self._name}: {msg}")

        def warning(self, msg, *args):
            print(f"[WARN] {self._name}: {msg}")

        def error(self, msg, *args):
            print(f"[ERROR] {self._name}: {msg}")

        def critical(self, msg, *args):
            print(f"[CRIT] {self._name}: {msg}")

    class logging:  # noqa: N801
        """Stub logging module for MicroPython using print."""

        # Log level constants
        DEBUG = 10
        INFO = 20
        WARNING = 30
        ERROR = 40
        CRITICAL = 50

        Logger = _PrintLogger

        @staticmethod
        def getLogger(name=None):
            return _PrintLogger(name)

        @staticmethod
        def basicConfig(level=None):
            """No-op for MicroPython - logging config is ignored."""
            pass


# enum compatibility
try:
    import enum
    from enum import Enum, IntEnum, auto
except ImportError:
    # MicroPython stub for enum - minimal implementation
    # Enum members are just their raw values (int or str)
    # This is simpler but loses .name/.value properties

    _auto_value = 0

    def auto():
        """Return an auto-incrementing integer value."""
        global _auto_value
        _auto_value += 1
        return _auto_value

    class Enum:
        """Minimal Enum base class for MicroPython.

        Subclass attributes become enum members as their raw values.
        """
        pass

    class IntEnum(int):
        """Minimal IntEnum base class for MicroPython.

        Subclass attributes become enum members as integers.
        """
        pass

    # Create a stub enum module
    class enum:  # noqa: N801
        Enum = Enum
        IntEnum = IntEnum
        auto = staticmethod(auto)


# dataclasses compatibility
try:
    from dataclasses import dataclass, field

    def make_dataclass(frozen, slots):
        """Create a dataclass decorator with positional args (works on both CPython and MicroPython).

        Usage: @make_dataclass(True, True) instead of @dataclass(frozen=True, slots=True)
        This syntax avoids kwargs which don't work in MicroPython frozen modules.
        """
        def decorator(cls):
            return dataclass(cls, frozen=frozen, slots=slots)
        return decorator

except ImportError:
    # MicroPython stub for dataclasses - generates __init__ from __annotations__

    class _MISSING:
        """Sentinel for missing default values."""
        pass

    MISSING = _MISSING()

    class _Field:
        """Represents a dataclass field with default value info."""
        __slots__ = ('default', 'default_factory')

        def __init__(self, default=MISSING, default_factory=MISSING):
            self.default = default
            self.default_factory = default_factory

    def field(default=MISSING, default_factory=MISSING):  # noqa: N802
        """Create a field descriptor for dataclasses."""
        return _Field(default, default_factory)

    def make_dataclass(frozen, slots):  # noqa: N802
        """Create a dataclass decorator with positional args (for MicroPython frozen modules).

        Usage: @make_dataclass(True, True) instead of @dataclass(frozen=True, slots=True)
        """
        def decorator(cls):
            return dataclass(cls, frozen, slots)
        return decorator

    def dataclass(cls=None, frozen=False, slots=False):  # noqa: N802
        """Minimal dataclass decorator for MicroPython.

        Generates __init__ from __annotations__. Supports default values.
        Note: MicroPython may not fully support __annotations__, so we also
        check __slots__ as a fallback for field names.
        """
        def wrapper(cls):
            # Get field names - try multiple sources for MicroPython compatibility
            # Priority: _field_order_ (explicit) > __annotations__ > __slots__
            if hasattr(cls, '_field_order_'):
                field_names = list(cls._field_order_)
            else:
                annotations = getattr(cls, '__annotations__', {})
                field_names = list(annotations.keys())
                # MicroPython fallback: if no annotations, try __slots__
                if not field_names and hasattr(cls, '__slots__'):
                    field_names = list(cls.__slots__)

            # Get defaults - try _field_defaults_ first, then class attributes
            defaults = {}
            if hasattr(cls, '_field_defaults_'):
                defaults.update(cls._field_defaults_)

            for name in field_names:
                if name not in defaults and hasattr(cls, name):
                    val = getattr(cls, name)
                    if isinstance(val, _Field):
                        if val.default is not MISSING:
                            defaults[name] = val.default
                        elif val.default_factory is not MISSING:
                            defaults[name] = val.default_factory
                    elif not callable(val) and not isinstance(val, (tuple, type)):
                        # Skip class methods, tuples (like _field_order_), and types
                        defaults[name] = val

            # Build __init__ method - positional args only for MicroPython frozen compatibility
            def make_init(field_names, defaults):
                def __init__(self, *args):
                    # Assign positional args first
                    for i, val in enumerate(args):
                        if i < len(field_names):
                            setattr(self, field_names[i], val)

                    # Fill in defaults for remaining fields
                    for i in range(len(args), len(field_names)):
                        name = field_names[i]
                        if name in defaults:
                            default = defaults[name]
                            if callable(default):
                                setattr(self, name, default())
                            else:
                                setattr(self, name, default)

                    # Call __post_init__ if it exists
                    if hasattr(self, '__post_init__'):
                        self.__post_init__()

                return __init__

            cls.__init__ = make_init(field_names, defaults)

            # Add __slots__ if requested (won't work retroactively, but marks intent)
            if slots and not hasattr(cls, '__slots__'):
                cls.__slots__ = tuple(field_names)

            return cls

        if cls is None:
            return wrapper
        return wrapper(cls)


# collections.abc compatibility
try:
    from collections.abc import MutableSequence
except ImportError:
    # MicroPython stub - just use list as base
    MutableSequence = list


def import_module(name, package=None):
    """Import a module by name, compatible with both CPython and MicroPython.

    Arguments:
    ---------
        name: Module name (can be relative like ".module_name")
        package: Package name for relative imports

    Returns:
    -------
        The imported module
    """
    if name.startswith('.'):
        # Relative import - construct full module path
        full_name = package + name
    else:
        full_name = name

    # Use __import__ which works on both CPython and MicroPython
    # For "a.b.c", __import__ returns "a", so we need to traverse
    parts = full_name.split('.')
    module = __import__(full_name)
    for part in parts[1:]:
        module = getattr(module, part)
    return module


# abc compatibility
try:
    from abc import ABC, abstractmethod
except ImportError:
    # MicroPython stub for abc
    class ABC:
        """Abstract Base Class stub for MicroPython."""
        pass

    def abstractmethod(func):
        """Abstract method decorator stub - just returns the function."""
        return func


# pathlib compatibility
try:
    from pathlib import Path
except ImportError:
    # Minimal Path stub for MicroPython
    import os

    class Path:
        """Minimal pathlib.Path implementation for MicroPython."""

        __slots__ = ('_path',)

        def __init__(self, path):
            self._path = str(path)

        def __str__(self):
            return self._path

        def __repr__(self):
            return f"Path({self._path!r})"

        def __truediv__(self, other):
            return Path(self._path + "/" + str(other))

        def __eq__(self, other):
            if isinstance(other, Path):
                return self._path == other._path
            return self._path == str(other)

        def __hash__(self):
            return hash(self._path)

        def exists(self):
            try:
                os.stat(self._path)
                return True
            except OSError:
                return False

        def is_file(self):
            try:
                return (os.stat(self._path)[0] & 0x8000) != 0
            except OSError:
                return False

        def is_dir(self):
            try:
                return (os.stat(self._path)[0] & 0x4000) != 0
            except OSError:
                return False

        def read_bytes(self):
            with open(self._path, "rb") as f:
                return f.read()

        def read_text(self, encoding="utf-8"):
            with open(self._path, "r") as f:
                return f.read()

        def write_bytes(self, data):
            with open(self._path, "wb") as f:
                f.write(data)

        def write_text(self, data, encoding="utf-8"):
            with open(self._path, "w") as f:
                f.write(data)

        @property
        def name(self):
            return self._path.rstrip("/").split("/")[-1]

        @property
        def stem(self):
            name = self.name
            if "." in name:
                return name.rsplit(".", 1)[0]
            return name

        @property
        def suffix(self):
            name = self.name
            if "." in name:
                return "." + name.rsplit(".", 1)[1]
            return ""

        @property
        def parent(self):
            parts = self._path.rstrip("/").split("/")
            if len(parts) <= 1:
                return Path(".")
            return Path("/".join(parts[:-1]))

        def joinpath(self, *args):
            result = self
            for arg in args:
                result = result / arg
            return result

        def iterdir(self):
            for name in os.listdir(self._path):
                yield Path(self._path + "/" + name)

        def glob(self, pattern):
            # Very basic glob - only supports "*" at the end
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                for item in self.iterdir():
                    if item.name.startswith(prefix):
                        yield item
            else:
                # Exact match
                child = self / pattern
                if child.exists():
                    yield child
