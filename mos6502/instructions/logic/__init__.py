#!/usr/bin/env python3
"""Logic instructions for the MOS 6502 CPU."""

# Import from individual logic instruction modules
from mos6502.instructions.logic.and_ import (  # noqa: F401
    AND_ABSOLUTE_0x2D,
    AND_ABSOLUTE_X_0x3D,
    AND_ABSOLUTE_Y_0x39,
    AND_IMMEDIATE_0x29,
    AND_INDEXED_INDIRECT_X_0x21,
    AND_INDIRECT_INDEXED_Y_0x31,
    AND_ZEROPAGE_0x25,
    AND_ZEROPAGE_X_0x35,
    register_and_instructions,
)
from mos6502.instructions.logic.eor import (  # noqa: F401
    EOR_ABSOLUTE_0x4D,
    EOR_ABSOLUTE_X_0x5D,
    EOR_ABSOLUTE_Y_0x59,
    EOR_IMMEDIATE_0x49,
    EOR_INDEXED_INDIRECT_X_0x41,
    EOR_INDIRECT_INDEXED_Y_0x51,
    EOR_ZEROPAGE_0x45,
    EOR_ZEROPAGE_X_0x55,
    register_eor_instructions,
)
from mos6502.instructions.logic.ora import (  # noqa: F401
    ORA_ABSOLUTE_0x0D,
    ORA_ABSOLUTE_X_0x1D,
    ORA_ABSOLUTE_Y_0x19,
    ORA_IMMEDIATE_0x09,
    ORA_INDEXED_INDIRECT_X_0x01,
    ORA_INDIRECT_INDEXED_Y_0x11,
    ORA_ZEROPAGE_0x05,
    ORA_ZEROPAGE_X_0x15,
    register_ora_instructions,
)

__all__ = [
    # AND
    'AND_IMMEDIATE_0x29',
    'AND_ZEROPAGE_0x25',
    'AND_ZEROPAGE_X_0x35',
    'AND_ABSOLUTE_0x2D',
    'AND_ABSOLUTE_X_0x3D',
    'AND_ABSOLUTE_Y_0x39',
    'AND_INDEXED_INDIRECT_X_0x21',
    'AND_INDIRECT_INDEXED_Y_0x31',
    'register_and_instructions',
    # EOR
    'EOR_IMMEDIATE_0x49',
    'EOR_ZEROPAGE_0x45',
    'EOR_ZEROPAGE_X_0x55',
    'EOR_ABSOLUTE_0x4D',
    'EOR_ABSOLUTE_X_0x5D',
    'EOR_ABSOLUTE_Y_0x59',
    'EOR_INDEXED_INDIRECT_X_0x41',
    'EOR_INDIRECT_INDEXED_Y_0x51',
    'register_eor_instructions',
    # ORA
    'ORA_IMMEDIATE_0x09',
    'ORA_ZEROPAGE_0x05',
    'ORA_ZEROPAGE_X_0x15',
    'ORA_ABSOLUTE_0x0D',
    'ORA_ABSOLUTE_X_0x1D',
    'ORA_ABSOLUTE_Y_0x19',
    'ORA_INDEXED_INDIRECT_X_0x01',
    'ORA_INDIRECT_INDEXED_Y_0x11',
    'register_ora_instructions',
]


def register_all_logic_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all logic instructions."""
    register_and_instructions(instruction_set_class, instruction_map)
    register_eor_instructions(instruction_set_class, instruction_map)
    register_ora_instructions(instruction_set_class, instruction_map)
