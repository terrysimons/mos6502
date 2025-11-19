#!/usr/bin/env python3
"""BMI (Branch on Result Minus) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#BMI
# Branch on Result Minus
#
# branch on N = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BMI oper	30	2	2**
BMI_RELATIVE_0x30: Literal[48] = 0x30


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
    """Register BMI instructions in the InstructionSet.

    Note: BMI doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_bmi_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'BMI_RELATIVE_0x30',
    'register_bmi_instructions',
]
