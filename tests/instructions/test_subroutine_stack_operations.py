#!/usr/bin/env python3
"""Comprehensive tests for JSR, RTS, and RTI stack operations.

These tests verify behavior documented at:
https://www.masswerk.at/6502/6502_instruction_set.html

Key behaviors verified:
- JSR pushes PC+2 (last byte of JSR instruction) to stack, high byte first
- RTS pops low byte first, then high byte, adds 1 to get return address
- RTI pops status first, then PC (low, high), no +1 added
- Stack operations wrap within page 1 ($0100-$01FF)

References:
- https://www.masswerk.at/6502/6502_instruction_set.html#JSR
- https://www.masswerk.at/6502/6502_instruction_set.html#RTS
- https://www.masswerk.at/6502/6502_instruction_set.html#RTI
"""
import contextlib

from mos6502 import CPU, errors, instructions
from mos6502.flags import FlagsRegister


class TestJSRStackBehavior:
    """Tests for JSR instruction stack behavior per masswerk.at documentation.

    JSR (Jump to Subroutine):
    - Pushes (PC+2) to stack, which is the address of the last byte of the JSR instruction
    - After fetching the 2-byte operand, PC points past JSR, so we push PC-1
    - High byte pushed first, then low byte (stack grows down)
    - S decremented by 2 after pushing both bytes
    """

    def test_jsr_pushes_correct_return_address(self, cpu: CPU) -> None:
        """JSR should push PC+2 (address of last byte of JSR instruction).

        From masswerk.at: "push (PC+2)"
        After JSR at $0400, the return address on stack should be $0402
        (pointing to the last byte of the JSR instruction).
        """
        cpu.reset()
        cpu.PC = 0x0400
        initial_s = cpu.S & 0xFF  # Get 8-bit stack pointer value

        # JSR $1234 at address $0400
        cpu.ram[0x0400] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0x0401] = 0x34  # Low byte of target
        cpu.ram[0x0402] = 0x12  # High byte of target

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # Verify PC jumped to target
        assert cpu.PC == 0x1234

        # Verify stack pointer decremented by 2
        assert (cpu.S & 0xFF) == (initial_s - 2) & 0xFF

        # Verify return address pushed is $0402 (last byte of JSR instruction)
        # Stack layout after JSR:
        # $01FF (initial_s): high byte of return address ($04)
        # $01FE (initial_s-1): low byte of return address ($02)
        stack_base = 0x0100
        high_byte_addr = stack_base | initial_s
        low_byte_addr = stack_base | ((initial_s - 1) & 0xFF)

        assert cpu.ram[high_byte_addr] == 0x04  # High byte of $0402
        assert cpu.ram[low_byte_addr] == 0x02   # Low byte of $0402

    def test_jsr_pushes_high_byte_first(self, cpu: CPU) -> None:
        """JSR pushes high byte of return address before low byte.

        When S=$FF before JSR:
        - High byte goes to $01FF
        - Low byte goes to $01FE
        - S becomes $FD after both pushes
        """
        cpu.reset()
        cpu.PC = 0x0400
        cpu.S = 0x01FF  # Start with full stack

        cpu.ram[0x0400] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0x0401] = 0x00  # Target low
        cpu.ram[0x0402] = 0x80  # Target high ($8000)

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # Return address should be $0402
        # High byte ($04) at $01FF, low byte ($02) at $01FE
        assert cpu.ram[0x01FF] == 0x04  # High byte first
        assert cpu.ram[0x01FE] == 0x02  # Low byte second
        assert (cpu.S & 0xFF) == 0xFD   # S decremented by 2

    def test_jsr_from_different_addresses(self, cpu: CPU) -> None:
        """Test JSR from various addresses to verify return address calculation."""
        test_cases = [
            (0x0200, 0x1000, 0x0202),  # JSR at $0200, return addr $0202
            (0x1000, 0x2000, 0x1002),  # JSR at $1000, return addr $1002
            (0xFFFD, 0x8000, 0xFFFF),  # JSR near top of memory
        ]

        for jsr_addr, target_addr, expected_return in test_cases:
            cpu.reset()
            cpu.PC = jsr_addr
            cpu.S = 0x01FF

            cpu.ram[jsr_addr] = instructions.JSR_ABSOLUTE_0x20
            cpu.ram[(jsr_addr + 1) & 0xFFFF] = target_addr & 0xFF
            cpu.ram[(jsr_addr + 2) & 0xFFFF] = (target_addr >> 8) & 0xFF

            with contextlib.suppress(errors.CPUCycleExhaustionError):
                cpu.execute(cycles=6)

            # Verify return address on stack
            pushed_high = cpu.ram[0x01FF]
            pushed_low = cpu.ram[0x01FE]
            pushed_addr = (pushed_high << 8) | pushed_low

            assert pushed_addr == expected_return, \
                f"JSR at ${jsr_addr:04X}: expected return ${expected_return:04X}, got ${pushed_addr:04X}"


