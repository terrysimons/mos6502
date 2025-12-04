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
sys.path.insert(0, str(project_root))

from systems.c64 import C64


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


def write_crt_cartridge(path: Path, roml: bytes, romh: bytes | None = None, name: str = "TEST") -> None:
    """Write a CRT format cartridge file."""
    is_16k = romh is not None

    # CRT Header (64 bytes)
    header = bytearray(64)
    header[0:16] = b'C64 CARTRIDGE   '  # Signature
    header[0x10:0x14] = (64).to_bytes(4, 'big')  # Header length
    header[0x14] = 1  # Version hi
    header[0x15] = 0  # Version lo
    header[0x16:0x18] = (0).to_bytes(2, 'big')  # Hardware type (0 = generic)
    header[0x18] = 0  # EXROM (0 = active)
    header[0x19] = 0 if is_16k else 1  # GAME (0 = active for 16K, 1 = inactive for 8K)
    name_bytes = name.encode('ascii')[:32].ljust(32, b'\x00')
    header[0x20:0x40] = name_bytes

    # CHIP packet for ROML
    chip_roml = bytearray(16)
    chip_roml[0:4] = b'CHIP'
    chip_roml[4:8] = (16 + len(roml)).to_bytes(4, 'big')  # Packet length
    chip_roml[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
    chip_roml[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
    chip_roml[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # Load address
    chip_roml[14:16] = (len(roml)).to_bytes(2, 'big')  # ROM size

    with open(path, 'wb') as f:
        f.write(bytes(header))
        f.write(bytes(chip_roml))
        f.write(roml)

        if romh is not None:
            # CHIP packet for ROMH
            chip_romh = bytearray(16)
            chip_romh[0:4] = b'CHIP'
            chip_romh[4:8] = (16 + len(romh)).to_bytes(4, 'big')
            chip_romh[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
            chip_romh[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
            chip_romh[12:14] = (C64.ROMH_START).to_bytes(2, 'big')  # Load address ($A000)
            chip_romh[14:16] = (len(romh)).to_bytes(2, 'big')
            f.write(bytes(chip_romh))
            f.write(romh)


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

    # Create 16KB cartridge
    print("\nCreating 16KB test cartridge...")
    roml_16k, romh_16k, desc_16k = create_16k_cartridge()

    path_16k_bin = fixtures_dir / "test_cart_16k.bin"
    write_raw_cartridge(path_16k_bin, roml_16k, romh_16k)
    print(f"  {path_16k_bin} ({len(roml_16k) + len(romh_16k)} bytes)")
    print(f"  {desc_16k}")

    path_16k_crt = fixtures_dir / "test_cart_16k.crt"
    write_crt_cartridge(path_16k_crt, roml_16k, romh_16k, name="16K TEST CARTRIDGE")
    print(f"  {path_16k_crt}")

    print("\nDone! Test with:")
    print(f"  python systems/c64.py --rom-dir systems/roms --cartridge {path_8k_bin}")
    print(f"  python systems/c64.py --rom-dir systems/roms --cartridge {path_16k_bin}")


if __name__ == '__main__':
    main()
