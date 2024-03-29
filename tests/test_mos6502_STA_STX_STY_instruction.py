#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import exceptions, flags, instructions
from mos6502.memory import Byte, Word

log: logging.Logger = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)

def check_noop_flags(expected_cpu, actual_cpu) -> None:
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]

def verify_store_zeropage(cpu, data, instruction, offset, register_name, expected_flags,
                          expected_cycles, offset_register_name=None, offset_value=0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Load the register with a value to be stored in memory
    setattr(cpu, register_name, data)

    # Load the offset register, if necessary
    if offset_register_name:
        setattr(cpu, offset_register_name, offset_value)

    # Load with zeropage offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = offset

    # zero page is 0x00-0xFF, so need to handle wraparound
    cpu.ram[(offset + offset_value) & 0xFF] = 0x00

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[(offset + offset_value) & 0xFF] == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

def verify_store_absolute(cpu, data, instruction, offset, register_name, expected_flags,
                          expected_cycles, offset_register_name=None, offset_value=0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Load the register with a value to be stored in memory
    setattr(cpu, register_name, data)

    # Load with absolute offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = offset.lowbyte
    cpu.ram[0xFFFE] = offset.highbyte

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[offset & 0xFFFF] == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

def verify_store_indexed_indirect(cpu, pc_value, data, instruction, offset, register_name,
                                  expected_flags, expected_cycles, offset_value=0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    setattr(cpu, register_name, 0x00)
    cpu.X = offset_value

    # Store with indirect x offset
    # @PC
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = pc_value

    # @ZP offset
    cpu.ram[(pc_value + offset_value) & 0xFF] = (offset) & 0xFF # zeropage addr
    cpu.ram[(pc_value + offset_value + 1) & 0xFF] = (offset >> 8) & 0xFF # zerpage addr + 1

    address: Word = Word(offset)

    # @ RAM
    cpu.ram[address & 0xFFFF] = data

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[address & 0xFFFF] == data
    assert getattr(cpu, register_name) == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

def verify_store_indirect_indexed(cpu, pc_value, data, instruction, offset, register_name,
                                  expected_flags, expected_cycles, offset_value=0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Load the register with a value to be stored in memory
    setattr(cpu, register_name, 0x00)
    cpu.Y = offset_value

    # Load with indirect x offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = pc_value

    # @ZP offset
    cpu.ram[(pc_value) & 0xFF] = (offset) & 0xFF # zeropage addr
    cpu.ram[(pc_value + 1) & 0xFF] = (offset >> 8) & 0xFF # zerpage addr + 1

    # @Address
    cpu.ram[(offset + offset_value) & 0xFFFF] = data

    address: Word = Word(offset + offset_value, endianness=cpu.endianness)

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[address & 0xFFFF] == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

"""STA"""
instructions.STA_ABSOLUTE_0x8D
def test_cpu_instruction_STA_ABSOLUTE_0x8D() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_absolute(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ABSOLUTE_0x8D,
        offset=Word(0x8000, endianness=cpu.endianness),
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

instructions.STA_ABSOLUTE_X_0x9D
def test_cpu_instruction_STA_ABSOLUTE_X_0x9D() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_absolute(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ABSOLUTE_X_0x9D,
        offset=Word(0x8000, endianness=cpu.endianness),
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="X",
        offset_value=0x0F,
    )

instructions.STA_ABSOLUTE_Y_0x99
def test_cpu_instruction_STA_ABSOLUTE_Y_0x99() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_absolute(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ABSOLUTE_Y_0x99,
        offset=Word(0x8000, endianness=cpu.endianness),
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="Y",
        offset_value=0x0F,
    )

instructions.STA_INDEXED_INDIRECT_X_0x81
def test_cpu_instruction_STA_INDEXED_INDIRECT_X_0x81() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_indexed_indirect(
        cpu=cpu,
        pc_value=0x02,
        data=0xFF,
        instruction=instructions.STA_INDEXED_INDIRECT_X_0x81,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=22,
        offset_value=0x04,
    )

instructions.STA_INDIRECT_INDEXED_Y_0x91
def test_cpu_instruction_STA_INDIRECT_INDEXED_Y_0x91() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_indirect_indexed(
        cpu=cpu,
        pc_value=0x80,
        data=0xFF,
        instruction=instructions.STA_INDIRECT_INDEXED_Y_0x91,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0x04,
    )

instructions.STA_ZEROPAGE_0x85
def test_cpu_instruction_STA_ZEROPAGE_0x85() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ZEROPAGE_0x85,
        offset=0x80,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=3,
    )

instructions.STA_ZEROPAGE_X_0x95
def test_cpu_instruction_STA_ZEROPAGE_X_0x95() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ZEROPAGE_X_0x95,
        offset=0x80,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="X",
        offset_value=0x0F,
    )

"""STX"""
instructions.STX_ABSOLUTE_0x8E
def test_cpu_instruction_STX_ABSOLUTE_0x8E():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_absolute(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STX_ABSOLUTE_0x8E,
        offset=Word(0x8000, endianness=cpu.endianness),
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=3,
    )

instructions.STX_ZEROPAGE_0x86
def test_cpu_instruction_STX_ZEROPAGE_0x86():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STX_ZEROPAGE_0x86,
        offset=0x80,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

instructions.STX_ZEROPAGE_Y_0x96
def test_cpu_instruction_STX_ZEROPAGE_Y_0x96():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STX_ZEROPAGE_Y_0x96,
        offset=0x80,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x0F,
    )

"""STY"""
instructions.STY_ABSOLUTE_0x8C
def test_cpu_instruction_STY_ABSOLUTE_0x8C():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_absolute(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STY_ABSOLUTE_0x8C,
        offset=Word(0x8000, endianness=cpu.endianness),
        register_name="Y",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

instructions.STY_ZEROPAGE_0x84
def test_cpu_instruction_STY_ZEROPAGE_0x84():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STY_ZEROPAGE_0x84,
        offset=0x80,
        register_name="Y",
        expected_flags=expected_flags,
        expected_cycles=3,
    )

instructions.STY_ZEROPAGE_X_0x94
def test_cpu_instruction_STY_ZEROPAGE_X_0x94():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STY_ZEROPAGE_X_0x94,
        offset=0x80,
        register_name="Y",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="X",
        offset_value=0x0F,
    )


