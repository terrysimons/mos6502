"""Tests for MOS 6522 VIA (Versatile Interface Adapter) emulation.

The 6522 VIA is used in the 1541 disk drive for:
- VIA1 ($1800): IEC serial bus communication
- VIA2 ($1C00): Disk drive mechanics control

Reference: https://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/6522-VIA.txt
"""

import pytest
from systems.c64.drive.via6522 import (
    VIA6522,
    REG_ORB, REG_ORA, REG_DDRB, REG_DDRA,
    REG_T1CL, REG_T1CH, REG_T1LL, REG_T1LH,
    REG_T2CL, REG_T2CH,
    REG_SR, REG_ACR, REG_PCR, REG_IFR, REG_IER,
    IRQ_T1, IRQ_T2, IRQ_SR, IRQ_CA1, IRQ_CB1, IRQ_ANY,
    ACR_T1_CONTINUOUS, ACR_T1_PB7_OUTPUT, ACR_T2_COUNT_PB6,
)


class TestVIA6522PortRegisters:
    """Test VIA port register behavior."""

    def test_initial_state(self):
        """VIA starts with all outputs low and DDR as input."""
        via = VIA6522()
        assert via.ora == 0x00
        assert via.orb == 0x00
        assert via.ddra == 0x00
        assert via.ddrb == 0x00

    def test_read_ddr_returns_current_value(self):
        """DDR reads return the current direction setting."""
        via = VIA6522()
        via.write(REG_DDRA, 0xF0)
        via.write(REG_DDRB, 0x0F)
        assert via.read(REG_DDRA) == 0xF0
        assert via.read(REG_DDRB) == 0x0F

    def test_write_ora_stores_value(self):
        """Writing ORA stores the output value."""
        via = VIA6522()
        via.write(REG_ORA, 0xAB)
        assert via.ora == 0xAB

    def test_write_orb_stores_value(self):
        """Writing ORB stores the output value."""
        via = VIA6522()
        via.write(REG_ORB, 0xCD)
        assert via.orb == 0xCD

    def test_read_port_a_mixes_input_output(self):
        """Reading port A mixes input pins (via callback) and output pins."""
        via = VIA6522()
        via.ddra = 0xF0  # Upper 4 bits output, lower 4 input
        via.ora = 0xA0   # Output pattern
        via.port_a_read_callback = lambda: 0x05  # Input pattern

        result = via.read(REG_ORA)
        # Upper 4 bits from ORA (0xA), lower 4 from callback (0x5)
        assert result == 0xA5

    def test_read_port_b_mixes_input_output(self):
        """Reading port B mixes input and output pins."""
        via = VIA6522()
        via.ddrb = 0x0F  # Lower 4 bits output, upper 4 input
        via.orb = 0x03   # Output pattern
        via.port_b_read_callback = lambda: 0xC0  # Input pattern

        result = via.read(REG_ORB)
        # Upper 4 bits from callback (0xC), lower 4 from ORB (0x3)
        assert result == 0xC3

    def test_port_write_triggers_callback(self):
        """Writing to port triggers the write callback."""
        via = VIA6522()
        callback_value = []
        via.ddra = 0xFF  # All output
        via.port_a_write_callback = lambda v: callback_value.append(v)

        via.write(REG_ORA, 0x55)
        assert callback_value == [0x55]


