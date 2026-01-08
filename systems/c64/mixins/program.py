"""C64 Program Mixin.

Mixin for program loading.
"""

from mos6502.compat import logging, Path, Optional, Tuple
from c64.memory import BASIC_PROGRAM_START

log = logging.getLogger("c64")


class C64ProgramMixin:
    """Mixin for program loading."""

    def load_program(
        self, program_path: Path, load_address: Optional[int] = None
    ) -> Tuple[int, int]:
        """Load a program into memory.

        Arguments:
            program_path: Path to the program file
            load_address: Address to load program at (default: $0801 for BASIC programs)
                         If None and file has a 2-byte header, use header address

        Returns:
            Tuple of (load_address, end_address) - the address range used
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
            load_address = BASIC_PROGRAM_START

        # Write program to memory
        for offset, byte_value in enumerate(program_data):
            self.cpu.ram[load_address + offset] = byte_value

        end_address = load_address + len(program_data)

        log.info(
            f"Loaded program: {program_path.name} "
            f"at ${load_address:04X}-${end_address - 1:04X} "
            f"({len(program_data)} bytes)"
        )

        return load_address, end_address

    def update_basic_pointers(self, program_end: int) -> None:
        """Update BASIC memory pointers after loading a program.

        When loading a BASIC program at $0801, BASIC's internal pointers
        must be updated so that RUN knows where the program ends.

        Arguments:
            program_end: Address immediately after the last byte of the program
        """
        # VARTAB, ARYTAB, and STREND should all point to the end of the program
        # (They get properly set up when BASIC parses the program, but for
        # directly loaded programs we need to set them manually)
        lo = program_end & 0xFF
        hi = (program_end >> 8) & 0xFF

        # Set VARTAB (start of variables = end of program)
        self.cpu.ram[self.VARTAB] = lo
        self.cpu.ram[self.VARTAB + 1] = hi

        # Set ARYTAB (start of arrays = end of variables)
        self.cpu.ram[self.ARYTAB] = lo
        self.cpu.ram[self.ARYTAB + 1] = hi

        # Set STREND (end of arrays = bottom of strings)
        self.cpu.ram[self.STREND] = lo
        self.cpu.ram[self.STREND + 1] = hi

        log.info(f"Updated BASIC pointers: VARTAB/ARYTAB/STREND = ${program_end:04X}")
