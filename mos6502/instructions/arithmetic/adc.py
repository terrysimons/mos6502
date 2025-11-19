#!/usr/bin/env python3
"""ADC (Add Memory to Accumulator with Carry) instruction."""
from typing import Literal

# https://www.masswerk.at/6502/6502_instruction_set.html#ADC
#
# Add Memory to Accumulator with Carry
#
# A + M + C -> A, C
# N	Z	C	I	D	V
# +	+	+	-	-	+
# addressing	assembler	opc	bytes	cycles
# immediate	ADC #oper	69	2	2
# zeropage	ADC oper	65	2	3
# zeropage,X	ADC oper,X	75	2	4
# absolute	ADC oper	6D	3	4
# absolute,X	ADC oper,X	7D	3	4*
# absolute,Y	ADC oper,Y	79	3	4*
# (indirect,X)	ADC (oper,X)	61	2	6
# (indirect),Y	ADC (oper),Y	71	2	5*
ADC_IMMEDIATE_0x69: Literal[105] = 0x69
ADC_ZEROPAGE_0x65: Literal[101] = 0x65
ADC_ZEROPAGE_X_0x75: Literal[117] = 0x75
ADC_ABSOLUTE_0x6D: Literal[109] = 0x6D
ADC_ABSOLUTE_X_0x7D: Literal[125] = 0x7D
ADC_ABSOLUTE_Y_0x79: Literal[121] = 0x79
ADC_INDEXED_INDIRECT_X_0x61: Literal[97] = 0x61
ADC_INDIRECT_INDEXED_Y_0x71: Literal[113] = 0x71


def add_adc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ADC instructions to the InstructionSet enum dynamically."""
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

    for value, name in [
        (ADC_IMMEDIATE_0x69, 'ADC_IMMEDIATE_0x69'),
        (ADC_ZEROPAGE_0x65, 'ADC_ZEROPAGE_0x65'),
        (ADC_ZEROPAGE_X_0x75, 'ADC_ZEROPAGE_X_0x75'),
        (ADC_ABSOLUTE_0x6D, 'ADC_ABSOLUTE_0x6D'),
        (ADC_ABSOLUTE_X_0x7D, 'ADC_ABSOLUTE_X_0x7D'),
        (ADC_ABSOLUTE_Y_0x79, 'ADC_ABSOLUTE_Y_0x79'),
        (ADC_INDEXED_INDIRECT_X_0x61, 'ADC_INDEXED_INDIRECT_X_0x61'),
        (ADC_INDIRECT_INDEXED_Y_0x71, 'ADC_INDIRECT_INDEXED_Y_0x71'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_adc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ADC instructions in the InstructionSet.

    Note: ADC doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_adc_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'ADC_IMMEDIATE_0x69',
    'ADC_ZEROPAGE_0x65',
    'ADC_ZEROPAGE_X_0x75',
    'ADC_ABSOLUTE_0x6D',
    'ADC_ABSOLUTE_X_0x7D',
    'ADC_ABSOLUTE_Y_0x79',
    'ADC_INDEXED_INDIRECT_X_0x61',
    'ADC_INDIRECT_INDEXED_Y_0x71',
    'register_adc_instructions',
]
