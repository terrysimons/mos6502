#!/usr/bin/env python3
"""CIA1 (Complex Interface Adapter - MOS 6526) at $DC00-$DCFF.

Handles:
- Keyboard matrix scanning (Port A/B)
- Joystick ports
- Timer A and Timer B with multiple clock sources
- Time-of-Day (TOD) clock
- Serial shift register
- IRQ generation
"""


from mos6502.compat import logging
import threading
from mos6502.compat import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU

log = logging.getLogger("c64")

# Debug flags - set to True to enable verbose logging
DEBUG_CIA = False      # CIA register reads/writes
DEBUG_KEYBOARD = False # Keyboard events

# Joystick bit masks (active low: 0 = pressed, 1 = released)
# Reference: https://www.c64-wiki.com/wiki/Joystick
JOYSTICK_UP = 0x01      # Bit 0
JOYSTICK_DOWN = 0x02    # Bit 1
JOYSTICK_LEFT = 0x04    # Bit 2
JOYSTICK_RIGHT = 0x08   # Bit 3
JOYSTICK_FIRE = 0x10    # Bit 4
JOYSTICK_BITS_MASK = 0x1F  # Bits 0-4 (joystick only, 5-7 are keyboard)

# Paddle fire button bit masks (active low: 0 = pressed, 1 = released)
# Note: Paddle fire buttons use DIFFERENT bits than joystick fire!
# Reference: https://www.c64-wiki.com/wiki/Paddle
PADDLE_1_FIRE = 0x04    # Bit 2 (same physical bit as joystick left)
PADDLE_2_FIRE = 0x08    # Bit 3 (same physical bit as joystick right)

# 1351 Mouse button bit masks (active low: 0 = pressed, 1 = released)
# The 1351 mouse buttons are directly wired to joystick-compatible pins
# Reference: https://www.c64-wiki.com/wiki/Mouse_1351
MOUSE_LEFT_BUTTON = 0x10   # Bit 4 (directly wired to fire button pin)
MOUSE_RIGHT_BUTTON = 0x01  # Bit 0 (directly wired to up direction pin)

# Lightpen button bit mask (active low: 0 = pressed, 1 = released)
# Lightpen only works on port 1, button triggers same as joystick fire
# Reference: https://www.c64-wiki.com/wiki/Light_pen
LIGHTPEN_BUTTON = 0x10  # Bit 4 (directly wired to fire button pin, port 1 only)

# Active-low button state constants
# C64 control port buttons use active-low logic
BUTTON_PRESSED = 0x00        # Bit is low when button is pressed
BUTTON_RELEASED = 0x01       # Bit is high when button is released (per-bit, not mask)
ALL_BUTTONS_RELEASED = 0xFF  # All bits high = no buttons pressed


