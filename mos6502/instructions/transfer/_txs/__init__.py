#!/usr/bin/env python3
"""TXS (Transfer Index X to Stack Pointer) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#TXS
# Transfer Index X to Stack Pointer
#
# X -> S
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TXS	9A	1	2
TXS_IMPLIED_0x9A = InstructionOpcode(
    0x9A,
    "mos6502.instructions.transfer._txs",
    "txs_implied_0x9a"
)


def add_txs_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TXS instruction to the InstructionSet enum dynamically."""
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

    txs_member = PseudoEnumMember(TXS_IMPLIED_0x9A, "TXS_IMPLIED_0x9A")
    instruction_set_class._value2member_map_[TXS_IMPLIED_0x9A] = txs_member
    setattr(instruction_set_class, "TXS_IMPLIED_0x9A", TXS_IMPLIED_0x9A)


def register_txs_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TXS instruction in the InstructionSet."""
    add_txs_to_instruction_set_enum(instruction_set_class)

    # TXS doesn't modify any flags
    txs_implied_0x9a_can_modify_flags: Byte = Byte()
    instruction_map[TXS_IMPLIED_0x9A] = {
        "addressing": "implied",
        "assembler": "TXS",
        "opc": TXS_IMPLIED_0x9A,
        "bytes": "1",
        "cycles": "2",
        "flags": txs_implied_0x9a_can_modify_flags,
    }


__all__ = ["TXS_IMPLIED_0x9A", "register_txs_instructions"]
