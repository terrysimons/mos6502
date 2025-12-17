#!/usr/bin/env python3
"""Factory module for bitarray implementation selection.

This module provides a unified interface for bitarray functionality,
selecting between the native bitarray library (if available) and a
pure-Python implementation.

Usage:
    from mos6502.bitarray_factory import bitarray, ba2int, int2ba

The factory defaults to native bitarray when available. To force
pure-Python mode, set the environment variable:
    MOS6502_PURE_PYTHON=1

Or call configure() before any other imports:
    from mos6502 import bitarray_factory
    bitarray_factory.configure(use_native=False)

PyPy is automatically detected and forces pure-Python mode for better
performance (PyPy's JIT works better with pure Python code).
"""

import os
import sys
from mos6502.compat import Literal, Union

# Auto-detect PyPy and force pure-Python mode
# PyPy's JIT compiler works much better with pure Python than with C extensions
if sys.implementation.name == "pypy":
    os.environ.setdefault("MOS6502_PURE_PYTHON", "1")

# Configuration - can be overridden before first use
_USE_NATIVE: Union[bool, None]= None  # None means auto-detect
_NATIVE_AVAILABLE: bool = False

# Try to import native bitarray
try:
    from bitarray import bitarray as _native_bitarray
    from bitarray.util import ba2int as _native_ba2int
    from bitarray.util import int2ba as _native_int2ba

    _NATIVE_AVAILABLE = True
except ImportError:
    _native_bitarray = None  # type: ignore[assignment, misc]
    _native_ba2int = None  # type: ignore[assignment]
    _native_int2ba = None  # type: ignore[assignment]
    _NATIVE_AVAILABLE = False

# Import pure-Python implementation
from mos6502.pybitarray import ba2int as _py_ba2int
from mos6502.pybitarray import int2ba as _py_int2ba
from mos6502.pybitarray import pybitarray as _pybitarray


def _should_use_native() -> bool:
    """Determine whether to use native bitarray."""
    global _USE_NATIVE

    # If explicitly configured, use that
    if _USE_NATIVE is not None:
        return _USE_NATIVE and _NATIVE_AVAILABLE

    # Check environment variable
    env_val = os.environ.get("MOS6502_PURE_PYTHON", "").lower()
    if env_val in ("1", "true", "yes"):
        _USE_NATIVE = False
        return False

    # Default: use native if available
    _USE_NATIVE = _NATIVE_AVAILABLE
    return _NATIVE_AVAILABLE


def configure(*, use_native: Union[bool, None]= None) -> None:
    """Configure which bitarray implementation to use.

    Args:
    ----
        use_native: True to use native bitarray, False for pure-Python,
                   None for auto-detect (default)

    Raises:
    ------
        ImportError: if use_native=True but bitarray is not installed

    """
    global _USE_NATIVE

    if use_native is True and not _NATIVE_AVAILABLE:
        msg = "Native bitarray requested but not installed"
        raise ImportError(msg)

    _USE_NATIVE = use_native


def is_native() -> bool:
    """Return True if using native bitarray implementation."""
    return _should_use_native()


def is_available() -> bool:
    """Return True if native bitarray is available."""
    return _NATIVE_AVAILABLE


def is_bitarray(obj: object) -> bool:
    """Check if obj is a bitarray (native or pybitarray).

    Use this instead of isinstance(obj, bitarray) since the factory
    returns different types based on configuration.

    Args:
    ----
        obj: object to check

    Returns:
    -------
        True if obj is a bitarray instance

    """
    if isinstance(obj, _pybitarray):
        return True
    if _NATIVE_AVAILABLE and isinstance(obj, _native_bitarray):
        return True
    return False


# Export the appropriate implementation
# These are determined at first access based on configuration

class _LazyBitarray:
    """Lazy loader that selects implementation on first use."""

    def __new__(cls, *args, **kwargs):  # noqa: ANN204, ANN002, ANN003
        if _should_use_native():
            return _native_bitarray(*args, **kwargs)
        return _pybitarray(*args, **kwargs)


def int2ba(
    value: int,
    length: int = 8,
    endian: Literal["little", "big"] = "little",
):  # noqa: ANN201
    """Convert an integer to a bitarray.

    Args:
    ----
        value: integer value to convert
        length: number of bits in result
        endian: "little" or "big" endianness

    Returns:
    -------
        bitarray (native or pybitarray) representing the value

    """
    if _should_use_native():
        return _native_int2ba(value, length=length, endian=endian)
    return _py_int2ba(value, length=length, endian=endian)


def ba2int(ba) -> int:  # noqa: ANN001
    """Convert a bitarray to an integer.

    Args:
    ----
        ba: bitarray (native or pybitarray) to convert

    Returns:
    -------
        integer value

    """
    if _should_use_native():
        return _native_ba2int(ba)
    return _py_ba2int(ba)


# The main export - use this as the bitarray class
bitarray = _LazyBitarray
