#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_BNE_RELATIVE_0xD0_branch_taken(cpu: CPU) -> None:  # noqa: N802
    """Test BNE when zero flag is clear (branch taken)."""
    # given:

    # Clear zero flag
    cpu.flags[flags.Z] = 0

    # BNE with offset +5
    cpu.ram[0xFFFC] = instructions.BNE_RELATIVE_0xD0
    cpu.ram[0xFFFD] = 0x05

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.PC == (0xFFFE + 5) & 0xFFFF  # PC after fetch_byte + offset (wrapped)
    assert cpu.cycles_executed == 3  # 1 opcode + 1 read offset + 1 branch taken


def test_cpu_instruction_BNE_RELATIVE_0xD0_branch_not_taken(cpu: CPU) -> None:  # noqa: N802
    """Test BNE when zero flag is set (branch not taken)."""
    # given:

    # Set zero flag
    cpu.flags[flags.Z] = 1

    # BNE with offset +5
    cpu.ram[0xFFFC] = instructions.BNE_RELATIVE_0xD0
    cpu.ram[0xFFFD] = 0x05

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == 0xFFFE  # PC just moved past offset byte
    assert cpu.cycles_executed == 2  # 1 opcode + 1 read offset


def test_cpu_instruction_BNE_RELATIVE_0xD0_negative_offset(cpu: CPU) -> None:  # noqa: N802
    """Test BNE with negative offset (branch backward)."""
    # given:

    # Clear zero flag
    cpu.flags[flags.Z] = 0

    # Start at 0x0200
    cpu.PC = 0x0200

    # BNE with offset -10 (0xF6 in two's complement)
    cpu.ram[0x0200] = instructions.BNE_RELATIVE_0xD0
    cpu.ram[0x0201] = 0xF6  # -10 in signed byte

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=3)

    # then:
    assert cpu.PC == 0x0202 - 10  # PC after fetch_byte, then minus 10
    assert cpu.cycles_executed == 3


def test_cpu_instruction_BNE_RELATIVE_0xD0_page_boundary_cross(cpu: CPU) -> None:  # noqa: N802
    """Test BNE with page boundary crossing (costs extra cycle)."""
    # given:

    # Clear zero flag
    cpu.flags[flags.Z] = 0

    # Start at 0x02FD (so after fetch we're at 0x02FF)
    cpu.PC = 0x02FD

    # BNE with offset +5
    # After opcode fetch: PC = 0x02FE
    # After offset fetch: PC = 0x02FF (page 0x02)
    # After branch: PC = 0x02FF + 5 = 0x0304 (page 0x03) - crosses boundary!
    cpu.ram[0x02FD] = instructions.BNE_RELATIVE_0xD0
    cpu.ram[0x02FE] = 0x05

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.PC == 0x02FF + 5  # Crossed page boundary
    assert cpu.cycles_executed == 4  # 1 opcode + 1 read + 1 branch + 1 page cross
