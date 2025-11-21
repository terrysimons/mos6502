"""Tests for BRK return address handling.

This test verifies that BRK pushes PC+2 (skipping the signature byte)
and that RTI returns to the correct address.
"""

import contextlib
import pytest
from mos6502 import CPU, errors


@pytest.fixture(params=["6502", "6502A", "6502C", "65C02"])
def cpu(request):
    """Create a CPU with the specified variant."""
    cpu_variant = request.param
    cpu_instance = CPU(cpu_variant=cpu_variant)
    cpu_instance.reset()
    return cpu_instance


def test_brk_pushes_pc_plus_2(cpu):
    """Test that BRK pushes PC+2 to the stack.

    BRK is a 2-byte instruction: opcode (0x00) + signature byte.
    After executing BRK at address $1000, the return address pushed
    should be $1002 (original PC + 2), so RTI returns to $1002.
    """
    # Set up IRQ vector to point to a simple RTI handler
    cpu.ram[0xFFFE] = 0x00  # IRQ vector low byte
    cpu.ram[0xFFFF] = 0x20  # IRQ vector high byte ($2000)

    # Put RTI at IRQ handler
    cpu.ram[0x2000] = 0x40  # RTI opcode

    # Put BRK at $1000 followed by signature byte
    cpu.ram[0x1000] = 0x00  # BRK
    cpu.ram[0x1001] = 0xAA  # Signature byte (should be skipped)

    # Put NOP at $1002 (where we should return to)
    cpu.ram[0x1002] = 0xEA  # NOP

    # Start execution at $1000
    cpu.PC = 0x1000

    # Execute BRK (7 cycles) + RTI (6 cycles) = 13 cycles exactly
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=13)

    # After BRK + RTI, PC should be at $1002 (skipping signature byte at $1001)
    assert cpu.PC == 0x1002, f"Expected PC=0x1002 after BRK+RTI, got 0x{cpu.PC:04X}"


def test_brk_return_address_on_stack(cpu):
    """Test that BRK pushes the correct return address onto the stack."""
    # Set up IRQ vector
    cpu.ram[0xFFFE] = 0x00
    cpu.ram[0xFFFF] = 0x20

    # Put BRK at $5000
    cpu.ram[0x5000] = 0x00  # BRK
    cpu.ram[0x5001] = 0xFF  # Signature byte

    # Put a halt at IRQ handler so we can inspect the stack
    cpu.ram[0x2000] = 0xEA  # NOP (we'll stop after BRK)

    cpu.PC = 0x5000
    initial_sp = cpu.S  # Full 16-bit value (0x01FD)

    # Execute BRK (7 cycles)
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=7)

    # Stack should have PC+2 = $5002 pushed
    # 6502 pushes high byte first, then low byte, then status
    # Stack grows downward, so S decreases by 3 (PC high, PC low, status)
    assert cpu.S == initial_sp - 3, f"Expected S=0x{initial_sp - 3:04X}, got 0x{cpu.S:04X}"

    # Read return address from stack
    # BRK writes to current S, then decrements
    # Starting with initial_sp (0x01FD):
    # - PC_high written to 0x01FD (initial_sp), then S becomes 0x01FC
    # - PC_low written to 0x01FC (initial_sp - 1), then S becomes 0x01FB
    # - Status written to 0x01FB (initial_sp - 2), then S becomes 0x01FA
    pc_high = cpu.ram[initial_sp]      # PC high at initial SP
    pc_low = cpu.ram[initial_sp - 1]   # PC low at initial SP - 1
    pushed_pc = (pc_high << 8) | pc_low

    assert pushed_pc == 0x5002, f"Expected return address 0x5002 on stack, got 0x{pushed_pc:04X}"


def test_multiple_brk_rti_cycles(cpu):
    """Test multiple BRK/RTI cycles to ensure address handling is consistent."""
    # Set up IRQ vector to RTI handler
    cpu.ram[0xFFFE] = 0x00
    cpu.ram[0xFFFF] = 0x30
    cpu.ram[0x3000] = 0x40  # RTI

    # Create a sequence: BRK, NOP, BRK, NOP at $4000+
    cpu.ram[0x4000] = 0x00  # BRK
    cpu.ram[0x4001] = 0x11  # Signature
    cpu.ram[0x4002] = 0xEA  # NOP
    cpu.ram[0x4003] = 0x00  # BRK
    cpu.ram[0x4004] = 0x22  # Signature
    cpu.ram[0x4005] = 0xEA  # NOP (target)

    cpu.PC = 0x4000

    # Execute: BRK(7) + RTI(6) + NOP(2) + BRK(7) + RTI(6) = 28 cycles
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=30)

    # Should be at $4005 (after second BRK+RTI+NOP)
    assert cpu.PC == 0x4005, f"Expected PC=0x4005, got 0x{cpu.PC:04X}"
