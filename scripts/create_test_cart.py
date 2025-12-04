#!/usr/bin/env python3
"""Create test cartridges that display messages on screen.

Usage:
    python scripts/create_test_cart.py

Creates:
    tests/fixtures/test_cart_8k.bin  - Raw 8KB cartridge (ROML only)
    tests/fixtures/test_cart_8k.crt  - CRT format 8KB cartridge
    tests/fixtures/test_cart_16k.bin - Raw 16KB cartridge (ROML + ROMH)
    tests/fixtures/test_cart_16k.crt - CRT format 16KB cartridge
"""
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "systems"))

from c64 import C64


def text_to_screen_codes(text: str) -> list[int]:
    """Convert ASCII text to C64 screen codes."""
    screen_codes = []
    for ch in text:
        if 'A' <= ch <= 'Z':
            screen_codes.append(ord(ch) - ord('A') + 1)
        elif 'a' <= ch <= 'z':
            screen_codes.append(ord(ch) - ord('a') + 1)
        elif '0' <= ch <= '9':
            screen_codes.append(ord(ch) - ord('0') + 0x30)
        elif ch == ' ':
            screen_codes.append(0x20)
        elif ch == '!':
            screen_codes.append(0x21)
        elif ch == '.':
            screen_codes.append(0x2E)
        elif ch == ',':
            screen_codes.append(0x2C)
        elif ch == ':':
            screen_codes.append(0x3A)
        elif ch == '-':
            screen_codes.append(0x2D)
        elif ch == '+':
            screen_codes.append(0x2B)
        elif ch == '=':
            screen_codes.append(0x3D)
        elif ch == '$':
            screen_codes.append(0x24)
        else:
            screen_codes.append(0x20)  # space for unknown
    return screen_codes


def create_display_code(message: str, line: int = 0, color: int = 0x01) -> list[int]:
    """Create code to display a message on a specific screen line.

    Args:
        message: Text to display (max 40 chars)
        line: Screen line (0-24)
        color: Color value (0-15)

    Returns:
        List of machine code bytes
    """
    code = []
    screen_codes = text_to_screen_codes(message)
    start_pos = (40 - len(message)) // 2
    screen_addr = 0x0400 + (line * 40) + start_pos
    color_addr = 0xD800 + (line * 40) + start_pos

    # Write each character and its color
    for i, sc in enumerate(screen_codes):
        # Write character to screen RAM
        code.extend([
            0xA9, sc,                                    # LDA #screen_code
            0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,  # STA screen_addr
        ])
        # Write color to color RAM
        code.extend([
            0xA9, color,                                 # LDA #color
            0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,    # STA color_addr
        ])

    return code


def create_8k_cartridge() -> tuple[bytes, str]:
    """Create an 8KB test cartridge.

    Returns:
        Tuple of (cartridge bytes, description)
    """
    cart = bytearray(C64.ROML_SIZE)

    # Cartridge header at $8000-$8008
    cart[0x0000] = 0x09  # Cold start lo -> $8009
    cart[0x0001] = 0x80  # Cold start hi
    cart[0x0002] = 0x09  # Warm start lo -> $8009
    cart[0x0003] = 0x80  # Warm start hi
    cart[0x0004] = 0xC3  # 'C' (CBM80 signature)
    cart[0x0005] = 0xC2  # 'B'
    cart[0x0006] = 0xCD  # 'M'
    cart[0x0007] = 0x38  # '8'
    cart[0x0008] = 0x30  # '0'

    # Code starts at $8009
    code_offset = 0x0009
    code = []

    # Initialize - disable interrupts, set up stack
    code.extend([
        0x78,              # SEI - disable interrupts
        0xA2, 0xFF,        # LDX #$FF
        0x9A,              # TXS - set stack pointer
    ])

    # Clear screen by filling $0400-$07E7 with spaces (0x20)
    code.extend([
        0xA9, 0x20,        # LDA #$20 (space)
        0xA2, 0x00,        # LDX #$00
    ])
    # clear_loop:
    code.extend([
        0x9D, 0x00, 0x04,  # STA $0400,X
        0x9D, 0x00, 0x05,  # STA $0500,X
        0x9D, 0x00, 0x06,  # STA $0600,X
        0x9D, 0x00, 0x07,  # STA $0700,X
        0xE8,              # INX
        0xD0, 0xF1,        # BNE clear_loop (branch back -15 bytes)
    ])

    # Set border and background to blue
    code.extend([
        0xA9, 0x06,        # LDA #$06 (blue)
        0x8D, 0x20, 0xD0,  # STA $D020 (border color)
        0x8D, 0x21, 0xD0,  # STA $D021 (background color)
    ])

    # Display messages
    code.extend(create_display_code("8K CARTRIDGE TEST", line=0, color=0x01))  # white
    code.extend(create_display_code("ROML AT $8000-$9FFF", line=2, color=0x07))  # yellow
    code.extend(create_display_code("EXROM=0 GAME=1", line=4, color=0x05))  # green

    # Infinite loop
    loop_addr = C64.ROML_START + code_offset + len(code)
    code.extend([
        0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,  # JMP to self
    ])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        cart[code_offset + i] = byte

    return bytes(cart), f"Code size: {len(code)} bytes starting at $8009"


