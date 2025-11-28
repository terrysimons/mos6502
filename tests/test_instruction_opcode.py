#!/usr/bin/env python3
"""Test that InstructionOpcode works with existing code patterns."""

import pytest

from mos6502 import CPU, errors
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte, RAM

# Create a test opcode
NOP_WITH_METADATA = InstructionOpcode(0xEA, "mos6502.instructions.nop", "nop_implied_0xea")
NOP_PLAIN = 0xEA


def test_opcode_value_equality() -> None:
    """Test that InstructionOpcode equals its numeric value."""
    assert NOP_WITH_METADATA == 0xEA
    assert NOP_WITH_METADATA == NOP_PLAIN
    assert 0xEA == NOP_WITH_METADATA


def test_opcode_case_matching() -> None:
    """Test that InstructionOpcode works in match/case statements."""
    value = NOP_WITH_METADATA

    match value:
        case 0xEA:
            result = "matched"
        case _:
            result = "no match"

    assert result == "matched"


def test_opcode_dict_key() -> None:
    """Test that InstructionOpcode works as dictionary key."""
    instruction_map = {}
    instruction_map[NOP_WITH_METADATA] = {"name": "NOP"}

    # Should be able to look up with plain int
    assert instruction_map[0xEA] == {"name": "NOP"}
    assert instruction_map[NOP_WITH_METADATA] == {"name": "NOP"}
    assert instruction_map[NOP_PLAIN] == {"name": "NOP"}


def test_opcode_ram_write() -> None:
    """Test that InstructionOpcode can be written to RAM."""
    ram = RAM()
    ram[0x1000] = NOP_WITH_METADATA

    # Should read back as the value
    assert ram[0x1000] == 0xEA


def test_opcode_byte_conversion() -> None:
    """Test that InstructionOpcode works with Byte."""
    byte_value = Byte(NOP_WITH_METADATA)
    assert int(byte_value) == 0xEA


def test_opcode_string_formatting() -> None:
    """Test that InstructionOpcode formats like an int."""
    assert f"{NOP_WITH_METADATA:02X}" == "EA"
    assert f"{NOP_WITH_METADATA}" == "234"


def test_opcode_isinstance() -> None:
    """Test that InstructionOpcode is still an int."""
    assert isinstance(NOP_WITH_METADATA, int)


def test_opcode_has_metadata() -> None:
    """Test that InstructionOpcode carries metadata."""
    assert hasattr(NOP_WITH_METADATA, "package")
    assert hasattr(NOP_WITH_METADATA, "function")
    assert NOP_WITH_METADATA.package == "mos6502.instructions.nop"  # type: ignore
    assert NOP_WITH_METADATA.function == "nop_implied_0xea"  # type: ignore


def test_opcode_arithmetic_loses_metadata() -> None:
    """Test that arithmetic operations return plain int."""
    result = NOP_WITH_METADATA + 1
    assert result == 0xEB
    assert isinstance(result, int)
    # Metadata is lost (this is expected behavior)
    assert not hasattr(result, "package")


def test_opcode_with_cpu() -> None:
    """Test that InstructionOpcode works with CPU execution."""
    cpu = CPU()
    cpu.reset()
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    # Write NOP instruction to memory
    cpu.ram[pc] = NOP_WITH_METADATA

    # Execute it
    import contextlib
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # Should have executed NOP
    assert cpu.PC == pc + 1
    assert cpu.cycles_executed - cycles_before == 2


def test_opcode_comparison_operators() -> None:
    """Test comparison operators work correctly."""
    assert NOP_WITH_METADATA == 0xEA
    assert NOP_WITH_METADATA != 0xEB
    assert NOP_WITH_METADATA < 0xEB
    assert NOP_WITH_METADATA > 0xE9
    assert NOP_WITH_METADATA <= 0xEA
    assert NOP_WITH_METADATA >= 0xEA


def test_opcode_hash() -> None:
    """Test that InstructionOpcode hashes like its value."""
    # Same hash as plain int
    assert hash(NOP_WITH_METADATA) == hash(0xEA)
    assert hash(NOP_WITH_METADATA) == hash(NOP_PLAIN)

    # Can use in sets
    opcode_set = {NOP_WITH_METADATA}
    assert 0xEA in opcode_set
    assert NOP_PLAIN in opcode_set
