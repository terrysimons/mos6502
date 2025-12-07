#!/usr/bin/env python3
"""CIA2 (Complex Interface Adapter - MOS 6526) at $DD00-$DDFF.

Handles:
- VIC bank selection (Port A bits 0-1)
- Serial bus (Port A bits 2-7)
- User port (Port B)
- Timer A and Timer B with multiple clock sources
- Time-of-Day (TOD) clock
- Serial shift register
- NMI generation (directly to CPU)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU

log = logging.getLogger("c64")


class CIA2:
    """CIA2 (Complex Interface Adapter) at $DD00-$DDFF.

    Handles:
    - VIC bank selection (Port A bits 0-1)
    - Serial bus (Port A bits 2-7)
    - User port (Port B)
    - Timer A and Timer B with multiple clock sources
    - Time-of-Day (TOD) clock
    - Serial shift register
    - NMI generation (directly to CPU)
    """

    def __init__(self, cpu: MOS6502CPU) -> None:
        # 16 registers, mirrored through $DD00–$DD0F
        self.regs = [0x00] * 16

        # Reference to CPU for NMI signaling
        self.cpu = cpu

        # Port A: VIC bank selection + serial bus
        # Bits 0-1: VIC bank (active low, inverted)
        #   %00 = Bank 3 ($C000-$FFFF)
        #   %01 = Bank 2 ($8000-$BFFF)
        #   %10 = Bank 1 ($4000-$7FFF)
        #   %11 = Bank 0 ($0000-$3FFF) - default
        # Bits 2-7: Serial bus control
        self.port_a = 0x03  # Default: VIC bank 0 (bits 0-1 = %11, inverted = %00)
        self.ddr_a = 0x3F   # Default: lower 6 bits output

        # Port B: User port
        self.port_b = 0xFF
        self.ddr_b = 0x00   # Default: all inputs

        # Timer A state
        self.timer_a_counter = 0xFFFF
        self.timer_a_latch = 0xFFFF
        self.timer_a_running = False
        self.timer_a_oneshot = False
        self.timer_a_pb6_mode = 0
        self.timer_a_cnt_mode = False
        self.timer_a_underflowed = False
        self.pb6_output_state = False  # PB6 toggle flip-flop state
        self.pb6_pulse_cycles = 0      # Cycles remaining for PB6 pulse output

        # Timer B state
        self.timer_b_counter = 0xFFFF
        self.timer_b_latch = 0xFFFF
        self.timer_b_running = False
        self.timer_b_oneshot = False
        self.timer_b_pb7_mode = 0
        self.timer_b_input_mode = 0
        self.pb7_output_state = False  # PB7 toggle flip-flop state
        self.pb7_pulse_cycles = 0      # Cycles remaining for PB7 pulse output

        # Interrupt state
        self.icr_data = 0x00
        self.icr_mask = 0x00

        # Time-of-Day (TOD) clock
        self.tod_10ths = 0x00
        self.tod_sec = 0x00
        self.tod_min = 0x00
        self.tod_hr = 0x00

        # TOD alarm
        self.alarm_10ths = 0x00
        self.alarm_sec = 0x00
        self.alarm_min = 0x00
        self.alarm_hr = 0x00

        # TOD control
        self.tod_running = True
        self.tod_latched = False
        self.tod_latch = [0, 0, 0, 0]
        self.tod_write_alarm = False
        self.tod_50hz = False
        self.tod_cycles = 0
        self.tod_cycles_per_tick = 98525

        # Serial shift register
        self.sdr = 0x00
        self.sdr_bits_remaining = 0
        self.sdr_output_mode = False

        # CNT and FLAG pins
        self.cnt_pin = True
        self.cnt_last = True
        self.flag_pin = True

        # Reference to other CIA for FLAG pin cross-triggering (IEC bus simulation)
        self.other_cia = None

        # IEC bus reference (optional - if None, use loopback simulation)
        self.iec_bus = None

        # Track last CPU cycle count for timer updates
        self.last_cycle_count = 0

    def set_other_cia(self, other_cia) -> None:
        """Set reference to the other CIA for FLAG pin cross-triggering."""
        self.other_cia = other_cia

    def set_iec_bus(self, iec_bus) -> None:
        """Set reference to the IEC bus for serial communication.

        Args:
            iec_bus: IECBus instance connecting C64 to drives
        """
        self.iec_bus = iec_bus

    def trigger_flag_interrupt(self) -> None:
        """Trigger FLAG pin interrupt (bit 4 of ICR).

        Called by the other CIA when serial data is transmitted,
        simulating the IEC bus connection between CIA1 and CIA2.
        """
        # Set FLAG interrupt flag (bit 4)
        self.icr_data |= 0x10
        # If FLAG interrupts are enabled, signal CPU NMI (CIA2 generates NMI, not IRQ)
        if self.icr_mask & 0x10:
            self.cpu.nmi_pending = True

    def get_vic_bank(self) -> int:
        """Get the current VIC bank address (0x0000, 0x4000, 0x8000, or 0xC000).

        The VIC bank is determined by bits 0-1 of Port A, inverted.
        """
        bank_bits = (~self.port_a) & 0x03
        return bank_bits * 0x4000

    def read(self, addr) -> int:
        reg = addr & 0x0F

        # Port A ($DD00)
        if reg == 0x00:
            # Read Port A with IEC serial bus state
            # Bits 0-1: VIC bank (directly from port)
            # Bit 2: RS-232 TXD (directly from port)
            # Bit 3: ATN OUT (directly to bus)
            # Bit 4: CLK OUT (directly to bus, directly to CLK IN via loopback)
            # Bit 5: DATA OUT (directly to bus, directly to DATA IN via loopback)
            # Bit 6: CLK IN (directly from bus - reflects CLK OUT when no device)
            # Bit 7: DATA IN (directly from bus - reflects DATA OUT when no device)

            # Start with output bits from port_a, input bits pulled high
            result = (self.port_a & self.ddr_a) | (~self.ddr_a & 0xFF)

            iec_bus = self.iec_bus
            if iec_bus is not None:
                # Update IEC bus state before reading to ensure we see
                # the drive's current output (especially DATA line for ATN ack)
                iec_bus.update()
                # Use real IEC bus state from connected devices
                bus_input = iec_bus.get_c64_input()
                # Apply bus state to input bits (6 and 7) in one operation
                # Mask out bits that are inputs, then OR in bus state for those bits
                input_mask = ~self.ddr_a & 0xC0  # Which of bits 6-7 are inputs
                result = (result & ~input_mask) | (bus_input & input_mask)

            else:
                # IEC bus loopback for input bits (when configured as input)
                # No devices connected - outputs loop back to inputs.
                # The IEC bus uses open-collector logic with a 7406 inverter:
                # - Port bit = 1 → inverted → drives bus line LOW
                # - Port bit = 0 → inverted → releases bus line (goes HIGH)
                # Reference: https://www.c64-wiki.com/wiki/Serial_Port
                if not (self.ddr_a & 0x40):  # Bit 6 is input
                    if self.port_a & 0x10:  # CLK OUT is 1 (driving bus LOW)
                        result &= ~0x40  # CLK IN goes LOW
                    # else: CLK OUT is 0 (bus released), CLK IN stays HIGH
                if not (self.ddr_a & 0x80):  # Bit 7 is input
                    if self.port_a & 0x20:  # DATA OUT is 1 (driving bus LOW)
                        result &= ~0x80  # DATA IN goes LOW
                    # else: DATA OUT is 0 (bus released), DATA IN stays HIGH

            return result

        # Port B ($DD01) - User port
        if reg == 0x01:
            result = (self.port_b & self.ddr_b) | (~self.ddr_b & 0xFF)

            # Apply timer outputs to PB6/PB7 when enabled
            # Timer A output to PB6 (if pb6_mode bit 0 is set = CRA bit 1)
            if self.timer_a_pb6_mode & 0x01:
                if self.pb6_output_state or self.pb6_pulse_cycles > 0:
                    result |= 0x40
                else:
                    result &= ~0x40

            # Timer B output to PB7 (if pb7_mode bit 0 is set = CRB bit 1)
            if self.timer_b_pb7_mode & 0x01:
                if self.pb7_output_state or self.pb7_pulse_cycles > 0:
                    result |= 0x80
                else:
                    result &= ~0x80

            return result

        # Port A DDR ($DD02)
        if reg == 0x02:
            return self.ddr_a

        # Port B DDR ($DD03)
        if reg == 0x03:
            return self.ddr_b

        # Timer A Low Byte ($DD04)
        if reg == 0x04:
            return self.timer_a_counter & 0xFF

        # Timer A High Byte ($DD05)
        if reg == 0x05:
            return (self.timer_a_counter >> 8) & 0xFF

        # Timer B Low Byte ($DD06)
        if reg == 0x06:
            return self.timer_b_counter & 0xFF

        # Timer B High Byte ($DD07)
        if reg == 0x07:
            return (self.timer_b_counter >> 8) & 0xFF

        # TOD 1/10 Seconds ($DD08)
        if reg == 0x08:
            if self.tod_latched:
                result = self.tod_latch[0]
                self.tod_latched = False
            else:
                result = self.tod_10ths
            return result

        # TOD Seconds ($DD09)
        if reg == 0x09:
            if self.tod_latched:
                return self.tod_latch[1]
            return self.tod_sec

        # TOD Minutes ($DD0A)
        if reg == 0x0A:
            if self.tod_latched:
                return self.tod_latch[2]
            return self.tod_min

        # TOD Hours ($DD0B)
        if reg == 0x0B:
            if not self.tod_latched:
                self.tod_latched = True
                self.tod_latch = [self.tod_10ths, self.tod_sec, self.tod_min, self.tod_hr]
            return self.tod_latch[3]

        # Serial Data Register ($DD0C)
        if reg == 0x0C:
            return self.sdr

        # Interrupt Control Register (ICR) ($DD0D)
        if reg == 0x0D:
            result = self.icr_data
            if result & self.icr_mask:
                result |= 0x80
            self.icr_data = 0x00
            # Clear CPU NMI line - on real 6526, reading ICR de-asserts /NMI
            self.cpu.nmi_pending = False
            return result

        # Control Register A ($DD0E)
        if reg == 0x0E:
            result = 0x00
            if self.timer_a_running:
                result |= 0x01
            result |= (self.timer_a_pb6_mode & 0x03) << 1
            if self.timer_a_oneshot:
                result |= 0x08
            if self.timer_a_cnt_mode:
                result |= 0x20
            if self.sdr_output_mode:
                result |= 0x40
            if self.tod_50hz:
                result |= 0x80
            return result

        # Control Register B ($DD0F)
        if reg == 0x0F:
            result = 0x00
            if self.timer_b_running:
                result |= 0x01
            result |= (self.timer_b_pb7_mode & 0x03) << 1
            if self.timer_b_oneshot:
                result |= 0x08
            result |= (self.timer_b_input_mode & 0x03) << 5
            if self.tod_write_alarm:
                result |= 0x80
            return result

        return self.regs[reg]

    def write(self, addr, value) -> None:
        reg = addr & 0x0F
        self.regs[reg] = value

        # Port A ($DD00) - VIC bank + serial bus
        if reg == 0x00:
            old_port_a = self.port_a
            self.port_a = value
            if old_port_a != value:
                new_bank = self.get_vic_bank()
                log.debug(f"CIA2 Port A WRITE: ${value:02X}, VIC bank=${new_bank:04X}")
                # Immediately update IEC bus when serial lines change
                if self.iec_bus is not None:
                    self.iec_bus.update()

        # Port B ($DD01) - User port
        if reg == 0x01:
            self.port_b = value

        # Port A DDR ($DD02)
        if reg == 0x02:
            old_ddr_a = self.ddr_a
            self.ddr_a = value
            # DDR change affects IEC bus outputs
            if old_ddr_a != value and self.iec_bus is not None:
                self.iec_bus.update()

        # Port B DDR ($DD03)
        if reg == 0x03:
            self.ddr_b = value

        # Timer A Low Byte ($DD04)
        if reg == 0x04:
            self.timer_a_latch = (self.timer_a_latch & 0xFF00) | value

        # Timer A High Byte ($DD05)
        if reg == 0x05:
            self.timer_a_latch = (self.timer_a_latch & 0x00FF) | (value << 8)
            # 6526 behavior: Writing high byte while timer stopped loads latch into counter
            if not self.timer_a_running:
                self.timer_a_counter = self.timer_a_latch

        # Timer B Low Byte ($DD06)
        if reg == 0x06:
            self.timer_b_latch = (self.timer_b_latch & 0xFF00) | value

        # Timer B High Byte ($DD07)
        if reg == 0x07:
            self.timer_b_latch = (self.timer_b_latch & 0x00FF) | (value << 8)
            # 6526 behavior: Writing high byte while timer stopped loads latch into counter
            if not self.timer_b_running:
                self.timer_b_counter = self.timer_b_latch

        # TOD 1/10 Seconds ($DD08)
        if reg == 0x08:
            if self.tod_write_alarm:
                self.alarm_10ths = value & 0x0F
            else:
                self.tod_10ths = value & 0x0F
                self.tod_running = True

        # TOD Seconds ($DD09)
        if reg == 0x09:
            if self.tod_write_alarm:
                self.alarm_sec = value & 0x7F
            else:
                self.tod_sec = value & 0x7F

        # TOD Minutes ($DD0A)
        if reg == 0x0A:
            if self.tod_write_alarm:
                self.alarm_min = value & 0x7F
            else:
                self.tod_min = value & 0x7F

        # TOD Hours ($DD0B)
        if reg == 0x0B:
            if self.tod_write_alarm:
                self.alarm_hr = value
            else:
                self.tod_hr = value
                self.tod_running = False

        # Serial Data Register ($DD0C)
        if reg == 0x0C:
            self.sdr = value
            if self.sdr_output_mode:
                self.sdr_bits_remaining = 8
                # Trigger FLAG interrupt on the other CIA (IEC bus simulation)
                # This simulates the start of serial transmission
                if self.other_cia is not None:
                    self.other_cia.trigger_flag_interrupt()

        # Interrupt Control Register ($DD0D)
        if reg == 0x0D:
            if value & 0x80:
                # Set mask bits
                new_bits = value & 0x1F
                self.icr_mask |= new_bits
                # 6526 behavior: If enabling a mask bit and the corresponding
                # ICR data bit is already set, fire interrupt immediately
                if self.icr_data & new_bits:
                    self.cpu.nmi_pending = True  # CIA2 generates NMI
            else:
                # Clear mask bits
                self.icr_mask &= ~(value & 0x1F)

        # Control Register A ($DD0E)
        if reg == 0x0E:
            old_running = self.timer_a_running
            self.timer_a_running = bool(value & 0x01)
            # Rising edge of bit 0 sets the PB6 toggle flip-flop high
            if self.timer_a_running and not old_running:
                self.pb6_output_state = True
            self.timer_a_pb6_mode = (value >> 1) & 0x03
            self.timer_a_oneshot = bool(value & 0x08)
            if value & 0x10:
                self.timer_a_counter = self.timer_a_latch
            self.timer_a_cnt_mode = bool(value & 0x20)
            # Bit 6: Serial port direction (0=input, 1=output)
            old_sdr_output_mode = self.sdr_output_mode
            self.sdr_output_mode = bool(value & 0x40)
            # If transitioning to output mode, trigger FLAG on other CIA
            # This handles case where SDR is written before output mode is enabled
            if self.sdr_output_mode and not old_sdr_output_mode:
                if self.other_cia is not None:
                    self.other_cia.trigger_flag_interrupt()
            self.tod_50hz = bool(value & 0x80)
            if self.tod_50hz:
                self.tod_cycles_per_tick = 98525
            else:
                self.tod_cycles_per_tick = 102273

        # Control Register B ($DD0F)
        if reg == 0x0F:
            old_running = self.timer_b_running
            self.timer_b_running = bool(value & 0x01)
            # Rising edge of bit 0 sets the PB7 toggle flip-flop high
            if self.timer_b_running and not old_running:
                self.pb7_output_state = True
            self.timer_b_pb7_mode = (value >> 1) & 0x03
            self.timer_b_oneshot = bool(value & 0x08)
            if value & 0x10:
                self.timer_b_counter = self.timer_b_latch
            self.timer_b_input_mode = (value >> 5) & 0x03
            self.tod_write_alarm = bool(value & 0x80)

    def update(self) -> None:
        """Update CIA2 timers and TOD based on CPU cycles."""
        cycles_elapsed = self.cpu.cycles_executed - self.last_cycle_count
        self.last_cycle_count = self.cpu.cycles_executed

        # Fast path: Both timers running with no underflow, TOD not running,
        # no PB6/PB7 pulse cycles, and timers not in special modes
        # This is the common case during normal operation
        timer_a_counter = self.timer_a_counter
        timer_b_counter = self.timer_b_counter
        if (self.timer_a_running and not self.timer_a_cnt_mode and
            timer_a_counter > cycles_elapsed and
            self.timer_b_running and self.timer_b_input_mode == 0 and
            timer_b_counter > cycles_elapsed and
            not self.tod_running and
            self.pb6_pulse_cycles == 0 and self.pb7_pulse_cycles == 0):
            # Simple countdown - no underflows, no special handling needed
            self.timer_a_counter = timer_a_counter - cycles_elapsed
            self.timer_b_counter = timer_b_counter - cycles_elapsed
            self.timer_a_underflowed = False
            return

        self.timer_a_underflowed = False
        timer_a_underflow_count = 0

        # Update Timer A
        if self.timer_a_running and cycles_elapsed > 0 and not self.timer_a_cnt_mode:
            if self.timer_a_counter >= cycles_elapsed:
                self.timer_a_counter -= cycles_elapsed
            else:
                timer_a_underflow_count = (cycles_elapsed - self.timer_a_counter) // (self.timer_a_latch + 1) + 1
                self.timer_a_underflowed = True

                if self.timer_a_oneshot:
                    self.timer_a_counter = 0
                    self.timer_a_running = False
                else:
                    self.timer_a_counter = self.timer_a_latch - ((cycles_elapsed - self.timer_a_counter - 1) % (self.timer_a_latch + 1))

                self.icr_data |= 0x01
                if self.icr_mask & 0x01:
                    # CIA2 generates NMI, not IRQ
                    self.cpu.nmi_pending = True

                # Handle SDR (Serial Data Register) shifting
                # Timer A underflows clock the SDR when in output mode
                if self.sdr_output_mode and self.sdr_bits_remaining > 0:
                    # Each Timer A underflow shifts one bit
                    bits_to_shift = min(timer_a_underflow_count, self.sdr_bits_remaining)
                    self.sdr_bits_remaining -= bits_to_shift
                    if self.sdr_bits_remaining == 0:
                        # All 8 bits shifted - trigger SDR interrupt (bit 3)
                        self.icr_data |= 0x08
                        if self.icr_mask & 0x08:
                            # CIA2 generates NMI, not IRQ
                            self.cpu.nmi_pending = True
                        # Also trigger FLAG interrupt on the other CIA (IEC bus simulation)
                        if self.other_cia is not None:
                            self.other_cia.trigger_flag_interrupt()

                # Handle PB6 timer output
                if self.timer_a_pb6_mode & 0x02:
                    # Toggle mode - flip PB6 state on each underflow
                    for _ in range(timer_a_underflow_count):
                        self.pb6_output_state = not self.pb6_output_state
                else:
                    # Pulse mode - output high for one cycle per underflow
                    self.pb6_pulse_cycles = 1

        # Decrement PB6 pulse cycles
        if self.pb6_pulse_cycles > 0:
            self.pb6_pulse_cycles = max(0, self.pb6_pulse_cycles - cycles_elapsed)

        # Update Timer B
        if self.timer_b_running:
            decrement = 0
            if self.timer_b_input_mode == 0:
                decrement = cycles_elapsed
            elif self.timer_b_input_mode == 2:
                decrement = timer_a_underflow_count
            elif self.timer_b_input_mode == 3:
                if self.cnt_pin:
                    decrement = timer_a_underflow_count

            if decrement > 0:
                if self.timer_b_counter >= decrement:
                    self.timer_b_counter -= decrement
                else:
                    if self.timer_b_oneshot:
                        self.timer_b_counter = 0
                        self.timer_b_running = False
                    else:
                        if self.timer_b_input_mode == 0:
                            self.timer_b_counter = self.timer_b_latch - ((decrement - self.timer_b_counter - 1) % (self.timer_b_latch + 1))
                        else:
                            self.timer_b_counter = self.timer_b_latch

                    self.icr_data |= 0x02
                    if self.icr_mask & 0x02:
                        self.cpu.nmi_pending = True

                    # Handle PB7 timer output
                    # pb7_mode bit 0 (CRB bit 1): enable output
                    # pb7_mode bit 1 (CRB bit 2): 0=pulse, 1=toggle
                    if self.timer_b_pb7_mode & 0x02:
                        # Toggle mode - flip PB7 state on underflow
                        self.pb7_output_state = not self.pb7_output_state
                    else:
                        # Pulse mode - output high for one cycle
                        self.pb7_pulse_cycles = 1

        # Decrement PB7 pulse cycles
        if self.pb7_pulse_cycles > 0:
            self.pb7_pulse_cycles = max(0, self.pb7_pulse_cycles - cycles_elapsed)

        # Update TOD clock
        if self.tod_running:
            self.tod_cycles += cycles_elapsed
            while self.tod_cycles >= self.tod_cycles_per_tick:
                self.tod_cycles -= self.tod_cycles_per_tick
                self._tick_tod()

    def _tick_tod(self) -> None:
        """Advance TOD clock by 1/10 second."""
        self.tod_10ths = (self.tod_10ths + 1) & 0x0F
        if self.tod_10ths > 9:
            self.tod_10ths = 0

            sec_lo = (self.tod_sec & 0x0F) + 1
            sec_hi = (self.tod_sec >> 4) & 0x07
            if sec_lo > 9:
                sec_lo = 0
                sec_hi += 1
            if sec_hi > 5:
                sec_hi = 0

                min_lo = (self.tod_min & 0x0F) + 1
                min_hi = (self.tod_min >> 4) & 0x07
                if min_lo > 9:
                    min_lo = 0
                    min_hi += 1
                if min_hi > 5:
                    min_hi = 0

                    hr_lo = (self.tod_hr & 0x0F) + 1
                    hr_hi = (self.tod_hr >> 4) & 0x01
                    pm = bool(self.tod_hr & 0x80)

                    if hr_lo > 9:
                        hr_lo = 0
                        hr_hi += 1

                    hr_val = hr_hi * 10 + hr_lo
                    if hr_val == 12:
                        pm = not pm
                    elif hr_val == 13:
                        hr_lo = 1
                        hr_hi = 0

                    self.tod_hr = (0x80 if pm else 0x00) | (hr_hi << 4) | hr_lo

                self.tod_min = (min_hi << 4) | min_lo
            self.tod_sec = (sec_hi << 4) | sec_lo

        # Check for alarm match
        if (self.tod_10ths == self.alarm_10ths and
            self.tod_sec == self.alarm_sec and
            self.tod_min == self.alarm_min and
            self.tod_hr == self.alarm_hr):
            self.icr_data |= 0x04
            if self.icr_mask & 0x04:
                self.cpu.nmi_pending = True
