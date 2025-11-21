#!/usr/bin/env python3
"""Commodore 64 Emulator using the mos6502 CPU package."""

import logging
import sys
from pathlib import Path
from typing import Optional

from mos6502 import CPU, CPUVariant, errors
from mos6502.core import INFINITE_CYCLES
from mos6502.memory import Byte, Word

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("c64")

COLORS = [
    (0x00, 0x00, 0x00),   # 0  Black
    (0xFF, 0xFF, 0xFF),   # 1  White
    (0x68, 0x37, 0x2B),   # 2  Red
    (0x70, 0xA4, 0xB2),   # 3  Cyan
    (0x6F, 0x3D, 0x86),   # 4  Purple
    (0x58, 0x8D, 0x43),   # 5  Green
    (0x35, 0x28, 0x79),   # 6  Blue
    (0xB8, 0xC7, 0x6F),   # 7  Yellow
    (0x6F, 0x4F, 0x25),   # 8  Orange
    (0x43, 0x39, 0x00),   # 9  Brown
    (0x9A, 0x67, 0x59),   # 10 Light red
    (0x44, 0x44, 0x44),   # 11 Dark gray
    (0x6C, 0x6C, 0x6C),   # 12 Medium gray
    (0x9A, 0xD2, 0x84),   # 13 Light green
    (0x6C, 0x5E, 0xB5),   # 14 Light blue
    (0x95, 0x95, 0x95),   # 15 Light gray
]