class TestRTSStackBehavior:
    """Tests for RTS instruction stack behavior per masswerk.at documentation.

    RTS (Return from Subroutine):
    - Pops low byte first, then high byte
    - Adds 1 to the popped address to get actual return address
    - S incremented by 2 after popping both bytes
    """

    def test_rts_pops_and_adds_one(self, cpu: CPU) -> None:
        """RTS should pop address from stack and add 1.

        From masswerk.at: "pull PC, PC+1 -> PC"
        If stack contains $0402, RTS should return to $0403.
        """
        cpu.reset()
        cpu.PC = 0x8000  # Current location (subroutine)

        # Set up stack with return address $0402
        # After RTS, PC should be $0403
        cpu.ram[0x01FF] = 0x04  # High byte
        cpu.ram[0x01FE] = 0x02  # Low byte
        cpu.S = 0x01FD  # Stack pointer below the pushed address

        cpu.ram[0x8000] = instructions.RTS_IMPLIED_0x60

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # RTS adds 1 to popped address: $0402 + 1 = $0403
        assert cpu.PC == 0x0403
        # Stack pointer should be back to $01FF
        assert (cpu.S & 0xFF) == 0xFF

    def test_rts_pops_low_byte_first(self, cpu: CPU) -> None:
        """RTS pops low byte first, then high byte.

        Stack layout before RTS (S=$FD):
        - $01FE: low byte (read second after incrementing S)
        - $01FF: high byte (read last after incrementing S again)
        """
        cpu.reset()
        cpu.PC = 0x5000

        # Push $ABCD-1 = $ABCC so RTS returns to $ABCD
        cpu.ram[0x01FF] = 0xAB  # High byte
        cpu.ram[0x01FE] = 0xCC  # Low byte ($ABCC)
        cpu.S = 0x01FD

        cpu.ram[0x5000] = instructions.RTS_IMPLIED_0x60

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # $ABCC + 1 = $ABCD
        assert cpu.PC == 0xABCD

    def test_jsr_rts_round_trip(self, cpu: CPU) -> None:
        """JSR followed by RTS should return to instruction after JSR."""
        cpu.reset()
        cpu.PC = 0x0400

        # JSR $8000
        cpu.ram[0x0400] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0x0401] = 0x00  # Low byte
        cpu.ram[0x0402] = 0x80  # High byte

        # RTS at $8000
        cpu.ram[0x8000] = instructions.RTS_IMPLIED_0x60

        # Execute JSR
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        assert cpu.PC == 0x8000

        # Execute RTS
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # Should return to instruction after JSR ($0403)
        assert cpu.PC == 0x0403

    def test_multiple_jsr_rts(self, cpu: CPU) -> None:
        """Multiple nested JSR/RTS calls should work correctly."""
        cpu.reset()
        cpu.PC = 0x0400

        # Main: JSR $1000
        cpu.ram[0x0400] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0x0401] = 0x00
        cpu.ram[0x0402] = 0x10

        # Sub1 at $1000: JSR $2000
        cpu.ram[0x1000] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0x1001] = 0x00
        cpu.ram[0x1002] = 0x20

        # Sub2 at $2000: RTS
        cpu.ram[0x2000] = instructions.RTS_IMPLIED_0x60

        # Sub1 continues at $1003: RTS
        cpu.ram[0x1003] = instructions.RTS_IMPLIED_0x60

        # Execute: JSR $1000
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)
        assert cpu.PC == 0x1000

        # Execute: JSR $2000
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)
        assert cpu.PC == 0x2000

        # Execute: RTS (return to $1003)
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)
        assert cpu.PC == 0x1003

        # Execute: RTS (return to $0403)
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)
        assert cpu.PC == 0x0403