def create_16k_cartridge() -> tuple[bytes, bytes, str]:
    """Create a 16KB test cartridge with code split between ROML and ROMH.

    The cartridge demonstrates that both ROML ($8000) and ROMH ($A000) are
    accessible by calling a subroutine in ROMH from ROML.

    Returns:
        Tuple of (ROML bytes, ROMH bytes, description)
    """
    roml = bytearray(C64.ROML_SIZE)
    romh = bytearray(C64.ROMH_SIZE)

    # === ROML at $8000-$9FFF ===

    # Cartridge header at $8000-$8008
    roml[0x0000] = 0x09  # Cold start lo -> $8009
    roml[0x0001] = 0x80  # Cold start hi
    roml[0x0002] = 0x09  # Warm start lo -> $8009
    roml[0x0003] = 0x80  # Warm start hi
    roml[0x0004] = 0xC3  # 'C' (CBM80 signature)
    roml[0x0005] = 0xC2  # 'B'
    roml[0x0006] = 0xCD  # 'M'
    roml[0x0007] = 0x38  # '8'
    roml[0x0008] = 0x30  # '0'

    # Code starts at $8009
    code_offset = 0x0009
    code = []

    # Initialize - disable interrupts, set up stack
    code.extend([
        0x78,              # SEI - disable interrupts
        0xA2, 0xFF,        # LDX #$FF
        0x9A,              # TXS - set stack pointer
    ])

    # Clear screen
    code.extend([
        0xA9, 0x20,        # LDA #$20 (space)
        0xA2, 0x00,        # LDX #$00
    ])
    code.extend([
        0x9D, 0x00, 0x04,  # STA $0400,X
        0x9D, 0x00, 0x05,  # STA $0500,X
        0x9D, 0x00, 0x06,  # STA $0600,X
        0x9D, 0x00, 0x07,  # STA $0700,X
        0xE8,              # INX
        0xD0, 0xF1,        # BNE clear_loop
    ])

    # Set border and background to dark gray
    code.extend([
        0xA9, 0x0B,        # LDA #$0B (dark gray)
        0x8D, 0x20, 0xD0,  # STA $D020 (border color)
        0x8D, 0x21, 0xD0,  # STA $D021 (background color)
    ])

    # Display ROML messages
    code.extend(create_display_code("16K CARTRIDGE TEST", line=0, color=0x01))  # white
    code.extend(create_display_code("CODE IN ROML $8000", line=2, color=0x07))  # yellow

    # Call subroutine in ROMH to prove it's accessible
    # JSR $A000
    code.extend([
        0x20, 0x00, 0xA0,  # JSR $A000 (subroutine in ROMH)
    ])

    # Display success message (we returned from ROMH!)
    code.extend(create_display_code("RETURNED FROM ROMH!", line=6, color=0x05))  # green
    code.extend(create_display_code("EXROM=0 GAME=0", line=8, color=0x03))  # cyan

    # Infinite loop
    loop_addr = C64.ROML_START + code_offset + len(code)
    code.extend([
        0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,  # JMP to self
    ])

    # Copy code into ROML
    for i, byte in enumerate(code):
        roml[code_offset + i] = byte

    # === ROMH at $A000-$BFFF ===

    # Subroutine at $A000 that displays a message and returns
    romh_code = []

    # Display message from ROMH
    romh_code.extend(create_display_code("HELLO FROM ROMH $A000", line=4, color=0x0E))  # light blue

    # Return to caller
    romh_code.extend([
        0x60,  # RTS
    ])

    # Copy code into ROMH
    for i, byte in enumerate(romh_code):
        romh[i] = byte

    desc = f"ROML code: {len(code)} bytes, ROMH code: {len(romh_code)} bytes"
    return bytes(roml), bytes(romh), desc


