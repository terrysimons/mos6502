#!/usr/bin/env python3
"""LDA (Load Accumulator) instruction."""
from mos6502.instructions import CPUInstruction, InstructionOpcode, register_instructions

# https://masswerk.at/6502/6502_instruction_set.html#LDA
# Load Accumulator with Memory
#
# M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	LDA #oper	A9	2	2
# zeropage	LDA oper	A5	2	3
# zeropage,X	LDA oper,X	B5	2	4
# absolute	LDA oper	AD	3	4
# absolute,X	LDA oper,X	BD	3	4*
# absolute,Y	LDA oper,Y	B9	3	4*
# (indirect,X)	LDA (oper,X)	A1	2	6
# (indirect),Y	LDA (oper),Y	B1	2	5*

_PKG = "mos6502.instructions.load._lda"

# Instruction definitions using CPUInstruction dataclass
LDA_INSTRUCTIONS = [
    CPUInstruction(0xA9, "LDA", "immediate", "LDA #{oper}", 2, 2, "NZ", _PKG, "lda_immediate_0xa9"),
    CPUInstruction(0xA5, "LDA", "zeropage", "LDA {oper}", 2, 3, "NZ", _PKG, "lda_zeropage_0xa5"),
    CPUInstruction(0xB5, "LDA", "zeropage,X", "LDA {oper},X", 2, 4, "NZ", _PKG, "lda_zeropage_x_0xb5"),
    CPUInstruction(0xAD, "LDA", "absolute", "LDA {oper}", 3, 4, "NZ", _PKG, "lda_absolute_0xad"),
    CPUInstruction(0xBD, "LDA", "absolute,X", "LDA {oper},X", 3, 4, "NZ", _PKG, "lda_absolute_x_0xbd", True),
    CPUInstruction(0xB9, "LDA", "absolute,Y", "LDA {oper},Y", 3, 4, "NZ", _PKG, "lda_absolute_y_0xb9", True),
    CPUInstruction(0xA1, "LDA", "(indirect,X)", "LDA ({oper},X)", 2, 6, "NZ", _PKG, "lda_indexed_indirect_x_0xa1"),
    CPUInstruction(0xB1, "LDA", "(indirect),Y", "LDA ({oper}),Y", 2, 5, "NZ", _PKG, "lda_indirect_indexed_y_0xb1", True),
]

# InstructionOpcode instances for variant dispatch (backward compatibility)
LDA_IMMEDIATE_0xA9 = InstructionOpcode(0xA9, _PKG, "lda_immediate_0xa9")
LDA_ZEROPAGE_0xA5 = InstructionOpcode(0xA5, _PKG, "lda_zeropage_0xa5")
LDA_ZEROPAGE_X_0xB5 = InstructionOpcode(0xB5, _PKG, "lda_zeropage_x_0xb5")
LDA_ABSOLUTE_0xAD = InstructionOpcode(0xAD, _PKG, "lda_absolute_0xad")
LDA_ABSOLUTE_X_0xBD = InstructionOpcode(0xBD, _PKG, "lda_absolute_x_0xbd")
LDA_ABSOLUTE_Y_0xB9 = InstructionOpcode(0xB9, _PKG, "lda_absolute_y_0xb9")
LDA_INDEXED_INDIRECT_X_0xA1 = InstructionOpcode(0xA1, _PKG, "lda_indexed_indirect_x_0xa1")
LDA_INDIRECT_INDEXED_Y_0xB1 = InstructionOpcode(0xB1, _PKG, "lda_indirect_indexed_y_0xb1")


def register_lda_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register LDA instructions in the InstructionSet."""
    register_instructions(LDA_INSTRUCTIONS, instruction_set_class, instruction_map)


__all__ = [
    "LDA_IMMEDIATE_0xA9",
    "LDA_ZEROPAGE_0xA5",
    "LDA_ZEROPAGE_X_0xB5",
    "LDA_ABSOLUTE_0xAD",
    "LDA_ABSOLUTE_X_0xBD",
    "LDA_ABSOLUTE_Y_0xB9",
    "LDA_INDEXED_INDIRECT_X_0xA1",
    "LDA_INDIRECT_INDEXED_Y_0xB1",
    "register_lda_instructions",
]
