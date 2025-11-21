#!/usr/bin/env python3
"""Branch instructions for the MOS 6502 CPU."""

# Import from individual branch instruction modules
from mos6502.instructions.branch._bcc import (
    BCC_RELATIVE_0x90,
    register_bcc_instructions,
)
from mos6502.instructions.branch._bcs import (
    BCS_RELATIVE_0xB0,
    register_bcs_instructions,
)
from mos6502.instructions.branch._beq import (
    BEQ_RELATIVE_0xF0,
    register_beq_instructions,
)
from mos6502.instructions.branch._bmi import (
    BMI_RELATIVE_0x30,
    register_bmi_instructions,
)
from mos6502.instructions.branch._bne import (
    BNE_RELATIVE_0xD0,
    register_bne_instructions,
)
from mos6502.instructions.branch._bpl import (
    BPL_RELATIVE_0x10,
    register_bpl_instructions,
)
from mos6502.instructions.branch._bvc import (
    BVC_RELATIVE_0x50,
    register_bvc_instructions,
)
from mos6502.instructions.branch._bvs import (
    BVS_RELATIVE_0x70,
    register_bvs_instructions,
)

__all__ = [
    # BCC
    "BCC_RELATIVE_0x90",
    "register_bcc_instructions",
    # BCS
    "BCS_RELATIVE_0xB0",
    "register_bcs_instructions",
    # BEQ
    "BEQ_RELATIVE_0xF0",
    "register_beq_instructions",
    # BMI
    "BMI_RELATIVE_0x30",
    "register_bmi_instructions",
    # BNE
    "BNE_RELATIVE_0xD0",
    "register_bne_instructions",
    # BPL
    "BPL_RELATIVE_0x10",
    "register_bpl_instructions",
    # BVC
    "BVC_RELATIVE_0x50",
    "register_bvc_instructions",
    # BVS
    "BVS_RELATIVE_0x70",
    "register_bvs_instructions",
]


def register_all_branch_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all branch instructions."""
    register_bcc_instructions(instruction_set_class, instruction_map)
    register_bcs_instructions(instruction_set_class, instruction_map)
    register_beq_instructions(instruction_set_class, instruction_map)
    register_bmi_instructions(instruction_set_class, instruction_map)
    register_bne_instructions(instruction_set_class, instruction_map)
    register_bpl_instructions(instruction_set_class, instruction_map)
    register_bvc_instructions(instruction_set_class, instruction_map)
    register_bvs_instructions(instruction_set_class, instruction_map)
