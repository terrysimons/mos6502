#!/usr/bin/env python3
"""Tests for CIA timer functionality.

These tests verify that the 6526 CIA timers work correctly,
including the auto-load behavior when writing the timer latch high byte.
"""

import pytest


class TestCIATimerLatchAutoLoad:
    """Test that writing timer latch high byte auto-loads counter when stopped."""

    def test_timer_a_autoload_on_high_byte_write_cia1(self, c64) -> None:
        """CIA1 Timer A: Writing high byte while stopped should load counter."""
        cia1 = c64.cia1

        # Ensure timer is stopped
        cia1.timer_a_running = False

        # Write latch low byte ($DC04)
        cia1.write(0x04, 0x34)
        assert cia1.timer_a_latch & 0xFF == 0x34, "Latch low byte should be set"

        # Write latch high byte ($DC05) - should auto-load counter
        cia1.write(0x05, 0x12)
        assert cia1.timer_a_latch == 0x1234, "Latch should be $1234"
        assert cia1.timer_a_counter == 0x1234, \
            f"Counter should auto-load to $1234 when high byte written while stopped, got ${cia1.timer_a_counter:04X}"

    def test_timer_a_no_autoload_when_running_cia1(self, c64) -> None:
        """CIA1 Timer A: Writing high byte while running should NOT load counter."""
        cia1 = c64.cia1

        # Set counter to a known value and start timer
        cia1.timer_a_counter = 0x5000
        cia1.timer_a_running = True

        # Write latch low byte ($DC04)
        cia1.write(0x04, 0x34)

        # Write latch high byte ($DC05) - should NOT auto-load counter
        cia1.write(0x05, 0x12)
        assert cia1.timer_a_latch == 0x1234, "Latch should be $1234"
        assert cia1.timer_a_counter == 0x5000, \
            f"Counter should NOT change when timer is running, got ${cia1.timer_a_counter:04X}"

    def test_timer_b_autoload_on_high_byte_write_cia1(self, c64) -> None:
        """CIA1 Timer B: Writing high byte while stopped should load counter."""
        cia1 = c64.cia1

        # Ensure timer is stopped
        cia1.timer_b_running = False

        # Write latch low byte ($DC06)
        cia1.write(0x06, 0xAB)

        # Write latch high byte ($DC07) - should auto-load counter
        cia1.write(0x07, 0xCD)
        assert cia1.timer_b_latch == 0xCDAB, "Latch should be $CDAB"
        assert cia1.timer_b_counter == 0xCDAB, \
            f"Counter should auto-load to $CDAB, got ${cia1.timer_b_counter:04X}"

    def test_timer_a_autoload_on_high_byte_write_cia2(self, c64) -> None:
        """CIA2 Timer A: Writing high byte while stopped should load counter."""
        cia2 = c64.cia2

        # Ensure timer is stopped
        cia2.timer_a_running = False

        # Write latch low byte ($DD04)
        cia2.write(0x04, 0x78)

        # Write latch high byte ($DD05) - should auto-load counter
        cia2.write(0x05, 0x56)
        assert cia2.timer_a_latch == 0x5678, "Latch should be $5678"
        assert cia2.timer_a_counter == 0x5678, \
            f"Counter should auto-load to $5678, got ${cia2.timer_a_counter:04X}"

    def test_timer_b_autoload_on_high_byte_write_cia2(self, c64) -> None:
        """CIA2 Timer B: Writing high byte while stopped should load counter."""
        cia2 = c64.cia2

        # Ensure timer is stopped
        cia2.timer_b_running = False

        # Write latch low byte ($DD06)
        cia2.write(0x06, 0xEF)

        # Write latch high byte ($DD07) - should auto-load counter
        cia2.write(0x07, 0xBE)
        assert cia2.timer_b_latch == 0xBEEF, "Latch should be $BEEF"
        assert cia2.timer_b_counter == 0xBEEF, \
            f"Counter should auto-load to $BEEF, got ${cia2.timer_b_counter:04X}"


