#!/usr/bin/env python3
"""RTS (Return from Subroutine) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#RTS
# Return from Subroutine
#
# pull PC, PC+1 -> PC
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	RTS	60	1	6
RTS_IMPLIED_0x60 = InstructionOpcode(
    0x60,
    "mos6502.instructions.subroutines._rts",
    "rts_implied_0x60"
)


def add_rts_to_instruction_set_enum(instruction_set_class) -> None:
    """Add RTS instruction to the InstructionSet enum dynamically."""
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

    rts_member = PseudoEnumMember(RTS_IMPLIED_0x60, 'RTS_IMPLIED_0x60')
    instruction_set_class._value2member_map_[RTS_IMPLIED_0x60] = rts_member
    setattr(instruction_set_class, 'RTS_IMPLIED_0x60', RTS_IMPLIED_0x60)


def register_rts_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register RTS instruction in the InstructionSet."""
    add_rts_to_instruction_set_enum(instruction_set_class)

    # RTS doesn't modify any flags
    rts_implied_0x60_can_modify_flags: Byte = Byte()
    instruction_map[RTS_IMPLIED_0x60] = {
        "addressing": "implied",
        "assembler": "RTS",
        "opc": RTS_IMPLIED_0x60,
        "bytes": "1",
        "cycles": "6",
        "flags": rts_implied_0x60_can_modify_flags,
    }


__all__ = ['RTS_IMPLIED_0x60', 'register_rts_instructions']
