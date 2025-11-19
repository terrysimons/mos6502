#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: mos6502.CPU, actual_cpu: mos6502.CPU) -> None:
    """JMP does not affect any flags."""
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]


def test_cpu_instruction_JMP_ABSOLUTE_0x4C() -> None:  # noqa: N802
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    cpu.ram[0xFFFC] = instructions.JMP_ABSOLUTE_0x4C
    cpu.ram[0xFFFD] = 0x00
    cpu.ram[0xFFFE] = 0x80  # Jump to 0x8000

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.PC == 0x8000
    assert cpu.cycles_executed == 3  # 1 opcode + 2 for fetch_word
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_JMP_INDIRECT_0x6C() -> None:  # noqa: N802
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    # JMP ($1020) - normal case (no page boundary)
    cpu.ram[0xFFFC] = instructions.JMP_INDIRECT_0x6C
    cpu.ram[0xFFFD] = 0x20
    cpu.ram[0xFFFE] = 0x10  # Indirect address = 0x1020

    # Address stored at 0x1020
    cpu.ram[0x1020] = 0x00
    cpu.ram[0x1021] = 0x90  # Jump target = 0x9000

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.PC == 0x9000
    assert cpu.cycles_executed == 5  # 1 opcode + 2 fetch_word + 2 read_word
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_JMP_INDIRECT_0x6C_page_boundary_bug() -> None:  # noqa: N802
    """Test the famous 6502 page boundary bug in JMP indirect.

    VARIANT: 6502/6502A - When indirect address is 0xXXFF, the high byte
    wraps to 0xXX00 instead of crossing to the next page.
    VARIANT: 65C02 - Bug is fixed, correctly crosses page boundary.
    """
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    # JMP ($10FF) - page boundary bug case
    cpu.ram[0xFFFC] = instructions.JMP_INDIRECT_0x6C
    cpu.ram[0xFFFD] = 0xFF
    cpu.ram[0xFFFE] = 0x10  # Indirect address = 0x10FF

    # For 6502/6502A (bug): reads low byte from 0x10FF, high byte from 0x1000
    cpu.ram[0x10FF] = 0x34  # Low byte
    cpu.ram[0x1000] = 0x12  # High byte (wraps within page)
    cpu.ram[0x1100] = 0x56  # This would be high byte on 65C02 (bug fixed)

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    # VARIANT: 6502/6502A - Jump to 0x1234 (bug behavior)
    assert cpu.PC == 0x1234
    # VARIANT: 65C02 - Would jump to 0x5634 (correct behavior)

    assert cpu.cycles_executed == 5
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_JMP_INDIRECT_0x6C_not_page_boundary() -> None:  # noqa: N802
    """Verify that non-page-boundary addresses work normally."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    # JMP ($10FE) - not on page boundary
    cpu.ram[0xFFFC] = instructions.JMP_INDIRECT_0x6C
    cpu.ram[0xFFFD] = 0xFE
    cpu.ram[0xFFFE] = 0x10  # Indirect address = 0x10FE

    # Address stored at 0x10FE (crosses page boundary correctly)
    cpu.ram[0x10FE] = 0x42
    cpu.ram[0x10FF] = 0xA5  # Jump target = 0xA542

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=5)

    # then:
    assert cpu.PC == 0xA542
    assert cpu.cycles_executed == 5
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