class TestRTIStackBehavior:
    """Tests for RTI instruction stack behavior per masswerk.at documentation.

    RTI (Return from Interrupt):
    - Pops status register first
    - Then pops PC (low byte, then high byte)
    - Does NOT add 1 to PC (unlike RTS)
    - S incremented by 3 after popping all bytes
    """

    def test_rti_does_not_add_one(self, cpu: CPU) -> None:
        """RTI should NOT add 1 to the return address (unlike RTS).

        From masswerk.at: "pull SR, pull PC"
        If stack contains PC=$1234, RTI returns to exactly $1234.
        """
        cpu.reset()
        cpu.PC = 0x8000

        # Stack layout (S=$FC):
        # $01FD: status register
        # $01FE: PC low byte
        # $01FF: PC high byte
        cpu.ram[0x01FF] = 0x12  # PC high
        cpu.ram[0x01FE] = 0x34  # PC low
        cpu.ram[0x01FD] = 0x00  # Status (all flags clear)
        cpu.S = 0x01FC

        cpu.ram[0x8000] = instructions.RTI_IMPLIED_0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # RTI returns to exact address, no +1
        assert cpu.PC == 0x1234
        assert (cpu.S & 0xFF) == 0xFF

    def test_rti_pops_status_first(self, cpu: CPU) -> None:
        """RTI pops status register before PC."""
        cpu.reset()
        cpu.PC = 0x8000

        # Set up stack
        cpu.ram[0x01FF] = 0x00  # PC high
        cpu.ram[0x01FE] = 0x00  # PC low
        cpu.ram[0x01FD] = 0xFF  # Status (all flags set)
        cpu.S = 0x01FC

        # Clear all flags before RTI
        cpu._flags = FlagsRegister(0x00)

        cpu.ram[0x8000] = instructions.RTI_IMPLIED_0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # Status should be restored
        assert cpu.flags.value == 0xFF

    def test_rti_vs_rts_address_difference(self, cpu: CPU) -> None:
        """RTI and RTS handle the return address differently.

        Given same address on stack ($1234):
        - RTS returns to $1235 (adds 1)
        - RTI returns to $1234 (exact address)
        """
        # Test RTS
        cpu.reset()
        cpu.PC = 0x8000
        cpu.ram[0x01FF] = 0x12
        cpu.ram[0x01FE] = 0x34
        cpu.S = 0x01FD
        cpu.ram[0x8000] = instructions.RTS_IMPLIED_0x60

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        rts_result = cpu.PC

        # Test RTI
        cpu.reset()
        cpu.PC = 0x8000
        cpu.ram[0x01FF] = 0x12  # PC high
        cpu.ram[0x01FE] = 0x34  # PC low
        cpu.ram[0x01FD] = 0x00  # Status
        cpu.S = 0x01FC
        cpu.ram[0x8000] = instructions.RTI_IMPLIED_0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        rti_result = cpu.PC

        # RTS adds 1, RTI doesn't
        assert rts_result == 0x1235  # $1234 + 1
        assert rti_result == 0x1234  # Exact address


