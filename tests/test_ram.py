#!/usr/bin/env python3

from mos6502.bitarray_factory import int2ba

import mos6502
import mos6502.memory as ram
from mos6502 import errors
from mos6502.core import INFINITE_CYCLES
from mos6502.memory import Byte, Word


def test_ram_byte() -> None:
    a: Byte = Byte(value=1)
    b: Byte = Byte(value=2)

    c: Byte = a + b

    assert(c == int2ba(3, length=8, endian=ram.ENDIANNESS))

    assert(c == 3)

    d: Byte = Byte(value=3)

    assert(c == d)

    d: Word = Word(value=3)

    assert(c == d)

def test_ram_word() -> None:
    a: Word = Word(value=1)
    b: Word = Word(value=2)

    c: Word = a + b

    assert(c == int2ba(3, length=16, endian=ram.ENDIANNESS))

    assert(c == 3)

    d: Word = Word(value=3)

    assert(c == d)

    d: Word = Byte(value=3)

    assert(c == d)

def test_ram_size() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # There are 64k bytes total
    # 0-65535
    #
    # 0-255 - zeropage
    # 256-511 - stack
    # 512 - 65535 - heap
    assert len(cpu.ram.zeropage) == 256
    assert len(cpu.ram.stack) == 256
    assert len(cpu.ram.heap) == 65536 - 512
    assert len(cpu.ram) == 65536

def test_ram_zeropage() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    for address in range(256):
        assert cpu.ram.memory_section(address=address) == "zeropage"

def test_ram_stack() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    for address in range(256):
        assert cpu.ram.memory_section(address=address + 256) == "stack"

def test_ram_heap() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    for address in range(65536 - 512):
        assert cpu.ram.memory_section(address=address + 512) == "heap"

def test_ram_out_of_bounds() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    expected_section: None= None
    section: None = expected_section
    got_exception = False
    try:
        section: None = cpu.ram.memory_section(address=len(cpu.ram) + 1)
    except errors.InvalidMemoryLocationError:
        got_exception = True

    assert section == expected_section
    assert got_exception is True

    got_exception = False
    try:
        section: None = cpu.ram.memory_section(-1)
    except errors.InvalidMemoryLocationError:
        got_exception = True

    assert got_exception is True

    got_exception = False
    try:
        section: None = cpu.ram.memory_section(len(cpu.ram) + 1)
    except errors.InvalidMemoryLocationError:
        got_exception = True

    assert got_exception is True

def test_ram_read_byte() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    cpu.cycles = INFINITE_CYCLES

    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    cpu.ram[0x4242] = 0xFF
    cpu.PC = 0x4242

    # when:
    data = cpu.read_byte(address=0x4242)

    # then:
    assert data == cpu.ram[0x4242]
    assert cpu.cycles_executed - cycles_before == 1

def test_ram_fetch_byte() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.cycles = INFINITE_CYCLES
    cpu.reset()

    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    cpu.ram[0x4242] = 0xFF
    cpu.PC = 0x4242

    # when:
    data = cpu.fetch_byte()

    # then:
    assert data == cpu.ram[0x4242]
    assert cpu.cycles_executed - cycles_before == 1

def test_ram_read_word() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.cycles = INFINITE_CYCLES
    cpu.reset()

    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    cpu.ram[0x4242] = 0xEF
    cpu.ram[0x4243] = 0xBE
    cpu.PC = 0x4242

    # when:
    data: Word = cpu.read_word(address=0x4242)

    # then:
    assert data == Word(0xBEEF, endianness=cpu.endianness)
    assert cpu.cycles_executed - cycles_before == 2

def test_ram_fetch_word() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.cycles = INFINITE_CYCLES
    cpu.reset()

    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    cpu.ram[0x4242] = 0xEF
    cpu.ram[0x4243] = 0xBE
    cpu.PC = 0x4242

    # when:
    data: Word = cpu.fetch_word()

    # then:
    assert data == Word(0xBEEF, endianness=cpu.endianness)
    assert cpu.cycles_executed - cycles_before == 2

def test_ram_write_byte() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.cycles = INFINITE_CYCLES
    cpu.reset()

    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    cpu.ram[0x4242] = 0x00

    # when:
    cpu.write_byte(address=0x4242, data=0xFF)

    # then:
    assert cpu.ram[0x4242] == 0xFF
    assert cpu.cycles_executed - cycles_before == 1

def test_ram_write_word() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.cycles = INFINITE_CYCLES
    cpu.reset()

    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    cpu.ram[0x4242] = 0x00
    cpu.ram[0x4243] = 0x00

    # when:
    cpu.write_word(address=0x4242, data=Word(0xBEEF, endianness="little"))

    # then:
    assert cpu.ram[0x4242] == 0xEF
    assert cpu.ram[0x4243] == 0xBE
    assert cpu.cycles_executed - cycles_before == 2