class TestVIA6522Timer1:
    """Test VIA Timer 1 behavior."""

    def test_write_t1ch_starts_timer(self):
        """Writing T1C-H loads counter from latch and starts timer."""
        via = VIA6522()
        via.write(REG_T1LL, 0x00)
        via.write(REG_T1LH, 0x10)  # Latch = $1000
        via.write(REG_T1CL, 0x00)
        via.write(REG_T1CH, 0x10)  # Load and start

        assert via.t1_counter == 0x1000
        assert via.t1_running is True

    def test_timer1_counts_down(self):
        """Timer 1 counts down each cycle."""
        via = VIA6522()
        via.t1_latch = 0x1000
        via.t1_counter = 0x1000
        via.t1_running = True

        via.tick(100)
        assert via.t1_counter == 0x1000 - 100

    def test_timer1_oneshot_stops_on_underflow(self):
        """In one-shot mode, timer stops after underflow."""
        via = VIA6522()
        via.acr = 0x00  # One-shot mode
        via.t1_latch = 0x0100
        via.t1_counter = 0x0050
        via.t1_running = True

        via.tick(0x60)  # More than counter value

        assert via.t1_running is False
        assert via.ifr & IRQ_T1  # Interrupt flag set

    def test_timer1_continuous_reloads(self):
        """In continuous mode, timer reloads from latch after underflow."""
        via = VIA6522()
        via.acr = ACR_T1_CONTINUOUS
        via.t1_latch = 0x0100
        via.t1_counter = 0x0050
        via.t1_running = True

        via.tick(0x60)  # Causes underflow

        assert via.t1_running is True
        assert via.ifr & IRQ_T1
        # Counter should have reloaded and decremented remaining cycles
        assert via.t1_counter < 0x0100

    def test_read_t1cl_clears_interrupt(self):
        """Reading T1C-L clears the T1 interrupt flag."""
        via = VIA6522()
        via.ifr = IRQ_T1

        via.read(REG_T1CL)
        assert (via.ifr & IRQ_T1) == 0

    def test_timer1_pb7_toggles(self):
        """Timer 1 toggles PB7 on underflow when enabled."""
        via = VIA6522()
        via.acr = ACR_T1_CONTINUOUS | ACR_T1_PB7_OUTPUT
        via.ddrb = 0x80  # PB7 output
        via.t1_latch = 0x0010
        via.t1_counter = 0x0005
        via.t1_running = True
        via.t1_pb7_state = False

        via.tick(0x10)  # Cause underflow

        assert via.t1_pb7_state is True  # Toggled


class TestVIA6522Timer2:
    """Test VIA Timer 2 behavior."""

    def test_write_t2ch_starts_timer(self):
        """Writing T2C-H loads counter and starts timer."""
        via = VIA6522()
        via.write(REG_T2CL, 0x00)  # Low latch
        via.write(REG_T2CH, 0x10)  # High byte + start

        assert via.t2_counter == 0x1000
        assert via.t2_running is True

    def test_timer2_counts_down(self):
        """Timer 2 counts down each cycle."""
        via = VIA6522()
        via.t2_counter = 0x0500
        via.t2_running = True

        via.tick(0x100)
        assert via.t2_counter == 0x0400

    def test_timer2_oneshot_sets_interrupt(self):
        """Timer 2 sets interrupt flag on underflow."""
        via = VIA6522()
        via.t2_counter = 0x0010
        via.t2_running = True

        via.tick(0x20)

        assert via.ifr & IRQ_T2
        assert via.t2_running is False

    def test_read_t2cl_clears_interrupt(self):
        """Reading T2C-L clears the T2 interrupt flag."""
        via = VIA6522()
        via.ifr = IRQ_T2

        via.read(REG_T2CL)
        assert (via.ifr & IRQ_T2) == 0


