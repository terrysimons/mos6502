#!/usr/bin/env python3
"""Test that fetch_word() correctly advances PC by 2 bytes.

This test verifies the bug fix for fetch_word() which was only incrementing
PC by 1 instead of 2, causing all 3-byte instructions to misalign PC.
"""

import contextlib
import pytest

from mos6502 import CPU, errors, instructions


def test_fetch_word_advances_pc_by_2(cpu: CPU) -> None:
    """Test that fetch_word() advances PC by 2 bytes."""
    # given:
    cpu.cycles = 100  # Set cycles so spend_cpu_cycles doesn't fail
    cpu.PC = 0x1000
    cpu.ram[0x1000] = 0x34  # Low byte
    cpu.ram[0x1001] = 0x12  # High byte

    # when:
    word = cpu.fetch_word()

    # then:
    assert word == 0x1234, f"Expected word 0x1234, got 0x{word:04X}"
    assert cpu.PC == 0x1002, f"Expected PC=0x1002 after fetch_word, got PC=0x{cpu.PC:04X}"


def test_lda_absolute_advances_pc_by_3(cpu: CPU) -> None:
    """Test that LDA absolute (3-byte instruction) advances PC by 3."""
    # given:
    cpu.PC = 0x0800

    # LDA $1234 (absolute) - opcode AD, address $1234
    cpu.ram[0x0800] = 0xAD  # LDA absolute opcode
    cpu.ram[0x0801] = 0x34  # Low byte of address
    cpu.ram[0x0802] = 0x12  # High byte of address
    cpu.ram[0x1234] = 0x42  # Value to load into A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)  # LDA absolute takes exactly 4 cycles

    # then:
    assert cpu.A == 0x42, f"Expected A=0x42, got A=0x{cpu.A:02X}"
    assert cpu.PC == 0x0803, f"Expected PC=0x0803 after LDA absolute, got PC=0x{cpu.PC:04X}"


def test_sequential_three_byte_instructions(cpu: CPU) -> None:
    """Test multiple sequential 3-byte instructions advance PC correctly.

    This is the critical test that exposes the PC misalignment bug.
    If fetch_word() only increments PC by 1, the second instruction will
    start at the wrong address and execute garbage.
    """
    # given:
    cpu.PC = 0x0800

    # First instruction: LDA $1234 (absolute) at $0800
    cpu.ram[0x0800] = 0xAD  # LDA absolute
    cpu.ram[0x0801] = 0x34  # Low byte
    cpu.ram[0x0802] = 0x12  # High byte
    cpu.ram[0x1234] = 0x11  # Value at $1234

    # Second instruction: LDA $5678 (absolute) at $0803
    cpu.ram[0x0803] = 0xAD  # LDA absolute
    cpu.ram[0x0804] = 0x78  # Low byte
    cpu.ram[0x0805] = 0x56  # High byte
    cpu.ram[0x5678] = 0x22  # Value at $5678

    # Third instruction: LDA $ABCD (absolute) at $0806
    cpu.ram[0x0806] = 0xAD  # LDA absolute
    cpu.ram[0x0807] = 0xCD  # Low byte
    cpu.ram[0x0808] = 0xAB  # High byte
    cpu.ram[0xABCD] = 0x33  # Value at $ABCD

    # when: Execute first instruction
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then: PC should be at $0803 (start of second instruction)
    assert cpu.PC == 0x0803, (
        f"After first LDA: Expected PC=0x0803, got PC=0x{cpu.PC:04X}. "
        f"fetch_word() likely only incremented PC by 1 instead of 2!"
    )
    assert cpu.A == 0x11, f"After first LDA: Expected A=0x11, got A=0x{cpu.A:02X}"

    # when: Execute second instruction
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then: PC should be at $0806 (start of third instruction)
    assert cpu.PC == 0x0806, (
        f"After second LDA: Expected PC=0x0806, got PC=0x{cpu.PC:04X}"
    )
    assert cpu.A == 0x22, f"After second LDA: Expected A=0x22, got A=0x{cpu.A:02X}"

    # when: Execute third instruction
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then: PC should be at $0809 (byte after third instruction)
    assert cpu.PC == 0x0809, (
        f"After third LDA: Expected PC=0x0809, got PC=0x{cpu.PC:04X}"
    )
    assert cpu.A == 0x33, f"After third LDA: Expected A=0x33, got A=0x{cpu.A:02X}"