def write_raw_cartridge(path: Path, roml: bytes, romh: bytes | None = None) -> None:
    """Write a raw binary cartridge file."""
    with open(path, 'wb') as f:
        f.write(roml)
        if romh is not None:
            f.write(romh)


def create_error_cartridge(hw_type: int, type_name: str) -> bytes:
    """Create an 8KB error cartridge that displays the unsupported type info.

    Args:
        hw_type: CRT hardware type number
        type_name: Human-readable name of the cartridge type

    Returns:
        8KB cartridge ROM data
    """
    cart = bytearray(C64.ROML_SIZE)

    # Cartridge header at $8000-$8008
    cart[0x0000] = 0x09  # Cold start lo -> $8009
    cart[0x0001] = 0x80  # Cold start hi
    cart[0x0002] = 0x09  # Warm start lo -> $8009
    cart[0x0003] = 0x80  # Warm start hi
    cart[0x0004] = 0xC3  # 'C' (CBM80 signature)
    cart[0x0005] = 0xC2  # 'B'
    cart[0x0006] = 0xCD  # 'M'
    cart[0x0007] = 0x38  # '8'
    cart[0x0008] = 0x30  # '0'

    # Code starts at $8009
    code_offset = 0x0009
    code = []

    # Initialize - disable interrupts, set up stack
    code.extend([
        0x78,              # SEI - disable interrupts
        0xA2, 0xFF,        # LDX #$FF
        0x9A,              # TXS - set stack pointer
    ])

    # Clear screen by filling $0400-$07E7 with spaces (0x20)
    code.extend([
        0xA9, 0x20,        # LDA #$20 (space)
        0xA2, 0x00,        # LDX #$00
    ])
    # clear_loop:
    code.extend([
        0x9D, 0x00, 0x04,  # STA $0400,X
        0x9D, 0x00, 0x05,  # STA $0500,X
        0x9D, 0x00, 0x06,  # STA $0600,X
        0x9D, 0x00, 0x07,  # STA $0700,X
        0xE8,              # INX
        0xD0, 0xF1,        # BNE clear_loop (branch back -15 bytes)
    ])

    # Set border and background to red
    code.extend([
        0xA9, 0x02,        # LDA #$02 (red)
        0x8D, 0x20, 0xD0,  # STA $D020 (border color)
        0x8D, 0x21, 0xD0,  # STA $D021 (background color)
    ])

    # Display messages
    lines = [
        ("UNSUPPORTED CARTRIDGE TYPE", 1, 0x01),   # white
        ("", 3, 0x01),
        (f"TYPE: {hw_type}", 4, 0x07),             # yellow
        (f"NAME: {type_name.upper()}", 6, 0x07),   # yellow
        ("", 8, 0x01),
        ("THIS CARTRIDGE TYPE REQUIRES", 9, 0x05),  # green
        ("BANK SWITCHING HARDWARE THAT", 10, 0x05),
        ("IS NOT YET IMPLEMENTED.", 11, 0x05),
        ("", 13, 0x01),
        ("ONLY TYPE 0 (NORMAL CARTRIDGE)", 14, 0x0E),  # light blue
        ("IS CURRENTLY SUPPORTED.", 15, 0x0E),
    ]

    for text, line, color in lines:
        code.extend(create_display_code(text, line=line, color=color))

    # Infinite loop
    loop_addr = C64.ROML_START + code_offset + len(code)
    code.extend([
        0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,  # JMP to self
    ])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        cart[code_offset + i] = byte

    return bytes(cart)