class TestStackBoundaryWrapping:
    """Tests for stack operations wrapping within page 1 ($0100-$01FF).

    The 6502 stack is 256 bytes at $0100-$01FF. Stack operations must wrap
    within this page, never crossing into page 0 or page 2.
    """

    def test_jsr_wraps_at_stack_bottom(self, cpu: CPU) -> None:
        """JSR with S near bottom of stack should wrap correctly.

        If S=$01 before JSR, pushing 2 bytes should wrap:
        - First push (high byte) to $0101
        - Second push (low byte) to $0100
        - S becomes $FF (wraps from $00-1 to $FF within page)
        """
        cpu.reset()
        cpu.PC = 0x0400
        cpu.S = 0x0101  # S points to $0101 (only 2 bytes left)

        cpu.ram[0x0400] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0x0401] = 0x00
        cpu.ram[0x0402] = 0x80

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # Verify wrapping occurred
        assert cpu.ram[0x0101] == 0x04  # High byte at $0101
        assert cpu.ram[0x0100] == 0x02  # Low byte at $0100
        assert (cpu.S & 0xFF) == 0xFF   # S wrapped to $FF

    def test_jsr_wraps_at_very_bottom(self, cpu: CPU) -> None:
        """JSR with S=$00 should wrap both pushes within page 1.

        If S=$00 before JSR:
        - First push (high byte) to $0100
        - S decrements to $FF (wraps)
        - Second push (low byte) to $01FF
        - S decrements to $FE
        """
        cpu.reset()
        cpu.PC = 0x0400
        cpu.S = 0x0100  # S points to $0100 (bottom of stack)

        cpu.ram[0x0400] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0x0401] = 0x00
        cpu.ram[0x0402] = 0x80

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # After first push: high byte to $0100, S wraps to $FF
        # After second push: low byte to $01FF, S becomes $FE
        assert cpu.ram[0x0100] == 0x04  # High byte
        assert cpu.ram[0x01FF] == 0x02  # Low byte (wrapped)
        assert (cpu.S & 0xFF) == 0xFE

    def test_rts_wraps_at_stack_top(self, cpu: CPU) -> None:
        """RTS with S near top of stack should wrap correctly.

        If S=$FE before RTS:
        - S increments to $FF, read low byte from $01FF
        - S increments and wraps to $00, read high byte from $0100
        """
        cpu.reset()
        cpu.PC = 0x8000
        cpu.S = 0x01FE  # Near top

        # Set up return address spanning the wrap
        cpu.ram[0x01FF] = 0x02  # Low byte at $01FF
        cpu.ram[0x0100] = 0x04  # High byte at $0100 (wrapped)

        cpu.ram[0x8000] = instructions.RTS_IMPLIED_0x60

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # Return address = $0402 + 1 = $0403
        assert cpu.PC == 0x0403
        assert (cpu.S & 0xFF) == 0x00  # S wrapped to $00

    def test_rts_wraps_at_very_top(self, cpu: CPU) -> None:
        """RTS with S=$FF should wrap correctly.

        If S=$FF before RTS:
        - S wraps to $00, read low byte from $0100
        - S increments to $01, read high byte from $0101
        """
        cpu.reset()
        cpu.PC = 0x8000
        cpu.S = 0x01FF

        cpu.ram[0x0100] = 0x02  # Low byte at $0100
        cpu.ram[0x0101] = 0x04  # High byte at $0101

        cpu.ram[0x8000] = instructions.RTS_IMPLIED_0x60

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        assert cpu.PC == 0x0403
        assert (cpu.S & 0xFF) == 0x01

    def test_rti_wraps_at_stack_top(self, cpu: CPU) -> None:
        """RTI with S near top should wrap correctly (3 pops: status, low PC, high PC)."""
        cpu.reset()
        cpu.PC = 0x8000
        cpu.S = 0x01FD  # Need to pop 3 bytes

        # Stack layout spanning wrap:
        cpu.ram[0x01FE] = 0x00  # Status at $01FE
        cpu.ram[0x01FF] = 0x34  # PC low at $01FF
        cpu.ram[0x0100] = 0x12  # PC high at $0100 (wrapped)

        cpu.ram[0x8000] = instructions.RTI_IMPLIED_0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        assert cpu.PC == 0x1234
        assert (cpu.S & 0xFF) == 0x00

    def test_rti_wraps_with_all_bytes_wrapped(self, cpu: CPU) -> None:
        """RTI where all 3 bytes need wrap handling."""
        cpu.reset()
        cpu.PC = 0x8000
        cpu.S = 0x01FE  # Very near top

        # All pops will wrap:
        cpu.ram[0x01FF] = 0xAA  # Status at $01FF
        cpu.ram[0x0100] = 0xCD  # PC low at $0100
        cpu.ram[0x0101] = 0xAB  # PC high at $0101

        cpu.ram[0x8000] = instructions.RTI_IMPLIED_0x40

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        assert cpu.PC == 0xABCD
        assert cpu.flags.value == 0xAA
        assert (cpu.S & 0xFF) == 0x01

    def test_jsr_rts_round_trip_at_boundary(self, cpu: CPU) -> None:
        """JSR/RTS round trip should work correctly at stack boundary."""
        cpu.reset()
        cpu.PC = 0x0400
        cpu.S = 0x0101  # Near bottom - will wrap on JSR

        # JSR $8000
        cpu.ram[0x0400] = instructions.JSR_ABSOLUTE_0x20
        cpu.ram[0x0401] = 0x00
        cpu.ram[0x0402] = 0x80

        # RTS at $8000
        cpu.ram[0x8000] = instructions.RTS_IMPLIED_0x60

        # Execute JSR
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        assert cpu.PC == 0x8000

        # Execute RTS - should correctly unwrap and return
        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=6)

        # Should return to $0403 even with wrapping
        assert cpu.PC == 0x0403


