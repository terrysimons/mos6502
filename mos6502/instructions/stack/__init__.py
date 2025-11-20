#!/usr/bin/env python3
"""Stack manipulation instructions for the MOS 6502 CPU."""

# Import from individual stack instruction modules
from mos6502.instructions.stack._pha import PHA_IMPLIED_0x48, register_pha_instructions  # noqa: F401
from mos6502.instructions.stack._php import PHP_IMPLIED_0x08, register_php_instructions  # noqa: F401
from mos6502.instructions.stack._pla import PLA_IMPLIED_0x68, register_pla_instructions  # noqa: F401
from mos6502.instructions.stack._plp import PLP_IMPLIED_0x28, register_plp_instructions  # noqa: F401

__all__ = [
    # PHA
    'PHA_IMPLIED_0x48',
    'register_pha_instructions',
    # PHP
    'PHP_IMPLIED_0x08',
    'register_php_instructions',
    # PLA
    'PLA_IMPLIED_0x68',
    'register_pla_instructions',
    # PLP
    'PLP_IMPLIED_0x28',
    'register_plp_instructions',
]


def register_all_stack_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all stack instructions."""
    register_pha_instructions(instruction_set_class, instruction_map)
    register_php_instructions(instruction_set_class, instruction_map)
    register_pla_instructions(instruction_set_class, instruction_map)
    register_plp_instructions(instruction_set_class, instruction_map)