def write_crt_cartridge(
    path: Path,
    roml: bytes,
    romh: bytes | None = None,
    name: str = "TEST",
    single_chip: bool = False,
    hardware_type: int = 0,
    exrom: int | None = None,
    game: int | None = None,
) -> None:
    """Write a CRT format cartridge file.

    Args:
        path: Output file path
        roml: ROML data (8KB, $8000-$9FFF)
        romh: ROMH data (8KB, $A000-$BFFF) or None for 8K carts
        name: Cartridge name (max 32 chars)
        single_chip: If True and romh is provided, write as single 16KB CHIP packet
                     at $8000 (like many real-world cartridges). If False, write
                     as two separate CHIP packets (ROML at $8000, ROMH at $A000).
        hardware_type: CRT hardware type ID (0-85)
        exrom: EXROM line state (0=active, 1=inactive). If None, defaults based on size.
        game: GAME line state (0=active, 1=inactive). If None, defaults based on size.
    """
    is_16k = romh is not None

    # Default EXROM/GAME based on cartridge size if not specified
    if exrom is None:
        exrom = 0  # Active (cartridge present)
    if game is None:
        game = 0 if is_16k else 1  # 0 for 16K, 1 for 8K

    # CRT Header (64 bytes)
    header = bytearray(64)
    header[0:16] = b'C64 CARTRIDGE   '  # Signature
    header[0x10:0x14] = (64).to_bytes(4, 'big')  # Header length
    header[0x14] = 1  # Version hi
    header[0x15] = 0  # Version lo
    header[0x16:0x18] = hardware_type.to_bytes(2, 'big')  # Hardware type
    header[0x18] = exrom  # EXROM
    header[0x19] = game   # GAME
    name_bytes = name.encode('ascii')[:32].ljust(32, b'\x00')
    header[0x20:0x40] = name_bytes

    with open(path, 'wb') as f:
        f.write(bytes(header))

        if is_16k and single_chip:
            # Write as single 16KB CHIP packet at $8000 (common real-world format)
            combined_rom = roml + romh
            chip = bytearray(16)
            chip[0:4] = b'CHIP'
            chip[4:8] = (16 + len(combined_rom)).to_bytes(4, 'big')  # Packet length
            chip[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
            chip[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
            chip[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # Load address ($8000)
            chip[14:16] = (len(combined_rom)).to_bytes(2, 'big')  # ROM size (16384)
            f.write(bytes(chip))
            f.write(combined_rom)
        else:
            # Write ROML as separate CHIP packet
            chip_roml = bytearray(16)
            chip_roml[0:4] = b'CHIP'
            chip_roml[4:8] = (16 + len(roml)).to_bytes(4, 'big')  # Packet length
            chip_roml[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
            chip_roml[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
            chip_roml[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # Load address
            chip_roml[14:16] = (len(roml)).to_bytes(2, 'big')  # ROM size
            f.write(bytes(chip_roml))
            f.write(roml)

            if romh is not None:
                # Write ROMH as separate CHIP packet
                chip_romh = bytearray(16)
                chip_romh[0:4] = b'CHIP'
                chip_romh[4:8] = (16 + len(romh)).to_bytes(4, 'big')
                chip_romh[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
                chip_romh[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
                chip_romh[12:14] = (C64.ROMH_START).to_bytes(2, 'big')  # Load address ($A000)
                chip_romh[14:16] = (len(romh)).to_bytes(2, 'big')
                f.write(bytes(chip_romh))
                f.write(romh)


def create_ultimax_cartridge() -> tuple[bytes, str]:
    """Create an Ultimax mode test cartridge with ROM at $E000.

    Ultimax mode has EXROM=1, GAME=0 and places ROM at $E000-$FFFF,
    replacing the KERNAL ROM. This is used by diagnostic cartridges
    like the Dead Test ROM.

    Returns:
        Tuple of (cartridge bytes for $E000, description)
    """
    # Ultimax ROM is 8KB at $E000-$FFFF
    cart = bytearray(C64.ROML_SIZE)

    # Reset vector at $FFFC-$FFFD points to start of our code
    # Code starts at $E009 (after the CBM80-style header area)
    code_start = 0xE009

    # Put reset vector at the end of ROM
    # $FFFC = lo byte, $FFFD = hi byte of reset vector
    cart[0x1FFC] = code_start & 0xFF        # $FFFC - reset vector lo
    cart[0x1FFD] = (code_start >> 8) & 0xFF  # $FFFD - reset vector hi

    # Also put a valid NMI vector (point to RTI)
    rti_addr = 0xE000 + 0x1FF0  # Put RTI near end
    cart[0x1FFA] = rti_addr & 0xFF          # $FFFA - NMI vector lo
    cart[0x1FFB] = (rti_addr >> 8) & 0xFF   # $FFFB - NMI vector hi
    cart[0x1FF0] = 0x40                      # RTI instruction

    # IRQ vector (also point to RTI)
    cart[0x1FFE] = rti_addr & 0xFF          # $FFFE - IRQ vector lo
    cart[0x1FFF] = (rti_addr >> 8) & 0xFF   # $FFFF - IRQ vector hi

    # Code starts at $E009
    code_offset = 0x0009
    code = []

    # Initialize - disable interrupts, set up stack
    code.extend([
        0x78,              # SEI - disable interrupts
        0xA2, 0xFF,        # LDX #$FF
        0x9A,              # TXS - set stack pointer
    ])

    # In Ultimax mode, we need to initialize the VIC and screen RAM ourselves
    # since KERNAL is not available

    # Set up VIC for text mode
    code.extend([
        0xA9, 0x1B,        # LDA #$1B - enable screen, text mode
        0x8D, 0x11, 0xD0,  # STA $D011
        0xA9, 0x08,        # LDA #$08 - 40 columns
        0x8D, 0x16, 0xD0,  # STA $D016
        0xA9, 0x14,        # LDA #$14 - screen at $0400, charset at $1000
        0x8D, 0x18, 0xD0,  # STA $D018
    ])

    # Clear screen by filling $0400-$07E7 with spaces (0x20)
    code.extend([
        0xA9, 0x20,        # LDA #$20 (space)
        0xA2, 0x00,        # LDX #$00
    ])
    # clear_loop:
    code.extend([
        0x9D, 0x00, 0x04,  # STA $0400,X
        0x9D, 0x00, 0x05,  # STA $0500,X
        0x9D, 0x00, 0x06,  # STA $0600,X
        0x9D, 0x00, 0x07,  # STA $0700,X
        0xE8,              # INX
        0xD0, 0xF1,        # BNE clear_loop (branch back -15 bytes)
    ])

    # Set border and background to purple
    code.extend([
        0xA9, 0x04,        # LDA #$04 (purple)
        0x8D, 0x20, 0xD0,  # STA $D020 (border color)
        0x8D, 0x21, 0xD0,  # STA $D021 (background color)
    ])

    # Display messages
    code.extend(create_display_code("ULTIMAX CARTRIDGE TEST", line=0, color=0x01))  # white
    code.extend(create_display_code("ROM AT $E000-$FFFF", line=2, color=0x07))  # yellow
    code.extend(create_display_code("REPLACES KERNAL ROM", line=4, color=0x07))  # yellow
    code.extend(create_display_code("EXROM=1 GAME=0", line=6, color=0x05))  # green

    # Infinite loop
    loop_addr = 0xE000 + code_offset + len(code)
    code.extend([
        0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,  # JMP to self
    ])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        cart[code_offset + i] = byte

    return bytes(cart), f"Code size: {len(code)} bytes starting at $E009"


def write_ultimax_crt_cartridge(
    path: Path,
    ultimax_romh: bytes,
    roml: bytes | None = None,
    name: str = "TEST",
) -> None:
    """Write a CRT format Ultimax cartridge file.

    Args:
        path: Output file path
        ultimax_romh: ROM data for $E000-$FFFF (8KB, replaces KERNAL)
        roml: Optional ROM data for $8000-$9FFF (8KB)
        name: Cartridge name (max 32 chars)
    """
    # CRT Header (64 bytes)
    header = bytearray(64)
    header[0:16] = b'C64 CARTRIDGE   '  # Signature
    header[0x10:0x14] = (64).to_bytes(4, 'big')  # Header length
    header[0x14] = 1  # Version hi
    header[0x15] = 0  # Version lo
    header[0x16:0x18] = (0).to_bytes(2, 'big')  # Hardware type (0 = normal)
    header[0x18] = 1  # EXROM = 1 (inactive)
    header[0x19] = 0  # GAME = 0 (active) -> Ultimax mode
    name_bytes = name.encode('ascii')[:32].ljust(32, b'\x00')
    header[0x20:0x40] = name_bytes

    with open(path, 'wb') as f:
        f.write(bytes(header))

        # Write optional ROML CHIP packet
        if roml is not None:
            chip_roml = bytearray(16)
            chip_roml[0:4] = b'CHIP'
            chip_roml[4:8] = (16 + len(roml)).to_bytes(4, 'big')
            chip_roml[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
            chip_roml[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
            chip_roml[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # $8000
            chip_roml[14:16] = (len(roml)).to_bytes(2, 'big')
            f.write(bytes(chip_roml))
            f.write(roml)

        # Write Ultimax ROMH CHIP packet at $E000
        chip_romh = bytearray(16)
        chip_romh[0:4] = b'CHIP'
        chip_romh[4:8] = (16 + len(ultimax_romh)).to_bytes(4, 'big')
        chip_romh[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
        chip_romh[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
        chip_romh[12:14] = (C64.KERNAL_ROM_START).to_bytes(2, 'big')  # $E000
        chip_romh[14:16] = (len(ultimax_romh)).to_bytes(2, 'big')
        f.write(bytes(chip_romh))
        f.write(ultimax_romh)


def create_mapper_test_cartridge(hw_type: int, type_name: str) -> bytes:
    """Create an 8KB test cartridge that displays the mapper type info.

    This creates a valid cartridge ROM that can be used to test that
    a specific hardware type is correctly identified and handled.

    Args:
        hw_type: CRT hardware type number
        type_name: Human-readable name of the cartridge type

    Returns:
        8KB cartridge ROM data
    """
    cart = bytearray(C64.ROML_SIZE)

    # Cartridge header at $8000-$8008
    cart[0x0000] = 0x09  # Cold start lo -> $8009
    cart[0x0001] = 0x80  # Cold start hi
    cart[0x0002] = 0x09  # Warm start lo -> $8009
    cart[0x0003] = 0x80  # Warm start hi
    cart[0x0004] = 0xC3  # 'C' (CBM80 signature)
    cart[0x0005] = 0xC2  # 'B'
    cart[0x0006] = 0xCD  # 'M'
    cart[0x0007] = 0x38  # '8'
    cart[0x0008] = 0x30  # '0'

    # Code starts at $8009
    code_offset = 0x0009
    code = []

    # Initialize - disable interrupts, set up stack
    code.extend([
        0x78,              # SEI - disable interrupts
        0xA2, 0xFF,        # LDX #$FF
        0x9A,              # TXS - set stack pointer
    ])

    # Clear screen by filling $0400-$07E7 with spaces (0x20)
    code.extend([
        0xA9, 0x20,        # LDA #$20 (space)
        0xA2, 0x00,        # LDX #$00
    ])
    # clear_loop:
    code.extend([
        0x9D, 0x00, 0x04,  # STA $0400,X
        0x9D, 0x00, 0x05,  # STA $0500,X
        0x9D, 0x00, 0x06,  # STA $0600,X
        0x9D, 0x00, 0x07,  # STA $0700,X
        0xE8,              # INX
        0xD0, 0xF1,        # BNE clear_loop (branch back -15 bytes)
    ])

    # Set border and background to dark blue
    code.extend([
        0xA9, 0x06,        # LDA #$06 (blue)
        0x8D, 0x20, 0xD0,  # STA $D020 (border color)
        0x8D, 0x21, 0xD0,  # STA $D021 (background color)
    ])

    # Display messages - showing the mapper type
    lines = [
        ("MAPPER TEST CARTRIDGE", 1, 0x01),   # white
        ("", 3, 0x01),
        (f"TYPE: {hw_type}", 4, 0x07),        # yellow
        (f"NAME: {type_name.upper()[:30]}", 6, 0x07),  # yellow (truncated)
        ("", 8, 0x01),
        ("THIS CARTRIDGE IS FOR TESTING", 10, 0x05),  # green
        ("THE MAPPER TYPE IDENTIFICATION", 11, 0x05),
        ("AND BANK SWITCHING LOGIC.", 12, 0x05),
        ("", 14, 0x01),
        ("CODE IS EXECUTING IN ROML", 16, 0x0E),  # light blue
        ("AT $8000-$9FFF", 17, 0x0E),
    ]

    for text, line, color in lines:
        code.extend(create_display_code(text, line=line, color=color))

    # Infinite loop
    loop_addr = C64.ROML_START + code_offset + len(code)
    code.extend([
        0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,  # JMP to self
    ])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        cart[code_offset + i] = byte

    return bytes(cart)


def main():
    fixtures_dir = project_root / "tests" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Create 8KB cartridge
    print("Creating 8KB test cartridge...")
    roml_8k, desc_8k = create_8k_cartridge()

    path_8k_bin = fixtures_dir / "test_cart_8k.bin"
    write_raw_cartridge(path_8k_bin, roml_8k)
    print(f"  {path_8k_bin} ({len(roml_8k)} bytes)")
    print(f"  {desc_8k}")

    path_8k_crt = fixtures_dir / "test_cart_8k.crt"
    write_crt_cartridge(path_8k_crt, roml_8k, name="8K TEST CARTRIDGE")
    print(f"  {path_8k_crt}")

    # Create 16KB cartridge (two CHIP packets - ROML + ROMH separately)
    print("\nCreating 16KB test cartridge (two CHIP packets)...")
    roml_16k, romh_16k, desc_16k = create_16k_cartridge()

    path_16k_bin = fixtures_dir / "test_cart_16k.bin"
    write_raw_cartridge(path_16k_bin, roml_16k, romh_16k)
    print(f"  {path_16k_bin} ({len(roml_16k) + len(romh_16k)} bytes)")
    print(f"  {desc_16k}")

    path_16k_crt = fixtures_dir / "test_cart_16k.crt"
    write_crt_cartridge(path_16k_crt, roml_16k, romh_16k, name="16K TEST CARTRIDGE")
    print(f"  {path_16k_crt}")

    # Create 16KB cartridge (single CHIP packet - like Q*bert and many real carts)
    # This format stores both ROML and ROMH as one 16KB chunk at $8000
    print("\nCreating 16KB test cartridge (single CHIP packet)...")
    path_16k_single_crt = fixtures_dir / "test_cart_16k_single_chip.crt"
    write_crt_cartridge(
        path_16k_single_crt, roml_16k, romh_16k,
        name="16K SINGLE CHIP TEST", single_chip=True
    )
    print(f"  {path_16k_single_crt}")
    print("  (Tests single 16KB CHIP at $8000 that must be split into ROML+ROMH)")

    # Create Ultimax mode cartridge (ROM at $E000, replaces KERNAL)
    print("\nCreating Ultimax test cartridge (ROM at $E000)...")
    ultimax_rom, desc_ultimax = create_ultimax_cartridge()

    path_ultimax_bin = fixtures_dir / "test_cart_ultimax.bin"
    write_raw_cartridge(path_ultimax_bin, ultimax_rom)
    print(f"  {path_ultimax_bin} ({len(ultimax_rom)} bytes)")
    print(f"  {desc_ultimax}")

    path_ultimax_crt = fixtures_dir / "test_cart_ultimax.crt"
    write_ultimax_crt_cartridge(path_ultimax_crt, ultimax_rom, name="ULTIMAX TEST CARTRIDGE")
    print(f"  {path_ultimax_crt}")
    print("  (Tests Ultimax mode: EXROM=1, GAME=0, ROM at $E000-$FFFF)")

    # Create error cartridges for all unsupported hardware types
    # These display a message showing what type of cartridge was attempted
    # Error carts are runtime resources, so they live in the c64 package
    print("\nCreating error cartridges for unsupported types...")
    error_cart_dir = project_root / "systems" / "c64" / "cartridges" / "error_cartridges"
    error_cart_dir.mkdir(parents=True, exist_ok=True)

    for hw_type, type_name in sorted(C64.CRT_HARDWARE_TYPES.items()):
        if hw_type == 0:  # Skip type 0 (supported)
            continue
        error_rom = create_error_cartridge(hw_type, type_name)
        # Use a sanitized filename
        safe_name = type_name.lower().replace(" ", "_").replace(",", "").replace("/", "_")
        path = error_cart_dir / f"error_type_{hw_type:02d}_{safe_name}.bin"
        write_raw_cartridge(path, error_rom)
        print(f"  Type {hw_type:2d}: {path.name}")

    print(f"\n  Created {len(C64.CRT_HARDWARE_TYPES) - 1} error cartridges in {error_cart_dir}")

    # Create test CRT files for each mapper type in tests/fixtures/cartridge_types/
    # These are used to test cartridge type identification and loading
    print("\nCreating mapper test cartridges for all hardware types...")
    cartridge_types_dir = fixtures_dir / "cartridge_types"
    cartridge_types_dir.mkdir(parents=True, exist_ok=True)

    for hw_type, type_name in sorted(C64.CRT_HARDWARE_TYPES.items()):
        # Create a test ROM that displays the mapper type
        mapper_rom = create_mapper_test_cartridge(hw_type, type_name)
        # Use a sanitized filename
        safe_name = type_name.lower().replace(" ", "_").replace(",", "").replace("/", "_").replace("(", "").replace(")", "").replace(".", "")
        path = cartridge_types_dir / f"type_{hw_type:02d}_{safe_name}.crt"
        write_crt_cartridge(path, mapper_rom, name=f"TYPE {hw_type} TEST", hardware_type=hw_type)
        print(f"  Type {hw_type:2d}: {path.name}")

    print(f"\n  Created {len(C64.CRT_HARDWARE_TYPES)} mapper test cartridges in {cartridge_types_dir}")

    print("\nDone! Test with:")
    print(f"  python systems/c64.py --rom-dir systems/roms --cartridge {path_8k_crt}")
    print(f"  python systems/c64.py --rom-dir systems/roms --cartridge {path_16k_crt}")
    print(f"  python systems/c64.py --rom-dir systems/roms --cartridge {path_16k_single_crt}")
    print(f"  python systems/c64.py --rom-dir systems/roms --cartridge {path_ultimax_crt}")
    print(f"\nTest unsupported type (should show error cart):")
    print(f"  python systems/c64.py --rom-dir systems/roms --cartridge {cartridge_types_dir}/type_01_action_replay.crt")


if __name__ == '__main__':
    main()
