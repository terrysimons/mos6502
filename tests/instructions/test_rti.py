#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions
from mos6502.flags import FlagsRegister
from mos6502.memory import Byte

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_RTI_IMPLIED_0x40(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    # Simulate interrupt state: PC and status pushed on stack
    # (BRK pushes PC first, then status)

    # Push PC (0x8000) - low byte at S-1, high byte at S
    cpu.ram[cpu.S] = 0x80  # High byte at 0x1FF
    cpu.ram[cpu.S - 1] = 0x00  # Low byte at 0x1FE
    cpu.S -= 2

    # Push status (0xF3: C=1, Z=1, I=1, D=1, V=1, N=1)
    status_value: int = 0xF3
    cpu.ram[cpu.S] = status_value
    cpu.S -= 1

    # Clear flags to verify RTI restores them
    cpu._flags = Byte(0x00)

    cpu.ram[pc] = instructions.RTI_IMPLIED_0x40

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.PC == 0x8000
    assert cpu.cycles_executed - cycles_before == 6  # 1 opcode + 1 read status + 2 read PC + 2 overhead
    assert cpu.flags.value == status_value
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.I] == 1
    assert cpu.flags[flags.D] == 1
    assert cpu.flags[flags.V] == 1
    assert cpu.flags[flags.N] == 1


def test_cpu_instruction_RTI_IMPLIED_0x40_stack_pointer(cpu: CPU) -> None:  # noqa: N802
    """Test that RTI correctly adjusts stack pointer."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    initial_sp: int = cpu.S

    # Simulate interrupt state: push PC and status (same order as BRK)
    # Push PC (0x1234) - low byte at S-1, high byte at S
    cpu.ram[cpu.S] = 0x12  # High byte at 0x1FF
    cpu.ram[cpu.S - 1] = 0x34  # Low byte at 0x1FE
    cpu.S -= 2

    # Push status
    cpu.ram[cpu.S] = 0x00  # Status at 0x1FD
    cpu.S -= 1

    stack_after_push: int = cpu.S

    cpu.ram[pc] = instructions.RTI_IMPLIED_0x40

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then: Stack pointer should be restored
    assert cpu.S == initial_sp  # Stack fully popped
    assert cpu.PC == 0x1234


def test_cpu_instruction_RTI_preserves_FlagsRegister_type(cpu: CPU) -> None:  # noqa: N802
    """Test that RTI maintains the FlagsRegister type, not replacing it with plain Byte."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    # Push PC (0x8000)
    cpu.ram[cpu.S] = 0x80
    cpu.ram[cpu.S - 1] = 0x00
    cpu.S -= 2

    # Push status
    cpu.ram[cpu.S] = 0xF0
    cpu.S -= 1

    cpu.ram[pc] = instructions.RTI_IMPLIED_0x40

    # Verify we start with a FlagsRegister
    assert isinstance(cpu._flags, FlagsRegister), "CPU should start with FlagsRegister"

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert isinstance(cpu._flags, FlagsRegister), \
        "RTI must preserve FlagsRegister type for flag logging to work"
    assert cpu.flags.value == 0xF0
    assert cpu.PC == 0x8000
