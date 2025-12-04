#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    """PHP does not affect any flags."""
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]


def test_cpu_instruction_PHP_IMPLIED_0x08(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Set some flags
    cpu.flags[flags.C] = 1
    cpu.flags[flags.Z] = 1
    cpu.flags[flags.N] = 1

    initial_sp: int = cpu.S
    initial_flags: int = cpu.flags.value

    cpu.ram[pc] = instructions.PHP_IMPLIED_0x08

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.PC == pc + 1
    assert cpu.cycles_executed - cycles_before == 3  # 1 opcode + 2 for push
    assert cpu.S == initial_sp - 1  # Stack pointer decremented

    # PHP pushes status with B flag set (bits 4 and 5 set to 1)
    pushed_status: int = cpu.ram[initial_sp]
    assert pushed_status == (initial_flags | 0b00110000)

    # Verify original flags unchanged
    assert cpu.flags.value == initial_flags


def test_cpu_instruction_PHP_IMPLIED_0x08_b_flag(cpu: CPU) -> None:  # noqa: N802
    """Test that PHP sets B flag in pushed status."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    # Clear all flags to start with a known state
    cpu._flags.value = 0x00
    initial_sp: int = cpu.S
    initial_flags: int = cpu.flags.value

    cpu.ram[pc] = instructions.PHP_IMPLIED_0x08

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    pushed_status: int = cpu.ram[initial_sp]
    # B flag (bit 4) and unused flag (bit 5) should be set in pushed value
    # Standard 6502 status register layout: NV-BDIZC (bit 7 to bit 0)
    assert pushed_status == 0b00110000  # 0x30: B and unused bits set
    # But actual flags should still be 0
    assert cpu.flags.value == initial_flags
