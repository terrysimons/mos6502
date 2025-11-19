#!/usr/bin/env python3
"""Transfer instructions for the MOS 6502 CPU."""

# Import from individual transfer instruction modules
from mos6502.instructions.transfer.tax import TAX_IMPLIED_0xAA, register_tax_instructions  # noqa: F401
from mos6502.instructions.transfer.tay import TAY_IMPLIED_0xA8, register_tay_instructions  # noqa: F401
from mos6502.instructions.transfer.tsx import TSX_IMPLIED_0xBA, register_tsx_instructions  # noqa: F401
from mos6502.instructions.transfer.txa import TXA_IMPLIED_0x8A, register_txa_instructions  # noqa: F401
from mos6502.instructions.transfer.txs import TXS_IMPLIED_0x9A, register_txs_instructions  # noqa: F401
from mos6502.instructions.transfer.tya import TYA_IMPLIED_0x98, register_tya_instructions  # noqa: F401

__all__ = [
    'TAX_IMPLIED_0xAA',
    'register_tax_instructions',
    'TAY_IMPLIED_0xA8',
    'register_tay_instructions',
    'TSX_IMPLIED_0xBA',
    'register_tsx_instructions',
    'TXA_IMPLIED_0x8A',
    'register_txa_instructions',
    'TXS_IMPLIED_0x9A',
    'register_txs_instructions',
    'TYA_IMPLIED_0x98',
    'register_tya_instructions',
]


def register_all_transfer_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all transfer instructions."""
    register_tax_instructions(instruction_set_class, instruction_map)
    register_tay_instructions(instruction_set_class, instruction_map)
    register_tsx_instructions(instruction_set_class, instruction_map)
    register_txa_instructions(instruction_set_class, instruction_map)
    register_txs_instructions(instruction_set_class, instruction_map)
    register_tya_instructions(instruction_set_class, instruction_map)
