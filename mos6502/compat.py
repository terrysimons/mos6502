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

    # NamedTuple - use collections.namedtuple as the base
    try:
        from collections import namedtuple as _namedtuple

        def NamedTuple(typename, fields=None):
            if fields is None:
                fields = []
            field_names = [f[0] for f in fields]
            return _namedtuple(typename, field_names)
    except ImportError:
        # If even namedtuple isn't available, provide a minimal implementation
        def NamedTuple(typename, fields=None):
            return tuple


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
    class _PrintLogger:
        """Simple logger that uses print() for MicroPython."""

        def __init__(self, name=None):
            self._name = name or "root"

        def debug(self, msg, *args, **kwargs):
            print(f"[DEBUG] {self._name}: {msg}")

        def info(self, msg, *args, **kwargs):
            print(f"[INFO] {self._name}: {msg}")

        def warning(self, msg, *args, **kwargs):
            print(f"[WARN] {self._name}: {msg}")

        def error(self, msg, *args, **kwargs):
            print(f"[ERROR] {self._name}: {msg}")

        def critical(self, msg, *args, **kwargs):
            print(f"[CRIT] {self._name}: {msg}")

    class logging:  # noqa: N801
        """Stub logging module for MicroPython using print."""

        Logger = _PrintLogger

        @staticmethod
        def getLogger(name=None):
            return _PrintLogger(name)


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

    def field(default=MISSING, default_factory=MISSING, **kwargs):  # noqa: N802
        """Create a field descriptor for dataclasses."""
        return _Field(default=default, default_factory=default_factory)

    def dataclass(cls=None, frozen=False, slots=False, **kwargs):  # noqa: N802
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

            # Build __init__ method
            def make_init(field_names, defaults):
                def __init__(self, *args, **kw):
                    # Track which fields have been set
                    num_positional = len(args)

                    # Assign positional args first
                    for i, val in enumerate(args):
                        if i < len(field_names):
                            setattr(self, field_names[i], val)

                    # Then assign keyword args and defaults for remaining fields
                    for i, name in enumerate(field_names):
                        if i < num_positional:
                            # Already set by positional arg
                            continue
                        if name in kw:
                            setattr(self, name, kw[name])
                        elif name in defaults:
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
