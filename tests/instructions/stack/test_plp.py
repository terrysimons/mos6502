#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions
from mos6502.flags import FlagsRegister

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_PLP_IMPLIED_0x28(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    # Push a status value onto the stack
    # Standard 6502 status register layout: NV-BDIZC (bit 7 to bit 0)
    # Set all flags: C=1, Z=1, I=1, D=1, B=1, _=1, V=1, N=1 = 0xFF
    status_value: int = 0xFF
    cpu.ram[cpu.S] = status_value
    cpu.S -= 1

    cpu.ram[pc] = instructions.PLP_IMPLIED_0x28

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=4

    # then:
    assert cpu.PC == pc + 1
    # assert cpu.cycles_executed - cycles_before == 4  # 1 opcode + 3 for pull
    assert cpu.flags.value == status_value  # Flags restored from stack
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.I] == 1
    assert cpu.flags[flags.D] == 1
    assert cpu.flags[flags.V] == 1
    assert cpu.flags[flags.N] == 1


def test_cpu_instruction_PLP_IMPLIED_0x28_clear_flags(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    # Set some flags initially using individual flag setters
    cpu.flags[flags.C] = 1
    cpu.flags[flags.Z] = 1
    cpu.flags[flags.N] = 1

    # Push zero status onto the stack
    cpu.ram[cpu.S] = 0x00
    cpu.S -= 1

    cpu.ram[pc] = instructions.PLP_IMPLIED_0x28

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=4

    # then:
    assert cpu.PC == pc + 1
    # assert cpu.cycles_executed - cycles_before == 4
    assert cpu.instructions_executed - instructions_before == 1
    assert cpu.flags.value == 0x00  # All flags cleared
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.I] == 0
    assert cpu.flags[flags.D] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.flags[flags.N] == 0


def test_cpu_instruction_PLP_IMPLIED_0x28_with_php(cpu: CPU) -> None:  # noqa: N802
    """Test PLP after PHP - round trip."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    # Set some specific flags
    cpu.flags[flags.C] = 1
    cpu.flags[flags.Z] = 1
    cpu.flags[flags.N] = 1
    initial_flags: int = cpu.flags.value

    cpu.ram[pc] = instructions.PHP_IMPLIED_0x08
    cpu.ram[pc + 1] = instructions.PLP_IMPLIED_0x28

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=2)  # cycles=7

    # then:
    assert cpu.PC == pc + 2
    # assert cpu.cycles_executed - cycles_before == 7  # 3 for PHP + 4 for PLP

    # Flags should be restored (PHP pushes with B flag set, but PLP restores all bits)
    # So we get back the original flags OR'd with the B bits that were pushed
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.N] == 1


def test_cpu_instruction_PLP_preserves_FlagsRegister_type(cpu: CPU) -> None:  # noqa: N802
    """Test that PLP maintains the FlagsRegister type, not replacing it with plain Byte."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    cpu.ram[cpu.S] = 0xF0
    cpu.S -= 1
    cpu.ram[pc] = instructions.PLP_IMPLIED_0x28

    # Verify we start with a FlagsRegister
    assert isinstance(cpu._flags, FlagsRegister), "CPU should start with FlagsRegister"

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=4

    # then:
    assert isinstance(cpu._flags, FlagsRegister), \
        "PLP must preserve FlagsRegister type for flag logging to work"
    assert cpu.flags.value == 0xF0
