#!/usr/bin/env python3
"""Illegal NOP instruction implementations for CMOS 65C02 variant.

On 65C02, these opcodes are officially NOPs with specific byte/cycle counts.
The behavior is identical to NMOS variants - they just consume bytes without
modifying any registers or flags.

VARIANT: 65C02 - Official NOPs (same behavior as NMOS illegal NOPs)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from __future__ import annotations

# 65C02 illegal NOP behavior is identical to NMOS - just import all handlers
from mos6502.instructions.illegal._nop_illegal._nop_illegal_6502 import (
    # 1-byte implied
    nop_implied_0x1a,
    nop_implied_0x3a,
    nop_implied_0x5a,
    nop_implied_0x7a,
    nop_implied_0xda,
    nop_implied_0xfa,
    # 2-byte immediate
    nop_immediate_0x80,
    nop_immediate_0x82,
    nop_immediate_0x89,
    nop_immediate_0xc2,
    nop_immediate_0xe2,
    # 2-byte zero page
    nop_zeropage_0x04,
    nop_zeropage_0x44,
    nop_zeropage_0x64,
    # 2-byte zero page,X
    nop_zeropage_x_0x14,
    nop_zeropage_x_0x34,
    nop_zeropage_x_0x54,
    nop_zeropage_x_0x74,
    nop_zeropage_x_0xd4,
    nop_zeropage_x_0xf4,
    # 3-byte absolute
    nop_absolute_0x0c,
    # 3-byte absolute,X
    nop_absolute_x_0x1c,
    nop_absolute_x_0x3c,
    nop_absolute_x_0x5c,
    nop_absolute_x_0x7c,
    nop_absolute_x_0xdc,
    nop_absolute_x_0xfc,
)

__all__ = [
    # 1-byte implied
    "nop_implied_0x1a",
    "nop_implied_0x3a",
    "nop_implied_0x5a",
    "nop_implied_0x7a",
    "nop_implied_0xda",
    "nop_implied_0xfa",
    # 2-byte immediate
    "nop_immediate_0x80",
    "nop_immediate_0x82",
    "nop_immediate_0x89",
    "nop_immediate_0xc2",
    "nop_immediate_0xe2",
    # 2-byte zero page
    "nop_zeropage_0x04",
    "nop_zeropage_0x44",
    "nop_zeropage_0x64",
    # 2-byte zero page,X
    "nop_zeropage_x_0x14",
    "nop_zeropage_x_0x34",
    "nop_zeropage_x_0x54",
    "nop_zeropage_x_0x74",
    "nop_zeropage_x_0xd4",
    "nop_zeropage_x_0xf4",
    # 3-byte absolute
    "nop_absolute_0x0c",
    # 3-byte absolute,X
    "nop_absolute_x_0x1c",
    "nop_absolute_x_0x3c",
    "nop_absolute_x_0x5c",
    "nop_absolute_x_0x7c",
    "nop_absolute_x_0xdc",
    "nop_absolute_x_0xfc",
]