class TestCIATimerCountdown:
    """Test that CIA timers count down correctly."""

    def test_timer_a_counts_down_cia1(self, c64) -> None:
        """CIA1 Timer A should count down when running."""
        cia1 = c64.cia1

        # Set up timer with a known value
        cia1.timer_a_counter = 1000
        cia1.timer_a_latch = 1000
        cia1.timer_a_running = True
        cia1.timer_a_cnt_mode = False  # Count CPU cycles, not CNT pin

        # Record initial cycle count
        initial_cycles = c64.cpu.cycles_executed
        cia1.last_cycle_count = initial_cycles

        # Simulate some cycles passing
        c64.cpu.cycles_executed = initial_cycles + 100

        # Update CIA
        cia1.update()

        # Timer should have counted down by 100
        assert cia1.timer_a_counter == 900, \
            f"Timer should count down from 1000 to 900, got {cia1.timer_a_counter}"

    def test_timer_a_underflow_sets_icr_flag_cia1(self, c64) -> None:
        """CIA1 Timer A underflow should set ICR flag."""
        cia1 = c64.cia1

        # Set up timer to underflow quickly
        cia1.timer_a_counter = 10
        cia1.timer_a_latch = 100
        cia1.timer_a_running = True
        cia1.timer_a_cnt_mode = False
        cia1.timer_a_oneshot = False  # Continuous mode
        cia1.icr_data = 0x00

        # Record initial cycle count
        initial_cycles = c64.cpu.cycles_executed
        cia1.last_cycle_count = initial_cycles

        # Simulate enough cycles to cause underflow
        c64.cpu.cycles_executed = initial_cycles + 50

        # Update CIA
        cia1.update()

        # ICR bit 0 (Timer A) should be set
        assert cia1.icr_data & 0x01, \
            f"ICR Timer A flag should be set after underflow, ICR=${cia1.icr_data:02X}"

    def test_timer_a_underflow_triggers_irq_when_enabled_cia1(self, c64) -> None:
        """CIA1 Timer A underflow should trigger IRQ when enabled."""
        cia1 = c64.cia1

        # Enable Timer A interrupt
        cia1.icr_mask = 0x01

        # Set up timer to underflow quickly
        cia1.timer_a_counter = 10
        cia1.timer_a_latch = 100
        cia1.timer_a_running = True
        cia1.timer_a_cnt_mode = False
        cia1.timer_a_oneshot = False

        # Clear any pending IRQ
        c64.cpu.irq_pending = False

        # Record initial cycle count
        initial_cycles = c64.cpu.cycles_executed
        cia1.last_cycle_count = initial_cycles

        # Simulate enough cycles to cause underflow
        c64.cpu.cycles_executed = initial_cycles + 50

        # Update CIA
        cia1.update()

        # IRQ should be pending
        assert c64.cpu.irq_pending, "IRQ should be pending after Timer A underflow with interrupt enabled"

    def test_timer_a_underflow_triggers_nmi_cia2(self, c64) -> None:
        """CIA2 Timer A underflow should trigger NMI when enabled."""
        cia2 = c64.cia2

        # Enable Timer A interrupt
        cia2.icr_mask = 0x01

        # Set up timer to underflow quickly
        cia2.timer_a_counter = 10
        cia2.timer_a_latch = 100
        cia2.timer_a_running = True
        cia2.timer_a_cnt_mode = False
        cia2.timer_a_oneshot = False

        # Clear any pending NMI
        c64.cpu.nmi_pending = False

        # Record initial cycle count
        initial_cycles = c64.cpu.cycles_executed
        cia2.last_cycle_count = initial_cycles

        # Simulate enough cycles to cause underflow
        c64.cpu.cycles_executed = initial_cycles + 50

        # Update CIA
        cia2.update()

        # NMI should be pending
        assert c64.cpu.nmi_pending, "NMI should be pending after CIA2 Timer A underflow with interrupt enabled"


class TestCIATimerControlRegister:
    """Test CIA timer control register behavior."""

    def test_force_load_loads_counter_cia1(self, c64) -> None:
        """CIA1: Force load bit should load latch into counter."""
        cia1 = c64.cia1

        # Set latch to a value
        cia1.timer_a_latch = 0x1234
        cia1.timer_a_counter = 0x0000

        # Write control register with force load bit (bit 4)
        cia1.write(0x0E, 0x10)  # Force load only, timer stopped

        assert cia1.timer_a_counter == 0x1234, \
            f"Force load should set counter to latch value, got ${cia1.timer_a_counter:04X}"

    def test_start_timer_cia1(self, c64) -> None:
        """CIA1: Control register bit 0 should start timer."""
        cia1 = c64.cia1

        # Ensure timer is stopped
        cia1.timer_a_running = False

        # Write control register with start bit (bit 0)
        cia1.write(0x0E, 0x01)

        assert cia1.timer_a_running, "Timer A should be running after setting bit 0"

    def test_oneshot_mode_stops_after_underflow_cia1(self, c64) -> None:
        """CIA1: One-shot mode should stop timer after underflow."""
        cia1 = c64.cia1

        # Set up timer in one-shot mode
        cia1.timer_a_counter = 10
        cia1.timer_a_latch = 100
        cia1.timer_a_running = True
        cia1.timer_a_cnt_mode = False
        cia1.timer_a_oneshot = True

        # Record initial cycle count
        initial_cycles = c64.cpu.cycles_executed
        cia1.last_cycle_count = initial_cycles

        # Simulate enough cycles to cause underflow
        c64.cpu.cycles_executed = initial_cycles + 50

        # Update CIA
        cia1.update()

        # Timer should have stopped
        assert not cia1.timer_a_running, "Timer should stop after underflow in one-shot mode"