class C64:
    """Commodore 64 Emulator.

    Memory Map:
        $0000-$0001: I/O Ports (6510 specific - stubbed)
        $0002-$9FFF: RAM (40KB usable)
        $A000-$BFFF: BASIC ROM (8KB)
        $C000-$CFFF: RAM (4KB)
        $D000-$DFFF: I/O and Color RAM (4KB - stubbed)
        $E000-$FFFF: KERNAL ROM (8KB)
    """

    # Memory regions
    BASIC_ROM_START = 0xA000
    BASIC_ROM_END = 0xBFFF
    BASIC_ROM_SIZE = 0x2000  # 8KB

    KERNAL_ROM_START = 0xE000
    KERNAL_ROM_END = 0xFFFF
    KERNAL_ROM_SIZE = 0x2000  # 8KB

    CHAR_ROM_START = 0xD000
    CHAR_ROM_END = 0xDFFF
    CHAR_ROM_SIZE = 0x1000  # 4KB

    # I/O regions within $D000-$DFFF
    VIC_START = 0xD000
    VIC_END = 0xD3FF
    SID_START = 0xD400
    SID_END = 0xD7FF
    COLOR_RAM_START = 0xD800
    COLOR_RAM_END = 0xDBFF
    CIA1_START = 0xDC00
    CIA1_END = 0xDCFF
    CIA2_START = 0xDD00
    CIA2_END = 0xDDFF

    # C64 BASIC programs typically start here
    BASIC_PROGRAM_START = 0x0801

    # Reset vector location
    RESET_VECTOR_ADDR = 0xFFFC

    class CIA1:
        def __init__(self):
            # 16 registers, mirrored through $DC00–$DC0F
            self.regs = [0x00] * 16

            # Keyboard matrix all released (1 = released)
            self.keyboard_matrix = [0xFF] * 8

        def read(self, addr) -> int:
            reg = addr & 0x0F

            # Port A ($DC00) — keyboard matrix read
            if reg == 0x00:
                return self._read_keyboard_port()

            # Port B ($DC01) — joystick + keyboard rows
            if reg == 0x01:
                return 0xFF  # no joystick pressed

            # CIA will return 0xFF for most unimplemented registers
            # or stored timer values if necessary
            if reg == 0x0D:
                # Interrupt Control Register (ICR)
                return 0x00  # no interrupts pending

            # Return stored register contents
            return self.regs[reg]

        def write(self, addr, value) -> None:
            reg = addr & 0x0F
            self.regs[reg] = value

        def _read_keyboard_port(self):
            # The C64 keyboard is an 8x8 matrix.
            # KERNAL polls port A with each row selected on port B.
            # Returning 0xFF emulates “no keys pressed.”
            return 0xFF

    class CIA2:
        def __init__(self):
            self.regs = [0x00] * 16

        def read(self, addr) -> int:
            reg = addr & 0x0F

            if reg == 0x0D:
                # ICR — no interrupts pending
                return 0x00

            return 0xFF  # CIA2 usually floats high where unused

        def write(self, addr, value) -> None:
            reg = addr & 0x0F
            self.regs[reg] = value

    class C64VIC:
        def __init__(self, char_rom, cpu):
            self.log = logging.getLogger("c64.vic")
            self.regs = [0] * 0x40
            self.char_rom = char_rom
            self.cpu = cpu

            # NTSC timing: 263 raster lines, 63 cycles per line
            self.raster_lines = 263
            self.cycles_per_line = 63
            self.cycles_per_frame = self.raster_lines * self.cycles_per_line  # 16,569

            # Current raster line - start at a reasonable position
            self.current_raster = 0

            # Interrupt flags - latched until read/cleared
            # Set bit 0 initially so KERNAL can clear it (boot requirement)
            self.irq_flags = 0x01  # Bit 0=raster, 1=sprite-bg, 2=sprite-sprite, 3=lightpen
            self.irq_enabled = 0x00  # Which interrupts are enabled

            # Track last cycle count to know when to increment raster
            self.last_cycle_count = 0

            # Track initialization state
            self.initialized = False

            self.log.info("VIC-II initialized (NTSC: 263 lines, 63 cycles/line)")

        def update(self) -> None:
            """Update VIC state based on CPU cycles. Should be called periodically."""
            # Calculate raster line based on total CPU cycles
            total_lines = self.cpu.cycles_executed // self.cycles_per_line
            new_raster = total_lines % self.raster_lines

            # Debug: detect if update is being called excessively
            if not hasattr(self, "_update_count"):
                self._update_count = 0
                self._last_cycles = 0
            self._update_count += 1
            if self._update_count % 100000 == 0:
                cycles_diff = self.cpu.cycles_executed - self._last_cycles
                self.log.warning(f"VIC update() called {self._update_count:,} times, cycles_diff={cycles_diff}")
                self._last_cycles = self.cpu.cycles_executed

            # Check if we should trigger raster IRQ on raster line match
            if new_raster != self.current_raster:
                raster_compare = self.regs[0x12] | ((self.regs[0x11] & 0x80) << 1)
                if new_raster == raster_compare:
                    # Set raster IRQ flag (bit 0)
                    self.irq_flags |= 0x01

            self.current_raster = new_raster

        def read(self, addr) -> int:
            reg = addr & 0x3F

            # $D012: Raster line register (read current raster position)
            if reg == 0x12:
                self.update()
                return self.current_raster & 0xFF

            # $D019: Interrupt flags (read and acknowledge)
            if reg == 0x19:
                # Return current flags with bit 7 set if any enabled IRQ is active
                flags = self.irq_flags
                # Bit 7 is set if any interrupt occurred (regardless of enable)
                if flags & 0x0F:
                    flags |= 0x80
                return flags

            return self.regs[reg]

        def write(self, addr, val) -> None:
            reg = addr & 0x3F
            self.regs[reg] = val

            # $D019: Interrupt flags - writing 1 to a bit CLEARS it (acknowledge)
            if reg == 0x19:
                # Writing 1 clears the corresponding flag (interrupt latch behavior)
                was_set = self.irq_flags & 0x0F
                self.irq_flags &= ~(val & 0x0F)

                # Log when KERNAL acknowledges the initial IRQ (completion of VIC init)
                if not self.initialized and was_set and (self.irq_flags & 0x0F) == 0:
                    self.initialized = True
                    self.log.info("VIC-II initialization complete (IRQ acknowledged)")

            # $D01A: Interrupt enable register
            if reg == 0x1A:
                self.irq_enabled = val & 0x0F

        def render_text(self, surface, ram, color_ram) -> None:
            screen_base = 0x0400  # default
            for row in range(25):
                for col in range(40):
                    cell_addr = screen_base + row * 40 + col
                    char_code = ram[cell_addr]
                    color = color_ram[cell_addr - 0x0400] & 0x0F

                    # Each char = 8 bytes in ROM
                    glyph = self.char_rom[char_code * 8 : char_code * 8 + 8]

                    for y in range(8):
                        line = glyph[y]
                        for x in range(8):
                            pixel = (line >> (7 - x)) & 1
                            surface.set_at((col*8 + x, row*8 + y),
                                        COLORS[color] if pixel else COLORS[0])


    class C64Memory:
        def __init__(self, ram, *, basic_rom, kernal_rom, char_rom, cia1, cia2, vic):
            # Store references to actual RAM storage for direct access (avoids delegation loop)
            self.ram_zeropage = ram.zeropage
            self.ram_stack = ram.stack
            self.ram_heap = ram.heap
            self.basic = basic_rom
            self.kernal = kernal_rom
            self.char = char_rom
            self.cia1 = cia1
            self.cia2 = cia2
            self.vic = vic

            # Color RAM - 1000 bytes ($D800-$DBE7), only low 4 bits used
            self.ram_color = bytearray(1024)

            # CPU I/O port
            self.ddr = 0x00  # $0000
            self.port = 0x37  # $0001 default value

        def _read_ram_direct(self, addr):
            """Read directly from RAM storage without delegation."""
            if 0 <= addr < 256:
                return self.ram_zeropage[addr].value
            elif 256 <= addr < 512:
                return self.ram_stack[addr - 256].value
            elif addr <= 65535:
                return self.ram_heap[addr - 512].value
            return 0

        def _write_ram_direct(self, addr, value):
            """Write directly to RAM storage without delegation."""
            from mos6502.memory import Byte, int2ba
            if 0 <= addr < 256:
                self.ram_zeropage[addr] = Byte(value=int2ba(value, length=8, endian="little"), endianness="little")
            elif 256 <= addr < 512:
                self.ram_stack[addr - 256] = Byte(value=int2ba(value, length=8, endian="little"), endianness="little")
            elif addr <= 65535:
                self.ram_heap[addr - 512] = Byte(value=int2ba(value, length=8, endian="little"), endianness="little")

        def read(self, addr) -> int:
            # CPU internal port
            if addr == 0x0000: return self.ddr
            if addr == 0x0001:
                # Bits with DDR=0 read as 1
                return (self.port | (~self.ddr)) & 0xFF

            # Memory banking logic
            io_enabled = self.port & 0b00000100
            basic_enabled = self.port & 0b00000001
            kernal_enabled = self.port & 0b00000010

            # BASIC ROM
            if C64.BASIC_ROM_START <= addr <= C64.BASIC_ROM_END and basic_enabled:
                return self.basic[addr - C64.BASIC_ROM_START]

            # KERNAL ROM
            if C64.KERNAL_ROM_START <= addr <= C64.KERNAL_ROM_END and kernal_enabled:
                return self.kernal[addr - C64.KERNAL_ROM_START]

            # I/O or CHAR ROM
            if C64.CHAR_ROM_START <= addr <= C64.CHAR_ROM_END:
                if io_enabled:
                    # VIC registers
                    if C64.VIC_START <= addr <= C64.VIC_END:
                        return self.vic.read(addr)
                    # SID registers
                    if C64.SID_START <= addr <= C64.SID_END:
                        return 0xFF  # SID stub
                    # Color RAM
                    if C64.COLOR_RAM_START <= addr <= C64.COLOR_RAM_END:
                        return self.ram_color[addr - C64.COLOR_RAM_START] | 0xF0
                    # CIA1
                    if C64.CIA1_START <= addr <= C64.CIA1_END:
                        return self.cia1.read(addr)
                    # CIA2
                    if C64.CIA2_START <= addr <= C64.CIA2_END:
                        return self.cia2.read(addr)
                    return 0xFF
                else:
                    return self.char[addr - C64.CHAR_ROM_START]

            # RAM fallback
            return self._read_ram_direct(addr)

        def write(self, addr, value) -> None:
            """Write to C64 memory with banking logic."""
            # CPU internal port
            if addr == 0x0000:
                self.ddr = value & 0xFF
                return
            if addr == 0x0001:
                self.port = value & 0xFF
                return

            # Memory banking logic
            io_enabled = self.port & 0b00000100

            # I/O area
            if C64.CHAR_ROM_START <= addr <= C64.CHAR_ROM_END and io_enabled:
                # VIC registers
                if 0xD000 <= addr <= 0xD3FF:
                    self.vic.write(addr, value)
                    return
                # SID registers (stub)
                if 0xD400 <= addr <= 0xD7FF:
                    return  # Ignore writes to SID
                # Color RAM
                if 0xD800 <= addr <= 0xDBFF:
                    self.ram_color[addr - 0xD800] = value & 0x0F  # Only 4 bits
                    return
                # CIA1
                if 0xDC00 <= addr <= 0xDCFF:
                    self.cia1.write(addr, value)
                    return
                # CIA2
                if 0xDD00 <= addr <= 0xDDFF:
                    self.cia2.write(addr, value)
                    return

            # Can't write to ROM areas (BASIC/KERNAL/CHAR)
            # But we can write to underlying RAM which may be visible later
            # For simplicity, just write to RAM - banking will handle visibility
            self._write_ram_direct(addr, value & 0xFF)


    def __init__(self, rom_dir: Path = Path("./roms")):
        """Initialize the C64 emulator.

        Arguments:
            rom_dir: Directory containing ROM files (basic, kernal, char)
        """
        self.rom_dir = Path(rom_dir)

        # Initialize CPU (6510 is essentially a 6502 with I/O ports)
        # We'll use NMOS 6502 as the base
        self.cpu = CPU(cpu_variant=CPUVariant.NMOS_6502)

        log.info(f"Initialized CPU: {self.cpu.variant_name}")

        # Storage for ROMs
        self.basic_rom: Optional[bytes] = None
        self.kernal_rom: Optional[bytes] = None
        self.char_rom: Optional[bytes] = None
        self.vic: Optional[C64.C64VIC] = None
        self.cia1: Optional[C64.CIA1] = None
        self.cia2: Optional[C64.CIA2] = None

        # self.memory = C64.C64Memory(self.cpu.ram, self.basic_rom, self.kernal_rom, self.char_rom)
        # self.cpu.memory = self.memory

    def load_rom(self, filename: str, expected_size: int, description: str) -> bytes:
        """Load a ROM file from the rom directory.

        Arguments:
            filename: Name of the ROM file
            expected_size: Expected size in bytes
            description: Human-readable description for logging

        Returns:
            ROM data as bytes

        Raises:
            FileNotFoundError: If ROM file doesn't exist
            ValueError: If ROM file size is incorrect
        """
        rom_path = self.rom_dir / filename

        if not rom_path.exists():
            raise FileNotFoundError(
                f"{description} ROM not found: {rom_path}\n"
                f"Expected file: {filename} in directory: {self.rom_dir}"
            )

        rom_data = rom_path.read_bytes()

        if len(rom_data) != expected_size:
            raise ValueError(
                f"{description} ROM has incorrect size: {len(rom_data)} bytes "
                f"(expected {expected_size} bytes)"
            )

        log.info(f"Loaded {description} ROM: {rom_path} ({len(rom_data)} bytes)")
        return rom_data

    def load_roms(self) -> None:
        """Load all C64 ROM files into memory."""
        # Try common ROM filenames
        basic_names = ["basic", "basic.rom", "basic.901226-01.bin"]
        kernal_names = ["kernal", "kernal.rom", "kernal.901227-03.bin"]
        char_names = ["char", "char.rom", "characters.901225-01.bin", "chargen"]

        # Load BASIC ROM
        for name in basic_names:
            try:
                self.basic_rom = self.load_rom(name, self.BASIC_ROM_SIZE, "BASIC")
                break
            except FileNotFoundError:
                continue
        else:
            raise FileNotFoundError(
                f"BASIC ROM not found. Tried: {', '.join(basic_names)} in {self.rom_dir}"
            )

        # Load KERNAL ROM
        for name in kernal_names:
            try:
                self.kernal_rom = self.load_rom(name, self.KERNAL_ROM_SIZE, "KERNAL")
                break
            except FileNotFoundError:
                continue
        else:
            raise FileNotFoundError(
                f"KERNAL ROM not found. Tried: {', '.join(kernal_names)} in {self.rom_dir}"
            )

        # Load CHAR ROM (optional for now)
        for name in char_names:
            try:
                self.char_rom = self.load_rom(name, self.CHAR_ROM_SIZE, "CHAR")
                break
            except FileNotFoundError:
                continue

        if self.char_rom is None:
            log.warning(f"CHAR ROM not found (optional). Tried: {', '.join(char_names)}")

        # Write ROMs to CPU memory
        self._write_rom_to_memory(self.BASIC_ROM_START, self.basic_rom)
        self._write_rom_to_memory(self.KERNAL_ROM_START, self.kernal_rom)

        if self.char_rom:
            self._write_rom_to_memory(self.CHAR_ROM_START, self.char_rom)


        # Now set up the CIA1 and CIA2 and VIC
        self.cia1 = C64.CIA1()
        self.cia2 = C64.CIA2()
        self.vic = C64.C64VIC(char_rom=self.char_rom, cpu=self.cpu)

        # Initialize memory
        self.memory = C64.C64Memory(
            self.cpu.ram,
            basic_rom=self.basic_rom,
            kernal_rom=self.kernal_rom,
            char_rom=self.char_rom,
            cia1=self.cia1,
            cia2=self.cia2,
            vic=self.vic,
        )
        # Hook up the memory handler so CPU RAM accesses go through C64Memory
        self.cpu.ram.memory_handler = self.memory

        log.info("All ROMs loaded into memory")

    def _write_rom_to_memory(self, start_addr: int, rom_data: bytes):
        """Write ROM data to CPU memory.

        Arguments:
            start_addr: Starting address in CPU memory
            rom_data: ROM data to write
        """
        for offset, byte_value in enumerate(rom_data):
            self.cpu.ram[start_addr + offset] = byte_value

        log.debug(f"Wrote ROM to ${start_addr:04X}-${start_addr + len(rom_data) - 1:04X}")

    def load_program(self, program_path: Path, load_address: Optional[int] = None) -> int:
        """Load a program into memory.

        Arguments:
            program_path: Path to the program file
            load_address: Address to load program at (default: $0801 for BASIC programs)
                         If None and file has a 2-byte header, use header address

        Returns:
            The actual load address used
        """
        program_path = Path(program_path)

        if not program_path.exists():
            raise FileNotFoundError(f"Program not found: {program_path}")

        program_data = program_path.read_bytes()

        # Check if program has a load address header (common for .prg files)
        if load_address is None and len(program_data) >= 2:
            # First two bytes might be load address (little-endian)
            header_addr = program_data[0] | (program_data[1] << 8)

            # If it looks like a reasonable address, use it
            if 0x0000 <= header_addr <= 0xFFFF:
                load_address = header_addr
                program_data = program_data[2:]  # Skip header
                log.info(f"Using load address from file header: ${load_address:04X}")

        # Default to BASIC program start
        if load_address is None:
            load_address = self.BASIC_PROGRAM_START

        # Write program to memory
        for offset, byte_value in enumerate(program_data):
            self.cpu.ram[load_address + offset] = byte_value

        log.info(
            f"Loaded program: {program_path.name} "
            f"at ${load_address:04X}-${load_address + len(program_data) - 1:04X} "
            f"({len(program_data)} bytes)"
        )

        return load_address

    def reset(self) -> None:
        """Reset the C64 (CPU reset)."""
        log.info("Resetting C64...")

        self.cpu.reset()

        # Read reset vector from KERNAL ROM
        reset_vector = self.cpu.peek_word(self.RESET_VECTOR_ADDR)
        log.info(f"Reset vector at ${self.RESET_VECTOR_ADDR:04X}: ${reset_vector:04X}")

        # Set PC to reset vector (property setter will log new value)
        self.cpu.PC = reset_vector

    def run(self, max_cycles: int = INFINITE_CYCLES) -> None:
        """Run the C64 emulator.

        Arguments:
            max_cycles: Maximum number of CPU cycles to execute
                       (default: INFINITE_CYCLES for continuous execution)
        """
        log.info(f"Starting execution at PC=${self.cpu.PC:04X}")
        log.info("Press Ctrl+C to stop")

        try:
            # Execute with cycle counter display
            import threading
            import time
            import sys as _sys

            # Check if we're in a TTY (terminal) for interactive display
            is_tty = _sys.stdout.isatty()

            # Flag to stop the display thread
            stop_display = threading.Event()

            def display_cycles():
                """Display cycle count and CPU state on a single updating line."""
                while not stop_display.is_set():
                    if is_tty:
                        # Use \r to return to start of line and overwrite
                        # Get flag values
                        flags = f"{'N' if self.cpu.N else 'n'}"
                        flags += f"{'V' if self.cpu.V else 'v'}"
                        flags += "-"  # Unused flag
                        flags += f"{'B' if self.cpu.B else 'b'}"
                        flags += f"{'D' if self.cpu.D else 'd'}"
                        flags += f"{'I' if self.cpu.I else 'i'}"
                        flags += f"{'Z' if self.cpu.Z else 'z'}"
                        flags += f"{'C' if self.cpu.C else 'c'}"

                        # Determine what's mapped at PC
                        pc = self.cpu.PC
                        port = self.memory.port
                        if pc < C64.BASIC_ROM_START:
                            region = "RAM"
                        elif C64.BASIC_ROM_START <= pc <= C64.BASIC_ROM_END:
                            region = "BASIC" if (port & 0x01) else "RAM"
                        elif C64.CHAR_ROM_START <= pc <= C64.CHAR_ROM_END:
                            region = "I/O" if (port & 0x04) else ("CHAR" if (port & 0x03) == 0x01 else "RAM")
                        elif C64.KERNAL_ROM_START <= pc <= C64.KERNAL_ROM_END:
                            region = "KERNAL" if (port & 0x02) else "RAM"
                        else:
                            region = "???"

                        # Disassemble current instruction
                        try:
                            inst_str = self.disassemble_instruction(pc)
                            # disassemble_instruction returns: "78        SEI  ; implied"
                            # We want the whole thing as-is (hex bytes, mnemonic, addressing mode)
                            inst_display = inst_str.strip()
                        except Exception:
                            # Fallback: just show opcode bytes
                            try:
                                b0 = self.cpu.ram[pc]
                                b1 = self.cpu.ram[pc+1]
                                b2 = self.cpu.ram[pc+2]
                                inst_display = f"{b0:02X} {b1:02X} {b2:02X}  ???"
                            except:
                                inst_display = "???"

                        status = (f"Cycles: {self.cpu.cycles_executed:,} | "
                                f"PC=${self.cpu.PC:04X}[{region}] {inst_display:20s} | "
                                f"A=${self.cpu.A:02X} X=${self.cpu.X:02X} "
                                f"Y=${self.cpu.Y:02X} S=${self.cpu.S & 0xFF:02X} P={flags}    ")
                        _sys.stdout.write(f"\r{status}")
                        _sys.stdout.flush()
                    time.sleep(0.1)  # Update 10 times per second

            # Start the display thread only if we're in a TTY
            if is_tty:
                display_thread = threading.Thread(target=display_cycles, daemon=True)
                display_thread.start()

            try:
                self.cpu.execute(cycles=max_cycles)
            finally:
                # Stop the display thread and print final state on new line
                if is_tty:
                    stop_display.set()
                    display_thread.join(timeout=0.5)
                    # Print final state
                    flags = f"{'N' if self.cpu.N else 'n'}"
                    flags += f"{'V' if self.cpu.V else 'v'}"
                    flags += "-"
                    flags += f"{'B' if self.cpu.B else 'b'}"
                    flags += f"{'D' if self.cpu.D else 'd'}"
                    flags += f"{'I' if self.cpu.I else 'i'}"
                    flags += f"{'Z' if self.cpu.Z else 'z'}"
                    flags += f"{'C' if self.cpu.C else 'c'}"
                    # print(f"\rCycles: {self.cpu.cycles_executed:,} | "
                    #       f"PC=${self.cpu.PC:04X} A=${self.cpu.A:02X} X=${self.cpu.X:02X} "
                    #       f"Y=${self.cpu.Y:02X} S=${self.cpu.S & 0xFF:02X} P={flags}")

        except errors.CPUCycleExhaustionError as e:
            log.info(f"CPU execution completed: {e}")
        except errors.CPUBreakError as e:
            log.info(f"Program terminated (BRK at PC=${self.cpu.PC:04X})")
        except KeyboardInterrupt:
            log.info("\nExecution interrupted by user")
            log.info(f"PC=${self.cpu.PC:04X}, Cycles={self.cpu.cycles_executed}")
        except Exception as e:
            log.error(f"Execution error at PC=${self.cpu.PC:04X}: {e}")
            # Show context around error
            try:
                pc_val = int(self.cpu.PC)
                self.show_disassembly(max(0, pc_val - 10), num_instructions=20)
                self.dump_memory(max(0, pc_val - 16), min(0xFFFF, pc_val + 16))
            except Exception as display_err:
                log.error(f"Could not display context: {display_err}")
            raise
        finally:
            self.show_screen()

    def dump_memory(self, start: int, end: int, bytes_per_line: int = 16) -> None:
        """Dump memory contents for debugging.

        Arguments:
            start: Starting address
            end: Ending address
            bytes_per_line: Number of bytes to display per line
        """
        print(f"\nMemory dump ${start:04X}-${end:04X}:")
        print("      ", end="")
        for i in range(bytes_per_line):
            print(f" {i:02X}", end="")
        print()

        for addr in range(start, end + 1, bytes_per_line):
            print(f"{addr:04X}: ", end="")
            for offset in range(bytes_per_line):
                if addr + offset <= end:
                    byte_val = self.cpu.ram[addr + offset]
                    print(f" {byte_val:02X}", end="")
                else:
                    print("   ", end="")
            print()

    def dump_registers(self) -> None:
        """Dump CPU register state."""
        print(f"\nCPU Registers:")
        print(f"  PC: ${self.cpu.PC:04X}")
        print(f"  A:  ${self.cpu.A:02X}  ({self.cpu.A})")
        print(f"  X:  ${self.cpu.X:02X}  ({self.cpu.X})")
        print(f"  Y:  ${self.cpu.Y:02X}  ({self.cpu.Y})")
        print(f"  S:  ${self.cpu.S:04X}")
        print(f"  Flags: C={self.cpu.C} Z={self.cpu.Z} I={self.cpu.I} "
              f"D={self.cpu.D} B={self.cpu.B} V={self.cpu.V} N={self.cpu.N}")
        print(f"  Cycles executed: {self.cpu.cycles_executed}")

    def disassemble_at(self, address: int, num_instructions: int = 10) -> list[str]:
        """Disassemble instructions starting at address.

        Arguments:
            address: Starting address
            num_instructions: Number of instructions to disassemble

        Returns:
            List of disassembly strings
        """
        from mos6502 import instructions

        lines = []
        current_addr = address

        for _ in range(num_instructions):
            if current_addr > 0xFFFF:
                break

            opcode = self.cpu.ram[current_addr]

            # First try InstructionSet.map (has full metadata)
            if opcode in instructions.InstructionSet.map:
                inst_info = instructions.InstructionSet.map[opcode]
                # Convert bytes/cycles to int (they might be strings in the map)
                try:
                    num_bytes = int(inst_info.get("bytes", 1))
                except (ValueError, TypeError):
                    num_bytes = 1

                # Extract mnemonic from assembler string (e.g., "LDX #{oper}" -> "LDX")
                assembler = inst_info.get("assembler", "???")
                mnemonic = assembler.split()[0] if assembler != "???" else "???"
                mode = inst_info.get("addressing", "")

            # If not in map, try OPCODE_LOOKUP (just has opcode objects)
            elif opcode in instructions.OPCODE_LOOKUP:
                opcode_obj = instructions.OPCODE_LOOKUP[opcode]
                # Extract mnemonic from function name (e.g., "sei_implied_0x78" -> "SEI")
                func_name = opcode_obj.function
                mnemonic = func_name.split("_")[0].upper()

                # Guess number of bytes from function name
                if "implied" in func_name or "accumulator" in func_name:
                    num_bytes = 1
                elif "relative" in func_name or "immediate" in func_name or "zeropage" in func_name:
                    num_bytes = 2
                else:
                    num_bytes = 3

                mode = "implied"

            else:
                # Unknown/illegal opcode
                hex_str = f"{opcode:02X}"
                line = f"${current_addr:04X}: {hex_str}        ???  ; ILLEGAL/UNKNOWN ${opcode:02X}"
                lines.append(line)
                current_addr += 1
                continue

            # Build hex dump
            hex_bytes = [f"{self.cpu.ram[current_addr + i]:02X}"
                        for i in range(min(num_bytes, 3))]
            hex_str = " ".join(hex_bytes).ljust(8)

            # Build operand display
            if num_bytes == 1:
                operand_str = ""
            elif num_bytes == 2:
                operand = self.cpu.ram[current_addr + 1]
                operand_str = f" ${operand:02X}"
            elif num_bytes == 3:
                lo = self.cpu.ram[current_addr + 1]
                hi = self.cpu.ram[current_addr + 2]
                operand = (hi << 8) | lo
                operand_str = f" ${operand:04X}"
            else:
                operand_str = ""

            # Mark illegal opcodes
            if mnemonic == "???":
                line = f"${current_addr:04X}: {hex_str}  {mnemonic}  ; ILLEGAL ${opcode:02X}"
            else:
                line = f"${current_addr:04X}: {hex_str}  {mnemonic}{operand_str}  ; {mode}"
            lines.append(line)
            current_addr += num_bytes

        return lines

    def show_disassembly(self, address: int, num_instructions: int = 10) -> None:
        """Display disassembly at address."""
        print(f"\nDisassembly at ${address:04X}:")
        print("-" * 60)
        for line in self.disassemble_at(address, num_instructions):
            print(line)

    def petscii_to_ascii(self, petscii_code: int) -> str:
        """Convert PETSCII code to displayable ASCII character.

        Arguments:
            petscii_code: PETSCII character code (0-255)

        Returns:
            ASCII character or representation
        """
        # Basic PETSCII to ASCII conversion (simplified)
        # Uppercase letters (PETSCII 65-90 = ASCII 65-90)
        if 65 <= petscii_code <= 90:
            return chr(petscii_code)
        # Lowercase letters (PETSCII 97-122 = ASCII 97-122)
        if 97 <= petscii_code <= 122:
            return chr(petscii_code)
        # Digits (PETSCII 48-57 = ASCII 48-57)
        if 48 <= petscii_code <= 57:
            return chr(petscii_code)
        # Space
        if petscii_code == 32:
            return " "
        # Common punctuation
        punctuation = {
            33: "!", 34: '"', 35: "#", 36: "$", 37: "%", 38: "&", 39: "'",
            40: "(", 41: ")", 42: "*", 43: "+", 44: ",", 45: "-", 46: ".", 47: "/",
            58: ":", 59: ";", 60: "<", 61: "=", 62: ">", 63: "?", 64: "@",
            91: "[", 93: "]", 95: "_"
        }
        if petscii_code in punctuation:
            return punctuation[petscii_code]
        # Screen codes 1-26 map to letters A-Z (reverse video in C64)
        if 1 <= petscii_code <= 26:
            return chr(64 + petscii_code)  # Convert to uppercase letter
        # Default: show as '.' for unprintable
        return "."

    def show_screen(self) -> None:
        """Display the C64 screen (40x25 characters from screen RAM at $0400)."""
        screen_start = 0x0400
        screen_end = 0x07E7
        cols = 40
        rows = 25

        print("\n" + "=" * 42)
        print(" C64 SCREEN")
        print("=" * 42)

        for row in range(rows):
            line = ""
            for col in range(cols):
                addr = screen_start + (row * cols) + col
                if addr <= screen_end:
                    petscii = int(self.cpu.ram[addr])
                    line += self.petscii_to_ascii(petscii)
                else:
                    line += " "
            # Only print non-empty lines
            if line.strip():
                print(line.rstrip())
            else:
                print()

        print("=" * 42)

    def disassemble_instruction(self, address: int) -> str:
        """Disassemble a single instruction at the given address.

        Arguments:
            address: Address of instruction to disassemble

        Returns:
            Formatted disassembly string for the instruction
        """
        from mos6502 import instructions

        opcode = self.cpu.ram[address]

        # First try InstructionSet.map (has full metadata)
        if opcode in instructions.InstructionSet.map:
            inst_info = instructions.InstructionSet.map[opcode]
            # Convert bytes/cycles to int (they might be strings in the map)
            try:
                num_bytes = int(inst_info.get("bytes", 1))
            except (ValueError, TypeError):
                num_bytes = 1

            # Extract mnemonic from assembler string (e.g., "LDX #{oper}" -> "LDX")
            assembler = inst_info.get("assembler", "???")
            mnemonic = assembler.split()[0] if assembler != "???" else "???"
            mode = inst_info.get("addressing", "")

        # If not in map, try OPCODE_LOOKUP (just has opcode objects)
        elif opcode in instructions.OPCODE_LOOKUP:
            opcode_obj = instructions.OPCODE_LOOKUP[opcode]
            # Extract mnemonic from function name (e.g., "sei_implied_0x78" -> "SEI")
            func_name = opcode_obj.function
            mnemonic = func_name.split("_")[0].upper()

            # Guess number of bytes from function name
            if "implied" in func_name or "accumulator" in func_name:
                num_bytes = 1
            elif "relative" in func_name or "immediate" in func_name or "zeropage" in func_name:
                num_bytes = 2
            else:
                num_bytes = 3

            mode = "implied"

        else:
            # Unknown/illegal opcode - return formatted string
            return f"{opcode:02X}              ???  ; ILLEGAL ${opcode:02X}"

        # Build hex dump
        hex_bytes = [f"{self.cpu.ram[address + i]:02X}"
                    for i in range(min(num_bytes, 3))]
        hex_str = " ".join(hex_bytes).ljust(8)

        # Build operand display
        if num_bytes == 1:
            operand_str = ""
        elif num_bytes == 2:
            operand = self.cpu.ram[address + 1]
            operand_str = f" ${operand:02X}"
        elif num_bytes == 3:
            lo = self.cpu.ram[address + 1]
            hi = self.cpu.ram[address + 2]
            operand = (hi << 8) | lo
            operand_str = f" ${operand:04X}"
        else:
            operand_str = ""

        # Return formatted string without the address prefix
        if mnemonic == "???":
            return f"{hex_str}  {mnemonic}  ; ILLEGAL ${opcode:02X}"
        else:
            return f"{hex_str}  {mnemonic}{operand_str}  ; {mode}"


