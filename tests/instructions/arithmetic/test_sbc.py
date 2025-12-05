#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_simple(cpu: CPU) -> None:  # noqa: N802
    """Test SBC Immediate mode with simple subtraction."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x50
    cpu.flags[flags.C] = 1  # No borrow

    # SBC #$10
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x10

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x40  # 80 - 16 = 64
    assert cpu.flags[flags.C] == 1  # No borrow (A >= M)
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Positive
    assert cpu.flags[flags.V] == 0  # No overflow
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_with_borrow(cpu: CPU) -> None:  # noqa: N802
    """Test SBC with borrow (C=0)."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x50
    cpu.flags[flags.C] = 0  # Borrow set

    # SBC #$10
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x10

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x3F  # 80 - 16 - 1 = 63
    assert cpu.flags[flags.C] == 1  # No borrow needed for result
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    assert cpu.flags[flags.V] == 0
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_borrow_out(cpu: CPU) -> None:  # noqa: N802
    """Test SBC with borrow out (underflow)."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x00
    cpu.flags[flags.C] = 1  # No borrow in

    # SBC #$01
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x01

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0xFF  # 0 - 1 = -1 (255 in unsigned)
    assert cpu.flags[flags.C] == 0  # Borrow occurred
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Negative
    assert cpu.flags[flags.V] == 0  # No signed overflow
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_zero(cpu: CPU) -> None:  # noqa: N802
    """Test SBC resulting in zero."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x50
    cpu.flags[flags.C] = 1

    # SBC #$50
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x50

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x00
    assert cpu.flags[flags.C] == 1  # No borrow
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0
    assert cpu.flags[flags.V] == 0
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_overflow(cpu: CPU) -> None:  # noqa: N802
    """Test SBC signed overflow: positive - negative = negative."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x50  # +80
    cpu.flags[flags.C] = 1

    # SBC #$B0
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0xB0  # -80 in two's complement

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0xA0  # Result wraps (overflow)
    assert cpu.flags[flags.C] == 0  # Borrow occurred
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # Negative
    assert cpu.flags[flags.V] == 1  # Signed overflow
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_ZEROPAGE_0xE5(cpu: CPU) -> None:  # noqa: N802
    """Test SBC Zero Page mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x50
    cpu.ram[0x0042] = 0x30
    cpu.flags[flags.C] = 1

    # SBC $42
    cpu.ram[pc] = instructions.SBC_ZEROPAGE_0xE5
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=3

    # then:
    assert cpu.A == 0x20
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.V] == 0
    # assert cpu.cycles_executed - cycles_before == 3
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_ABSOLUTE_0xED(cpu: CPU) -> None:  # noqa: N802
    """Test SBC Absolute mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x50
    cpu.ram[0x1234] = 0x25
    cpu.flags[flags.C] = 0  # Borrow

    # SBC $1234
    cpu.ram[pc] = instructions.SBC_ABSOLUTE_0xED
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=4

    # then:
    assert cpu.A == 0x2A  # 80 - 37 - 1 = 42
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.V] == 0
    # assert cpu.cycles_executed - cycles_before == 4
    assert cpu.instructions_executed - instructions_before == 1


# BCD (Decimal) Mode Tests


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_bcd_simple(cpu: CPU) -> None:  # noqa: N802
    """Test SBC in BCD mode with simple subtraction."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x09  # BCD 09
    cpu.flags[flags.C] = 1  # No borrow
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # SBC #$05
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x05  # BCD 05

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x04  # BCD 09 - 05 = 04
    assert cpu.flags[flags.C] == 1  # No borrow
    assert cpu.flags[flags.Z] == 0
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_bcd_borrow_low_nibble(cpu: CPU) -> None:  # noqa: N802
    """Test SBC in BCD mode with borrow from low nibble."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x12  # BCD 12
    cpu.flags[flags.C] = 1  # No borrow
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # SBC #$09
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x09  # BCD 09

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x03  # BCD 12 - 09 = 03
    assert cpu.flags[flags.C] == 1  # No borrow out
    assert cpu.flags[flags.Z] == 0
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_bcd_underflow(cpu: CPU) -> None:  # noqa: N802
    """Test SBC in BCD mode with underflow."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x00  # BCD 00
    cpu.flags[flags.C] = 1  # No borrow in
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # SBC #$01
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x01  # BCD 01

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x99  # BCD 00 - 01 = -01, wraps to 99
    assert cpu.flags[flags.C] == 0  # Borrow occurred
    assert cpu.flags[flags.Z] == 0
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_bcd_with_borrow_in(cpu: CPU) -> None:  # noqa: N802
    """Test SBC in BCD mode with borrow in."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x50  # BCD 50
    cpu.flags[flags.C] = 0  # Borrow in
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # SBC #$10
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x10  # BCD 10

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x39  # BCD 50 - 10 - 1 = 39
    assert cpu.flags[flags.C] == 1  # No borrow out
    assert cpu.flags[flags.Z] == 0
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_bcd_zero_result(cpu: CPU) -> None:  # noqa: N802
    """Test SBC in BCD mode resulting in zero."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x50  # BCD 50
    cpu.flags[flags.C] = 1  # No borrow
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # SBC #$50
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x50  # BCD 50

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x00  # BCD 50 - 50 = 00
    assert cpu.flags[flags.C] == 1  # No borrow
    assert cpu.flags[flags.Z] == 1  # Zero
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_SBC_IMMEDIATE_0xE9_bcd_complex(cpu: CPU) -> None:  # noqa: N802
    """Test SBC in BCD mode with complex subtraction."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x73  # BCD 73
    cpu.flags[flags.C] = 0  # Borrow in
    cpu.flags[flags.D] = 1  # Enable decimal mode

    # SBC #$46
    cpu.ram[pc] = instructions.SBC_IMMEDIATE_0xE9
    cpu.ram[pc + 1] = 0x46  # BCD 46

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x26  # BCD 73 - 46 - 1 = 26
    assert cpu.flags[flags.C] == 1  # No borrow out
    assert cpu.flags[flags.Z] == 0
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1
