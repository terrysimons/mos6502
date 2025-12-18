"""C64 Debug Mixin.

Mixin for debugging and diagnostics.
"""

from mos6502.compat import logging, Optional, List
from c64.memory import (
    BASIC_ROM_START,
    BASIC_ROM_END,
    KERNAL_ROM_START,
    KERNAL_ROM_END,
)

log = logging.getLogger("c64")


class C64DebugMixin:
    """Mixin for debugging and diagnostics."""

    def get_pc_region(self) -> str:
        """Determine which memory region PC is currently in.

        Takes memory banking into account (via $0001 port).

        Returns:
            String describing the region: "RAM", "BASIC", "KERNAL", "I/O", "CHAR", or "???"
        """
        pc = self.cpu.PC
        port = self.memory.port

        if pc < BASIC_ROM_START:
            return "RAM"
        elif BASIC_ROM_START <= pc <= BASIC_ROM_END:
            # BASIC ROM only visible if bit 0 of port is set
            return "BASIC" if (port & 0x01) else "RAM"
        elif CHAR_ROM_START <= pc <= CHAR_ROM_END:
            # I/O vs CHAR vs RAM depends on bits in port
            if port & 0x04:
                return "I/O"
            elif (port & 0x03) == 0x01:
                return "CHAR"
            else:
                return "RAM"
        elif KERNAL_ROM_START <= pc <= KERNAL_ROM_END:
            # KERNAL ROM only visible if bit 1 of port is set
            return "KERNAL" if (port & 0x02) else "RAM"
        else:
            return "???"

    def _get_instruction_color(self, opcode: int) -> str:
        """Get ANSI color code for instruction based on type.

        Args:
            opcode: The instruction opcode byte

        Returns:
            ANSI escape sequence for the instruction color:
            - Light blue (96): Common instructions identical across variants
            - Yellow (93): Instructions that differ between variants (ADC, SBC, JMP, BRK)
            - Red (91): Illegal/undocumented instructions
        """
        from mos6502 import instructions

        # ANSI color codes
        LIGHT_BLUE = "\033[96m"  # Light cyan/blue
        YELLOW = "\033[93m"      # Yellow
        RED = "\033[91m"         # Red
        RESET = "\033[0m"

        if opcode not in instructions.OPCODE_LOOKUP:
            return RED  # Unknown opcode

        opcode_obj = instructions.OPCODE_LOOKUP[opcode]
        package = opcode_obj.package

        # Check if it's an illegal instruction
        if ".illegal." in package:
            return RED

        # Check if it's a variant-specific instruction
        # These have different implementations for 6502 vs 65C02
        variant_instructions = {
            "_adc",   # Decimal mode differs
            "_sbc",   # Decimal mode differs
            "_jmp",   # Indirect JMP page boundary bug
            "_brk",   # Flag handling differs
        }
        for variant_inst in variant_instructions:
            if variant_inst in package:
                return YELLOW

        return LIGHT_BLUE

    def _format_cpu_status(self, prefix: str = "C64") -> str:
        """Format C64 CPU status line.

        Args:
            prefix: Label prefix for the status line

        Returns:
            Formatted status string with colorized instruction display:
            - Light blue: Common instructions identical across variants
            - Yellow: Instructions that differ between variants (ADC, SBC, JMP, BRK)
            - Red: Illegal/undocumented instructions
        """
        from mos6502.flags import format_flags
        RESET = "\033[0m"

        flags = format_flags(self.cpu._flags.value)
        region = self.get_pc_region()
        pc = self.cpu.PC

        # Get opcode for colorization
        try:
            opcode = self.cpu.ram[pc]
            color = self._get_instruction_color(opcode)
        except (KeyError, IndexError):
            color = "\033[91m"  # Red for unknown
            opcode = None

        # Disassemble current instruction
        try:
            inst_str = self.disassemble_instruction(pc)
            inst_display = inst_str.strip()
        except (KeyError, ValueError, IndexError):
            try:
                b0 = self.cpu.ram[pc]
                b1 = self.cpu.ram[pc + 1]
                b2 = self.cpu.ram[pc + 2]
                inst_display = f"{b0:02X} {b1:02X} {b2:02X}  ???"
            except IndexError:
                inst_display = "???"

        # Apply color to instruction display
        colored_inst = f"{color}{inst_display:20s}{RESET}"

        return (f"{prefix}: Cycles: {self.cpu.cycles_executed:,} | "
                f"PC=${pc:04X}[{region}] {colored_inst} | "
                f"A=${self.cpu.A:02X} X=${self.cpu.X:02X} "
                f"Y=${self.cpu.Y:02X} S=${self.cpu.S & 0xFF:02X} P={flags}")

    def _format_drive_status(self) -> str:
        """Format 1541 drive CPU status line.

        Returns:
            Formatted status string with colorized instruction display:
            - Light blue: Common instructions identical across variants
            - Yellow: Instructions that differ between variants (ADC, SBC, JMP, BRK)
            - Red: Illegal/undocumented instructions
            Empty string if no drive attached.
        """
        if not self.drive8 or not self.drive8.cpu:
            return ""

        from mos6502.flags import format_flags
        from mos6502 import instructions
        RESET = "\033[0m"

        drive_cpu = self.drive8.cpu
        flags = format_flags(drive_cpu._flags.value)
        region = self.get_drive_pc_region()
        pc = drive_cpu.PC

        # Disassemble current instruction from drive memory
        try:
            b0 = self.drive8.memory.read(pc)
            b1 = self.drive8.memory.read(pc + 1)
            b2 = self.drive8.memory.read(pc + 2)

            # Get color for this opcode
            color = self._get_instruction_color(b0)

            # Use the instruction set to get mnemonic and operand size
            if b0 in instructions.InstructionSet.map:
                inst_info = instructions.InstructionSet.map[b0]
                try:
                    num_bytes = int(inst_info.get("bytes", 1))
                except (ValueError, TypeError):
                    num_bytes = 1
                assembler = inst_info.get("assembler", "???")
                mnemonic = assembler.split()[0] if assembler != "???" else "???"
                mode = inst_info.get("addressing", "")
            elif b0 in instructions.OPCODE_LOOKUP:
                opcode_obj = instructions.OPCODE_LOOKUP[b0]
                func_name = opcode_obj.function
                mnemonic = func_name.split("_")[0].upper()
                if "implied" in func_name or "accumulator" in func_name:
                    num_bytes = 1
                elif "relative" in func_name or "immediate" in func_name or "zeropage" in func_name:
                    num_bytes = 2
                else:
                    num_bytes = 3
                mode = ""
            else:
                num_bytes = 1
                mnemonic = "???"
                mode = ""

            # Build hex dump
            hex_bytes = [f"{self.drive8.memory.read(pc + i):02X}"
                        for i in range(min(num_bytes, 3))]
            hex_str = " ".join(hex_bytes).ljust(8)

            # Build operand display
            if num_bytes == 1:
                operand_str = ""
            elif num_bytes == 2:
                operand_str = f" ${b1:02X}"
            else:
                operand = (b2 << 8) | b1
                operand_str = f" ${operand:04X}"

            if mode:
                inst_display = f"{hex_str}  {mnemonic}{operand_str}  ; {mode}"
            else:
                inst_display = f"{hex_str}  {mnemonic}{operand_str}"

        except Exception:
            inst_display = "???"
            color = "\033[91m"  # Red for errors

        # Apply color to instruction display
        colored_inst = f"{color}{inst_display:20s}{RESET}"

        return (f"1541: Cycles: {drive_cpu.cycles_executed:,} | "
                f"PC=${pc:04X}[{region}] {colored_inst} | "
                f"A=${drive_cpu.A:02X} X=${drive_cpu.X:02X} "
                f"Y=${drive_cpu.Y:02X} S=${drive_cpu.S & 0xFF:02X} P={flags}")

    @property

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

    def dump_crash_report(self, exception: Exception = None) -> None:
        """Dump comprehensive crash report for illegal instruction or other CPU errors.

        Arguments:
            exception: The exception that triggered the crash (optional)
        """
        print("\n" + "=" * 70)
        print("CRASH REPORT - Illegal Instruction")
        print("=" * 70)

        # Show exception info
        if exception:
            print(f"\nException: {type(exception).__name__}: {exception}")

        # CPU state
        pc = int(self.cpu.PC)
        opcode = self.cpu.ram[pc]
        print(f"\nCPU State at crash:")
        print(f"  PC:     ${pc:04X}  (opcode: ${opcode:02X})")
        print(f"  A:      ${self.cpu.A:02X}")
        print(f"  X:      ${self.cpu.X:02X}")
        print(f"  Y:      ${self.cpu.Y:02X}")
        print(f"  S:      ${self.cpu.S & 0xFF:02X}  (stack pointer)")
        print(f"  P:      ${self.cpu._flags.value:02X}  (N={int(self.cpu.N)} V={int(self.cpu.V)} B={int(self.cpu.B)} D={int(self.cpu.D)} I={int(self.cpu.I)} Z={int(self.cpu.Z)} C={int(self.cpu.C)})")
        print(f"  Cycles: {self.cpu.cycles_executed:,}")

        # Memory region
        region = "RAM"
        if 0xA000 <= pc <= 0xBFFF and (self.memory.read(1) & 0x03):
            region = "BASIC ROM"
        elif 0xD000 <= pc <= 0xDFFF:
            region = "I/O" if (self.memory.read(1) & 0x04) else "CHAR ROM"
        elif 0xE000 <= pc <= 0xFFFF and (self.memory.read(1) & 0x02):
            region = "KERNAL ROM"
        print(f"  Region: {region}")

        # Stack contents (show 16 bytes from current SP)
        sp = self.cpu.S & 0xFF
        print(f"\nStack (${sp:02X} -> $FF):")
        stack_addr = 0x0100 + sp
        print("       ", end="")
        for i in range(16):
            print(f" {i:02X}", end="")
        print()
        for row_start in range(stack_addr, 0x0200, 16):
            if row_start >= 0x0200:
                break
            print(f"  {row_start:04X}:", end="")
            for offset in range(16):
                addr = row_start + offset
                if addr < 0x0200:
                    print(f" {self.cpu.ram[addr]:02X}", end="")
                else:
                    print("   ", end="")
            print()

        # Disassembly around crash
        print(f"\nDisassembly around PC ${pc:04X}:")
        try:
            start_addr = max(0, pc - 16)
            self.show_disassembly(start_addr, num_instructions=20)
        except Exception as e:
            print(f"  Could not disassemble: {e}")

        # Memory around PC
        print(f"\nMemory around PC ${pc:04X}:")
        mem_start = max(0, pc - 32)
        mem_end = min(0xFFFF, pc + 32)
        self.dump_memory(mem_start, mem_end)

        # Zero page (important for 6502)
        print("\nZero page ($00-$FF):")
        self.dump_memory(0x00, 0xFF)

        # Key C64 memory locations
        print("\nKey C64 Memory Locations:")
        print(f"  $00 (DDR):       ${self.cpu.ram[0x00]:02X}")
        print(f"  $01 (Bank):      ${self.cpu.ram[0x01]:02X}")
        print(f"  $90 (KERNAL ST): ${self.cpu.ram[0x90]:02X}")
        print(f"  $9D (Direct):    ${self.cpu.ram[0x9D]:02X}")
        print(f"  $2B-$2C (TXTTAB):${self.cpu.ram[0x2B]:02X}{self.cpu.ram[0x2C]:02X}")
        print(f"  $2D-$2E (VARTAB):${self.cpu.ram[0x2D]:02X}{self.cpu.ram[0x2E]:02X}")

        # Vectors
        print("\nInterrupt Vectors:")
        nmi = self.cpu.ram[0xFFFA] | (self.cpu.ram[0xFFFB] << 8)
        reset = self.cpu.ram[0xFFFC] | (self.cpu.ram[0xFFFD] << 8)
        irq = self.cpu.ram[0xFFFE] | (self.cpu.ram[0xFFFF] << 8)
        print(f"  NMI:   ${nmi:04X}")
        print(f"  RESET: ${reset:04X}")
        print(f"  IRQ:   ${irq:04X}")

        print("\n" + "=" * 70)
        print("END CRASH REPORT")
        print("=" * 70 + "\n")

    def get_speed_stats(self) -> Optional[dict]:
        """Calculate CPU execution speed statistics.

        Returns:
            Dictionary with speed stats, or None if timing data not available:
            - elapsed_seconds: Wall-clock time elapsed
            - cycles_executed: Total CPU cycles executed
            - cycles_per_second: Actual execution rate (lifetime average)
            - rolling_cycles_per_second: Rolling average over last 10 seconds (if available)
            - real_cpu_freq: Real C64 CPU frequency for this chip
            - speedup: Ratio of actual speed to real hardware speed (lifetime)
            - rolling_speedup: Ratio based on rolling average (if available)
            - chip_name: VIC-II chip name (6569, 6567R8, etc.)
        """
        if self._execution_start_time is None:
            return None

        import time
        end_time = self._execution_end_time or time.perf_counter()
        elapsed = end_time - self._execution_start_time

        if elapsed <= 0:
            return None

        cycles_executed = self.cpu.cycles_executed
        cycles_per_second = cycles_executed / elapsed
        real_cpu_freq = self.video_timing.cpu_freq
        speedup = cycles_per_second / real_cpu_freq

        result = {
            "elapsed_seconds": elapsed,
            "cycles_executed": cycles_executed,
            "cycles_per_second": cycles_per_second,
            "real_cpu_freq": real_cpu_freq,
            "speedup": speedup,
            "chip_name": self.video_timing.chip_name,
        }

        # Add rolling average if we have samples
        if self._speed_samples:
            rolling_cps = sum(self._speed_samples) / len(self._speed_samples)
            result["rolling_cycles_per_second"] = rolling_cps
            result["rolling_speedup"] = rolling_cps / real_cpu_freq

        return result

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

        # Show speed stats if available
        stats = self.get_speed_stats()
        if stats:
            chip = stats['chip_name']
            region = "PAL" if chip == "6569" else "NTSC"
            actual_mhz = stats['cycles_per_second'] / 1e6
            print(f"  Speed: {stats['cycles_per_second']:,.0f} ({actual_mhz:.3f}MHz) cycles/sec "
                  f"({stats['speedup']:.1%} of {region} ({chip}) C64 @ "
                  f"{stats['real_cpu_freq']/1e6:.3f}MHz)")

    def disassemble_at(self, address: int, num_instructions: int = 10) -> List[str]:
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
