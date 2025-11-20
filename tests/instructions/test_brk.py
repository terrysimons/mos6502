#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, exceptions, flags, instructions
from mos6502.memory import Byte

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_BRK_IMPLIED_0x00(cpu: CPU) -> None:  # noqa: N802
    """Test BRK instruction behavior.

    BRK should:
    1. Push PC+2 to stack (high byte first, then low byte)
    2. Push status register with B flag set to stack
    3. Set I (interrupt disable) flag
    4. Raise CPUBreakError exception
    5. Take 7 cycles
    """
    # given:

    # Set some flags to verify they're preserved in stack
    cpu.C = flags.ProcessorStatusFlags.C[flags.C]
    cpu.Z = flags.ProcessorStatusFlags.Z[flags.Z]
    cpu.V = flags.ProcessorStatusFlags.V[flags.V]
    initial_flags_value = cpu.flags.value

    # Store initial state
    initial_sp = cpu.S
    initial_pc = cpu.PC

    cpu.ram[0xFFFC] = instructions.BRK_IMPLIED_0x00
    cpu.ram[0xFFFD] = 0x00  # Padding byte

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError, exceptions.CPUBreakError):
        cpu.execute(cycles=7)

    # then:
    # 1. Verify stack pointer moved down by 3 (word + byte)
    assert cpu.S == initial_sp - 3, \
        f"Stack pointer should be {initial_sp - 3}, got {cpu.S}"

    # 2. Verify PC+1 was pushed to stack
    # write_word(S-1) writes: lowbyte at S-1, highbyte at S
    # So: lowbyte at 0x1FE, highbyte at 0x1FF
    pushed_pc_low = cpu.ram[initial_sp - 1]
    pushed_pc_high = cpu.ram[initial_sp]
    pushed_pc = (pushed_pc_high << 8) | pushed_pc_low
    expected_pushed_pc = initial_pc + 1  # PC+1 because we're at the opcode
    assert pushed_pc == expected_pushed_pc, \
        f"Pushed PC should be 0x{expected_pushed_pc:04X}, got 0x{pushed_pc:04X}"

    # 3. Verify status register with B flag set was pushed
    pushed_status = cpu.ram[initial_sp - 2]
    expected_status = initial_flags_value | (1 << flags.B)
    assert pushed_status == expected_status, \
        f"Pushed status should be 0x{expected_status:02X}, got 0x{pushed_status:02X}"

    # 4. Verify B flag is set in pushed status
    assert (pushed_status & (1 << flags.B)) != 0, \
        "B flag should be set in pushed status"

    # 5. Verify I flag is set in CPU
    assert cpu.I, "I (interrupt disable) flag should be set after BRK"

    # 6. Verify original flags (except I) are preserved in CPU
    assert cpu.C, "C flag should be preserved"
    assert cpu.Z, "Z flag should be preserved"
    assert cpu.V, "V flag should be preserved"

    # 7. Verify cycles
    assert cpu.cycles_executed == 7, \
        f"BRK should take 7 cycles, got {cpu.cycles_executed}"


def test_cpu_instruction_BRK_IMPLIED_0x00_raises_exception(cpu: CPU) -> None:  # noqa: N802
    """Test that BRK raises CPUBreakError exception."""
    # given:

    cpu.ram[0xFFFC] = instructions.BRK_IMPLIED_0x00
    cpu.ram[0xFFFD] = 0x00

    # when/then:
    exception_raised = False
    try:
        with contextlib.suppress(exceptions.CPUCycleExhaustionError):
            cpu.execute(cycles=7)
    except exceptions.CPUBreakError as e:
        exception_raised = True
        assert "BRK instruction executed" in str(e)
        assert "PC=0x" in str(e)

    assert exception_raised, "BRK should raise CPUBreakError"


def test_cpu_instruction_BRK_IMPLIED_0x00_with_all_flags_clear(cpu: CPU) -> None:  # noqa: N802
    """Test BRK when all flags are initially clear."""
    # given:

    # Clear all flags
    cpu.C = 0
    cpu.Z = 0
    cpu.I = 0
    cpu.D = 0
    cpu.V = 0
    cpu.N = 0

    initial_sp = cpu.S
    initial_flags = cpu.flags.value

    cpu.ram[0xFFFC] = instructions.BRK_IMPLIED_0x00
    cpu.ram[0xFFFD] = 0x00

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError, exceptions.CPUBreakError):
        cpu.execute(cycles=7)

    # then:
    # Status register pushed should have B flag set, even though all others are clear
    pushed_status = cpu.ram[initial_sp - 2]
    assert (pushed_status & (1 << flags.B)) != 0, \
        "B flag should be set in pushed status even when all flags clear"

    # I flag should now be set in CPU
    assert cpu.I, "I flag should be set after BRK"