class TestIRQStackBehavior:
    """Tests for hardware IRQ stack behavior.

    Hardware IRQ:
    - Pushes PC (high byte first, then low byte)
    - Pushes status register with B flag CLEAR
    - Sets I flag
    - Loads PC from $FFFE/$FFFF

    Note: IRQ is checked AFTER each instruction completes, so PC will
    point to the NEXT instruction when IRQ fires.
    """

    def test_irq_pushes_correct_pc(self, cpu: CPU) -> None:
        """IRQ should push PC at time of interrupt (after instruction completes)."""
        cpu.reset()
        cpu.PC = 0x1234
        cpu.I = 0  # Enable interrupts
        cpu.irq_pending = True
        initial_s = cpu.S & 0xFF

        # Set IRQ vector
        cpu.ram[0xFFFE] = 0x00
        cpu.ram[0xFFFF] = 0x80  # IRQ handler at $8000

        # Place a NOP at current PC so we can trigger IRQ
        # After NOP executes, PC will be $1235, then IRQ fires
        cpu.ram[0x1234] = 0xEA  # NOP

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=10)

        # Verify PC was pushed correctly
        # IRQ fires AFTER NOP completes, so PC is $1235 (not $1234)
        stack_base = 0x0100
        high_byte_addr = stack_base | initial_s
        low_byte_addr = stack_base | ((initial_s - 1) & 0xFF)

        assert cpu.ram[high_byte_addr] == 0x12  # High byte of $1235
        assert cpu.ram[low_byte_addr] == 0x35   # Low byte of $1235

    def test_irq_wraps_at_stack_boundary(self, cpu: CPU) -> None:
        """IRQ with S near boundary should wrap correctly."""
        cpu.reset()
        cpu.PC = 0x1234
        cpu.S = 0x0102  # Only 3 bytes before wrap
        cpu.I = 0
        cpu.irq_pending = True

        # Set IRQ vector
        cpu.ram[0xFFFE] = 0x00
        cpu.ram[0xFFFF] = 0x80

        # NOP at $1234 - after it executes, PC is $1235
        cpu.ram[0x1234] = 0xEA  # NOP

        with contextlib.suppress(errors.CPUCycleExhaustionError):
            cpu.execute(cycles=10)

        # IRQ pushes 3 bytes: PC high, PC low, status
        # PC is $1235 when IRQ fires (after NOP)
        # Starting at $0102:
        # - PC high ($12) at $0102
        # - PC low ($35) at $0101
        # - Status at $0100
        # S wraps to $FF
        assert cpu.ram[0x0102] == 0x12  # PC high
        assert cpu.ram[0x0101] == 0x35  # PC low
        # Status is at $0100
        assert (cpu.S & 0xFF) == 0xFF   # S wrapped


class TestStackPointerRegister:
    """Tests for stack pointer register behavior."""

    def test_s_register_always_in_page_1(self, cpu: CPU) -> None:
        """S register should always have high byte 0x01."""
        cpu.reset()

        # After reset, S should be in page 1
        assert (cpu.S & 0xFF00) == 0x0100

        # Set various values
        for val in [0x00, 0x7F, 0xFF, 0x50]:
            cpu.S = val
            assert (cpu.S & 0xFF00) == 0x0100
            assert (cpu.S & 0xFF) == val

    def test_s_register_wraps_on_underflow(self, cpu: CPU) -> None:
        """S should wrap within page 1 when decremented past 0."""
        cpu.reset()
        cpu.S = 0x0100  # S = $00 within page 1

        cpu.S -= 1

        # Should wrap to $FF, still in page 1
        assert cpu.S == 0x01FF
        assert (cpu.S & 0xFF) == 0xFF

    def test_s_register_wraps_on_overflow(self, cpu: CPU) -> None:
        """S should wrap within page 1 when incremented past $FF."""
        cpu.reset()
        cpu.S = 0x01FF  # S = $FF within page 1

        cpu.S += 1

        # Should wrap to $00, still in page 1
        assert cpu.S == 0x0100
        assert (cpu.S & 0xFF) == 0x00
