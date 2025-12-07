"""Tests for CPU execute() continuation across multiple calls.

These tests verify that the CPU state is correctly preserved when execute()
is called multiple times with CPUCycleExhaustionError between calls.
"""

import pytest
from mos6502 import errors
from mos6502.core import MOS6502CPU, INFINITE_CYCLES
from tests.c64.conftest import C64_ROMS_DIR, requires_c64_roms


class TestCPUExecuteContinuation:
    """Test that multiple execute() calls produce same results as single call."""

    @pytest.fixture
    def cpu_with_nop_loop(self):
        """Create a CPU with a simple NOP loop for testing."""
        cpu = MOS6502CPU()
        # Fill memory with NOPs ($EA)
        for i in range(0x10000):
            cpu.ram[i] = 0xEA
        # Put JMP $0000 at end to loop
        cpu.ram[0xFFFD] = 0x4C  # JMP
        cpu.ram[0xFFFE] = 0x00
        cpu.ram[0xFFFF] = 0x00
        # Set up reset vector to $0000
        cpu.ram[0xFFFC] = 0x00
        cpu.ram[0xFFFD] = 0x00
        cpu.reset()
        return cpu

    @pytest.fixture
    def cpu_with_counter(self):
        """Create a CPU that increments a counter in a loop."""
        cpu = MOS6502CPU()
        # Program: increment $10, loop forever
        # $0000: INC $10     ; E6 10
        # $0002: JMP $0000   ; 4C 00 00
        program = [
            0xE6, 0x10,        # INC $10
            0x4C, 0x00, 0x00,  # JMP $0000
        ]
        for i, byte in enumerate(program):
            cpu.ram[i] = byte
        # Set reset vector to $0000
        cpu.ram[0xFFFC] = 0x00
        cpu.ram[0xFFFD] = 0x00
        cpu.reset()
        return cpu

    def test_single_execute_vs_multiple_nop_loop(self, cpu_with_nop_loop):
        """Single execute should match multiple executes for NOP loop."""
        # Run 1000 cycles in one go
        cpu1 = cpu_with_nop_loop
        try:
            cpu1.execute(cycles=1000)
        except errors.CPUCycleExhaustionError:
            pass

        # Run 10 x 100 cycles
        cpu2 = MOS6502CPU()
        for i in range(0x10000):
            cpu2.ram[i] = 0xEA
        cpu2.ram[0xFFFC] = 0x00
        cpu2.ram[0xFFFD] = 0x00
        cpu2.reset()

        for _ in range(10):
            try:
                cpu2.execute(cycles=100)
            except errors.CPUCycleExhaustionError:
                pass

        # Both should have same state
        assert cpu1.PC == cpu2.PC, f"PC mismatch: {cpu1.PC} vs {cpu2.PC}"
        assert cpu1.A == cpu2.A, f"A mismatch: {cpu1.A} vs {cpu2.A}"
        assert cpu1.X == cpu2.X, f"X mismatch"
        assert cpu1.Y == cpu2.Y, f"Y mismatch"
        assert cpu1.S == cpu2.S, f"S mismatch"
        assert cpu1.cycles_executed == cpu2.cycles_executed, \
            f"cycles_executed mismatch: {cpu1.cycles_executed} vs {cpu2.cycles_executed}"

    def test_single_execute_vs_multiple_counter(self, cpu_with_counter):
        """Single execute should match multiple executes for counter program.

        Note: With atomic instructions, cycle-based execution may have slight
        variations when split into chunks. Use instruction-based execution for
        exact matching.
        """
        # Run 125 instructions (INC $10 + JMP = 1 iteration) in one go
        total_instructions = 250  # 125 iterations * 2 instructions each
        cpu1 = cpu_with_counter
        try:
            cpu1.execute(max_instructions=total_instructions)
        except errors.CPUCycleExhaustionError:
            pass
        counter1 = int(cpu1.ram[0x10])

        # Run in 10 chunks of 25 instructions each
        cpu2 = MOS6502CPU()
        program = [0xE6, 0x10, 0x4C, 0x00, 0x00]
        for i, byte in enumerate(program):
            cpu2.ram[i] = byte
        cpu2.ram[0xFFFC] = 0x00
        cpu2.ram[0xFFFD] = 0x00
        cpu2.reset()

        for _ in range(10):
            try:
                cpu2.execute(max_instructions=25)
            except errors.CPUCycleExhaustionError:
                pass
        counter2 = int(cpu2.ram[0x10])

        assert counter1 == counter2, f"Counter mismatch: {counter1} vs {counter2}"
        assert cpu1.PC == cpu2.PC, f"PC mismatch: {cpu1.PC} vs {cpu2.PC}"
        assert cpu1.cycles_executed == cpu2.cycles_executed

    def test_varying_chunk_sizes(self):
        """Different chunk sizes should produce same final state."""
        # Simple program that just loops
        def make_cpu():
            cpu = MOS6502CPU()
            program = [0xE6, 0x10, 0x4C, 0x00, 0x00]
            for i, byte in enumerate(program):
                cpu.ram[i] = byte
            cpu.ram[0xFFFC] = 0x00
            cpu.ram[0xFFFD] = 0x00
            cpu.reset()
            return cpu

        target_cycles = 10000

        # Run in one go
        cpu_single = make_cpu()
        try:
            cpu_single.execute(cycles=target_cycles)
        except errors.CPUCycleExhaustionError:
            pass

        # Test various chunk sizes
        chunk_sizes = [100, 500, 1000, 2500, 3333]

        for chunk_size in chunk_sizes:
            cpu = make_cpu()
            cycles_run = 0
            while cycles_run < target_cycles:
                try:
                    cpu.execute(cycles=min(chunk_size, target_cycles - cycles_run))
                except errors.CPUCycleExhaustionError:
                    pass
                cycles_run = cpu.cycles_executed - 7  # minus reset cycles

            assert cpu.PC == cpu_single.PC, \
                f"PC mismatch with chunk={chunk_size}: {cpu.PC} vs {cpu_single.PC}"
            assert cpu.cycles_executed == cpu_single.cycles_executed, \
                f"cycles mismatch with chunk={chunk_size}"

    def test_execute_from_mid_instruction_boundary(self):
        """Test that execute() handles instruction boundaries correctly."""
        cpu = MOS6502CPU()
        # LDA #$42 (2 bytes, 2 cycles)
        # NOP (1 byte, 2 cycles)
        # NOP (1 byte, 2 cycles)
        # JMP $0000
        program = [
            0xA9, 0x42,        # LDA #$42
            0xEA,              # NOP
            0xEA,              # NOP
            0x4C, 0x00, 0x00,  # JMP $0000
        ]
        for i, byte in enumerate(program):
            cpu.ram[i] = byte
        cpu.ram[0xFFFC] = 0x00
        cpu.ram[0xFFFD] = 0x00
        cpu.reset()

        # Run 3 cycles - should complete LDA but maybe partial into NOP
        try:
            cpu.execute(cycles=3)
        except errors.CPUCycleExhaustionError:
            pass

        pc_after_3 = cpu.PC
        cycles_after_3 = cpu.cycles_executed

        # Run more cycles
        try:
            cpu.execute(cycles=10)
        except errors.CPUCycleExhaustionError:
            pass

        # Should not have crashed
        assert cpu.cycles_executed > cycles_after_3


