#!/usr/bin/env python3
"""Generate test cartridges for all C64 cartridge hardware types.

This is a thin driver script that uses cartridge classes to generate test
fixtures. Each cartridge class implements get_cartridge_variants() and
create_test_cartridge() methods.

Usage:
    python scripts/create_test_carts.py

Creates:
    tests/fixtures/c64/cartridge_types/  - All test cartridges (CRT and BIN formats)
    systems/c64/cartridges/error_cartridges/  - Error display cartridges for unsupported types
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "systems"))

from c64 import C64
from c64.cartridges import (
    CARTRIDGE_TYPES,
    UNIMPLEMENTED_CARTRIDGE_TYPES,
    create_error_cartridge_rom,
)


def get_safe_name(hw_type: int) -> str:
    """Get safe filename from hardware type using C64.CRT_HARDWARE_TYPES.

    This must match test_cartridge_types.py's _get_crt_path logic exactly.
    """
    type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
    return (
        type_name.lower()
        .replace(" ", "_")
        .replace(",", "")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
    )


def get_cart_filename(hw_type: int, variant_desc: str) -> str:
    """Generate filename for a test cartridge.

    Format: test_cart_type_XX_{type_name}[_{variant}].crt
    """
    safe_name = get_safe_name(hw_type)
    base = f"test_cart_type_{hw_type:02d}_{safe_name}"
    if variant_desc:
        return f"{base}_{variant_desc}"
    return base


def create_mouse_test_cartridge() -> bytes:
    """Create a test cartridge for verifying mouse input.

    The cartridge:
    - Reads SID POT registers ($D419 POTX, $D41A POTY)
    - Reads CIA1 Port B ($DC01) for joystick 1 / mouse buttons
    - Stores values in zero-page for test framework verification:
      - $03: POTX mirror
      - $04: POTY mirror
      - $05: Joystick 1 bits
    - Displays values on screen for visual verification
    - Loops forever (test framework controls execution)

    Memory map for test verification:
      $02: Standard fail counter (not used by this cart, stays 0x00)
      $03: Current POTX value (updated each loop)
      $04: Current POTY value (updated each loop)
      $05: Current Joystick 1 bits (updated each loop)

    Returns:
        CRT file bytes
    """
    from c64.cartridges.rom_builder import (
        TestROMBuilder,
        text_to_screen_codes,
        COLOR_BLUE,
        COLOR_WHITE,
        COLOR_YELLOW,
        COLOR_CYAN,
        COLOR_GREEN,
        PERIPHERAL_TEST_ZP_X,
        PERIPHERAL_TEST_ZP_Y,
        PERIPHERAL_TEST_ZP_BUTTONS,
    )
    from mos6502.instructions import (
        LDA_ABSOLUTE_0xAD,
        STA_ZEROPAGE_0x85,
        STA_ABSOLUTE_0x8D,
        JMP_ABSOLUTE_0x4C,
        LDA_IMMEDIATE_0xA9,
        AND_IMMEDIATE_0x29,
        LSR_ACCUMULATOR_0x4A,
        ORA_IMMEDIATE_0x09,
        CLC_IMPLIED_0x18,
        ADC_IMMEDIATE_0x69,
        CMP_IMMEDIATE_0xC9,
        BCC_RELATIVE_0x90,
        SBC_IMMEDIATE_0xE9,
        BNE_RELATIVE_0xD0,
    )

    def emit_nibble_to_hex_screen_code(builder, screen_addr):
        """Convert nibble in A (0-15) to C64 screen code and store to screen.

        0-9 -> screen codes $30-$39 ('0'-'9')
        A-F -> screen codes $01-$06 ('A'-'F')
        """
        # CMP #$0A      ; Compare with 10
        # BCC is_digit  ; Branch if A < 10 (+4 bytes forward)
        # SBC #$09      ; A-F: 10-9=1='A', etc. (C=1 from CMP)
        # BNE store     ; Skip digit code (+2 bytes forward)
        # is_digit:
        # ADC #$30      ; 0-9: add $30 (C=0 from BCC)
        # store:
        # STA screen_addr
        builder.code.extend([
            CMP_IMMEDIATE_0xC9, 0x0A,  # Compare with 10
            BCC_RELATIVE_0x90, 0x04,   # Branch forward 4 bytes if < 10
            SBC_IMMEDIATE_0xE9, 0x09,  # A-F: subtract 9 (C=1)
            BNE_RELATIVE_0xD0, 0x02,   # Branch forward 2 bytes (skip ADC)
            # is_digit:
            ADC_IMMEDIATE_0x69, 0x30,  # 0-9: add $30 (C=0)
            # store:
            STA_ABSOLUTE_0x8D, screen_addr & 0xFF, (screen_addr >> 8) & 0xFF,
        ])

    # Hardware addresses
    SID_POTX = 0xD419
    SID_POTY = 0xD41A
    CIA1_PRB = 0xDC01  # Port B - Joystick 1

    builder = TestROMBuilder()
    builder.emit_screen_init()
    builder.emit_set_border_and_background(COLOR_BLUE)

    # Display title
    builder.emit_display_text("1351 MOUSE TEST", line=1, color=COLOR_WHITE)
    builder.emit_display_text("MOVE MOUSE AND CLICK", line=3, color=COLOR_CYAN)

    # Display labels
    builder.emit_display_text("POTX:", line=6, color=COLOR_YELLOW, centered=False)
    builder.emit_display_text("POTY:", line=8, color=COLOR_YELLOW, centered=False)
    builder.emit_display_text("BTNS:", line=10, color=COLOR_YELLOW, centered=False)

    # Mark start of main loop
    builder.label("main_loop")

    # Read POTX and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, SID_POTX & 0xFF, (SID_POTX >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, PERIPHERAL_TEST_ZP_X,
    ])

    # Read POTY and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, SID_POTY & 0xFF, (SID_POTY >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, PERIPHERAL_TEST_ZP_Y,
    ])

    # Read joystick 1 and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, CIA1_PRB & 0xFF, (CIA1_PRB >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, PERIPHERAL_TEST_ZP_BUTTONS,
    ])

    # Display POTX as hex (at screen position for line 6, column 6)
    # We'll display it as 2 hex digits
    potx_screen_addr = 0x0400 + (6 * 40) + 6
    # High nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_X, 0x00,  # Load POTX from ZP
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, potx_screen_addr)
    # Low nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_X, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, potx_screen_addr + 1)

    # Display POTY as hex (at screen position for line 8, column 6)
    poty_screen_addr = 0x0400 + (8 * 40) + 6
    # High nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_Y, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, poty_screen_addr)
    # Low nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_Y, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, poty_screen_addr + 1)

    # Display button state as hex (at screen position for line 10, column 6)
    btns_screen_addr = 0x0400 + (10 * 40) + 6
    # High nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_BUTTONS, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, btns_screen_addr)
    # Low nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_BUTTONS, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, btns_screen_addr + 1)

    # Jump back to main loop
    loop_addr = builder.labels["main_loop"]
    builder.code.extend([
        JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
    ])

    # Build the ROM
    rom = builder.build_rom()

    # Create CRT header
    # CRT file format:
    # - 64-byte header
    # - CHIP packets for each ROM bank
    crt_header = bytearray(64)
    crt_header[0:16] = b'C64 CARTRIDGE   '
    crt_header[16:20] = (64).to_bytes(4, 'big')  # Header length
    crt_header[20:22] = (0x0100).to_bytes(2, 'big')  # Version 1.0
    crt_header[22:24] = (0).to_bytes(2, 'big')  # Hardware type 0 (normal)
    crt_header[24] = 0  # EXROM line (active low, 0 = active)
    crt_header[25] = 1  # GAME line (active low, 1 = inactive) -> 8K mode
    crt_header[32:64] = b'MOUSE TEST'.ljust(32, b'\x00')

    # CHIP packet
    chip_header = bytearray(16)
    chip_header[0:4] = b'CHIP'
    chip_header[4:8] = (16 + len(rom)).to_bytes(4, 'big')  # Total packet length
    chip_header[8:10] = (0).to_bytes(2, 'big')  # Chip type (ROM)
    chip_header[10:12] = (0).to_bytes(2, 'big')  # Bank number
    chip_header[12:14] = (0x8000).to_bytes(2, 'big')  # Load address
    chip_header[14:16] = len(rom).to_bytes(2, 'big')  # ROM size

    return bytes(crt_header) + bytes(chip_header) + rom


def create_paddle_test_cartridge() -> bytes:
    """Create a test cartridge for verifying paddle input.

    The cartridge:
    - Reads SID POT registers ($D419 POTX, $D41A POTY)
    - Reads CIA1 Port B ($DC01) for joystick 1 / paddle buttons
    - Stores values in zero-page for test framework verification:
      - $03: POTX mirror (Paddle 1 position)
      - $04: POTY mirror (Paddle 2 position)
      - $05: Joystick 1 bits (paddle buttons)
    - Displays values on screen for visual verification
    - Loops forever (test framework controls execution)

    Memory map for test verification:
      $02: Standard fail counter (not used by this cart, stays 0x00)
      $03: Current POTX value / Paddle 1 position (updated each loop)
      $04: Current POTY value / Paddle 2 position (updated each loop)
      $05: Current Joystick 1 bits (updated each loop)

    Returns:
        CRT file bytes
    """
    from c64.cartridges.rom_builder import (
        TestROMBuilder,
        text_to_screen_codes,
        COLOR_BLUE,
        COLOR_WHITE,
        COLOR_YELLOW,
        COLOR_CYAN,
        COLOR_GREEN,
        PERIPHERAL_TEST_ZP_X,
        PERIPHERAL_TEST_ZP_Y,
        PERIPHERAL_TEST_ZP_BUTTONS,
    )
    from mos6502.instructions import (
        LDA_ABSOLUTE_0xAD,
        STA_ZEROPAGE_0x85,
        STA_ABSOLUTE_0x8D,
        JMP_ABSOLUTE_0x4C,
        LDA_IMMEDIATE_0xA9,
        AND_IMMEDIATE_0x29,
        LSR_ACCUMULATOR_0x4A,
        ORA_IMMEDIATE_0x09,
        CLC_IMPLIED_0x18,
        ADC_IMMEDIATE_0x69,
        CMP_IMMEDIATE_0xC9,
        BCC_RELATIVE_0x90,
        SBC_IMMEDIATE_0xE9,
        BNE_RELATIVE_0xD0,
    )

    def emit_nibble_to_hex_screen_code(builder, screen_addr):
        """Convert nibble in A (0-15) to C64 screen code and store to screen."""
        builder.code.extend([
            CMP_IMMEDIATE_0xC9, 0x0A,
            BCC_RELATIVE_0x90, 0x04,
            SBC_IMMEDIATE_0xE9, 0x09,
            BNE_RELATIVE_0xD0, 0x02,
            ADC_IMMEDIATE_0x69, 0x30,
            STA_ABSOLUTE_0x8D, screen_addr & 0xFF, (screen_addr >> 8) & 0xFF,
        ])

    # Zero-page locations for test verification
    PERIPHERAL_TEST_ZP_X = 0x03
    PERIPHERAL_TEST_ZP_Y = 0x04
    PERIPHERAL_TEST_ZP_BUTTONS = 0x05

    # Hardware addresses
    SID_POTX = 0xD419
    SID_POTY = 0xD41A
    CIA1_PRB = 0xDC01  # Port B - Joystick 1

    builder = TestROMBuilder()
    builder.emit_screen_init()
    builder.emit_set_border_and_background(COLOR_BLUE)

    # Display title
    builder.emit_display_text("PADDLE TEST", line=1, color=COLOR_WHITE)
    builder.emit_display_text("MOVE PADDLE LEFT/RIGHT", line=3, color=COLOR_CYAN)

    # Display labels - show paddle 1 and paddle 2
    builder.emit_display_text("PDL1:", line=6, color=COLOR_YELLOW, centered=False)
    builder.emit_display_text("PDL2:", line=8, color=COLOR_YELLOW, centered=False)
    builder.emit_display_text("FIRE:", line=10, color=COLOR_YELLOW, centered=False)

    # Mark start of main loop
    builder.label("main_loop")

    # Read POTX (Paddle 1) and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, SID_POTX & 0xFF, (SID_POTX >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, PERIPHERAL_TEST_ZP_X,
    ])

    # Read POTY (Paddle 2) and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, SID_POTY & 0xFF, (SID_POTY >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, PERIPHERAL_TEST_ZP_Y,
    ])

    # Read joystick 1 (paddle buttons) and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, CIA1_PRB & 0xFF, (CIA1_PRB >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, PERIPHERAL_TEST_ZP_BUTTONS,
    ])

    # Display Paddle 1 (POTX) as hex
    pdl1_screen_addr = 0x0400 + (6 * 40) + 6
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_X, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, pdl1_screen_addr)
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_X, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, pdl1_screen_addr + 1)

    # Display Paddle 2 (POTY) as hex
    pdl2_screen_addr = 0x0400 + (8 * 40) + 6
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_Y, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, pdl2_screen_addr)
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_Y, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, pdl2_screen_addr + 1)

    # Display button state as hex
    fire_screen_addr = 0x0400 + (10 * 40) + 6
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_BUTTONS, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, fire_screen_addr)
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_BUTTONS, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, fire_screen_addr + 1)

    # Jump back to main loop
    loop_addr = builder.labels["main_loop"]
    builder.code.extend([
        JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
    ])

    # Build the ROM
    rom = builder.build_rom()

    # Create CRT header
    crt_header = bytearray(64)
    crt_header[0:16] = b'C64 CARTRIDGE   '
    crt_header[16:20] = (64).to_bytes(4, 'big')  # Header length
    crt_header[20:22] = (0x0100).to_bytes(2, 'big')  # Version 1.0
    crt_header[22:24] = (0).to_bytes(2, 'big')  # Hardware type 0 (normal)
    crt_header[24] = 0  # EXROM line (active low, 0 = active)
    crt_header[25] = 1  # GAME line (active low, 1 = inactive) -> 8K mode
    crt_header[32:64] = b'PADDLE TEST'.ljust(32, b'\x00')

    # CHIP packet
    chip_header = bytearray(16)
    chip_header[0:4] = b'CHIP'
    chip_header[4:8] = (16 + len(rom)).to_bytes(4, 'big')
    chip_header[8:10] = (0).to_bytes(2, 'big')  # Chip type (ROM)
    chip_header[10:12] = (0).to_bytes(2, 'big')  # Bank number
    chip_header[12:14] = (0x8000).to_bytes(2, 'big')  # Load address
    chip_header[14:16] = len(rom).to_bytes(2, 'big')  # ROM size

    return bytes(crt_header) + bytes(chip_header) + rom


def create_lightpen_test_cartridge() -> bytes:
    """Create a test cartridge for verifying lightpen input.

    The cartridge:
    - Reads VIC-II lightpen registers ($D013 LPX, $D014 LPY)
    - Reads CIA1 Port B ($DC01) for joystick 1 / lightpen button
    - Stores values in zero-page for test framework verification:
      - $03: LPX mirror (X position / 2)
      - $04: LPY mirror (Y position in sprite coords)
      - $05: Joystick 1 bits (lightpen button)
    - Displays values on screen for visual verification
    - Loops forever (test framework controls execution)

    Memory map for test verification:
      $02: Standard fail counter (not used by this cart, stays 0x00)
      $03: Current LPX value (updated each loop)
      $04: Current LPY value (updated each loop)
      $05: Current Joystick 1 bits (updated each loop)

    Lightpen uses VIC-II registers (not SID POT like mouse/paddle):
    - $D013 (LPX): X coordinate divided by 2
    - $D014 (LPY): Y coordinate (sprite coordinates)
    - Button triggers joystick fire on port 1 (bit 4)
    Reference: https://www.c64-wiki.com/wiki/Light_pen

    Returns:
        CRT file bytes
    """
    from c64.cartridges.rom_builder import (
        TestROMBuilder,
        text_to_screen_codes,
        COLOR_BLUE,
        COLOR_WHITE,
        COLOR_YELLOW,
        COLOR_CYAN,
        COLOR_GREEN,
        PERIPHERAL_TEST_ZP_X,
        PERIPHERAL_TEST_ZP_Y,
        PERIPHERAL_TEST_ZP_BUTTONS,
    )
    from mos6502.instructions import (
        LDA_ABSOLUTE_0xAD,
        STA_ZEROPAGE_0x85,
        STA_ABSOLUTE_0x8D,
        JMP_ABSOLUTE_0x4C,
        LDA_IMMEDIATE_0xA9,
        AND_IMMEDIATE_0x29,
        LSR_ACCUMULATOR_0x4A,
        ORA_IMMEDIATE_0x09,
        CLC_IMPLIED_0x18,
        ADC_IMMEDIATE_0x69,
        CMP_IMMEDIATE_0xC9,
        BCC_RELATIVE_0x90,
        SBC_IMMEDIATE_0xE9,
        BNE_RELATIVE_0xD0,
    )

    def emit_nibble_to_hex_screen_code(builder, screen_addr):
        """Convert nibble in A (0-15) to C64 screen code and store to screen."""
        builder.code.extend([
            CMP_IMMEDIATE_0xC9, 0x0A,
            BCC_RELATIVE_0x90, 0x04,
            SBC_IMMEDIATE_0xE9, 0x09,
            BNE_RELATIVE_0xD0, 0x02,
            ADC_IMMEDIATE_0x69, 0x30,
            STA_ABSOLUTE_0x8D, screen_addr & 0xFF, (screen_addr >> 8) & 0xFF,
        ])

    # Zero-page locations for test verification
    LPX_MIRROR = 0x03
    LPY_MIRROR = 0x04
    PERIPHERAL_TEST_ZP_BUTTONS = 0x05

    # Hardware addresses
    VIC_LPX = 0xD013   # Lightpen X / 2
    VIC_LPY = 0xD014   # Lightpen Y
    CIA1_PRB = 0xDC01  # Port B - Joystick 1 / Lightpen button

    builder = TestROMBuilder()
    builder.emit_screen_init()
    builder.emit_set_border_and_background(COLOR_BLUE)

    # Display title
    builder.emit_display_text("LIGHTPEN TEST", line=1, color=COLOR_WHITE)
    builder.emit_display_text("MOVE PEN AND CLICK", line=3, color=COLOR_CYAN)

    # Display labels
    builder.emit_display_text("LPX:", line=6, color=COLOR_YELLOW, centered=False)
    builder.emit_display_text("LPY:", line=8, color=COLOR_YELLOW, centered=False)
    builder.emit_display_text("BTN:", line=10, color=COLOR_YELLOW, centered=False)

    # Mark start of main loop
    builder.label("main_loop")

    # Read LPX (VIC $D013) and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, VIC_LPX & 0xFF, (VIC_LPX >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, LPX_MIRROR,
    ])

    # Read LPY (VIC $D014) and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, VIC_LPY & 0xFF, (VIC_LPY >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, LPY_MIRROR,
    ])

    # Read joystick 1 (lightpen button) and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, CIA1_PRB & 0xFF, (CIA1_PRB >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, PERIPHERAL_TEST_ZP_BUTTONS,
    ])

    # Display LPX as hex (at screen position for line 6, column 5)
    lpx_screen_addr = 0x0400 + (6 * 40) + 5
    # High nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, LPX_MIRROR, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, lpx_screen_addr)
    # Low nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, LPX_MIRROR, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, lpx_screen_addr + 1)

    # Display LPY as hex (at screen position for line 8, column 5)
    lpy_screen_addr = 0x0400 + (8 * 40) + 5
    # High nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, LPY_MIRROR, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, lpy_screen_addr)
    # Low nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, LPY_MIRROR, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, lpy_screen_addr + 1)

    # Display button state as hex (at screen position for line 10, column 5)
    btn_screen_addr = 0x0400 + (10 * 40) + 5
    # High nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_BUTTONS, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, btn_screen_addr)
    # Low nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_BUTTONS, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, btn_screen_addr + 1)

    # Jump back to main loop
    loop_addr = builder.labels["main_loop"]
    builder.code.extend([
        JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
    ])

    # Build the ROM
    rom = builder.build_rom()

    # Create CRT header
    crt_header = bytearray(64)
    crt_header[0:16] = b'C64 CARTRIDGE   '
    crt_header[16:20] = (64).to_bytes(4, 'big')  # Header length
    crt_header[20:22] = (0x0100).to_bytes(2, 'big')  # Version 1.0
    crt_header[22:24] = (0).to_bytes(2, 'big')  # Hardware type 0 (normal)
    crt_header[24] = 0  # EXROM line (active low, 0 = active)
    crt_header[25] = 1  # GAME line (active low, 1 = inactive) -> 8K mode
    crt_header[32:64] = b'LIGHTPEN TEST'.ljust(32, b'\x00')

    # CHIP packet
    chip_header = bytearray(16)
    chip_header[0:4] = b'CHIP'
    chip_header[4:8] = (16 + len(rom)).to_bytes(4, 'big')
    chip_header[8:10] = (0).to_bytes(2, 'big')  # Chip type (ROM)
    chip_header[10:12] = (0).to_bytes(2, 'big')  # Bank number
    chip_header[12:14] = (0x8000).to_bytes(2, 'big')  # Load address
    chip_header[14:16] = len(rom).to_bytes(2, 'big')  # ROM size

    return bytes(crt_header) + bytes(chip_header) + rom


def create_joystick_test_cartridge() -> bytes:
    """Create a test cartridge for verifying joystick input on both ports.

    The cartridge:
    - Reads CIA1 Port B ($DC01) for joystick 1
    - Reads CIA1 Port A ($DC00) for joystick 2
    - Stores values in zero-page for test framework verification:
      - $05: Joystick 1 bits (from $DC01)
      - $06: Joystick 2 bits (from $DC00)
    - Displays values on screen for visual verification
    - Loops forever (test framework controls execution)

    Memory map for test verification:
      $02: Standard fail counter (not used by this cart, stays 0x00)
      $05: Current Joystick 1 bits (updated each loop)
      $06: Current Joystick 2 bits (updated each loop)

    Joystick bit mapping (active low: 0 = pressed, 1 = released):
    - Bit 0: Up
    - Bit 1: Down
    - Bit 2: Left
    - Bit 3: Right
    - Bit 4: Fire
    Reference: https://www.c64-wiki.com/wiki/Joystick

    Returns:
        CRT file bytes
    """
    from c64.cartridges.rom_builder import (
        TestROMBuilder,
        text_to_screen_codes,
        COLOR_BLUE,
        COLOR_WHITE,
        COLOR_YELLOW,
        COLOR_CYAN,
        COLOR_GREEN,
        PERIPHERAL_TEST_ZP_JOY1,
        PERIPHERAL_TEST_ZP_JOY2,
    )
    from mos6502.instructions import (
        LDA_ABSOLUTE_0xAD,
        STA_ZEROPAGE_0x85,
        STA_ABSOLUTE_0x8D,
        JMP_ABSOLUTE_0x4C,
        LDA_IMMEDIATE_0xA9,
        AND_IMMEDIATE_0x29,
        LSR_ACCUMULATOR_0x4A,
        ORA_IMMEDIATE_0x09,
        CLC_IMPLIED_0x18,
        ADC_IMMEDIATE_0x69,
        CMP_IMMEDIATE_0xC9,
        BCC_RELATIVE_0x90,
        SBC_IMMEDIATE_0xE9,
        BNE_RELATIVE_0xD0,
    )

    def emit_nibble_to_hex_screen_code(builder, screen_addr):
        """Convert nibble in A (0-15) to C64 screen code and store to screen."""
        builder.code.extend([
            CMP_IMMEDIATE_0xC9, 0x0A,
            BCC_RELATIVE_0x90, 0x04,
            SBC_IMMEDIATE_0xE9, 0x09,
            BNE_RELATIVE_0xD0, 0x02,
            ADC_IMMEDIATE_0x69, 0x30,
            STA_ABSOLUTE_0x8D, screen_addr & 0xFF, (screen_addr >> 8) & 0xFF,
        ])

    # Hardware addresses
    CIA1_PRA = 0xDC00  # Port A - Joystick 2
    CIA1_PRB = 0xDC01  # Port B - Joystick 1

    builder = TestROMBuilder()
    builder.emit_screen_init()
    builder.emit_set_border_and_background(COLOR_BLUE)

    # Display title
    builder.emit_display_text("JOYSTICK TEST", line=1, color=COLOR_WHITE)
    builder.emit_display_text("MOVE STICK AND FIRE", line=3, color=COLOR_CYAN)

    # Display labels
    builder.emit_display_text("JOY1:", line=6, color=COLOR_YELLOW, centered=False)
    builder.emit_display_text("JOY2:", line=8, color=COLOR_YELLOW, centered=False)

    # Mark start of main loop
    builder.label("main_loop")

    # Read joystick 1 (from $DC01) and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, CIA1_PRB & 0xFF, (CIA1_PRB >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, PERIPHERAL_TEST_ZP_JOY1,
    ])

    # Read joystick 2 (from $DC00) and store
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, CIA1_PRA & 0xFF, (CIA1_PRA >> 8) & 0xFF,
        STA_ZEROPAGE_0x85, PERIPHERAL_TEST_ZP_JOY2,
    ])

    # Display Joystick 1 as hex (at screen position for line 6, column 6)
    joy1_screen_addr = 0x0400 + (6 * 40) + 6
    # High nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_JOY1, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, joy1_screen_addr)
    # Low nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_JOY1, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, joy1_screen_addr + 1)

    # Display Joystick 2 as hex (at screen position for line 8, column 6)
    joy2_screen_addr = 0x0400 + (8 * 40) + 6
    # High nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_JOY2, 0x00,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
        LSR_ACCUMULATOR_0x4A,
    ])
    emit_nibble_to_hex_screen_code(builder, joy2_screen_addr)
    # Low nibble
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, PERIPHERAL_TEST_ZP_JOY2, 0x00,
        AND_IMMEDIATE_0x29, 0x0F,
    ])
    emit_nibble_to_hex_screen_code(builder, joy2_screen_addr + 1)

    # Jump back to main loop
    loop_addr = builder.labels["main_loop"]
    builder.code.extend([
        JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
    ])

    # Build the ROM
    rom = builder.build_rom()

    # Create CRT header
    crt_header = bytearray(64)
    crt_header[0:16] = b'C64 CARTRIDGE   '
    crt_header[16:20] = (64).to_bytes(4, 'big')  # Header length
    crt_header[20:22] = (0x0100).to_bytes(2, 'big')  # Version 1.0
    crt_header[22:24] = (0).to_bytes(2, 'big')  # Hardware type 0 (normal)
    crt_header[24] = 0  # EXROM line (active low, 0 = active)
    crt_header[25] = 1  # GAME line (active low, 1 = inactive) -> 8K mode
    crt_header[32:64] = b'JOYSTICK TEST'.ljust(32, b'\x00')

    # CHIP packet
    chip_header = bytearray(16)
    chip_header[0:4] = b'CHIP'
    chip_header[4:8] = (16 + len(rom)).to_bytes(4, 'big')
    chip_header[8:10] = (0).to_bytes(2, 'big')  # Chip type (ROM)
    chip_header[10:12] = (0).to_bytes(2, 'big')  # Bank number
    chip_header[12:14] = (0x8000).to_bytes(2, 'big')  # Load address
    chip_header[14:16] = len(rom).to_bytes(2, 'big')  # ROM size

    return bytes(crt_header) + bytes(chip_header) + rom


def main():
    """Generate all test cartridges."""
    fixtures_dir = project_root / "tests" / "fixtures" / "c64"
    cartridge_types_dir = fixtures_dir / "cartridge_types"
    cartridge_types_dir.mkdir(parents=True, exist_ok=True)

    print("Generating test cartridges...")
    print(f"  Output directory: {cartridge_types_dir}")
    print()

    total_carts = 0
    total_variants = 0

    # Process implemented cartridge types
    print("=== Implemented Types ===")
    for cart_type, cart_class in sorted(CARTRIDGE_TYPES.items(), key=lambda x: x[0].value):
        hw_type = cart_type.value
        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, cart_type.name)

        variants = cart_class.get_cartridge_variants()
        if not variants:
            print(f"  Type {hw_type:2d} ({type_name}): No variants, skipping")
            continue

        print(f"  Type {hw_type:2d} ({type_name}): {len(variants)} variant(s)")

        for variant in variants:
            image = cart_class.create_test_cartridge(variant)
            filename = get_cart_filename(hw_type, variant.description)

            crt_path = cartridge_types_dir / f"{filename}.crt"
            crt_path.write_bytes(image.to_crt())

            if hw_type == 0:
                bin_path = cartridge_types_dir / f"{filename}.bin"
                bin_path.write_bytes(image.to_bin())
                print(f"    - {filename}.crt + .bin")
            else:
                print(f"    - {filename}.crt")

            total_variants += 1
        total_carts += 1

    print()

    # Process unimplemented cartridge types
    print("=== Unimplemented Types ===")
    for hw_type, cart_class in sorted(UNIMPLEMENTED_CARTRIDGE_TYPES.items()):
        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"Type {hw_type}")
        variants = cart_class.get_cartridge_variants()

        print(f"  Type {hw_type:2d} ({type_name})")

        for variant in variants:
            image = cart_class.create_test_cartridge(variant)
            filename = get_cart_filename(hw_type, variant.description)

            crt_path = cartridge_types_dir / f"{filename}.crt"
            crt_path.write_bytes(image.to_crt())
            print(f"    - {filename}.crt")

            total_variants += 1
        total_carts += 1

    print()

    # Generate error cartridges for all unsupported hardware types
    print("=== Error Cartridges ===")
    error_cart_dir = project_root / "systems" / "c64" / "cartridges" / "error_cartridges"
    error_cart_dir.mkdir(parents=True, exist_ok=True)

    error_cart_count = 0
    # Generate error carts for types 1-85 (type 0 is always supported)
    for hw_type in range(1, 86):
        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
        safe_name = get_safe_name(hw_type)

        # Generate error display lines
        error_lines = [
            "{RED}UNSUPPORTED CARTRIDGE",
            "",
            f"{{WHITE}}TYPE: {{YELLOW}}{hw_type}",
            f"{{WHITE}}NAME: {{CYAN}}{type_name.upper()[:20]}",
            "",
            "{WHITE}THIS CARTRIDGE TYPE IS",
            "{WHITE}NOT YET IMPLEMENTED.",
        ]

        rom_data = create_error_cartridge_rom(error_lines, border_color=0x02)
        filename = f"error_cart_type_{hw_type:02d}_{safe_name}.bin"
        error_path = error_cart_dir / filename
        error_path.write_bytes(rom_data)
        error_cart_count += 1

    print(f"  Generated {error_cart_count} error cartridges")
    print(f"  Output directory: {error_cart_dir}")

    # Generate peripheral test cartridges
    print()
    print("=== Peripheral Test Cartridges ===")
    peripheral_test_dir = fixtures_dir / "peripheral_tests"
    peripheral_test_dir.mkdir(parents=True, exist_ok=True)

    # Mouse test cartridge
    mouse_cart = create_mouse_test_cartridge()
    mouse_cart_path = peripheral_test_dir / "test_mouse_input.crt"
    mouse_cart_path.write_bytes(mouse_cart)
    print(f"  - test_mouse_input.crt")

    # Paddle test cartridge
    paddle_cart = create_paddle_test_cartridge()
    paddle_cart_path = peripheral_test_dir / "test_paddle_input.crt"
    paddle_cart_path.write_bytes(paddle_cart)
    print(f"  - test_paddle_input.crt")

    # Lightpen test cartridge
    lightpen_cart = create_lightpen_test_cartridge()
    lightpen_cart_path = peripheral_test_dir / "test_lightpen_input.crt"
    lightpen_cart_path.write_bytes(lightpen_cart)
    print(f"  - test_lightpen_input.crt")

    # Joystick test cartridge
    joystick_cart = create_joystick_test_cartridge()
    joystick_cart_path = peripheral_test_dir / "test_joystick_input.crt"
    joystick_cart_path.write_bytes(joystick_cart)
    print(f"  - test_joystick_input.crt")

    print(f"  Output directory: {peripheral_test_dir}")

    print()
    print(f"=== Summary ===")
    print(f"  Total cartridge types: {total_carts}")
    print(f"  Total variant files: {total_variants}")
    print(f"  Total error cartridges: {error_cart_count}")
    print(f"  Test cart directory: {cartridge_types_dir}")
    print(f"  Error cart directory: {error_cart_dir}")


if __name__ == "__main__":
    main()