class TestCIATimerRead:
    """Test reading CIA timer values."""

    def test_read_timer_counter_cia1(self, c64) -> None:
        """CIA1: Reading timer registers should return counter value."""
        cia1 = c64.cia1

        # Set counter to a known value
        cia1.timer_a_counter = 0xABCD

        # Read low and high bytes
        low = cia1.read(0x04)
        high = cia1.read(0x05)

        assert low == 0xCD, f"Timer A low byte should be $CD, got ${low:02X}"
        assert high == 0xAB, f"Timer A high byte should be $AB, got ${high:02X}"


class TestCIAInterruptIntegration:
    """Test full interrupt flow - timer to IRQ handler."""

    def test_timer_a_irq_fires_and_vectors_to_handler(self, c64) -> None:
        """Full test: Timer A underflow should fire IRQ and vector to handler.

        On C64, the KERNAL ROM handles hardware IRQ vectors at $FFFE/$FFFF.
        The KERNAL's IRQ handler at $FF48 saves registers and then jumps
        through the vector at $0314/$0315 to the user's IRQ routine.
        After the user routine, it should JMP to $EA81 which restores
        registers and does RTI.
        """
        from mos6502 import errors

        # Set up a custom IRQ handler at $0400 that acknowledges interrupt and sets flag
        # Handler:
        #   LDA $DC0D   ; Read CIA1 ICR to acknowledge interrupt (clears irq_pending)
        #   INC $02     ; Increment flag
        #   JMP $EA81   ; KERNAL IRQ exit (restore regs and RTI)
        c64.memory.write(0x0400, 0xAD)  # LDA absolute
        c64.memory.write(0x0401, 0x0D)  # Low byte of $DC0D
        c64.memory.write(0x0402, 0xDC)  # High byte of $DC0D
        c64.memory.write(0x0403, 0xE6)  # INC $02
        c64.memory.write(0x0404, 0x02)
        c64.memory.write(0x0405, 0x4C)  # JMP $EA81 (KERNAL IRQ exit)
        c64.memory.write(0x0406, 0x81)
        c64.memory.write(0x0407, 0xEA)

        # Hook the KERNAL IRQ vector at $0314/$0315 to point to our handler
        c64.memory.write(0x0314, 0x00)  # Low byte -> $0400
        c64.memory.write(0x0315, 0x04)  # High byte

        # Put a simple NOP loop at $0200 for the CPU to run
        c64.memory.write(0x0200, 0xEA)  # NOP
        c64.memory.write(0x0201, 0x4C)  # JMP $0200
        c64.memory.write(0x0202, 0x00)
        c64.memory.write(0x0203, 0x02)

        # Set PC to our NOP loop
        c64.cpu.PC = 0x0200

        # Initialize flag location
        c64.memory.write(0x0002, 0x00)

        # Set up CIA1 Timer A for a quick underflow
        c64.cia1.timer_a_latch = 20  # Very short timer
        c64.cia1.timer_a_counter = 20
        c64.cia1.icr_mask = 0x01  # Enable Timer A interrupt
        c64.cia1.timer_a_running = True
        c64.cia1.timer_a_oneshot = True

        # Clear I flag to allow interrupts
        c64.cpu.I = 0

        # Sync CIA cycle count
        c64.cia1.last_cycle_count = c64.cpu.cycles_executed

        # Simulate enough cycles to cause timer underflow
        c64.cpu.cycles_executed += 50

        # Update CIA - this should set irq_pending
        c64.cia1.update()

        # Verify IRQ is pending
        assert c64.cpu.irq_pending, "IRQ should be pending after timer underflow"

        # Run some instructions - CPU should vector to IRQ handler
        try:
            c64.cpu.execute(max_instructions=20)
        except errors.CPUCycleExhaustionError:
            pass

        # Check if our IRQ handler ran (flag at $02 should be incremented)
        flag_value = c64.memory.read(0x0002)
        assert flag_value >= 0x01, \
            f"IRQ handler should have incremented $02, got ${flag_value:02X}. " \
            f"PC=${c64.cpu.PC:04X}, I flag={c64.cpu.I}, irq_pending={c64.cpu.irq_pending}"

    def test_polling_icr_detects_timer_underflow(self, c64) -> None:
        """Test polling ICR to detect timer underflow (no actual IRQ)."""
        # Set up CIA1 Timer A
        c64.cia1.timer_a_latch = 10
        c64.cia1.timer_a_counter = 10
        c64.cia1.icr_mask = 0x01  # Enable Timer A interrupt
        c64.cia1.timer_a_running = True
        c64.cia1.timer_a_oneshot = True

        # Sync cycle count
        c64.cia1.last_cycle_count = c64.cpu.cycles_executed

        # Simulate some cycles
        c64.cpu.cycles_executed += 50

        # Update CIA
        c64.cia1.update()

        # Read ICR - should show Timer A fired (bit 0) with bit 7 set (enabled interrupt)
        icr = c64.cia1.read(0x0D)

        assert icr & 0x01, f"ICR bit 0 (Timer A) should be set, got ${icr:02X}"
        assert icr & 0x80, f"ICR bit 7 should be set (enabled interrupt fired), got ${icr:02X}"


