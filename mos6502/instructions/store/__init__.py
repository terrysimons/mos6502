#!/usr/bin/env python3
"""Store instructions for the MOS 6502 CPU."""

# Import from individual store instruction modules
from mos6502.instructions.store._sta import (
    STA_ABSOLUTE_0x8D,
    STA_ABSOLUTE_X_0x9D,
    STA_ABSOLUTE_Y_0x99,
    STA_INDEXED_INDIRECT_X_0x81,
    STA_INDIRECT_INDEXED_Y_0x91,
    STA_ZEROPAGE_0x85,
    STA_ZEROPAGE_X_0x95,
    register_sta_instructions,
)
from mos6502.instructions.store._stx import (
    STX_ABSOLUTE_0x8E,
    STX_ZEROPAGE_0x86,
    STX_ZEROPAGE_Y_0x96,
    register_stx_instructions,
)
from mos6502.instructions.store._sty import (
    STY_ABSOLUTE_0x8C,
    STY_ZEROPAGE_0x84,
    STY_ZEROPAGE_X_0x94,
    register_sty_instructions,
)

__all__ = [
    # STA
    "STA_ZEROPAGE_0x85",
    "STA_ZEROPAGE_X_0x95",
    "STA_ABSOLUTE_0x8D",
    "STA_ABSOLUTE_X_0x9D",
    "STA_ABSOLUTE_Y_0x99",
    "STA_INDEXED_INDIRECT_X_0x81",
    "STA_INDIRECT_INDEXED_Y_0x91",
    "register_sta_instructions",
    # STX
    "STX_ZEROPAGE_0x86",
    "STX_ZEROPAGE_Y_0x96",
    "STX_ABSOLUTE_0x8E",
    "register_stx_instructions",
    # STY
    "STY_ZEROPAGE_0x84",
    "STY_ZEROPAGE_X_0x94",
    "STY_ABSOLUTE_0x8C",
    "register_sty_instructions",
]


def register_all_store_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all store instructions."""
    register_sta_instructions(instruction_set_class, instruction_map)
    register_stx_instructions(instruction_set_class, instruction_map)
    register_sty_instructions(instruction_set_class, instruction_map)
