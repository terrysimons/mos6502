"""MOS 6522 VIA (Versatile Interface Adapter) Emulation.

The 6522 VIA provides:
- Two 8-bit bidirectional I/O ports (Port A and Port B)
- Two 16-bit timers (Timer 1 and Timer 2)
- 8-bit shift register for serial I/O
- Handshake control lines (CA1, CA2, CB1, CB2)
- Interrupt generation

Register Map (accent by RS3-RS0):
    $0: ORB/IRB - Output/Input Register B
    $1: ORA/IRA - Output/Input Register A
    $2: DDRB    - Data Direction Register B
    $3: DDRA    - Data Direction Register A
    $4: T1C-L   - Timer 1 Counter Low (read) / Latch Low (write)
    $5: T1C-H   - Timer 1 Counter High
    $6: T1L-L   - Timer 1 Latch Low
    $7: T1L-H   - Timer 1 Latch High
    $8: T2C-L   - Timer 2 Counter Low (read) / Latch Low (write)
    $9: T2C-H   - Timer 2 Counter High
    $A: SR      - Shift Register
    $B: ACR     - Auxiliary Control Register
    $C: PCR     - Peripheral Control Register
    $D: IFR     - Interrupt Flag Register
    $E: IER     - Interrupt Enable Register
    $F: ORA/IRA - Same as $1 but no handshake

Reference:
- https://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/6522-VIA.txt
- http://archive.6502.org/datasheets/mos_6522_preliminary_nov_1977.pdf
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    pass

log = logging.getLogger("via6522")


# Register addresses (accent by lower 4 bits)
REG_ORB = 0x0   # Output/Input Register B
REG_ORA = 0x1   # Output/Input Register A
REG_DDRB = 0x2  # Data Direction Register B
REG_DDRA = 0x3  # Data Direction Register A
REG_T1CL = 0x4  # Timer 1 Counter Low
REG_T1CH = 0x5  # Timer 1 Counter High
REG_T1LL = 0x6  # Timer 1 Latch Low
REG_T1LH = 0x7  # Timer 1 Latch High
REG_T2CL = 0x8  # Timer 2 Counter Low
REG_T2CH = 0x9  # Timer 2 Counter High
REG_SR = 0xA    # Shift Register
REG_ACR = 0xB   # Auxiliary Control Register
REG_PCR = 0xC   # Peripheral Control Register
REG_IFR = 0xD   # Interrupt Flag Register
REG_IER = 0xE   # Interrupt Enable Register
REG_ORA_NHS = 0xF  # ORA without handshake

# IFR/IER bit definitions
IRQ_CA2 = 0x01     # CA2 interrupt
IRQ_CA1 = 0x02     # CA1 interrupt
IRQ_SR = 0x04      # Shift register interrupt
IRQ_CB2 = 0x08     # CB2 interrupt
IRQ_CB1 = 0x10     # CB1 interrupt
IRQ_T2 = 0x20      # Timer 2 interrupt
IRQ_T1 = 0x40      # Timer 1 interrupt
IRQ_ANY = 0x80     # Any interrupt (IFR bit 7)

# ACR bit definitions
ACR_PA_LATCH = 0x01   # Port A latch enable
ACR_PB_LATCH = 0x02   # Port B latch enable
ACR_SR_MASK = 0x1C    # Shift register control (bits 2-4)
ACR_SR_SHIFT = 2
ACR_T2_COUNT_PB6 = 0x20  # Timer 2: count pulses on PB6
ACR_T1_CONTINUOUS = 0x40  # Timer 1: continuous mode
ACR_T1_PB7_OUTPUT = 0x80  # Timer 1: output to PB7

# PCR bit definitions
PCR_CA1_POSITIVE = 0x01  # CA1: positive edge (1) or negative edge (0)
PCR_CA2_MASK = 0x0E      # CA2 control (bits 1-3)
PCR_CA2_SHIFT = 1
PCR_CB1_POSITIVE = 0x10  # CB1: positive edge (1) or negative edge (0)
PCR_CB2_MASK = 0xE0      # CB2 control (bits 5-7)
PCR_CB2_SHIFT = 5

# Shift register modes (ACR bits 4-2)
SR_DISABLED = 0
SR_SHIFT_IN_T2 = 1
SR_SHIFT_IN_PHI2 = 2
SR_SHIFT_IN_EXT = 3
SR_SHIFT_OUT_FREE = 4
SR_SHIFT_OUT_T2 = 5
SR_SHIFT_OUT_PHI2 = 6
SR_SHIFT_OUT_EXT = 7


class VIA6522:
    """MOS 6522 Versatile Interface Adapter emulation.

    This class emulates a single 6522 VIA chip. The 1541 drive contains
    two of these - VIA1 at $1800 for IEC bus communication and VIA2 at
    $1C00 for disk drive mechanics control.
    """

    def __init__(self, name: str = "VIA") -> None:
        """Initialize the VIA.

        Args:
            name: Identifier for logging (e.g., "VIA1", "VIA2")
        """
        self.name = name

        # Port registers
        self.ora = 0x00      # Output Register A (directly controls pins)
        self.orb = 0x00      # Output Register B
        self.ira = 0xFF      # Input Register A (latched input)
        self.irb = 0xFF      # Input Register B
        self.ddra = 0x00     # Data Direction A (0=input, 1=output)
        self.ddrb = 0x00     # Data Direction B

        # Timer 1
        self.t1_counter = 0xFFFF
        self.t1_latch = 0xFFFF
        self.t1_running = False
        self.t1_pb7_state = False  # PB7 toggle state for timer 1

        # Timer 2
        self.t2_counter = 0xFFFF
        self.t2_latch_low = 0xFF  # Only low byte is latched for T2
        self.t2_running = False

        # Shift register
        self.sr = 0x00
        self.sr_counter = 0  # Bits remaining to shift

        # Control registers
        self.acr = 0x00  # Auxiliary Control Register
        self.pcr = 0x00  # Peripheral Control Register
        self.ifr = 0x00  # Interrupt Flag Register
        self.ier = 0x00  # Interrupt Enable Register

        # Control/handshake lines state
        self.ca1 = True   # CA1 input line
        self.ca2 = True   # CA2 input/output line
        self.cb1 = True   # CB1 input line
        self.cb2 = True   # CB2 input/output line

        # Previous states for edge detection
        self._ca1_prev = True
        self._ca2_prev = True
        self._cb1_prev = True
        self._cb2_prev = True
        self._pb6_prev = True  # For T2 pulse counting

        # Callbacks for external hardware
        self.port_a_read_callback: Optional[Callable[[], int]] = None
        self.port_b_read_callback: Optional[Callable[[], int]] = None
        self.port_a_write_callback: Optional[Callable[[int], None]] = None
        self.port_b_write_callback: Optional[Callable[[int], None]] = None
        self.irq_callback: Optional[Callable[[bool], None]] = None

    def reset(self) -> None:
        """Reset VIA to power-on state."""
        self.ora = 0x00
        self.orb = 0x00
        self.ira = 0xFF
        self.irb = 0xFF
        self.ddra = 0x00
        self.ddrb = 0x00

        self.t1_counter = 0xFFFF
        self.t1_latch = 0xFFFF
        self.t1_running = False
        self.t1_pb7_state = False

        self.t2_counter = 0xFFFF
        self.t2_latch_low = 0xFF
        self.t2_running = False

        self.sr = 0x00
        self.sr_counter = 0

        self.acr = 0x00
        self.pcr = 0x00
        self.ifr = 0x00
        self.ier = 0x00

    def read(self, addr: int) -> int:
        """Read from VIA register.

        Args:
            addr: Address (only lower 4 bits used)

        Returns:
            Register value
        """
        reg = addr & 0x0F

        if reg == REG_ORB:
            # Read Port B - mix of input and output bits
            result = self._read_port_b()
            # Clear CB1/CB2 interrupt flags
            self.ifr &= ~(IRQ_CB1 | IRQ_CB2)
            self._update_irq()
            return result

        elif reg == REG_ORA or reg == REG_ORA_NHS:
            # Read Port A
            result = self._read_port_a()
            if reg == REG_ORA:
                # Clear CA1/CA2 interrupt flags (not for no-handshake variant)
                self.ifr &= ~(IRQ_CA1 | IRQ_CA2)
                self._update_irq()
            return result

        elif reg == REG_DDRB:
            return self.ddrb

        elif reg == REG_DDRA:
            return self.ddra

        elif reg == REG_T1CL:
            # Reading T1C-L clears T1 interrupt flag
            self.ifr &= ~IRQ_T1
            self._update_irq()
            return self.t1_counter & 0xFF

        elif reg == REG_T1CH:
            return (self.t1_counter >> 8) & 0xFF

        elif reg == REG_T1LL:
            return self.t1_latch & 0xFF

        elif reg == REG_T1LH:
            return (self.t1_latch >> 8) & 0xFF

        elif reg == REG_T2CL:
            # Reading T2C-L clears T2 interrupt flag
            self.ifr &= ~IRQ_T2
            self._update_irq()
            return self.t2_counter & 0xFF

        elif reg == REG_T2CH:
            return (self.t2_counter >> 8) & 0xFF

        elif reg == REG_SR:
            # Clear shift register interrupt flag
            self.ifr &= ~IRQ_SR
            self._update_irq()
            return self.sr

        elif reg == REG_ACR:
            return self.acr

        elif reg == REG_PCR:
            return self.pcr

        elif reg == REG_IFR:
            # Bit 7 is set if any enabled interrupt is active
            result = self.ifr
            if self.ifr & self.ier & 0x7F:
                result |= IRQ_ANY
            return result

        elif reg == REG_IER:
            # Bit 7 always reads as 1
            return self.ier | 0x80

        return 0xFF

    def write(self, addr: int, value: int) -> None:
        """Write to VIA register.

        Args:
            addr: Address (only lower 4 bits used)
            value: Value to write
        """
        reg = addr & 0x0F
        value = value & 0xFF

        if reg == REG_ORB:
            self.orb = value
            # Clear CB1/CB2 interrupt flags
            self.ifr &= ~(IRQ_CB1 | IRQ_CB2)
            self._update_irq()
            if self.port_b_write_callback:
                self.port_b_write_callback(self._get_port_b_output())

        elif reg == REG_ORA or reg == REG_ORA_NHS:
            self.ora = value
            if reg == REG_ORA:
                # Clear CA1/CA2 interrupt flags
                self.ifr &= ~(IRQ_CA1 | IRQ_CA2)
                self._update_irq()
            if self.port_a_write_callback:
                self.port_a_write_callback(self._get_port_a_output())

        elif reg == REG_DDRB:
            self.ddrb = value
            if self.port_b_write_callback:
                self.port_b_write_callback(self._get_port_b_output())

        elif reg == REG_DDRA:
            self.ddra = value
            if self.port_a_write_callback:
                self.port_a_write_callback(self._get_port_a_output())

        elif reg == REG_T1CL:
            # Write to T1 low latch only (doesn't start timer)
            self.t1_latch = (self.t1_latch & 0xFF00) | value

        elif reg == REG_T1CH:
            # Write to T1 high latch and counter, starts timer
            self.t1_latch = (self.t1_latch & 0x00FF) | (value << 8)
            self.t1_counter = self.t1_latch
            self.t1_running = True
            # Clear T1 interrupt flag
            self.ifr &= ~IRQ_T1
            self._update_irq()
            # Reset PB7 state if in output mode
            if self.acr & ACR_T1_PB7_OUTPUT:
                self.t1_pb7_state = False

        elif reg == REG_T1LL:
            self.t1_latch = (self.t1_latch & 0xFF00) | value

        elif reg == REG_T1LH:
            self.t1_latch = (self.t1_latch & 0x00FF) | (value << 8)
            # Clear T1 interrupt flag
            self.ifr &= ~IRQ_T1
            self._update_irq()

        elif reg == REG_T2CL:
            # Write to T2 low latch only
            self.t2_latch_low = value

        elif reg == REG_T2CH:
            # Write to T2 high counter and load low from latch, starts timer
            self.t2_counter = (value << 8) | self.t2_latch_low
            self.t2_running = True
            # Clear T2 interrupt flag
            self.ifr &= ~IRQ_T2
            self._update_irq()

        elif reg == REG_SR:
            self.sr = value
            # Start shift operation
            self.sr_counter = 8
            # Clear SR interrupt flag
            self.ifr &= ~IRQ_SR
            self._update_irq()

        elif reg == REG_ACR:
            self.acr = value

        elif reg == REG_PCR:
            self.pcr = value
            self._update_ca2_output()
            self._update_cb2_output()

        elif reg == REG_IFR:
            # Writing 1 to a bit clears that interrupt flag
            self.ifr &= ~(value & 0x7F)
            self._update_irq()

        elif reg == REG_IER:
            if value & 0x80:
                # Set mode: set bits where value has 1
                self.ier |= (value & 0x7F)
            else:
                # Clear mode: clear bits where value has 1
                self.ier &= ~(value & 0x7F)
            self._update_irq()

    def tick(self, cycles: int = 1) -> None:
        """Advance VIA state by specified number of CPU cycles.

        Args:
            cycles: Number of cycles to advance
        """
        # Update Timer 1
        if self.t1_running:
            if self.t1_counter <= cycles:
                # Timer 1 underflow
                underflows = 1 + (cycles - self.t1_counter - 1) // (self.t1_latch + 1)

                if self.acr & ACR_T1_CONTINUOUS:
                    # Continuous mode - reload from latch
                    remaining = cycles - self.t1_counter - 1
                    self.t1_counter = self.t1_latch - (remaining % (self.t1_latch + 1))
                else:
                    # One-shot mode - stop timer
                    self.t1_counter = 0xFFFF - (cycles - self.t1_counter - 1)
                    self.t1_running = False

                # Set T1 interrupt flag
                self.ifr |= IRQ_T1
                self._update_irq()

                # Toggle PB7 if in output mode (odd underflows toggle, even don't)
                if self.acr & ACR_T1_PB7_OUTPUT and (underflows & 1):
                    self.t1_pb7_state = not self.t1_pb7_state
            else:
                self.t1_counter -= cycles

        # Update Timer 2 (if not in pulse counting mode)
        if self.t2_running and not (self.acr & ACR_T2_COUNT_PB6):
            if self.t2_counter <= cycles:
                # Timer 2 underflow (one-shot only)
                self.t2_counter = 0xFFFF - (cycles - self.t2_counter - 1)
                self.t2_running = False

                # Set T2 interrupt flag
                self.ifr |= IRQ_T2
                self._update_irq()
            else:
                self.t2_counter -= cycles

    def set_ca1(self, state: bool) -> None:
        """Set CA1 input line state.

        Args:
            state: New line state (True = high, False = low)
        """
        edge_detected = False
        if self.pcr & PCR_CA1_POSITIVE:
            # Positive edge trigger
            edge_detected = state and not self._ca1_prev
        else:
            # Negative edge trigger
            edge_detected = not state and self._ca1_prev

        if edge_detected:
            self.ifr |= IRQ_CA1
            self._update_irq()
            # Latch Port A if enabled
            if self.acr & ACR_PA_LATCH:
                self.ira = self._read_port_a_pins()

        # Update previous state for next edge detection
        self._ca1_prev = state
        self.ca1 = state

    def set_ca2(self, state: bool) -> None:
        """Set CA2 input line state (only effective in input mode).

        Args:
            state: New line state
        """
        ca2_mode = (self.pcr & PCR_CA2_MASK) >> PCR_CA2_SHIFT

        # Only process as input if in input mode (modes 0-3)
        if ca2_mode < 4:
            edge_detected = False
            if ca2_mode & 0x01:
                # Positive edge
                edge_detected = state and not self._ca2_prev
            else:
                # Negative edge
                edge_detected = not state and self._ca2_prev

            if edge_detected:
                self.ifr |= IRQ_CA2
                self._update_irq()

        # Update previous state for next edge detection
        self._ca2_prev = state
        self.ca2 = state

    def set_cb1(self, state: bool) -> None:
        """Set CB1 input line state.

        Args:
            state: New line state
        """
        edge_detected = False
        if self.pcr & PCR_CB1_POSITIVE:
            # Positive edge trigger
            edge_detected = state and not self._cb1_prev
        else:
            # Negative edge trigger
            edge_detected = not state and self._cb1_prev

        if edge_detected:
            self.ifr |= IRQ_CB1
            self._update_irq()
            # Latch Port B if enabled
            if self.acr & ACR_PB_LATCH:
                self.irb = self._read_port_b_pins()

        # Update previous state for next edge detection
        self._cb1_prev = state
        self.cb1 = state

    def set_cb2(self, state: bool) -> None:
        """Set CB2 input line state (only effective in input mode).

        Args:
            state: New line state
        """
        cb2_mode = (self.pcr & PCR_CB2_MASK) >> PCR_CB2_SHIFT

        # Only process as input if in input mode (modes 0-3)
        if cb2_mode < 4:
            edge_detected = False
            if cb2_mode & 0x01:
                # Positive edge
                edge_detected = state and not self._cb2_prev
            else:
                # Negative edge
                edge_detected = not state and self._cb2_prev

            if edge_detected:
                self.ifr |= IRQ_CB2
                self._update_irq()

        # Update previous state for next edge detection
        self._cb2_prev = state
        self.cb2 = state

    def get_ca2(self) -> bool:
        """Get CA2 output state (when in output mode)."""
        return self.ca2

    def get_cb2(self) -> bool:
        """Get CB2 output state (when in output mode)."""
        return self.cb2

    def _read_port_a(self) -> int:
        """Read Port A value."""
        if self.acr & ACR_PA_LATCH:
            # Latched mode - return latched value for inputs
            input_bits = self.ira & ~self.ddra
        else:
            # Non-latched mode - read pins directly
            input_bits = self._read_port_a_pins() & ~self.ddra

        output_bits = self.ora & self.ddra
        return input_bits | output_bits

    def _read_port_b(self) -> int:
        """Read Port B value."""
        if self.acr & ACR_PB_LATCH:
            # Latched mode
            input_bits = self.irb & ~self.ddrb
        else:
            # Non-latched mode
            input_bits = self._read_port_b_pins() & ~self.ddrb

        output_bits = self.orb & self.ddrb
        result = input_bits | output_bits

        # PB7 may be controlled by Timer 1
        if self.acr & ACR_T1_PB7_OUTPUT:
            if self.t1_pb7_state:
                result |= 0x80
            else:
                result &= ~0x80

        return result

    def _read_port_a_pins(self) -> int:
        """Read actual Port A pin states from external hardware."""
        if self.port_a_read_callback:
            return self.port_a_read_callback()
        return 0xFF  # Default: all high (pull-ups)

    def _read_port_b_pins(self) -> int:
        """Read actual Port B pin states from external hardware."""
        if self.port_b_read_callback:
            return self.port_b_read_callback()
        return 0xFF  # Default: all high

    def _get_port_a_output(self) -> int:
        """Get the output value being driven on Port A."""
        return self.ora & self.ddra

    def _get_port_b_output(self) -> int:
        """Get the output value being driven on Port B."""
        result = self.orb & self.ddrb
        # PB7 may be controlled by Timer 1
        if self.acr & ACR_T1_PB7_OUTPUT:
            if self.ddrb & 0x80:  # Only if PB7 is output
                if self.t1_pb7_state:
                    result |= 0x80
                else:
                    result &= ~0x80
        return result

    def _update_ca2_output(self) -> None:
        """Update CA2 output based on PCR settings."""
        ca2_mode = (self.pcr & PCR_CA2_MASK) >> PCR_CA2_SHIFT
        if ca2_mode >= 6:
            # Manual output mode
            self.ca2 = bool(ca2_mode & 0x01)

    def _update_cb2_output(self) -> None:
        """Update CB2 output based on PCR settings."""
        cb2_mode = (self.pcr & PCR_CB2_MASK) >> PCR_CB2_SHIFT
        if cb2_mode >= 6:
            # Manual output mode
            self.cb2 = bool(cb2_mode & 0x01)

    def _update_irq(self) -> None:
        """Update IRQ output based on IFR and IER."""
        irq_active = bool(self.ifr & self.ier & 0x7F)
        if self.irq_callback:
            self.irq_callback(irq_active)