def test_jsr_advances_pc_correctly(cpu: CPU) -> None:
    """Test that JSR (3-byte instruction) advances PC correctly before pushing to stack.

    JSR is particularly important because it pushes PC-1 to the stack.
    If PC isn't advanced correctly by fetch_word(), the return address will be wrong.
    """
    # given:
    cpu.PC = 0x0800
    initial_sp = cpu.S

    # JSR $1234 at $0800
    cpu.ram[0x0800] = 0x20  # JSR opcode
    cpu.ram[0x0801] = 0x34  # Low byte of target
    cpu.ram[0x0802] = 0x12  # High byte of target

    # RTS at $1234 (subroutine)
    cpu.ram[0x1234] = 0x60  # RTS opcode

    # when: Execute JSR
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=6)  # JSR takes 6 cycles

    # then: PC should be at subroutine address
    assert cpu.PC == 0x1234, f"Expected PC=0x1234 after JSR, got PC=0x{cpu.PC:04X}"

    # Stack should contain return address (PC after JSR - 1, which is $0802)
    # JSR pushes PC-1 (the address of the last byte of the JSR instruction)
    # Stack grows downward: high byte at S, low byte at S-1, then S decremented by 2
    return_addr_high = cpu.ram[initial_sp]
    return_addr_low = cpu.ram[initial_sp - 1]
    return_addr = (return_addr_high << 8) | return_addr_low

    assert return_addr == 0x0802, (
        f"Expected return address 0x0802 on stack, got 0x{return_addr:04X}. "
        f"This means PC wasn't advanced correctly before JSR pushed it."
    )

    # when: Execute RTS
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=6)  # RTS takes 6 cycles

    # then: PC should return to $0803 (instruction after JSR)
    assert cpu.PC == 0x0803, f"Expected PC=0x0803 after RTS, got PC=0x{cpu.PC:04X}"


def test_lda_absolute_y_advances_pc_by_3(cpu: CPU) -> None:
    """Test LDA absolute,Y (the exact instruction that triggered the C64 bug).

    This is the instruction that crashed the C64 KERNAL boot:
    $FD20: B9 14 03  LDA $0314,Y
    """
    # given:
    cpu.PC = 0xFD20
    cpu.Y = 0x05

    # LDA $0314,Y (absolute,Y) - opcode B9
    cpu.ram[0xFD20] = 0xB9  # LDA absolute,Y opcode
    cpu.ram[0xFD21] = 0x14  # Low byte of address
    cpu.ram[0xFD22] = 0x03  # High byte of address
    cpu.ram[0x0319] = 0xAA  # Value at $0314 + $05 = $0319

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)  # Base 4 cycles (no page crossing: $0314+$05 = $0319, same page)

    # then:
    assert cpu.A == 0xAA, f"Expected A=0xAA, got A=0x{cpu.A:02X}"
    assert cpu.PC == 0xFD23, (
        f"Expected PC=0xFD23 after LDA absolute,Y, got PC=0x{cpu.PC:04X}. "
        f"This is the EXACT bug that caused C64 KERNAL to crash!"
    )


def test_all_absolute_addressing_modes_advance_pc_correctly(cpu: CPU) -> None:
    """Test that all absolute addressing mode variants advance PC by 3.

    Tests: absolute, absolute,X, and absolute,Y
    """
    test_cases = [
        # (opcode, addressing_mode, x_value, y_value, description)
        (0xAD, "absolute", 0x00, 0x00, "LDA absolute"),
        (0xBD, "absolute,X", 0x05, 0x00, "LDA absolute,X"),
        (0xB9, "absolute,Y", 0x00, 0x03, "LDA absolute,Y"),
    ]

    for opcode, mode, x_val, y_val, description in test_cases:
        # given: Reset CPU for each test
        cpu.reset()
        cpu.PC = 0x1000
        cpu.X = x_val
        cpu.Y = y_val

        # Set up instruction
        cpu.ram[0x1000] = opcode
        cpu.ram[0x1001] = 0x00  # Low byte of $2000
        cpu.ram[0x1002] = 0x20  # High byte of $2000
        cpu.ram[0x2000 + x_val + y_val] = 0xFF  # Value to load

        # when:
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=4)  # LDA absolute/absolute,X/absolute,Y takes 4 cycles (no page crossing)

        # then:
        assert cpu.PC == 0x1003, (
            f"{description}: Expected PC=0x1003, got PC=0x{cpu.PC:04X}"
        )
        assert cpu.A == 0xFF, (
            f"{description}: Expected A=0xFF, got A=0x{cpu.A:02X}"
        )