class TestCIAICRBehavior:
    """Test CIA Interrupt Control Register behavior."""

    def test_icr_read_clears_irq_pending_cia1(self, c64) -> None:
        """CIA1: Reading ICR should clear cpu.irq_pending."""
        cia1 = c64.cia1

        # Set up an interrupt condition
        cia1.icr_data = 0x01  # Timer A interrupt
        cia1.icr_mask = 0x01  # Timer A interrupt enabled
        c64.cpu.irq_pending = True

        # Read ICR
        result = cia1.read(0x0D)

        # Should return 0x81 (bit 7 + bit 0)
        assert result == 0x81, f"ICR should return $81, got ${result:02X}"

        # irq_pending should be cleared
        assert not c64.cpu.irq_pending, "Reading ICR should clear irq_pending"

        # icr_data should be cleared
        assert cia1.icr_data == 0x00, "Reading ICR should clear icr_data"

    def test_icr_read_clears_nmi_pending_cia2(self, c64) -> None:
        """CIA2: Reading ICR should clear cpu.nmi_pending."""
        cia2 = c64.cia2

        # Set up an interrupt condition
        cia2.icr_data = 0x01  # Timer A interrupt
        cia2.icr_mask = 0x01  # Timer A interrupt enabled
        c64.cpu.nmi_pending = True

        # Read ICR
        result = cia2.read(0x0D)

        # Should return 0x81 (bit 7 + bit 0)
        assert result == 0x81, f"ICR should return $81, got ${result:02X}"

        # nmi_pending should be cleared
        assert not c64.cpu.nmi_pending, "Reading ICR should clear nmi_pending"

    def test_icr_bit7_only_set_when_enabled_interrupt_active(self, c64) -> None:
        """ICR bit 7 should only be set if an enabled interrupt has fired."""
        cia1 = c64.cia1

        # Set interrupt flag but NOT mask
        cia1.icr_data = 0x01  # Timer A interrupt occurred
        cia1.icr_mask = 0x00  # But not enabled

        # Read ICR
        result = cia1.read(0x0D)

        # Should return 0x01 (just bit 0, NOT bit 7)
        assert result == 0x01, f"ICR should return $01 (no bit 7), got ${result:02X}"

    def test_icr_returns_all_interrupt_flags(self, c64) -> None:
        """ICR should return all interrupt flags that fired."""
        cia1 = c64.cia1

        # Set multiple interrupt flags
        cia1.icr_data = 0x03  # Timer A and Timer B
        cia1.icr_mask = 0x01  # Only Timer A enabled

        # Read ICR
        result = cia1.read(0x0D)

        # Should return 0x83 (bit 7 + bits 1,0 - all flags, bit 7 because Timer A enabled)
        assert result == 0x83, f"ICR should return $83, got ${result:02X}"


