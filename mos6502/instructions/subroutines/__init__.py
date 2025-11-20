#!/usr/bin/env python3
"""Subroutine and flow control instructions for the MOS 6502 CPU."""

# Import from individual subroutine instruction modules
from mos6502.instructions.subroutines._jmp import (  # noqa: F401
    JMP_ABSOLUTE_0x4C,
    JMP_INDIRECT_0x6C,
    register_jmp_instructions,
)
from mos6502.instructions.subroutines._jsr import (  # noqa: F401
    JSR_ABSOLUTE_0x20,
    register_jsr_instructions,
)
from mos6502.instructions.subroutines._rti import (  # noqa: F401
    RTI_IMPLIED_0x40,
    register_rti_instructions,
)
from mos6502.instructions.subroutines._rts import (  # noqa: F401
    RTS_IMPLIED_0x60,
    register_rts_instructions,
)

__all__ = [
    # JMP
    'JMP_ABSOLUTE_0x4C',
    'JMP_INDIRECT_0x6C',
    'register_jmp_instructions',
    # JSR
    'JSR_ABSOLUTE_0x20',
    'register_jsr_instructions',
    # RTI
    'RTI_IMPLIED_0x40',
    'register_rti_instructions',
    # RTS
    'RTS_IMPLIED_0x60',
    'register_rts_instructions',
]


def register_all_subroutine_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all subroutine and flow control instructions."""
    register_jmp_instructions(instruction_set_class, instruction_map)
    register_jsr_instructions(instruction_set_class, instruction_map)
    register_rti_instructions(instruction_set_class, instruction_map)
    register_rts_instructions(instruction_set_class, instruction_map)
