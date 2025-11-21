#!/usr/bin/env python3
"""ADC (Add with Carry) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#ADC
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

ADC_IMMEDIATE_0x69 = InstructionOpcode(
    0x69,
    "mos6502.instructions.arithmetic._adc",
    "adc_immediate_0x69"
)

ADC_ZEROPAGE_0x65 = InstructionOpcode(
    0x65,
    "mos6502.instructions.arithmetic._adc",
    "adc_zeropage_0x65"
)

ADC_ZEROPAGE_X_0x75 = InstructionOpcode(
    0x75,
    "mos6502.instructions.arithmetic._adc",
    "adc_zeropage_x_0x75"
)

ADC_ABSOLUTE_0x6D = InstructionOpcode(
    0x6D,
    "mos6502.instructions.arithmetic._adc",
    "adc_absolute_0x6d"
)

ADC_ABSOLUTE_X_0x7D = InstructionOpcode(
    0x7D,
    "mos6502.instructions.arithmetic._adc",
    "adc_absolute_x_0x7d"
)

ADC_ABSOLUTE_Y_0x79 = InstructionOpcode(
    0x79,
    "mos6502.instructions.arithmetic._adc",
    "adc_absolute_y_0x79"
)

ADC_INDEXED_INDIRECT_X_0x61 = InstructionOpcode(
    0x61,
    "mos6502.instructions.arithmetic._adc",
    "adc_indexed_indirect_x_0x61"
)

ADC_INDIRECT_INDEXED_Y_0x71 = InstructionOpcode(
    0x71,
    "mos6502.instructions.arithmetic._adc",
    "adc_indirect_indexed_y_0x71"
)


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
        (ADC_IMMEDIATE_0x69, "ADC_IMMEDIATE_0x69"),
        (ADC_ZEROPAGE_0x65, "ADC_ZEROPAGE_0x65"),
        (ADC_ZEROPAGE_X_0x75, "ADC_ZEROPAGE_X_0x75"),
        (ADC_ABSOLUTE_0x6D, "ADC_ABSOLUTE_0x6D"),
        (ADC_ABSOLUTE_X_0x7D, "ADC_ABSOLUTE_X_0x7D"),
        (ADC_ABSOLUTE_Y_0x79, "ADC_ABSOLUTE_Y_0x79"),
        (ADC_INDEXED_INDIRECT_X_0x61, "ADC_INDEXED_INDIRECT_X_0x61"),
        (ADC_INDIRECT_INDEXED_Y_0x71, "ADC_INDIRECT_INDEXED_Y_0x71"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_adc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ADC instructions in the InstructionSet."""
    add_adc_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    adc_can_modify_flags: Byte = Byte()
    adc_can_modify_flags[flags.N] = 1
    adc_can_modify_flags[flags.Z] = 1
    adc_can_modify_flags[flags.C] = 1
    adc_can_modify_flags[flags.V] = 1

    instruction_map[ADC_IMMEDIATE_0x69] = {
        "addressing": "immediate",
        "assembler": "ADC #{oper}",
        "opc": ADC_IMMEDIATE_0x69,
        "bytes": "2",
        "cycles": "2",
        "flags": adc_can_modify_flags,
    }

    instruction_map[ADC_ZEROPAGE_0x65] = {
        "addressing": "zeropage",
        "assembler": "ADC {oper}",
        "opc": ADC_ZEROPAGE_0x65,
        "bytes": "2",
        "cycles": "3",
        "flags": adc_can_modify_flags,
    }

    instruction_map[ADC_ZEROPAGE_X_0x75] = {
        "addressing": "zeropage,X",
        "assembler": "ADC {oper},X",
        "opc": ADC_ZEROPAGE_X_0x75,
        "bytes": "2",
        "cycles": "4",
        "flags": adc_can_modify_flags,
    }

    instruction_map[ADC_ABSOLUTE_0x6D] = {
        "addressing": "absolute",
        "assembler": "ADC {oper}",
        "opc": ADC_ABSOLUTE_0x6D,
        "bytes": "3",
        "cycles": "4",
        "flags": adc_can_modify_flags,
    }

    instruction_map[ADC_ABSOLUTE_X_0x7D] = {
        "addressing": "absolute,X",
        "assembler": "ADC {oper},X",
        "opc": ADC_ABSOLUTE_X_0x7D,
        "bytes": "3",
        "cycles": "4*",
        "flags": adc_can_modify_flags,
    }

    instruction_map[ADC_ABSOLUTE_Y_0x79] = {
        "addressing": "absolute,Y",
        "assembler": "ADC {oper},Y",
        "opc": ADC_ABSOLUTE_Y_0x79,
        "bytes": "3",
        "cycles": "4*",
        "flags": adc_can_modify_flags,
    }

    instruction_map[ADC_INDEXED_INDIRECT_X_0x61] = {
        "addressing": "(indirect,X)",
        "assembler": "ADC ({oper},X)",
        "opc": ADC_INDEXED_INDIRECT_X_0x61,
        "bytes": "2",
        "cycles": "6",
        "flags": adc_can_modify_flags,
    }

    instruction_map[ADC_INDIRECT_INDEXED_Y_0x71] = {
        "addressing": "(indirect),Y",
        "assembler": "ADC ({oper}),Y",
        "opc": ADC_INDIRECT_INDEXED_Y_0x71,
        "bytes": "2",
        "cycles": "5*",
        "flags": adc_can_modify_flags,
    }


__all__ = [
    "ADC_IMMEDIATE_0x69",
    "ADC_ZEROPAGE_0x65",
    "ADC_ZEROPAGE_X_0x75",
    "ADC_ABSOLUTE_0x6D",
    "ADC_ABSOLUTE_X_0x7D",
    "ADC_ABSOLUTE_Y_0x79",
    "ADC_INDEXED_INDIRECT_X_0x61",
    "ADC_INDIRECT_INDEXED_Y_0x71",
    "register_adc_instructions",
]
