#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import copy
import logging

import mos6502
import mos6502.flags as flags
import mos6502.instructions as instructions
import mos6502.exceptions as exceptions
from mos6502.memory import Byte, Word

log = logging.getLogger('mos6502')
log.setLevel(logging.DEBUG)

def check_noop_flags(expected_cpu, actual_cpu):
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]

def verify_load_immediate(cpu, data, instruction, register_name, expected_flags, expected_cycles) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    # Load direct to memory
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = data

    # when:
    try:
        cpu.execute(cycles=expected_cycles)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then:
    assert cpu.cycles_executed == expected_cycles
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

def verify_load_zeropage(cpu, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_register_name=None, offset_value=0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    if offset_register_name is not None:
        setattr(cpu, offset_register_name, offset_value)

    # Load with zeropage offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = offset
    cpu.ram[(offset + offset_value) & 0xFF] = data # zero page is 0x00-0xFF, so need to handle wraparound

    # when:
    try:
        cpu.execute(cycles=expected_cycles)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then:
    assert cpu.cycles_executed == expected_cycles
    if offset_register_name is not None:
        assert getattr(cpu, offset_register_name) == offset_value
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

def verify_load_absolute(cpu, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_register_name=None, offset_value=0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    if offset_register_name is not None:
        setattr(cpu, offset_register_name, offset_value)

    offset_address: Word = Word(offset, endianness=cpu.endianness)

    # Load with 16-bit address + cpu.X offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = 0xFF & offset_address.lowbyte
    cpu.ram[0xFFFE] = 0xFF & offset_address.highbyte
    cpu.ram[(offset_address + offset_value) & 0xFFFF] = data

    # when:
    try:
        cpu.execute(cycles=expected_cycles)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then:
    assert cpu.cycles_executed == expected_cycles
    if offset_register_name is not None:
        assert getattr(cpu, offset_register_name) == offset_value
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

def verify_load_indexed_indirect(cpu, sp_value, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_value=0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    setattr(cpu, 'X', offset_value)

    offset_address: Word = Word(offset, endianness=cpu.endianness)

    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = sp_value # fetch_byte() -> 0x02
    cpu.ram[sp_value + offset_value] = 0xFF & offset_address.lowbyte # 0x02 + cpu.X(value))
    cpu.ram[sp_value + offset_value + 1] = 0x80 & offset_address.highbyte # read_byte(0x06) == 0x00, read_byte(0x07) == 0x80 -> Word(0x8000)
    cpu.ram[offset_address & 0xFFFF] = data # read_byte(0x8000) -> cpu.A

    # when:
    try:
        cpu.execute(cycles=expected_cycles)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then:
    assert cpu.cycles_executed == expected_cycles
    assert getattr(cpu, 'X') == offset_value
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

def verify_load_indirect_indexed(cpu, sp_value, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_value=0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    setattr(cpu, 'Y', offset_value)

    offset_address: Word = Word(offset, endianness=cpu.endianness)

    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = sp_value # SP
    cpu.ram[sp_value] = 0xFF & offset_address.lowbyte # 0x02@0xFFFD is the start of our address vector in the zero page (LSB)
    cpu.ram[sp_value + 1] = 0xFF & offset_address.highbyte # 0x03 is the msb of our address (0x8000)
    cpu.ram[(offset_address + offset_value) & 0xFFFF] = data # 0x8000 + cpu.Y(0x80) [0x8080] -> cpu.A

    # when:
    try:
        cpu.execute(cycles=expected_cycles)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then
    assert cpu.cycles_executed == expected_cycles
    assert getattr(cpu, 'Y') == offset_value
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


''' LDA '''
def test_cpu_instruction_LDA_IMMEDIATE_0xA9_with_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0xFF, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDA_IMMEDIATE_0xA9,
        register_name='A', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=2
    )

def test_cpu_instruction_LDA_IMMEDIATE_0xA9_without_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x01, # Load 0x01 directly from 0xFFFD
        instruction=instructions.LDA_IMMEDIATE_0xA9,
        register_name='A', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=2
    )

def test_cpu_instruction_LDA_IMMEDIATE_0xA9_with_zero_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x00, # Load 0x00 directly from 0xFFFD
        instruction=instructions.LDA_IMMEDIATE_0xA9,
        register_name='A', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=2
    )

def test_cpu_instruction_LDA_ZEROPAGE_0xA5_with_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDA_ZEROPAGE_0xA5,
        register_name='A', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDA_ZEROPAGE_0xA5_without_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01,
        offset=0x42,
        instruction=instructions.LDA_ZEROPAGE_0xA5,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDA_ZEROPAGE_0xA5_with_zero_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00,
        offset=0x42,
        instruction=instructions.LDA_ZEROPAGE_0xA5,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_with_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x42,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0x08
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_without_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x42,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='X',
        offset_value=0x08
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_with_zero_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x42,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='X',
        offset_value=0x08
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_wrap_with_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x80,
        register_name='A',
        expected_flags=expected_flags,
        offset_register_name='X',
        expected_cycles=4,
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_wrap_without_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x80,
        register_name='A',
        expected_flags=expected_flags,
        offset_register_name='X',
        expected_cycles=4,
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_wrap_with_zero_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x80,
        register_name='A',
        expected_flags=expected_flags,
        offset_register_name='X',
        expected_cycles=4,
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_ABSOLUTE_0xAD_with_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_0xAD,
        offset=0x4222,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDA_ABSOLUTE_0xAD_without_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_0xAD,
        offset=0x4222,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDA_ABSOLUTE_0xAD_with_zero_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_0xAD,
        offset=0x4222,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_with_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4222,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='X',
        offset_value=0x01
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_without_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4222,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='X',
        offset_value=0x01
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_with_zero_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4220,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='X',
        offset_value=0x01
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_with_negative_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4223,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_without_negative_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4223,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_with_zero_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4223,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0xFF
    )


