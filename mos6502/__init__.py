#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CPU package for the mos6502."""
__version__ = '0.1.0'
__all__ = ['core', 'memory', 'exceptions', 'flags', 'instructions']

from mos6502.core import MOS6502CPU as CPU