class CIA1:
    """CIA1 (Complex Interface Adapter) at $DC00-$DCFF.

    Handles:
    - Keyboard matrix scanning (Port A/B)
    - Joystick ports
    - Timer A and Timer B with multiple clock sources
    - Time-of-Day (TOD) clock
    - Serial shift register
    - IRQ generation
    """

    def __init__(self, cpu: "MOS6502CPU") -> None:
        # 16 registers, mirrored through $DC00–$DC0F
        self.regs = [0x00] * 16

        # Reference to CPU for IRQ signaling
        self.cpu = cpu

        # Keyboard matrix: 8 rows x 8 columns
        # keyboard_matrix[row] = byte where each bit is a column
        # 0 = key pressed (active low), 1 = key released
        self.keyboard_matrix = [0xFF] * 8

        # Thread-safe keyboard access
        # Main thread (pygame/terminal) writes key presses
        # CPU thread reads during CIA register access
        self._keyboard_lock = threading.Lock()

        # Cached keyboard matrix snapshot for fast reads
        # Updated only when keys change (invalidated by press/release)
        self._kb_matrix_cache: list = [0xFF] * 8
        self._kb_cache_valid = True  # Start valid since matrix is all 0xFF

        # Pre-computed column results for each possible port_a value
        # _column_cache[port_a] = resulting column byte for Port B read
        # This avoids the double loop on every Port B read
        # Invalidated when keyboard matrix changes
        self._column_cache: dict = {}
        self._column_cache_valid = False  # Will be populated on first read

        # Track key press times for minimum hold duration
        # Key: (row, col), Value: press timestamp
        self._key_press_times: dict = {}
        self._min_key_hold = 0.012  # 12ms minimum hold (~0.7 frames at 60Hz)

        # Joystick state (active low: 0 = pressed, 1 = released)
        # Port A bits 0-4 (when input): Joystick 2
        # Port B bits 0-4 (when input): Joystick 1
        # Bit 0: Up, Bit 1: Down, Bit 2: Left, Bit 3: Right, Bit 4: Fire
        self.joystick_1 = 0xFF  # All released (bits high)
        self.joystick_2 = 0xFF  # All released (bits high)

        # Port values
        self.port_a = 0xFF  # Rows (written by KERNAL to select which rows to scan)
        self.port_b = 0xFF  # Columns (read by KERNAL to get key states)

        # Data Direction Registers
        # 0 = input, 1 = output
        self.ddr_a = 0xFF   # Port A all outputs (row selection)
        self.ddr_b = 0x00   # Port B all inputs (column sensing)

        # Timer A state
        self.timer_a_counter = 0xFFFF  # 16-bit counter
        self.timer_a_latch = 0xFFFF    # 16-bit latch (reload value)
        self.timer_a_running = False
        self.timer_a_oneshot = False   # One-shot mode (bit 3 of CRA)
        self.timer_a_pb6_mode = 0      # PB6 output mode (bits 1-2 of CRA)
                                       # Bit 0 (CRA bit 1): 1 = output to PB6 enabled
                                       # Bit 1 (CRA bit 2): 0 = pulse, 1 = toggle
        self.timer_a_cnt_mode = False  # Count CNT transitions (bit 5 of CRA)
        self.timer_a_underflowed = False  # Track underflow for Timer B chaining
        self.pb6_output_state = False  # PB6 toggle flip-flop state (for timer A output)
        self.pb6_pulse_cycles = 0      # Cycles remaining for PB6 pulse output

        # Timer B state
        self.timer_b_counter = 0xFFFF
        self.timer_b_latch = 0xFFFF
        self.timer_b_running = False
        self.timer_b_oneshot = False   # One-shot mode (bit 3 of CRB)
        self.timer_b_pb7_mode = 0      # PB7 output mode (bits 1-2 of CRB)
                                       # Bit 0 (CRB bit 1): 1 = output to PB7 enabled
                                       # Bit 1 (CRB bit 2): 0 = pulse, 1 = toggle
        self.pb7_output_state = False  # PB7 toggle flip-flop state (for timer B output)
        self.pb7_pulse_cycles = 0      # Cycles remaining for PB7 pulse output
        self.timer_b_input_mode = 0    # Input mode (bits 5-6 of CRB):
                                       # 0 = count CPU cycles
                                       # 1 = count CNT transitions
                                       # 2 = count Timer A underflows
                                       # 3 = count Timer A underflows when CNT high

        # Interrupt state
        self.icr_data = 0x00      # Interrupt data (which interrupts occurred)
        self.icr_mask = 0x00      # Interrupt mask (which interrupts are enabled)

        # Time-of-Day (TOD) clock
        # TOD counts in BCD format: 1/10 sec, seconds, minutes, hours
        self.tod_10ths = 0x00     # $DC08: 1/10 seconds (0-9 BCD)
        self.tod_sec = 0x00       # $DC09: seconds (0-59 BCD)
        self.tod_min = 0x00       # $DC0A: minutes (0-59 BCD)
        self.tod_hr = 0x00        # $DC0B: hours (1-12 BCD + AM/PM in bit 7)

        # TOD alarm
        self.alarm_10ths = 0x00   # Alarm 1/10 seconds
        self.alarm_sec = 0x00     # Alarm seconds
        self.alarm_min = 0x00     # Alarm minutes
        self.alarm_hr = 0x00      # Alarm hours

        # TOD control
        self.tod_running = True   # TOD clock running
        self.tod_latched = False  # TOD output latched (reading hours latches)
        self.tod_latch = [0, 0, 0, 0]  # Latched TOD values
        self.tod_write_alarm = False  # Write to alarm (bit 7 of CRB)
        self.tod_50hz = False     # 50Hz input (bit 7 of CRA)

        # TOD timing (updated via CPU cycles)
        self.tod_cycles = 0       # Cycles since last TOD tick
        self.tod_cycles_per_tick = 98525  # ~10Hz at 985248 Hz (PAL)

        # Serial shift register
        self.sdr = 0x00           # $DC0C: Serial Data Register
        self.sdr_bits_remaining = 0  # Bits left to shift
        self.sdr_output_mode = False  # True = output, False = input

        # CNT pin state (directly accessible by external hardware)
        self.cnt_pin = True       # CNT pin level (active high)
        self.cnt_last = True      # Last CNT pin state for edge detection

        # FLAG pin (directly accessible by external hardware)
        self.flag_pin = True      # FLAG pin level (directly accessible, directly clears)

        # Reference to other CIA for FLAG pin cross-triggering (IEC bus simulation)
        self.other_cia = None

        # Track last CPU cycle count for timer updates
        self.last_cycle_count = 0

    def set_other_cia(self, other_cia) -> None:
        """Set reference to the other CIA for FLAG pin cross-triggering."""
        self.other_cia = other_cia

    def trigger_flag_interrupt(self) -> None:
        """Trigger FLAG pin interrupt (bit 4 of ICR).

        Called by the other CIA when serial data is transmitted,
        simulating the IEC bus connection between CIA1 and CIA2.
        """
        # Set FLAG interrupt flag (bit 4)
        self.icr_data |= 0x10
        # If FLAG interrupts are enabled, signal CPU IRQ
        if self.icr_mask & 0x10:
            self.cpu.irq_pending = True

    def read(self, addr) -> int:
        reg = addr & 0x0F

        # Use cached keyboard matrix for registers that need it
        # The cache is invalidated when keys are pressed/released, avoiding
        # lock acquisition and copy on every read
        if reg in (0x00, 0x01):
            kb_matrix = self._get_cached_keyboard_matrix()
        else:
            kb_matrix = None

        # Port A ($DC00) — keyboard matrix row selection
        # WRITE: KERNAL writes row selection bits (active low)
        # READ: Returns row bits, with input rows pulled low if keys pressed
        if reg == 0x00:
            # Start with all input row bits HIGH (pulled up externally)
            port_a_ext = 0xFF

            # For input row bits, check if any keys in that row are pressed
            # If a key is pressed in an input row, that row bit goes LOW
            for row in range(8):
                row_is_input = not bool(self.ddr_a & (1 << row))
                if row_is_input:
                    # Check if any key in this row is pressed (using thread-safe snapshot)
                    if kb_matrix[row] != 0xFF:  # Some key pressed in this row
                        port_a_ext &= ~(1 << row)  # Pull this row bit LOW
                        log.info(f"*** PORT A INPUT ROW: row={row} has key pressed, pulling Port A bit {row} LOW, matrix[{row}]=${kb_matrix[row]:02X} ***")

            # Reading Port A respects DDR:
            # - Output bits (ddr_a=1): return port_a value (software-controlled)
            # - Input bits (ddr_a=0): return keyboard/joystick state
            # For input bits, combine keyboard row detection with joystick 2
            # Joystick 2 only uses bits 0-4, bits 5-7 are keyboard-only
            joy2_with_float = (self.joystick_2 & 0x1F) | 0xE0  # Joystick on bits 0-4, bits 5-7 high
            ext_combined = port_a_ext & joy2_with_float  # Combine keyboard rows and joystick

            # IMPORTANT: Joystick switches use wired-AND (active low) - when pressed,
            # they pull the line LOW regardless of DDR setting. The CIA cannot drive
            # a line HIGH if the joystick is grounding it. This is why joystick 2
            # works even when Port A is configured as outputs for keyboard scanning.
            # Reference: https://www.c64-wiki.com/wiki/Joystick
            cia_output = self.port_a & self.ddr_a  # CIA's driven output (for output bits)
            external_input = ext_combined & ~self.ddr_a  # External input (for input bits)

            # Joystick can override output bits (wired-AND: pressed switch pulls low)
            joystick_override = joy2_with_float  # Joystick state for bits 0-4

            # Final result: start with CIA output + external input, then AND with joystick
            # The AND ensures that if joystick is pressed (bit=0), the result is 0
            result = (cia_output | external_input) & joystick_override
            return result

        # Port B ($DC01) — keyboard matrix column sensing
        # READ: KERNAL reads column bits to detect which keys are pressed in selected rows
        # Each column bit is pulled low (0) if any key in that column is pressed in a selected row
        # This is where the keyboard magic happens!
        if reg == 0x01:
            # IMPORTANT: The C64 keyboard matrix is electrically bidirectional
            # Port A bits can be outputs (actively drive row selection) OR inputs (pulled high externally)
            #
            # DDRA bits: 1 = OUTPUT (software controlled), 0 = INPUT (pulled HIGH externally by pull-ups)
            #
            # When DDRA bit = 1 (OUTPUT):
            #   - port_a bit = 0: Row driven LOW (actively selects this row)
            #   - port_a bit = 1: Row driven HIGH (doesn't select this row)
            #
            # When DDRA bit = 0 (INPUT):
            #   - Row is pulled HIGH externally
            #   - Pressed keys can pull the row LOW through the keyboard matrix
            #   - The row line "floats" and keys can affect it
            #
            # This means ALL rows (both output and input) can have their keys detected!
            #
            # Row participates in Port B scanning if its Port A bit is LOW, regardless
            # of whether it's an output or input. The key insight: the KERNAL writes
            # specific bit patterns to Port A to select rows, and we should respect
            # that selection even for input rows.

            # Use optimized column computation - avoids double loop
            keyboard_ext = self._compute_keyboard_columns(self.port_a, kb_matrix)

            # Combine keyboard and joystick 1 inputs (both active low, so AND them)
            # Joystick 1 only affects bits 0-4 (Up, Down, Left, Right, Fire)
            # Bits 5-7 are keyboard-only
            ext = keyboard_ext & (self.joystick_1 | 0xE0)  # Only apply joystick to bits 0-4

            # Mix CIA output vs input:
            # - Output bits (ddr_b=1): CIA drives the line, return port_b value
            # - Input bits (ddr_b=0): External devices drive, return ext (keyboard/joystick) value
            # Note: On real hardware, output bits cannot be pulled low by external devices
            result = (self.port_b & self.ddr_b) | (ext & ~self.ddr_b)

            # Apply timer outputs to PB6/PB7 when enabled
            # Timer A output to PB6 (if pb6_mode bit 0 is set = CRA bit 1)
            if self.timer_a_pb6_mode & 0x01:
                # Timer output overrides normal port behavior on PB6
                if self.pb6_output_state or self.pb6_pulse_cycles > 0:
                    result |= 0x40   # Set PB6 high
                else:
                    result &= ~0x40  # Set PB6 low

            # Timer B output to PB7 (if pb7_mode bit 0 is set = CRB bit 1)
            if self.timer_b_pb7_mode & 0x01:
                # Timer output overrides normal port behavior on PB7
                if self.pb7_output_state or self.pb7_pulse_cycles > 0:
                    result |= 0x80   # Set PB7 high
                else:
                    result &= ~0x80  # Set PB7 low

            if result != 0xFF:  # Only log when a key might be detected
                # Show which row(s) are being actively scanned (output bits driven low)
                rows_scanned = []
                for r in range(8):
                    r_is_output = bool(self.ddr_a & (1 << r))
                    r_driven_low = not bool(self.port_a & (1 << r))
                    if r_is_output and r_driven_low:
                        rows_scanned.append(r)
                rows_str = ",".join(str(r) for r in rows_scanned) if rows_scanned else "none"

                # Show which column bits are low (key detected)
                cols_detected = []
                for c in range(8):
                    if not (result & (1 << c)):
                        cols_detected.append(c)
                cols_str = ",".join(str(c) for c in cols_detected) if cols_detected else "none"

                if DEBUG_CIA:
                    log.info(f"*** CIA1 Port B READ: result=${result:02X}, rows_scanned=[{rows_str}], cols_detected=[{cols_str}], port_a=${self.port_a:02X}, ddr_a=${self.ddr_a:02X}, port_b=${self.port_b:02X}, ddr_b=${self.ddr_b:02X}, keyboard_ext=${keyboard_ext:02X}, joystick_1=${self.joystick_1:02X} ***")
            return result & 0xFF

        # Port A DDR ($DC02)
        if reg == 0x02:
            return self.ddr_a

        # Port B DDR ($DC03)
        if reg == 0x03:
            return self.ddr_b

        # Timer A Low Byte ($DC04)
        if reg == 0x04:
            return self.timer_a_counter & 0xFF

        # Timer A High Byte ($DC05)
        if reg == 0x05:
            return (self.timer_a_counter >> 8) & 0xFF

        # Timer B Low Byte ($DC06)
        if reg == 0x06:
            return self.timer_b_counter & 0xFF

        # Timer B High Byte ($DC07)
        if reg == 0x07:
            return (self.timer_b_counter >> 8) & 0xFF

        # TOD 1/10 Seconds ($DC08)
        if reg == 0x08:
            if self.tod_latched:
                result = self.tod_latch[0]
                # Reading 10ths unlatches TOD
                self.tod_latched = False
            else:
                result = self.tod_10ths
            return result

        # TOD Seconds ($DC09)
        if reg == 0x09:
            if self.tod_latched:
                return self.tod_latch[1]
            return self.tod_sec

        # TOD Minutes ($DC0A)
        if reg == 0x0A:
            if self.tod_latched:
                return self.tod_latch[2]
            return self.tod_min

        # TOD Hours ($DC0B)
        if reg == 0x0B:
            # Reading hours latches all TOD registers
            if not self.tod_latched:
                self.tod_latched = True
                self.tod_latch = [self.tod_10ths, self.tod_sec, self.tod_min, self.tod_hr]
            return self.tod_latch[3]

        # Serial Data Register ($DC0C)
        if reg == 0x0C:
            return self.sdr

        # Interrupt Control Register (ICR) ($DC0D)
        if reg == 0x0D:
            # Reading ICR clears it and returns current interrupt state
            result = self.icr_data
            # Set bit 7 if any enabled interrupt has occurred
            if result & self.icr_mask:
                result |= 0x80
            # Log ICR reads
            if DEBUG_CIA:
                log.info(f"*** CIA1 ICR READ: data=${self.icr_data:02X}, result=${result:02X}, clearing ICR and irq_pending ***")
            # Clear interrupt data after read
            self.icr_data = 0x00
            # Clear CPU IRQ line - on real 6526, reading ICR de-asserts /IRQ
            # This is important for polling scenarios where IRQ handler isn't used
            self.cpu.irq_pending = False
            return result

        # Control Register A ($DC0E)
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

        # Control Register B ($DC0F)
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

        # Return stored register contents for other registers
        return self.regs[reg]

    def write(self, addr, value) -> None:
        reg = addr & 0x0F
        self.regs[reg] = value

        # Port A ($DC00) — keyboard row selection
        # KERNAL writes here to select which row(s) to scan (active low)
        if reg == 0x00:
            old_port_a = self.port_a
            self.port_a = value
            if old_port_a != value and DEBUG_CIA:
                log.info(f"*** CIA1 Port A WRITE (row select): ${value:02X} ***")

        # Port B ($DC01) — keyboard column sensing
        # Typically read-only for keyboard, but can be written (value used in output mixing)
        if reg == 0x01:
            old_port_b = self.port_b
            self.port_b = value
            if old_port_b != value:
                log.info(f"*** CIA1 Port B WRITE: ${value:02X} (unusual - Port B is typically input-only for keyboard) ***")

        # Port A DDR ($DC02)
        if reg == 0x02:
            old_ddr_a = self.ddr_a
            self.ddr_a = value
            log.info(f"*** CIA1 Port A DDR: ${old_ddr_a:02X} -> ${value:02X} (0=input, 1=output) ***")
            if value != 0xFF:
                log.info(f"*** WARNING: Port A DDR != 0xFF, rows {bin(~value & 0xFF)} will not be selectable! ***")

        # Port B DDR ($DC03)
        if reg == 0x03:
            self.ddr_b = value
            log.info(f"*** CIA1 Port B DDR: ${value:02X} (0=input, 1=output) ***")

        # Timer A Low Byte ($DC04)
        if reg == 0x04:
            self.timer_a_latch = (self.timer_a_latch & 0xFF00) | value

        # Timer A High Byte ($DC05)
        if reg == 0x05:
            self.timer_a_latch = (self.timer_a_latch & 0x00FF) | (value << 8)
            # 6526 behavior: Writing high byte while timer stopped loads latch into counter
            if not self.timer_a_running:
                self.timer_a_counter = self.timer_a_latch

        # Timer B Low Byte ($DC06)
        if reg == 0x06:
            self.timer_b_latch = (self.timer_b_latch & 0xFF00) | value

        # Timer B High Byte ($DC07)
        if reg == 0x07:
            self.timer_b_latch = (self.timer_b_latch & 0x00FF) | (value << 8)
            # 6526 behavior: Writing high byte while timer stopped loads latch into counter
            if not self.timer_b_running:
                self.timer_b_counter = self.timer_b_latch

        # TOD 1/10 Seconds ($DC08)
        if reg == 0x08:
            if self.tod_write_alarm:
                self.alarm_10ths = value & 0x0F
            else:
                self.tod_10ths = value & 0x0F
                # Writing 10ths starts TOD clock
                self.tod_running = True

        # TOD Seconds ($DC09)
        if reg == 0x09:
            if self.tod_write_alarm:
                self.alarm_sec = value & 0x7F
            else:
                self.tod_sec = value & 0x7F

        # TOD Minutes ($DC0A)
        if reg == 0x0A:
            if self.tod_write_alarm:
                self.alarm_min = value & 0x7F
            else:
                self.tod_min = value & 0x7F

        # TOD Hours ($DC0B)
        if reg == 0x0B:
            if self.tod_write_alarm:
                self.alarm_hr = value
            else:
                self.tod_hr = value
                # Writing hours stops TOD clock until 10ths is written
                self.tod_running = False

        # Serial Data Register ($DC0C)
        if reg == 0x0C:
            self.sdr = value
            # If in output mode, start shifting
            if self.sdr_output_mode:
                self.sdr_bits_remaining = 8
                # Trigger FLAG interrupt on the other CIA (IEC bus simulation)
                # This simulates the start of serial transmission
                if self.other_cia is not None:
                    self.other_cia.trigger_flag_interrupt()

        # Interrupt Control Register ($DC0D)
        if reg == 0x0D:
            # Bit 7: 1=set bits, 0=clear bits in mask
            if value & 0x80:
                # Set mask bits
                new_bits = value & 0x1F
                self.icr_mask |= new_bits
                # 6526 behavior: If enabling a mask bit and the corresponding
                # ICR data bit is already set, fire interrupt immediately
                if self.icr_data & new_bits:
                    self.cpu.irq_pending = True
            else:
                # Clear mask bits
                self.icr_mask &= ~(value & 0x1F)
            log.info(f"*** CIA1 ICR Mask: ${value:02X}, mask=${self.icr_mask:02X}, Timer A IRQ {'ENABLED' if (self.icr_mask & 0x01) else 'DISABLED'} ***")

        # Control Register A ($DC0E)
        if reg == 0x0E:
            # Bit 0: Start/Stop Timer A (1=start, 0=stop)
            old_running = self.timer_a_running
            self.timer_a_running = bool(value & 0x01)
            # Rising edge of bit 0 sets the PB6 toggle flip-flop high
            if self.timer_a_running and not old_running:
                self.pb6_output_state = True
            # Bits 1-2: PB6 output mode
            self.timer_a_pb6_mode = (value >> 1) & 0x03
            # Bit 3: One-shot mode (1=one-shot, 0=continuous)
            self.timer_a_oneshot = bool(value & 0x08)
            # Bit 4: Force load (1=load latch into counter)
            if value & 0x10:
                self.timer_a_counter = self.timer_a_latch
            # Bit 5: Timer A input mode (0=count cycles, 1=count CNT transitions)
            self.timer_a_cnt_mode = bool(value & 0x20)
            # Bit 6: Serial port direction (0=input, 1=output)
            old_sdr_output_mode = self.sdr_output_mode
            self.sdr_output_mode = bool(value & 0x40)
            # If transitioning to output mode, trigger FLAG on other CIA
            # This handles case where SDR is written before output mode is enabled
            if self.sdr_output_mode and not old_sdr_output_mode:
                if self.other_cia is not None:
                    self.other_cia.trigger_flag_interrupt()
            # Bit 7: TOD frequency (0=60Hz, 1=50Hz)
            self.tod_50hz = bool(value & 0x80)
            # Update TOD tick rate based on frequency
            if self.tod_50hz:
                self.tod_cycles_per_tick = 98525  # PAL: 985248 Hz / 10
            else:
                self.tod_cycles_per_tick = 102273  # NTSC: 1022730 Hz / 10
            log.info(f"*** CIA1 Timer A Control: ${value:02X}, running={self.timer_a_running}, oneshot={self.timer_a_oneshot}, latch=${self.timer_a_latch:04X} ***")

        # Control Register B ($DC0F)
        if reg == 0x0F:
            # Bit 0: Start/Stop Timer B (1=start, 0=stop)
            old_running = self.timer_b_running
            self.timer_b_running = bool(value & 0x01)
            # Rising edge of bit 0 sets the PB7 toggle flip-flop high
            if self.timer_b_running and not old_running:
                self.pb7_output_state = True
            # Bits 1-2: PB7 output mode
            self.timer_b_pb7_mode = (value >> 1) & 0x03
            # Bit 3: One-shot mode (1=one-shot, 0=continuous)
            self.timer_b_oneshot = bool(value & 0x08)
            # Bit 4: Force load (1=load latch into counter)
            if value & 0x10:
                self.timer_b_counter = self.timer_b_latch
            # Bits 5-6: Timer B input mode
            # 0 = count CPU cycles
            # 1 = count CNT transitions
            # 2 = count Timer A underflows
            # 3 = count Timer A underflows when CNT high
            self.timer_b_input_mode = (value >> 5) & 0x03
            # Bit 7: TOD alarm write (0=write TOD, 1=write alarm)
            self.tod_write_alarm = bool(value & 0x80)
            log.info(f"*** CIA1 Timer B Control: ${value:02X}, running={self.timer_b_running}, oneshot={self.timer_b_oneshot}, input_mode={self.timer_b_input_mode}, latch=${self.timer_b_latch:04X} ***")

    def update(self) -> None:
        """Update CIA timers and TOD based on CPU cycles.

        Called periodically to count down timers and generate interrupts.
        """
        # Calculate cycles elapsed since last update
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

        # Reset Timer A underflow flag for this update cycle
        self.timer_a_underflowed = False
        timer_a_underflow_count = 0

        # Update Timer A (only counts CPU cycles if not in CNT mode)
        if self.timer_a_running and cycles_elapsed > 0 and not self.timer_a_cnt_mode:
            # Count down by elapsed cycles
            if self.timer_a_counter >= cycles_elapsed:
                self.timer_a_counter -= cycles_elapsed
            else:
                # Timer underflow
                timer_a_underflow_count = (cycles_elapsed - self.timer_a_counter) // (self.timer_a_latch + 1) + 1
                self.timer_a_underflowed = True

                # In one-shot mode, stop timer after underflow
                if self.timer_a_oneshot:
                    self.timer_a_counter = 0
                    self.timer_a_running = False
                else:
                    self.timer_a_counter = self.timer_a_latch - ((cycles_elapsed - self.timer_a_counter - 1) % (self.timer_a_latch + 1))

                # Trigger Timer A interrupt (bit 0)
                self.icr_data |= 0x01

                # If Timer A interrupts are enabled, signal CPU IRQ
                if self.icr_mask & 0x01:
                    self.cpu.irq_pending = True

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
                            self.cpu.irq_pending = True
                        # Also trigger FLAG interrupt on the other CIA (IEC bus simulation)
                        if self.other_cia is not None:
                            self.other_cia.trigger_flag_interrupt()

                # Handle PB6 timer output
                # pb6_mode bit 0 (CRA bit 1): enable output
                # pb6_mode bit 1 (CRA bit 2): 0=pulse, 1=toggle
                if self.timer_a_pb6_mode & 0x02:
                    # Toggle mode - flip PB6 state on each underflow
                    for _ in range(timer_a_underflow_count):
                        self.pb6_output_state = not self.pb6_output_state
                else:
                    # Pulse mode - output high for one cycle per underflow
                    self.pb6_pulse_cycles = 1  # One cycle high pulse

        # Decrement PB6 pulse cycles
        if self.pb6_pulse_cycles > 0:
            self.pb6_pulse_cycles = max(0, self.pb6_pulse_cycles - cycles_elapsed)

        # Update Timer B
        if self.timer_b_running:
            decrement = 0

            # Determine clock source for Timer B
            if self.timer_b_input_mode == 0:
                # Mode 0: Count CPU cycles
                decrement = cycles_elapsed
            elif self.timer_b_input_mode == 1:
                # Mode 1: Count CNT transitions (not implemented for now)
                pass
            elif self.timer_b_input_mode == 2:
                # Mode 2: Count Timer A underflows
                decrement = timer_a_underflow_count
            elif self.timer_b_input_mode == 3:
                # Mode 3: Count Timer A underflows when CNT high
                if self.cnt_pin:
                    decrement = timer_a_underflow_count

            if decrement > 0:
                if self.timer_b_counter >= decrement:
                    self.timer_b_counter -= decrement
                else:
                    # Timer underflow
                    # In one-shot mode, stop timer after underflow
                    if self.timer_b_oneshot:
                        self.timer_b_counter = 0
                        self.timer_b_running = False
                    else:
                        if self.timer_b_input_mode == 0:
                            # CPU cycle mode - handle multiple underflows
                            self.timer_b_counter = self.timer_b_latch - ((decrement - self.timer_b_counter - 1) % (self.timer_b_latch + 1))
                        else:
                            # Timer A underflow mode - simpler reload
                            self.timer_b_counter = self.timer_b_latch

                    # Trigger Timer B interrupt (bit 1)
                    self.icr_data |= 0x02

                    # If Timer B interrupts are enabled, signal CPU IRQ
                    if self.icr_mask & 0x02:
                        self.cpu.irq_pending = True

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
        # Increment 1/10 seconds (BCD)
        self.tod_10ths = (self.tod_10ths + 1) & 0x0F
        if self.tod_10ths > 9:
            self.tod_10ths = 0

            # Increment seconds (BCD)
            sec_lo = (self.tod_sec & 0x0F) + 1
            sec_hi = (self.tod_sec >> 4) & 0x07
            if sec_lo > 9:
                sec_lo = 0
                sec_hi += 1
            if sec_hi > 5:
                sec_hi = 0

                # Increment minutes (BCD)
                min_lo = (self.tod_min & 0x0F) + 1
                min_hi = (self.tod_min >> 4) & 0x07
                if min_lo > 9:
                    min_lo = 0
                    min_hi += 1
                if min_hi > 5:
                    min_hi = 0

                    # Increment hours (BCD with AM/PM)
                    hr_lo = (self.tod_hr & 0x0F) + 1
                    hr_hi = (self.tod_hr >> 4) & 0x01
                    pm = bool(self.tod_hr & 0x80)

                    if hr_lo > 9:
                        hr_lo = 0
                        hr_hi += 1

                    # Handle 12-hour rollover
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
            # Trigger TOD alarm interrupt (bit 2)
            self.icr_data |= 0x04
            if self.icr_mask & 0x04:
                self.cpu.irq_pending = True

    def _read_keyboard_port(self) -> int:
        """Read keyboard matrix columns based on selected rows (thread-safe).

        The C64 keyboard is an 8x8 matrix:
        - KERNAL writes to Port A ($DC00) to select row(s) - active low
        - KERNAL reads from Port B ($DC01) to get column states - active low
        - 0 = pressed, 1 = released

        The KERNAL typically scans one row at a time by setting one bit low.
        But it can also scan multiple rows simultaneously (all bits low = scan all rows).
        """
        # Port A contains the row selection (active low)
        # Each bit low = scan that row
        selected_rows = ~self.port_a & 0xFF

        # Start with all columns high (no keys)
        result = 0xFF

        # Take thread-safe snapshot of keyboard matrix
        with self._keyboard_lock:
            kb_matrix = self.keyboard_matrix.copy()

        # Check each row
        for row in range(8):
            if selected_rows & (1 << row):
                # This row is selected, AND its columns into result
                # If any key in this row is pressed (bit=0), it will pull the result low
                result &= kb_matrix[row]

        return result

    def _get_key_name(self, row: int, col: int) -> str:
        """Get the PETSCII key name for a matrix position.

        Args:
            row: Row index (0-7)
            col: Column index (0-7)

        Returns:
            Key name string
        """
        # C64 keyboard matrix mapping: (row, col) -> key name
        # Reference: https://www.c64-wiki.com/wiki/Keyboard
        key_map = {
            # Row 0
            (0, 0): "DEL",
            (0, 1): "RETURN",
            (0, 2): "CRSR→",
            (0, 3): "F7",
            (0, 4): "F1",
            (0, 5): "F3",
            (0, 6): "F5",
            (0, 7): "CRSR↓",

            # Row 1
            (1, 0): "3",
            (1, 1): "W",
            (1, 2): "A",
            (1, 3): "4",
            (1, 4): "Z",
            (1, 5): "S",
            (1, 6): "E",
            (1, 7): "LSHIFT",

            # Row 2
            (2, 0): "5",
            (2, 1): "R",
            (2, 2): "D",
            (2, 3): "6",
            (2, 4): "C",
            (2, 5): "F",
            (2, 6): "T",
            (2, 7): "X",

            # Row 3
            (3, 0): "7",
            (3, 1): "Y",
            (3, 2): "G",
            (3, 3): "8",
            (3, 4): "B",
            (3, 5): "H",
            (3, 6): "U",
            (3, 7): "V",

            # Row 4
            (4, 0): "9",
            (4, 1): "I",
            (4, 2): "J",
            (4, 3): "0",
            (4, 4): "M",
            (4, 5): "K",
            (4, 6): "O",
            (4, 7): "N",

            # Row 5
            (5, 0): "+",
            (5, 1): "P",
            (5, 2): "L",
            (5, 3): "-",
            (5, 4): ".",
            (5, 5): ":",
            (5, 6): "@",
            (5, 7): ",",

            # Row 6
            (6, 0): "£",
            (6, 1): "*",
            (6, 2): ";",
            (6, 3): "HOME",
            (6, 4): "RSHIFT",
            (6, 5): "=",
            (6, 6): "↑",
            (6, 7): "/",

            # Row 7
            (7, 0): "1",
            (7, 1): "←",
            (7, 2): "CTRL",
            (7, 3): "2",
            (7, 4): "SPACE",
            (7, 5): "C=",
            (7, 6): "Q",
            (7, 7): "RUN/STOP",
        }

        # Simple key name lookup - just return the key label
        return key_map.get((row, col), f"?({row},{col})?")

    def _invalidate_keyboard_cache(self) -> None:
        """Invalidate keyboard caches when matrix changes.

        Must be called while holding _keyboard_lock.
        """
        self._kb_cache_valid = False
        self._column_cache_valid = False
        self._column_cache.clear()

    def _get_cached_keyboard_matrix(self) -> list:
        """Get keyboard matrix, using cache if valid.

        This avoids acquiring the lock and copying on every read.
        The cache is invalidated when keys are pressed/released.

        Returns:
            Cached copy of keyboard matrix (8 bytes)
        """
        if self._kb_cache_valid:
            return self._kb_matrix_cache

        # Cache miss - need to copy under lock
        with self._keyboard_lock:
            # Double-check after acquiring lock
            if not self._kb_cache_valid:
                self._kb_matrix_cache = self.keyboard_matrix.copy()
                self._kb_cache_valid = True
            return self._kb_matrix_cache

    def _compute_keyboard_columns(self, port_a: int, kb_matrix: list) -> int:
        """Compute keyboard column result for a given port_a value.

        This is the expensive double-loop that we want to cache.

        Args:
            port_a: Port A value (row selection, active low)
            kb_matrix: Keyboard matrix snapshot

        Returns:
            Column byte (active low: 0 = key pressed)
        """
        keyboard_ext = 0xFF

        for row in range(8):
            # Row participates if Port A bit is LOW (selected)
            if not (port_a & (1 << row)):
                # AND in this row's columns (pressed keys pull columns low)
                keyboard_ext &= kb_matrix[row]

        return keyboard_ext

    def press_key(self, row: int, col: int) -> None:
        """Press a key at the given matrix position (thread-safe).

        Args:
            row: Row index (0-7)
            col: Column index (0-7)
        """
        import time
        if 0 <= row < 8 and 0 <= col < 8:
            with self._keyboard_lock:
                # Clear the bit (active low = pressed)
                old_value = self.keyboard_matrix[row]
                self.keyboard_matrix[row] &= ~(1 << col)
                new_value = self.keyboard_matrix[row]
                # Invalidate cache since matrix changed
                if old_value != new_value:
                    self._invalidate_keyboard_cache()
                # Track press time for minimum hold duration
                self._key_press_times[(row, col)] = time.perf_counter()
                if DEBUG_KEYBOARD:
                    log.info(f"*** PRESS_KEY: row={row}, col={col}, matrix[{row}]: ${old_value:02X} -> ${new_value:02X} ***")

    def release_key(self, row: int, col: int) -> None:
        """Release a key at the given matrix position (thread-safe).

        Args:
            row: Row index (0-7)
            col: Column index (0-7)
        """
        if 0 <= row < 8 and 0 <= col < 8:
            with self._keyboard_lock:
                # Set the bit (active low = released)
                old_value = self.keyboard_matrix[row]
                self.keyboard_matrix[row] |= (1 << col)
                # Invalidate cache since matrix changed
                if old_value != self.keyboard_matrix[row]:
                    self._invalidate_keyboard_cache()
                # Clear press time tracking
                self._key_press_times.pop((row, col), None)

    def get_key_press_time(self, row: int, col: int) -> Union[float, None]:
        """Get when a key was pressed, or None if not pressed.

        Used to enforce minimum key hold duration for fast typists.
        """
        with self._keyboard_lock:
            return self._key_press_times.get((row, col))

    def get_keyboard_matrix_snapshot(self) -> list:
        """Get a thread-safe snapshot of the keyboard matrix."""
        with self._keyboard_lock:
            return self.keyboard_matrix.copy()