class TestCIAICRMaskImmediateInterrupt:
    """Test that enabling ICR mask bit fires interrupt immediately if data bit already set.

    6526 behavior: When writing to ICR with bit 7 set (enable mask bits),
    if the corresponding ICR data bit is already set, the interrupt should
    fire immediately.
    """

    def test_icr_mask_write_triggers_irq_if_data_set_cia1(self, c64) -> None:
        """CIA1: Enabling ICR mask should fire IRQ immediately if data bit already set."""
        cia1 = c64.cia1

        # Pre-condition: Timer A interrupt has occurred but is not enabled
        cia1.icr_data = 0x01  # Timer A interrupt flag set
        cia1.icr_mask = 0x00  # No interrupts enabled yet
        c64.cpu.irq_pending = False

        # Now enable Timer A interrupt via ICR write (bit 7 = set, bit 0 = Timer A)
        cia1.write(0x0D, 0x81)

        # IRQ should fire immediately because data bit was already set
        assert c64.cpu.irq_pending, \
            "Enabling ICR mask when data bit already set should trigger IRQ immediately"
        assert cia1.icr_mask == 0x01, "ICR mask should have Timer A enabled"

    def test_icr_mask_write_triggers_nmi_if_data_set_cia2(self, c64) -> None:
        """CIA2: Enabling ICR mask should fire NMI immediately if data bit already set."""
        cia2 = c64.cia2

        # Pre-condition: Timer A interrupt has occurred but is not enabled
        cia2.icr_data = 0x01  # Timer A interrupt flag set
        cia2.icr_mask = 0x00  # No interrupts enabled yet
        c64.cpu.nmi_pending = False

        # Now enable Timer A interrupt via ICR write (bit 7 = set, bit 0 = Timer A)
        cia2.write(0x0D, 0x81)

        # NMI should fire immediately because data bit was already set
        assert c64.cpu.nmi_pending, \
            "Enabling ICR mask when data bit already set should trigger NMI immediately"

    def test_icr_mask_write_no_irq_if_data_not_set_cia1(self, c64) -> None:
        """CIA1: Enabling ICR mask should NOT fire IRQ if data bit is not set."""
        cia1 = c64.cia1

        # Pre-condition: No interrupt has occurred
        cia1.icr_data = 0x00  # No interrupt flags set
        cia1.icr_mask = 0x00
        c64.cpu.irq_pending = False

        # Enable Timer A interrupt
        cia1.write(0x0D, 0x81)

        # IRQ should NOT fire - no data bit set
        assert not c64.cpu.irq_pending, \
            "Enabling ICR mask when no data bit set should NOT trigger IRQ"

    def test_icr_mask_write_triggers_irq_for_timer_b_cia1(self, c64) -> None:
        """CIA1: Enabling Timer B mask should fire IRQ if Timer B data bit set."""
        cia1 = c64.cia1

        # Timer B interrupt has occurred
        cia1.icr_data = 0x02  # Timer B interrupt flag set
        cia1.icr_mask = 0x00
        c64.cpu.irq_pending = False

        # Enable Timer B interrupt (bit 7 = set, bit 1 = Timer B)
        cia1.write(0x0D, 0x82)

        assert c64.cpu.irq_pending, \
            "Enabling Timer B mask when Timer B data bit set should trigger IRQ"

    def test_icr_mask_write_triggers_irq_for_flag_cia1(self, c64) -> None:
        """CIA1: Enabling FLAG mask should fire IRQ if FLAG data bit set."""
        cia1 = c64.cia1

        # FLAG interrupt has occurred
        cia1.icr_data = 0x10  # FLAG interrupt flag set (bit 4)
        cia1.icr_mask = 0x00
        c64.cpu.irq_pending = False

        # Enable FLAG interrupt (bit 7 = set, bit 4 = FLAG)
        cia1.write(0x0D, 0x90)

        assert c64.cpu.irq_pending, \
            "Enabling FLAG mask when FLAG data bit set should trigger IRQ"

    def test_icr_mask_clear_does_not_trigger_irq(self, c64) -> None:
        """CIA1: Clearing ICR mask bits should NOT trigger IRQ."""
        cia1 = c64.cia1

        # Set up interrupt condition
        cia1.icr_data = 0x01  # Timer A interrupt flag set
        cia1.icr_mask = 0x01  # Timer A enabled
        c64.cpu.irq_pending = False

        # Clear Timer A mask (bit 7 = 0 means clear bits)
        cia1.write(0x0D, 0x01)

        # IRQ should NOT fire from clearing mask
        assert not c64.cpu.irq_pending, \
            "Clearing ICR mask bits should NOT trigger IRQ"
        assert cia1.icr_mask == 0x00, "Timer A mask should be cleared"


