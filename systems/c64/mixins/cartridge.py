"""C64 Cartridge Mixin.

Mixin for cartridge loading and management.
"""

from mos6502.compat import logging, Path, List, Dict
from c64.cartridges import (
    Cartridge,
    CartridgeTestResults,
    StaticROMCartridge,
    ErrorCartridge,
    CARTRIDGE_TYPES,
    create_cartridge,
    create_error_cartridge_rom,
    ROML_START,
    ROML_END,
    ROML_SIZE,
    ROMH_START,
    ROMH_END,
    IO1_START,
    IO1_END,
    IO2_START,
    IO2_END,
)

log = logging.getLogger("c64")


class C64CartridgeMixin:
    """Mixin for cartridge loading and management."""

    def load_cartridge(self, path: Path, cart_type: str = "auto") -> None:
        """Load a cartridge ROM file.

        Supports:
        - Raw binary files (.bin, .rom): 8KB or 16KB
        - CRT files (.crt): Standard C64 cartridge format with header

        Arguments:
            path: Path to cartridge file
            cart_type: "auto" (detect from file), "8k", or "16k"

        Raises:
            FileNotFoundError: If cartridge file doesn't exist
            ValueError: If cartridge format is invalid or unsupported
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Cartridge file not found: {path}")

        data = path.read_bytes()
        suffix = path.suffix.lower()

        # Check for CRT format (has "C64 CARTRIDGE" signature)
        if suffix == ".crt" or data[:16] == b"C64 CARTRIDGE   ":
            self._load_crt_cartridge(data, path)
        else:
            # Raw binary format
            self._load_raw_cartridge(data, path, cart_type)

        # Log cartridge status
        if self.memory is not None and self.memory.cartridge is not None:
            cart = self.memory.cartridge
            log.info(
                f"Cartridge loaded: {path.name} "
                f"(type: {self.cartridge_type}, EXROM={0 if not cart.exrom else 1}, GAME={0 if not cart.game else 1})"
            )

    def _load_raw_cartridge(self, data: bytes, path: Path, cart_type: str) -> None:
        """Load a raw binary cartridge file.

        Arguments:
            data: Raw cartridge data
            path: Path to cartridge file (for error messages)
            cart_type: "auto", "8k", "16k", or "ultimax"

        Raises:
            ValueError: If size doesn't match expected cartridge size
        """
        size = len(data)

        # Determine cartridge type from size and content if auto
        if cart_type == "auto":
            if size == self.ROML_SIZE:
                # 8KB file - check if it's a standard 8K cart or Ultimax
                # Standard 8K carts have CBM80 signature at offset 4 ($8004)
                # Ultimax carts have reset vector at end pointing to $E000-$FFFF
                has_cbm80 = data[4:9] == b"CBM80"

                if has_cbm80:
                    cart_type = "8k"
                    log.debug(f"Auto-detected 8K cartridge (CBM80 signature found)")
                else:
                    # Check reset vector at end of file (offsets $1FFC/$1FFD)
                    # For Ultimax, this should point to $E000-$FFFF range
                    reset_lo = data[0x1FFC]
                    reset_hi = data[0x1FFD]
                    reset_vector = reset_lo | (reset_hi << 8)

                    if 0xE000 <= reset_vector <= 0xFFFF:
                        cart_type = "ultimax"
                        log.info(
                            f"Auto-detected Ultimax cartridge: reset vector ${reset_vector:04X} "
                            f"points to cartridge ROM space"
                        )
                    else:
                        # Default to 8K if we can't determine
                        cart_type = "8k"
                        log.debug(
                            f"Assuming 8K cartridge (no CBM80, reset vector ${reset_vector:04X})"
                        )
            elif size == self.ROML_SIZE + self.ROMH_SIZE:
                cart_type = "16k"
            else:
                raise ValueError(
                    f"Cannot auto-detect cartridge type for {path.name}: "
                    f"size {size} bytes (expected 8192 or 16384)"
                )

        # Validate size matches specified type and create Cartridge object
        if cart_type == "8k":
            if size != self.ROML_SIZE:
                raise ValueError(
                    f"8K cartridge {path.name} has wrong size: "
                    f"{size} bytes (expected {self.ROML_SIZE})"
                )
            cartridge = StaticROMCartridge(
                roml_data=data,
                romh_data=None,
                name=path.stem,
            )
            self.cartridge_type = "8k"
        elif cart_type == "16k":
            if size != self.ROML_SIZE + self.ROMH_SIZE:
                raise ValueError(
                    f"16K cartridge {path.name} has wrong size: "
                    f"{size} bytes (expected {self.ROML_SIZE + self.ROMH_SIZE})"
                )
            cartridge = StaticROMCartridge(
                roml_data=data[:self.ROML_SIZE],
                romh_data=data[self.ROML_SIZE:],
                name=path.stem,
            )
            self.cartridge_type = "16k"
        elif cart_type == "ultimax":
            if size != self.ROMH_SIZE:
                raise ValueError(
                    f"Ultimax cartridge {path.name} has wrong size: "
                    f"{size} bytes (expected {self.ROMH_SIZE})"
                )
            cartridge = StaticROMCartridge(
                roml_data=None,
                romh_data=None,
                ultimax_romh_data=data,
                name=path.stem,
            )
            self.cartridge_type = "ultimax"
        else:
            raise ValueError(f"Unknown cartridge type: {cart_type}")

        # Attach cartridge to memory handler
        if self.memory is not None:
            self.memory.cartridge = cartridge

        log.info(f"Loaded raw {cart_type.upper()} cartridge: {path.name} ({size} bytes)")

    def _create_error_cartridge(self, error_lines: List[str]) -> bytes:
        """Create an 8KB cartridge ROM that displays an error message.

        This is used when an unsupported cartridge type is loaded, to give
        the user a friendly on-screen message instead of crashing.

        Arguments:
            error_lines: List of text lines to display (max ~38 chars each)

        Returns:
            8KB cartridge ROM data
        """
        # Use the shared function from cartridges module (single source of truth)
        return create_error_cartridge_rom(error_lines, border_color=0x02)

    def _load_error_cartridge_with_results(self, results: CartridgeTestResults) -> None:
        """Generate and load an error cartridge displaying test results.

        Arguments:
            results: CartridgeTestResults with current pass/fail state
        """
        error_lines = results.to_display_lines()
        error_roml_data = self._create_error_cartridge(error_lines)

        # Create ErrorCartridge object
        cartridge = ErrorCartridge(
            roml_data=error_roml_data,
            original_type=results.hardware_type,
            original_name=results.cart_name,
        )
        self.cartridge_type = "error"

        # Attach cartridge to memory handler
        if self.memory is not None:
            self.memory.cartridge = cartridge

        log.info(f"Loaded error cartridge with test results for type {results.hardware_type}")

    def _load_crt_cartridge(self, data: bytes, path: Path) -> None:
        """Load a CRT format cartridge file.

        CRT format:
        - 64-byte header with signature, hardware type, EXROM/GAME lines
        - CHIP packets containing ROM data with load addresses

        Arguments:
            data: CRT file data
            path: Path to cartridge file (for error messages)

        Raises:
            ValueError: If CRT format is invalid or unsupported
        """
        # Create test results - starts with all FAILs
        results = CartridgeTestResults()

        # Validate CRT header size
        if len(data) < 64:
            # Generate error cart with current results (all FAIL)
            self._load_error_cartridge_with_results(results)
            return

        results.header_size_valid = True

        # Check signature
        signature = data[:16]
        if signature != b"C64 CARTRIDGE   ":
            # Generate error cart with current results
            self._load_error_cartridge_with_results(results)
            return

        results.signature_valid = True

        # Parse header (big-endian values)
        header_length = int.from_bytes(data[0x10:0x14], "big")
        version_hi = data[0x14]
        version_lo = data[0x15]
        hardware_type = int.from_bytes(data[0x16:0x18], "big")
        exrom_line = data[0x18]
        game_line = data[0x19]
        cart_name = data[0x20:0x40].rstrip(b"\x00").decode("latin-1", errors="replace")

        # Update results with parsed values
        results.version_valid = True  # We parsed it successfully
        results.hardware_type = hardware_type
        results.hardware_name = self.CRT_HARDWARE_TYPES.get(hardware_type, f"Unknown type {hardware_type}")
        results.exrom_line = exrom_line
        results.game_line = game_line
        results.cart_name = cart_name

        log.info(
            f"CRT header: name='{cart_name}', version={version_hi}.{version_lo}, "
            f"hardware_type={hardware_type} ({results.hardware_name}), EXROM={exrom_line}, GAME={game_line}"
        )

        # Check if hardware type is supported
        mapper_supported = hardware_type in CARTRIDGE_TYPES
        if mapper_supported:
            results.mapper_supported = True
        else:
            log.warning(
                f"Unsupported cartridge type {hardware_type} ({results.hardware_name}). "
                f"Will parse CHIP packets for diagnostics."
            )

        # Parse CHIP packets (even for unsupported types, for diagnostics)
        offset = header_length

        # For Type 0 (standard cartridge)
        roml_data = None
        romh_data = None
        ultimax_romh_data = None

        # For banked cartridges (Type 1+)
        banks: Dict[int, bytes] = {}  # bank_number -> rom_data

        # Ultimax mode detection from CRT header
        # EXROM=1, GAME=0 indicates Ultimax mode
        is_ultimax = (exrom_line == 1 and game_line == 0)

        while offset < len(data):
            if offset + 16 > len(data):
                break  # Not enough data for another CHIP header

            chip_sig = data[offset:offset + 4]
            if chip_sig != b"CHIP":
                # Invalid CHIP signature - generate error cart with results so far
                self._load_error_cartridge_with_results(results)
                return

            packet_length = int.from_bytes(data[offset + 4:offset + 8], "big")
            chip_type = int.from_bytes(data[offset + 8:offset + 10], "big")
            bank_number = int.from_bytes(data[offset + 10:offset + 12], "big")
            load_address = int.from_bytes(data[offset + 12:offset + 14], "big")
            rom_size = int.from_bytes(data[offset + 14:offset + 16], "big")

            log.debug(
                f"CHIP packet: type={chip_type}, bank={bank_number}, "
                f"load=${load_address:04X}, size={rom_size}"
            )

            # Track that we found a CHIP packet
            results.chip_count += 1
            results.chip_packets_found = True

            # Only handle ROM chips (type 0) for now
            if chip_type != 0:
                log.warning(f"Skipping non-ROM CHIP type {chip_type}")
                offset += packet_length
                continue

            # Extract ROM data
            rom_data = data[offset + 16:offset + 16 + rom_size]

            if hardware_type == 0:
                # Type 0: Standard cartridge - single bank only
                if bank_number != 0:
                    log.warning(f"Skipping bank {bank_number} for Type 0 cartridge")
                    offset += packet_length
                    continue

                if load_address == self.ROML_START:
                    # Check if this is a 16KB ROM that needs to be split
                    if rom_size > self.ROML_SIZE:
                        # Split 16KB ROM: first 8KB to ROML, second 8KB to ROMH
                        roml_data = rom_data[:self.ROML_SIZE]
                        romh_data = rom_data[self.ROML_SIZE:]
                        results.roml_valid = True
                        results.romh_valid = True
                        log.info(f"Loaded ROML: ${load_address:04X}-${load_address + self.ROML_SIZE - 1:04X} ({self.ROML_SIZE} bytes)")
                        log.info(f"Loaded ROMH: ${self.ROMH_START:04X}-${self.ROMH_START + len(romh_data) - 1:04X} ({len(romh_data)} bytes)")
                    else:
                        roml_data = rom_data
                        results.roml_valid = True
                        log.info(f"Loaded ROML: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                elif load_address == self.ROMH_START:
                    romh_data = rom_data
                    results.romh_valid = True
                    log.info(f"Loaded ROMH: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                elif load_address == KERNAL_ROM_START:
                    # Ultimax mode: ROM at $E000-$FFFF replaces KERNAL
                    ultimax_romh_data = rom_data
                    results.ultimax_romh_valid = True
                    log.info(f"Loaded Ultimax ROMH: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                else:
                    log.warning(f"Unknown CHIP load address: ${load_address:04X}")
            elif hardware_type == 3:
                # Type 3: Final Cartridge III - 4 x 16KB banks
                # Each bank is a single 16KB CHIP packet at $8000
                if load_address == self.ROML_START:
                    banks[bank_number] = rom_data
                    results.roml_valid = True
                    results.bank_switching_valid = len(banks) > 1
                    log.info(f"Loaded FC3 bank {bank_number}: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                else:
                    log.warning(f"Unknown CHIP load address for Type 3: ${load_address:04X}")
            elif hardware_type == 4 or hardware_type == 13:
                # Type 4: Simons' BASIC - 16KB cartridge with ROML + ROMH
                # Type 13: Final Cartridge I - 16KB cartridge with ROML + ROMH
                # Two CHIP packets: one for ROML at $8000, one for ROMH at $A000
                if load_address == self.ROML_START:
                    roml_data = rom_data
                    results.roml_valid = True
                    log.info(f"Loaded ROML: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                elif load_address == self.ROMH_START:
                    romh_data = rom_data
                    results.romh_valid = True
                    log.info(f"Loaded ROMH: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                else:
                    log.warning(f"Unknown CHIP load address for Type {hardware_type}: ${load_address:04X}")
            else:
                # Banked cartridges (Type 1, 5+): Collect all banks
                # Each bank is typically 8KB at $8000
                if load_address == self.ROML_START:
                    banks[bank_number] = rom_data
                    results.roml_valid = True  # At least one bank loaded to ROML region
                    results.bank_switching_valid = len(banks) > 1  # Multiple banks = bank switching works
                    log.info(f"Loaded bank {bank_number}: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                else:
                    log.warning(f"Unexpected load address ${load_address:04X} for bank {bank_number}")

            offset += packet_length

        # If mapper not supported, generate error cart with diagnostics
        if not mapper_supported:
            self._load_error_cartridge_with_results(results)
            return

        # Create appropriate cartridge object based on hardware type
        if hardware_type == 0:
            # Validate we got valid ROM data for Type 0
            if ultimax_romh_data is None and roml_data is None:
                # No usable ROM data - generate error cart
                self._load_error_cartridge_with_results(results)
                return

            cartridge = create_cartridge(
                hardware_type=0,
                roml_data=roml_data,
                romh_data=romh_data,
                ultimax_romh_data=ultimax_romh_data,
                name=cart_name,
            )

            # Determine cartridge type from what we loaded
            if ultimax_romh_data is not None:
                self.cartridge_type = "ultimax"
            elif romh_data is not None:
                self.cartridge_type = "16k"
            else:
                self.cartridge_type = "8k"
        elif hardware_type == 4:
            # Type 4: Simons' BASIC - needs both ROML and ROMH
            if roml_data is None or romh_data is None:
                # Missing ROM data - generate error cart
                self._load_error_cartridge_with_results(results)
                return

            cartridge = create_cartridge(
                hardware_type=4,
                roml_data=roml_data,
                romh_data=romh_data,
                name=cart_name,
            )
            self.cartridge_type = "simons_basic"
        elif hardware_type == 13:
            # Type 13: Final Cartridge I - needs both ROML and ROMH
            if roml_data is None:
                # Missing ROM data - generate error cart
                self._load_error_cartridge_with_results(results)
                return

            cartridge = create_cartridge(
                hardware_type=13,
                roml_data=roml_data,
                romh_data=romh_data,
                name=cart_name,
            )
            self.cartridge_type = "final_cartridge_i"
        else:
            # Banked cartridges - convert bank dict to sorted list
            if not banks:
                # No bank data - generate error cart
                self._load_error_cartridge_with_results(results)
                return

            # Create sorted list of banks (fill missing banks with empty data)
            max_bank = max(banks.keys())
            bank_list = []
            for i in range(max_bank + 1):
                if i in banks:
                    bank_list.append(banks[i])
                else:
                    # Fill missing banks with empty 8KB
                    log.warning(f"Bank {i} missing, filling with empty data")
                    bank_list.append(bytes(ROML_SIZE))

            cartridge = create_cartridge(
                hardware_type=hardware_type,
                banks=bank_list,
                name=cart_name,
            )
            self.cartridge_type = results.hardware_name.lower().replace(" ", "_")

        # Mark as fully loaded
        results.fully_loaded = True

        # Attach cartridge to memory handler
        if self.memory is not None:
            self.memory.cartridge = cartridge

        log.info(f"Loaded CRT cartridge: '{cart_name}' (type {hardware_type}: {results.hardware_name})")
