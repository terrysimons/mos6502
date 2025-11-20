#!/usr/bin/env python3
"""BMI (Branch on Minus/Negative) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#BMI
# Branch on Minus/Negative
# branch on N = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BMI oper	30	2	2**
BMI_RELATIVE_0x30 = InstructionOpcode(
    0x30,
    "mos6502.instructions.branch._bmi",
    "bmi_relative_0x30"
)


def add_bmi_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BMI instructions to the InstructionSet enum dynamically."""
    class PseudoEnumMember(int):
        def __new__(cls, value, name):
            obj = int.__new__(cls, value)
            obj._name = name
            obj._value_ = value
            return obj

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._value_

    member = PseudoEnumMember(BMI_RELATIVE_0x30, 'BMI_RELATIVE_0x30')
    instruction_set_class._value2member_map_[BMI_RELATIVE_0x30] = member
    setattr(instruction_set_class, 'BMI_RELATIVE_0x30', BMI_RELATIVE_0x30)


def register_bmi_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BMI instructions in the InstructionSet."""
    add_bmi_to_instruction_set_enum(instruction_set_class)

    bmi_relative_0x30_can_modify_flags: Byte = Byte()
    instruction_map[BMI_RELATIVE_0x30] = {
        "addressing": "relative",
        "assembler": "BMI {oper}",
        "opc": BMI_RELATIVE_0x30,
        "bytes": "2",
        "cycles": "2**",
        "flags": bmi_relative_0x30_can_modify_flags,
    }


__all__ = ['BMI_RELATIVE_0x30', 'register_bmi_instructions']
