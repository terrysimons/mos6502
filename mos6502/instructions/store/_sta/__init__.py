#!/usr/bin/env python3
"""STA (Store Accumulator) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#STA
# Store Accumulator in Memory
#
# A -> M
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	STA oper	85	2	3
# zeropage,X	STA oper,X	95	2	4
# absolute	STA oper	8D	3	4
# absolute,X	STA oper,X	9D	3	5
# absolute,Y	STA oper,Y	99	3	5
# (indirect,X)	STA (oper,X)	81	2	6
# (indirect),Y	STA (oper),Y	91	2	6

STA_ZEROPAGE_0x85 = InstructionOpcode(
    0x85,
    "mos6502.instructions.store._sta",
    "sta_zeropage_0x85"
)

STA_ZEROPAGE_X_0x95 = InstructionOpcode(
    0x95,
    "mos6502.instructions.store._sta",
    "sta_zeropage_x_0x95"
)

STA_ABSOLUTE_0x8D = InstructionOpcode(
    0x8D,
    "mos6502.instructions.store._sta",
    "sta_absolute_0x8d"
)

STA_ABSOLUTE_X_0x9D = InstructionOpcode(
    0x9D,
    "mos6502.instructions.store._sta",
    "sta_absolute_x_0x9d"
)

STA_ABSOLUTE_Y_0x99 = InstructionOpcode(
    0x99,
    "mos6502.instructions.store._sta",
    "sta_absolute_y_0x99"
)

STA_INDEXED_INDIRECT_X_0x81 = InstructionOpcode(
    0x81,
    "mos6502.instructions.store._sta",
    "sta_indexed_indirect_x_0x81"
)

STA_INDIRECT_INDEXED_Y_0x91 = InstructionOpcode(
    0x91,
    "mos6502.instructions.store._sta",
    "sta_indirect_indexed_y_0x91"
)


def add_sta_to_instruction_set_enum(instruction_set_class) -> None:
    """Add STA instructions to the InstructionSet enum dynamically."""
    class PseudoEnumMember(int):
        def __new__(cls, value, name) -> "InstructionSet":
            obj = int.__new__(cls, value)
            obj._name = name
            obj._value_ = value
            return obj

        @property
        def name(self) -> str:
            return self._name

        @property
        def value(self) -> int:
            return self._value_

    for value, name in [
        (STA_ZEROPAGE_0x85, "STA_ZEROPAGE_0x85"),
        (STA_ZEROPAGE_X_0x95, "STA_ZEROPAGE_X_0x95"),
        (STA_ABSOLUTE_0x8D, "STA_ABSOLUTE_0x8D"),
        (STA_ABSOLUTE_X_0x9D, "STA_ABSOLUTE_X_0x9D"),
        (STA_ABSOLUTE_Y_0x99, "STA_ABSOLUTE_Y_0x99"),
        (STA_INDEXED_INDIRECT_X_0x81, "STA_INDEXED_INDIRECT_X_0x81"),
        (STA_INDIRECT_INDEXED_Y_0x91, "STA_INDIRECT_INDEXED_Y_0x91"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_sta_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register STA instructions in the InstructionSet."""
    add_sta_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    sta_can_modify_flags: Byte = Byte()
    # STA doesn't modify any flags

    instruction_map[STA_ZEROPAGE_0x85] = {
        "addressing": "zeropage",
        "assembler": "STA {oper}",
        "opc": STA_ZEROPAGE_0x85,
        "bytes": "2",
        "cycles": "3",
        "flags": sta_can_modify_flags,
    }

    instruction_map[STA_ZEROPAGE_X_0x95] = {
        "addressing": "zeropage,X",
        "assembler": "STA {oper},X",
        "opc": STA_ZEROPAGE_X_0x95,
        "bytes": "2",
        "cycles": "4",
        "flags": sta_can_modify_flags,
    }

    instruction_map[STA_ABSOLUTE_0x8D] = {
        "addressing": "absolute",
        "assembler": "STA {oper}",
        "opc": STA_ABSOLUTE_0x8D,
        "bytes": "3",
        "cycles": "4",
        "flags": sta_can_modify_flags,
    }

    instruction_map[STA_ABSOLUTE_X_0x9D] = {
        "addressing": "absolute,X",
        "assembler": "STA {oper},X",
        "opc": STA_ABSOLUTE_X_0x9D,
        "bytes": "3",
        "cycles": "5",
        "flags": sta_can_modify_flags,
    }

    instruction_map[STA_ABSOLUTE_Y_0x99] = {
        "addressing": "absolute,Y",
        "assembler": "STA {oper},Y",
        "opc": STA_ABSOLUTE_Y_0x99,
        "bytes": "3",
        "cycles": "5",
        "flags": sta_can_modify_flags,
    }

    instruction_map[STA_INDEXED_INDIRECT_X_0x81] = {
        "addressing": "(indirect,X)",
        "assembler": "STA ({oper},X)",
        "opc": STA_INDEXED_INDIRECT_X_0x81,
        "bytes": "2",
        "cycles": "6",
        "flags": sta_can_modify_flags,
    }

    instruction_map[STA_INDIRECT_INDEXED_Y_0x91] = {
        "addressing": "(indirect),Y",
        "assembler": "STA ({oper}),Y",
        "opc": STA_INDIRECT_INDEXED_Y_0x91,
        "bytes": "2",
        "cycles": "6",
        "flags": sta_can_modify_flags,
    }


__all__ = [
    "STA_ZEROPAGE_0x85",
    "STA_ZEROPAGE_X_0x95",
    "STA_ABSOLUTE_0x8D",
    "STA_ABSOLUTE_X_0x9D",
    "STA_ABSOLUTE_Y_0x99",
    "STA_INDEXED_INDIRECT_X_0x81",
    "STA_INDIRECT_INDEXED_Y_0x91",
    "register_sta_instructions",
]