def main() -> int | None:
    """Main entry point for C64 emulator."""
    import argparse

    parser = argparse.ArgumentParser(description="Commodore 64 Emulator")
    parser.add_argument(
        "--rom-dir",
        type=Path,
        default=Path("./roms"),
        help="Directory containing ROM files (default: ./roms)",
    )
    parser.add_argument(
        "--program",
        type=Path,
        help="Program file to load and run (.prg, .bin, etc.)",
    )
    parser.add_argument(
        "--load-address",
        type=lambda x: int(x, 0),
        help="Override load address (hex or decimal, e.g., 0x0801 or 2049)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=INFINITE_CYCLES,
        help="Maximum CPU cycles to execute (default: infinite)",
    )
    parser.add_argument(
        "--dump-mem",
        nargs=2,
        metavar=("START", "END"),
        type=lambda x: int(x, 0),
        help="Dump memory region after execution (hex or decimal addresses)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--no-roms",
        action="store_true",
        help="Run without C64 ROMs (for testing standalone programs)",
    )
    parser.add_argument(
        "--disassemble",
        type=lambda x: int(x, 0),
        metavar="ADDRESS",
        help="Disassemble at address and exit (hex or decimal)",
    )
    parser.add_argument(
        "--num-instructions",
        type=int,
        default=20,
        help="Number of instructions to disassemble (default: 20)",
    )
    parser.add_argument(
        "--show-screen",
        action="store_true",
        help="Display screen RAM after execution (40x25 character display)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize C64
        c64 = C64(rom_dir=args.rom_dir)

        # Reset CPU FIRST (this clears RAM)
        c64.cpu.reset()

        logging.getLogger("mos6502").setLevel(logging.CRITICAL)

        # Then load ROMs (after RAM is cleared)
        if not args.no_roms:
            c64.load_roms()
            # Read reset vector and set PC
            reset_vector = c64.cpu.peek_word(c64.RESET_VECTOR_ADDR)
            log.info(f"Reset vector at ${c64.RESET_VECTOR_ADDR:04X}: ${reset_vector:04X}")
            c64.cpu.PC = reset_vector
            log.info(f"PC set to ${c64.cpu.PC:04X}")
        else:
            log.info(f"Running in headless mode (no ROMs)")

        # Load program AFTER reset (so it doesn't get cleared)
        if args.program:
            actual_load_addr = c64.load_program(args.program, load_address=args.load_address)
            # In no-roms mode, set PC to the program's load address
            if args.no_roms:
                c64.cpu.PC = actual_load_addr
                log.info(f"PC set to ${c64.cpu.PC:04X}")
        elif args.no_roms:
            log.error("--no-roms requires --program to be specified")
            return 1

        # If disassemble mode, show disassembly and exit
        if args.disassemble is not None:
            c64.show_disassembly(args.disassemble, num_instructions=args.num_instructions)
            if args.dump_mem:
                c64.dump_memory(args.dump_mem[0], args.dump_mem[1])
            return 0

        # Dump initial state if verbose
        if args.verbose:
            c64.dump_registers()
            if args.dump_mem:
                c64.dump_memory(args.dump_mem[0], args.dump_mem[1])

        # Run
        c64.run(max_cycles=0xFFFFFFFF)

        # Dump final state
        c64.dump_registers()

        if args.dump_mem:
            c64.dump_memory(args.dump_mem[0], args.dump_mem[1])

        logging.getLogger("mos6502").setLevel(logging.INFO)

        # Show screen if requested
        if args.show_screen:
            c64.show_screen()

        return 0

    except Exception as e:
        log.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