def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_with_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='Y',
        offset_value=0x01
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_without_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='Y',
        offset_value=0x01
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_with_zero_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='Y',
        offset_value=0x01
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_with_negative_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='Y',
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_without_negative_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='Y',
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_with_zero_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='Y',
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_INDEXED_INDIRECT_X_0xA1_with_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indexed_indirect(
        cpu=cpu,
        sp_value=0x02,
        data=0xFF,
        instruction=instructions.LDA_INDEXED_INDIRECT_X_0xA1,
        offset=0x8000,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0x04
    )

def test_cpu_instruction_LDA_INDEXED_INDIRECT_X_0xA1_without_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indexed_indirect(
        cpu=cpu,
        sp_value=0x02,
        data=0x01,
        instruction=instructions.LDA_INDEXED_INDIRECT_X_0xA1,
        offset=0x8000,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0x04
    )

def test_cpu_instruction_LDA_INDEXED_INDIRECT_X_0xA1_with_zero_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indexed_indirect(
        cpu=cpu,
        sp_value=0x02,
        data=0x00,
        instruction=instructions.LDA_INDEXED_INDIRECT_X_0xA1,
        offset=0x8000,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0x04
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_with_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    # def verify_load_indirect_indexed(cpu, sp_value, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_value=0x00) -> None:
    verify_load_indirect_indexed(
        cpu=cpu,
        sp_value=0x80,
        data=0xFF,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x8000,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_value=0x04
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_without_negative_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    # def verify_load_indirect_indexed(cpu, sp_value, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_value=0x00) -> None:
    verify_load_indirect_indexed(
        cpu=cpu,
        sp_value=0x80,
        data=0x01,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x8000,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_value=0x04
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_with_zero_flag() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    # def verify_load_indirect_indexed(cpu, sp_value, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_value=0x00) -> None:
    verify_load_indirect_indexed(
        cpu=cpu,
        sp_value=0x80,
        data=0x00,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x8000,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_value=0x04
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_with_negative_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    # def verify_load_indirect_indexed(cpu, sp_value, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_value=0x00) -> None:
    verify_load_indirect_indexed(
        cpu=cpu,
        sp_value=0xFF,
        data=0xFF,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x80FF,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_without_negative_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    # def verify_load_indirect_indexed(cpu, sp_value, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_value=0x00) -> None:
    verify_load_indirect_indexed(
        cpu=cpu,
        sp_value=0xFF,
        data=0x01,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x80FF,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0xFF
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_with_zero_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    # def verify_load_indirect_indexed(cpu, sp_value, data, instruction, offset, register_name, expected_flags, expected_cycles, offset_value=0x00) -> None:
    verify_load_indirect_indexed(
        cpu=cpu,
        sp_value=0xFF,
        data=0x00,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x80FF,
        register_name='A',
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0xFF
    )

''' LDX '''
def test_cpu_instruction_LDX_IMMEDIATE_0xA2_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0xFF, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDX_IMMEDIATE_0xA2,
        register_name='X', # Load into register X
        expected_flags=expected_flags,
        expected_cycles=2
    )

def test_cpu_instruction_LDX_IMMEDIATE_0xA2_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x01, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDX_IMMEDIATE_0xA2,
        register_name='X', # Load into register X
        expected_flags=expected_flags,
        expected_cycles=2
    )

def test_cpu_instruction_LDX_IMMEDIATE_0xA2_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x00, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDX_IMMEDIATE_0xA2,
        register_name='X', # Load into register X
        expected_flags=expected_flags,
        expected_cycles=2
    )

def test_cpu_instruction_LDX_ZEROPAGE_0xA6_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDX_ZEROPAGE_0xA6,
        register_name='X', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDX_ZEROPAGE_0xA6_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDX_ZEROPAGE_0xA6,
        register_name='X', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDX_ZEROPAGE_0xA6_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDX_ZEROPAGE_0xA6,
        register_name='X', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDX_ZEROPAGE_Y_0xB6_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDX_ZEROPAGE_Y_0xB6,
        offset=0x42,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='Y',
        offset_value=0x08
    )

def test_cpu_instruction_LDX_ZEROPAGE_Y_0xB6_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDX_ZEROPAGE_Y_0xB6,
        offset=0x42,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='Y',
        offset_value=0x08
    )

def test_cpu_instruction_LDX_ZEROPAGE_Y_0xB6_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDX_ZEROPAGE_Y_0xB6,
        offset=0x42,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='Y',
        offset_value=0x08
    )