class TestVIA6522InterruptRegisters:
    """Test VIA interrupt flag and enable registers."""

    def test_ifr_bit7_reflects_enabled_interrupts(self):
        """IFR bit 7 is set when any enabled interrupt is active."""
        via = VIA6522()
        via.ifr = IRQ_T1
        via.ier = 0x00  # No interrupts enabled

        assert (via.read(REG_IFR) & IRQ_ANY) == 0

        via.ier = IRQ_T1  # Enable T1
        assert (via.read(REG_IFR) & IRQ_ANY) != 0

    def test_ier_set_mode(self):
        """Writing IER with bit 7 set enables interrupts."""
        via = VIA6522()
        via.ier = 0x00

        via.write(REG_IER, 0x80 | IRQ_T1 | IRQ_T2)
        assert via.ier == (IRQ_T1 | IRQ_T2)

    def test_ier_clear_mode(self):
        """Writing IER with bit 7 clear disables interrupts."""
        via = VIA6522()
        via.ier = IRQ_T1 | IRQ_T2

        via.write(REG_IER, 0x00 | IRQ_T1)  # Clear T1
        assert via.ier == IRQ_T2

    def test_ier_read_returns_bit7_set(self):
        """Reading IER always returns bit 7 set."""
        via = VIA6522()
        via.ier = 0x05

        result = via.read(REG_IER)
        assert result == (0x80 | 0x05)

    def test_write_ifr_clears_flags(self):
        """Writing 1 to IFR bits clears those flags."""
        via = VIA6522()
        via.ifr = IRQ_T1 | IRQ_T2 | IRQ_CA1

        via.write(REG_IFR, IRQ_T1)  # Clear T1 only
        assert via.ifr == (IRQ_T2 | IRQ_CA1)

    def test_irq_callback_triggered(self):
        """IRQ callback is triggered when enabled interrupt becomes active."""
        via = VIA6522()
        irq_states = []
        via.irq_callback = lambda active: irq_states.append(active)
        via.ier = IRQ_T1

        via.t1_counter = 0x0005
        via.t1_running = True
        via.tick(0x10)  # Cause underflow

        assert True in irq_states


class TestVIA6522ControlLines:
    """Test VIA CA1/CA2/CB1/CB2 control line behavior."""

    def test_ca1_negative_edge_sets_flag(self):
        """CA1 falling edge sets interrupt flag when configured."""
        via = VIA6522()
        via.pcr = 0x00  # CA1 negative edge
        via.set_ca1(True)  # Start high

        via.set_ca1(False)  # Falling edge
        assert via.ifr & IRQ_CA1

    def test_ca1_positive_edge_sets_flag(self):
        """CA1 rising edge sets interrupt flag when configured."""
        via = VIA6522()
        via.pcr = 0x01  # CA1 positive edge
        via.set_ca1(False)  # Start low

        via.set_ca1(True)  # Rising edge
        assert via.ifr & IRQ_CA1

    def test_cb1_negative_edge_sets_flag(self):
        """CB1 falling edge sets interrupt flag when configured."""
        via = VIA6522()
        via.pcr = 0x00  # CB1 negative edge
        via.set_cb1(True)

        via.set_cb1(False)
        assert via.ifr & IRQ_CB1

    def test_read_orb_clears_cb_flags(self):
        """Reading ORB clears CB1 and CB2 interrupt flags."""
        via = VIA6522()
        via.ifr = IRQ_CB1 | IRQ_CA1

        via.read(REG_ORB)
        assert (via.ifr & IRQ_CB1) == 0
        assert via.ifr & IRQ_CA1  # CA1 not cleared


class TestVIA6522ShiftRegister:
    """Test VIA shift register behavior."""

    def test_write_sr_clears_interrupt(self):
        """Writing SR clears the shift register interrupt flag."""
        via = VIA6522()
        via.ifr = IRQ_SR

        via.write(REG_SR, 0xAA)
        assert (via.ifr & IRQ_SR) == 0

    def test_read_sr_clears_interrupt(self):
        """Reading SR clears the shift register interrupt flag."""
        via = VIA6522()
        via.ifr = IRQ_SR
        via.sr = 0x55

        result = via.read(REG_SR)
        assert result == 0x55
        assert (via.ifr & IRQ_SR) == 0


class TestVIA6522Reset:
    """Test VIA reset behavior."""

    def test_reset_clears_registers(self):
        """Reset returns VIA to initial state."""
        via = VIA6522()
        via.ora = 0xFF
        via.orb = 0xFF
        via.ddra = 0xFF
        via.ddrb = 0xFF
        via.t1_counter = 0x1234
        via.ifr = 0x7F
        via.ier = 0x7F

        via.reset()

        assert via.ora == 0x00
        assert via.orb == 0x00
        assert via.ddra == 0x00
        assert via.ddrb == 0x00
        assert via.t1_counter == 0xFFFF
        assert via.ifr == 0x00
        assert via.ier == 0x00