class TestCIAFLAGPinCrossTriggering:
    """Test FLAG pin cross-triggering between CIA1 and CIA2.

    When one CIA outputs serial data, the other CIA should receive
    a FLAG interrupt (simulating IEC bus communication).
    """

    def test_cias_are_linked(self, c64) -> None:
        """CIAs should have references to each other."""
        assert c64.cia1.other_cia is c64.cia2, "CIA1 should reference CIA2"
        assert c64.cia2.other_cia is c64.cia1, "CIA2 should reference CIA1"

    def test_trigger_flag_interrupt_sets_icr_data(self, c64) -> None:
        """trigger_flag_interrupt() should set FLAG bit in own ICR data.

        Note on semantics: trigger_flag_interrupt() sets the FLAG bit on SELF,
        not on other_cia. The cross-triggering happens at a higher level:
        - When CIA1 outputs serial data, it calls cia2.trigger_flag_interrupt()
        - When CIA2 outputs serial data, it calls cia1.trigger_flag_interrupt()

        So cia1.trigger_flag_interrupt() sets CIA1's FLAG bit (for when CIA2
        sends data TO CIA1), not CIA2's FLAG bit.
        """
        cia1 = c64.cia1

        # Clear ICR data
        cia1.icr_data = 0x00

        # Trigger FLAG on CIA1 (sets flag on itself, simulating receiving data)
        cia1.trigger_flag_interrupt()

        # CIA1 should have FLAG bit set
        assert cia1.icr_data & 0x10, \
            f"trigger_flag_interrupt should set FLAG bit, ICR=${cia1.icr_data:02X}"

    def test_cia1_sdr_write_triggers_flag_on_cia2(self, c64) -> None:
        """Writing to CIA1 SDR in output mode should trigger FLAG on CIA2."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # Enable SDR output mode on CIA1
        cia1.sdr_output_mode = True

        # Clear CIA2 ICR data
        cia2.icr_data = 0x00
        c64.cpu.nmi_pending = False

        # Write to SDR (this should trigger FLAG on CIA2)
        cia1.write(0x0C, 0xAA)

        # CIA2 should have FLAG bit set in ICR data
        assert cia2.icr_data & 0x10, \
            f"CIA2 FLAG bit should be set after CIA1 SDR write, ICR=${cia2.icr_data:02X}"

    def test_cia1_sdr_write_triggers_nmi_if_flag_enabled_on_cia2(self, c64) -> None:
        """CIA1 SDR write should trigger NMI on CIA2 if FLAG interrupt is enabled."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # Enable SDR output mode on CIA1
        cia1.sdr_output_mode = True

        # Enable FLAG interrupt on CIA2
        cia2.icr_mask = 0x10  # FLAG interrupt enabled
        cia2.icr_data = 0x00
        c64.cpu.nmi_pending = False

        # Write to SDR
        cia1.write(0x0C, 0x55)

        # NMI should be pending (CIA2 generates NMI)
        assert c64.cpu.nmi_pending, \
            "CIA1 SDR write should trigger NMI on CIA2 when FLAG enabled"

    def test_cia2_sdr_write_triggers_flag_on_cia1(self, c64) -> None:
        """Writing to CIA2 SDR in output mode should trigger FLAG on CIA1."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # Enable SDR output mode on CIA2
        cia2.sdr_output_mode = True

        # Clear CIA1 ICR data
        cia1.icr_data = 0x00
        c64.cpu.irq_pending = False

        # Write to SDR
        cia2.write(0x0C, 0xBB)

        # CIA1 should have FLAG bit set
        assert cia1.icr_data & 0x10, \
            f"CIA1 FLAG bit should be set after CIA2 SDR write, ICR=${cia1.icr_data:02X}"

    def test_cia2_sdr_write_triggers_irq_if_flag_enabled_on_cia1(self, c64) -> None:
        """CIA2 SDR write should trigger IRQ on CIA1 if FLAG interrupt is enabled."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # Enable SDR output mode on CIA2
        cia2.sdr_output_mode = True

        # Enable FLAG interrupt on CIA1
        cia1.icr_mask = 0x10  # FLAG interrupt enabled
        cia1.icr_data = 0x00
        c64.cpu.irq_pending = False

        # Write to SDR
        cia2.write(0x0C, 0xCC)

        # IRQ should be pending (CIA1 generates IRQ)
        assert c64.cpu.irq_pending, \
            "CIA2 SDR write should trigger IRQ on CIA1 when FLAG enabled"

    def test_sdr_write_no_flag_when_input_mode(self, c64) -> None:
        """SDR write should NOT trigger FLAG when in input mode."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # SDR is in INPUT mode (default)
        cia1.sdr_output_mode = False

        # Clear CIA2 state
        cia2.icr_data = 0x00

        # Write to SDR
        cia1.write(0x0C, 0xDD)

        # CIA2 should NOT have FLAG bit set
        assert not (cia2.icr_data & 0x10), \
            "SDR write in input mode should NOT trigger FLAG on other CIA"


class TestCIASDROutputModeEnableFLAG:
    """Test FLAG trigger when enabling SDR output mode.

    When transitioning SDR from input mode to output mode, if data has
    been written to SDR, the other CIA should receive FLAG interrupt.
    """

    def test_enabling_sdr_output_mode_triggers_flag_cia1(self, c64) -> None:
        """CIA1: Enabling SDR output mode should trigger FLAG on CIA2."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # Start in input mode
        cia1.sdr_output_mode = False

        # Clear CIA2 state
        cia2.icr_data = 0x00
        c64.cpu.nmi_pending = False

        # Write Control Register A with output mode bit set (bit 6)
        # This transitions from input to output mode
        cia1.write(0x0E, 0x40)

        # CIA2 should have FLAG bit set
        assert cia2.icr_data & 0x10, \
            f"Enabling SDR output mode should trigger FLAG on CIA2, ICR=${cia2.icr_data:02X}"

    def test_enabling_sdr_output_mode_triggers_nmi_if_enabled_cia1(self, c64) -> None:
        """CIA1: Enabling SDR output mode triggers NMI on CIA2 if FLAG enabled."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # Start in input mode
        cia1.sdr_output_mode = False

        # Enable FLAG interrupt on CIA2
        cia2.icr_mask = 0x10
        cia2.icr_data = 0x00
        c64.cpu.nmi_pending = False

        # Enable output mode on CIA1
        cia1.write(0x0E, 0x40)

        assert c64.cpu.nmi_pending, \
            "Enabling SDR output mode should trigger NMI when CIA2 FLAG enabled"

    def test_enabling_sdr_output_mode_triggers_flag_cia2(self, c64) -> None:
        """CIA2: Enabling SDR output mode should trigger FLAG on CIA1."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # Start in input mode
        cia2.sdr_output_mode = False

        # Clear CIA1 state
        cia1.icr_data = 0x00
        c64.cpu.irq_pending = False

        # Write Control Register A with output mode bit set
        cia2.write(0x0E, 0x40)

        # CIA1 should have FLAG bit set
        assert cia1.icr_data & 0x10, \
            f"Enabling SDR output mode should trigger FLAG on CIA1, ICR=${cia1.icr_data:02X}"

    def test_already_output_mode_no_extra_flag(self, c64) -> None:
        """Writing CRA when already in output mode should NOT trigger extra FLAG."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # Already in output mode
        cia1.sdr_output_mode = True

        # Clear CIA2 state
        cia2.icr_data = 0x00

        # Write Control Register A again with output mode (no transition)
        cia1.write(0x0E, 0x40)

        # CIA2 should NOT have FLAG bit set (no transition occurred)
        assert not (cia2.icr_data & 0x10), \
            "Re-writing output mode should NOT trigger FLAG (no transition)"

    def test_disabling_sdr_output_mode_no_flag(self, c64) -> None:
        """Disabling SDR output mode (transitioning to input) should NOT trigger FLAG."""
        cia1 = c64.cia1
        cia2 = c64.cia2

        # Start in output mode
        cia1.sdr_output_mode = True

        # Clear CIA2 state
        cia2.icr_data = 0x00

        # Disable output mode (set to input mode)
        cia1.write(0x0E, 0x00)

        # CIA2 should NOT have FLAG bit set
        assert not (cia2.icr_data & 0x10), \
            "Transitioning to input mode should NOT trigger FLAG"