def test_cpu_instruction_LDX_ABSOLUTE_0xAE_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDX_ABSOLUTE_0xAE,
        offset=0x4222,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=4
    )
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

def test_cpu_instruction_LDX_ABSOLUTE_0xAE_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDX_ABSOLUTE_0xAE,
        offset=0x4222,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDX_ABSOLUTE_0xAE_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDX_ABSOLUTE_0xAE,
        offset=0x4222,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4222,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='Y',
        offset_value=0x01
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4222,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='Y',
        offset_value=0x01
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4222,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='Y',
        offset_value=0x01
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_with_negative_flag_crossing_page_boundary():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4223,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='Y',
        offset_value=0xFF
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_without_negative_flag_flag_crossing_page_boundary():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4223,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='Y',
        offset_value=0xFF
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_with_zero_flag_flag_crossing_page_boundary():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4223,
        register_name='X',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='Y',
        offset_value=0xFF
    )


'''LDY'''
def test_cpu_instruction_LDY_IMMEDIATE_0xA0_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0xFF, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDY_IMMEDIATE_0xA0,
        register_name='Y', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=2
    )

def test_cpu_instruction_LDY_IMMEDIATE_0xA0_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x01, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDY_IMMEDIATE_0xA0,
        register_name='Y', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=2
    )

def test_cpu_instruction_LDY_IMMEDIATE_0xA0_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x00, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDY_IMMEDIATE_0xA0,
        register_name='Y', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=2
    )

def test_cpu_instruction_LDY_ZEROPAGE_0xA4_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDY_ZEROPAGE_0xA4,
        register_name='Y', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDY_ZEROPAGE_0xA4_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDY_ZEROPAGE_0xA4,
        register_name='Y', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDY_ZEROPAGE_0xA4_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDY_ZEROPAGE_0xA4,
        register_name='Y', # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDY_ZEROPAGE_X_0xB4_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDY_ZEROPAGE_X_0xB4,
        offset=0x42,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0x08
    )

def test_cpu_instruction_LDY_ZEROPAGE_X_0xB4_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDY_ZEROPAGE_X_0xB4,
        offset=0x42,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0x08
    )

def test_cpu_instruction_LDY_ZEROPAGE_X_0xB4_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDY_ZEROPAGE_X_0xB4,
        offset=0x42,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0x08
    )

def test_cpu_instruction_LDY_ABSOLUTE_0xAC_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDY_ABSOLUTE_0xAC,
        offset=0x4222,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDY_ABSOLUTE_0xAC_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDY_ABSOLUTE_0xAC,
        offset=0x4222,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDY_ABSOLUTE_0xAC_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDY_ABSOLUTE_0xAC,
        offset=0x4222,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=4
    )

def test_cpu_instruction_LDY_ABSOLUTE_X_0xBC_with_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDY_ABSOLUTE_X_0xBC,
        offset=0x4222,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='X',
        offset_value=0x01
    )

def test_cpu_instruction_LDY_ABSOLUTE_X_0xBC_without_negative_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDY_ABSOLUTE_X_0xBC,
        offset=0x4222,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='X',
        offset_value=0x01
    )

def test_cpu_instruction_LDY_ABSOLUTE_X_0xBC_with_zero_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDY_ABSOLUTE_X_0xBC,
        offset=0x4222,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name='X',
        offset_value=0x01
    )

def test_cpu_instruction_LDY_ABSOLUTE_X_0xBC_with_negative_flag_crossing_page_boundary() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDY_ABSOLUTE_X_0xBC,
        offset=0x4223,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0xFF
    )

def test_cpu_instruction_LDY_ABSOLUTE_X_0xBC_without_negative_flag_crossing_page_boundary():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDY_ABSOLUTE_X_0xBC,
        offset=0x4223,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0xFF
    )

def test_cpu_instruction_LDY_ABSOLUTE_X_0xBC_with_zero_flag_crossing_page_boundary():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDY_ABSOLUTE_X_0xBC,
        offset=0x4223,
        register_name='Y',
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name='X',
        offset_value=0xFF
    )