class TestCPUExecuteContinuationWithC64:
    """Test execute() continuation with real C64 ROMs."""

    @requires_c64_roms
    def test_c64_single_vs_multiple_execute(self):
        """C64 should behave same with single vs multiple execute calls."""
        from systems.c64 import C64

        total_cycles = 50000
        chunk_size = 10000

        # Single execute
        c64_single = C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')
        c64_single.cpu.reset()
        c64_single.cpu.periodic_callback = None  # Disable for clean test
        try:
            c64_single.cpu.execute(cycles=total_cycles)
        except errors.CPUCycleExhaustionError:
            pass

        # Multiple executes
        c64_multi = C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')
        c64_multi.cpu.reset()
        c64_multi.cpu.periodic_callback = None

        for _ in range(total_cycles // chunk_size):
            try:
                c64_multi.cpu.execute(cycles=chunk_size)
            except errors.CPUCycleExhaustionError:
                pass

        # Compare states
        assert c64_single.cpu.PC == c64_multi.cpu.PC, \
            f"PC mismatch: ${c64_single.cpu.PC:04X} vs ${c64_multi.cpu.PC:04X}"
        assert c64_single.cpu.A == c64_multi.cpu.A, "A mismatch"
        assert c64_single.cpu.X == c64_multi.cpu.X, "X mismatch"
        assert c64_single.cpu.Y == c64_multi.cpu.Y, "Y mismatch"
        assert c64_single.cpu.S == c64_multi.cpu.S, "S mismatch"

    @requires_c64_roms
    def test_c64_frame_by_frame_execution(self):
        """C64 should work correctly when executed frame-by-frame.

        Note: With atomic instructions, cycle-based execution doesn't guarantee
        exact matching when split into frames. Instead, we verify that both
        executions reach similar cycle counts (within one instruction's worth
        of overshoot per frame).
        """
        from systems.c64 import C64

        # PAL frame is ~19656 cycles
        cycles_per_frame = 19656
        num_frames = 10
        total_cycles = cycles_per_frame * num_frames

        # Single execute
        c64_single = C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')
        c64_single.cpu.reset()
        c64_single.cpu.periodic_callback = None
        try:
            c64_single.cpu.execute(cycles=total_cycles)
        except errors.CPUCycleExhaustionError:
            pass

        # Frame-by-frame
        c64_frames = C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')
        c64_frames.cpu.reset()
        c64_frames.cpu.periodic_callback = None

        for frame in range(num_frames):
            try:
                c64_frames.cpu.execute(cycles=cycles_per_frame)
            except errors.CPUCycleExhaustionError:
                pass

        # With atomic instructions, cycles may differ by up to one instruction
        # per frame boundary (max ~7 cycles per boundary = 70 cycles for 10 frames)
        cycle_tolerance = num_frames * 7  # Max instruction cycles * num frames
        cycle_diff = abs(c64_single.cpu.cycles_executed - c64_frames.cpu.cycles_executed)
        assert cycle_diff <= cycle_tolerance, \
            f"Cycle difference {cycle_diff} exceeds tolerance {cycle_tolerance}"

        # Note: PC won't match exactly due to cycle-based stopping variations


class TestCPUCycleExhaustionBehavior:
    """Test the behavior of CPUCycleExhaustionError itself."""

    def test_cycles_remaining_at_exception(self):
        """Test that cycles_remaining is correctly reported at exception."""
        cpu = MOS6502CPU()
        # Fill with NOPs
        for i in range(0x10000):
            cpu.ram[i] = 0xEA
        cpu.ram[0xFFFC] = 0x00
        cpu.ram[0xFFFD] = 0x00
        cpu.reset()

        try:
            cpu.execute(cycles=10)
        except errors.CPUCycleExhaustionError:
            pass

        # cpu.cycles should be 0 or negative at exhaustion
        assert cpu.cycles <= 0

    def test_pc_at_next_instruction_after_exhaustion(self):
        """Test that PC points to next instruction after exhaustion."""
        cpu = MOS6502CPU()
        # LDA #$00 at $0000 (2 bytes, 2 cycles)
        # LDA #$01 at $0002 (2 bytes, 2 cycles)
        # LDA #$02 at $0004 (2 bytes, 2 cycles)
        cpu.ram[0x0000] = 0xA9
        cpu.ram[0x0001] = 0x00
        cpu.ram[0x0002] = 0xA9
        cpu.ram[0x0003] = 0x01
        cpu.ram[0x0004] = 0xA9
        cpu.ram[0x0005] = 0x02
        cpu.ram[0x0006] = 0x4C
        cpu.ram[0x0007] = 0x00
        cpu.ram[0x0008] = 0x00
        cpu.ram[0xFFFC] = 0x00
        cpu.ram[0xFFFD] = 0x00
        cpu.reset()

        # Run exactly 2 cycles (one LDA #$00)
        # Note: reset() takes 7 cycles, so we need more
        initial_cycles = cpu.cycles_executed  # Should be 7 after reset

        try:
            cpu.execute(cycles=2)
        except errors.CPUCycleExhaustionError:
            pass

        # PC should point to $0002 (next instruction)
        assert cpu.PC == 0x0002, f"PC should be $0002, got ${cpu.PC:04X}"
        assert cpu.A == 0x00, "A should be $00 after LDA #$00"

    def test_execute_resumes_correctly(self):
        """Test that execute() resumes from correct position."""
        cpu = MOS6502CPU()
        # LDA #$AA
        # STA $10
        # LDA #$BB
        # STA $11
        # JMP $0000
        program = [
            0xA9, 0xAA,        # LDA #$AA
            0x85, 0x10,        # STA $10
            0xA9, 0xBB,        # LDA #$BB
            0x85, 0x11,        # STA $11
            0x4C, 0x00, 0x00,  # JMP $0000
        ]
        for i, byte in enumerate(program):
            cpu.ram[i] = byte
        cpu.ram[0xFFFC] = 0x00
        cpu.ram[0xFFFD] = 0x00
        cpu.reset()

        # Run a few cycles
        try:
            cpu.execute(cycles=5)  # Should complete LDA #$AA and part of STA $10
        except errors.CPUCycleExhaustionError:
            pass

        first_pc = cpu.PC

        # Run more cycles
        try:
            cpu.execute(cycles=10)
        except errors.CPUCycleExhaustionError:
            pass

        # Check that both memory locations were written
        assert int(cpu.ram[0x10]) == 0xAA, "Memory $10 should be $AA"
        # Note: $11 might not be written yet depending on exact cycle timing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
