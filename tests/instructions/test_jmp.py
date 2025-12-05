#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    """JMP does not affect any flags."""
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]


def test_cpu_instruction_JMP_ABSOLUTE_0x4C(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.ram[pc] = instructions.JMP_ABSOLUTE_0x4C
    cpu.ram[pc + 1] = 0x00
    cpu.ram[pc + 2] = 0x80  # Jump to 0x8000

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=3

    # then:
    assert cpu.PC == 0x8000
    # assert cpu.cycles_executed - cycles_before == 3  # 1 opcode + 2 for fetch_word
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_JMP_INDIRECT_0x6C(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    # JMP ($1020) - normal case (no page boundary)
    cpu.ram[pc] = instructions.JMP_INDIRECT_0x6C
    cpu.ram[pc + 1] = 0x20
    cpu.ram[pc + 2] = 0x10  # Indirect address = 0x1020

    # Address stored at 0x1020
    cpu.ram[0x1020] = 0x00
    cpu.ram[0x1021] = 0x90  # Jump target = 0x9000

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=5

    # then:
    assert cpu.PC == 0x9000
    # assert cpu.cycles_executed - cycles_before == 5  # 1 opcode + 2 fetch_word + 2 read_word
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_JMP_INDIRECT_0x6C_page_boundary_bug_nmos(nmos_cpu: CPU) -> None:  # noqa: N802
    """Test the famous 6502 page boundary bug in JMP indirect (NMOS variants).

    VARIANT: 6502 - When indirect address is 0xXXFF, the high byte wraps to
                    0xXX00 instead of crossing to the next page (BUG)
    VARIANT: 6502A - Same bug as 6502
    VARIANT: 6502C - Same bug as 6502
    """
    # given:
    cycles_before = nmos_cpu.cycles_executed
    nmos_cpu.PC = 0x0400
    pc = nmos_cpu.PC
    initial_cpu: CPU = copy.deepcopy(nmos_cpu)

    # JMP ($10FF) - page boundary bug case
    nmos_cpu.ram[pc] = instructions.JMP_INDIRECT_0x6C
    nmos_cpu.ram[pc + 1] = 0xFF
    nmos_cpu.ram[pc + 2] = 0x10  # Indirect address = 0x10FF

    # NMOS bug: reads low byte from 0x10FF, high byte from 0x1000 (wraps within page)
    nmos_cpu.ram[0x10FF] = 0x34  # Low byte
    nmos_cpu.ram[0x1000] = 0x12  # High byte (wraps within page - BUG)
    nmos_cpu.ram[0x1100] = 0x56  # This is NOT read on NMOS

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        nmos_cpu.execute(max_instructions=1)  # cycles=5

    # then:
    # VARIANT: 6502/6502A/6502C - Jump to 0x1234 (bug behavior)
    assert nmos_cpu.PC == 0x1234  # Jumps to 0x1234 due to page boundary bug
    # assert nmos_cpu.cycles_executed - cycles_before == 5
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=nmos_cpu)


def test_cpu_instruction_JMP_INDIRECT_0x6C_page_boundary_bug_cmos(cmos_cpu: CPU) -> None:  # noqa: N802
    """Test that JMP indirect page boundary bug is FIXED in 65C02.

    VARIANT: 65C02 - Bug is fixed, correctly crosses page boundary
    """
    # given:
    cycles_before = cmos_cpu.cycles_executed
    cmos_cpu.PC = 0x0400
    pc = cmos_cpu.PC
    initial_cpu: CPU = copy.deepcopy(cmos_cpu)

    # JMP ($10FF) - page boundary case
    cmos_cpu.ram[pc] = instructions.JMP_INDIRECT_0x6C
    cmos_cpu.ram[pc + 1] = 0xFF
    cmos_cpu.ram[pc + 2] = 0x10  # Indirect address = 0x10FF

    # CMOS fix: reads low byte from 0x10FF, high byte from 0x1100 (correctly crosses page)
    cmos_cpu.ram[0x10FF] = 0x34  # Low byte
    cmos_cpu.ram[0x1000] = 0x12  # This is NOT read on CMOS
    cmos_cpu.ram[0x1100] = 0x56  # High byte (correctly crosses page - FIX)

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cmos_cpu.execute(max_instructions=1)  # cycles=5

    # then:
    # VARIANT: 65C02 - Jump to 0x5634 (correct behavior, bug fixed)
    assert cmos_cpu.PC == 0x5634  # Jumps to 0x5634, bug is fixed
    # assert cmos_cpu.cycles_executed - cycles_before == 5
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cmos_cpu)


def test_cpu_instruction_JMP_INDIRECT_0x6C_not_page_boundary(cpu: CPU) -> None:  # noqa: N802
    """Verify that non-page-boundary addresses work normally."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    # JMP ($10FE) - not on page boundary
    cpu.ram[pc] = instructions.JMP_INDIRECT_0x6C
    cpu.ram[pc + 1] = 0xFE
    cpu.ram[pc + 2] = 0x10  # Indirect address = 0x10FE

    # Address stored at 0x10FE (crosses page boundary correctly)
    cpu.ram[0x10FE] = 0x42
    cpu.ram[0x10FF] = 0xA5  # Jump target = 0xA542

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=5

    # then:
    assert cpu.PC == 0xA542
    # assert cpu.cycles_executed - cycles_before == 5
    assert cpu.instructions_executed - instructions_before == 1
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
