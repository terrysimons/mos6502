#!/usr/bin/env python3
"""Pico main script for running C64 emulator.

This script is designed to run on a Raspberry Pi Pico 2 with MicroPython.
It displays the C64 screen over serial (USB) and accepts keyboard input
from the serial console.

For best results, use frozen firmware (build_firmware.py) which doesn't
consume heap RAM for bytecode. If using mpremote deployment, this script
uses gc.threshold() to reduce heap fragmentation.

Deploy this file as main.py on the Pico along with the ROMs in /roms/.
"""

import gc

# CRITICAL: Set aggressive GC threshold BEFORE any imports to prevent
# heap fragmentation. Without this, imports fragment the heap so badly
# that we can't allocate the 64KB RAM buffer later.
gc.threshold(4096)
gc.collect()

import sys
import time

# Compatibility: time.ticks_ms() is MicroPython-specific
try:
    _ticks_ms = time.ticks_ms
except AttributeError:
    # CPython fallback
    def _ticks_ms():
        return int(time.time() * 1000)

# Import the C64 emulator directly (avoid heavy c64/__init__.py)
gc.collect()
from c64.c64 import C64
gc.collect()
from mos6502 import errors
gc.collect()

# PETSCII to ASCII conversion table for screen output
# Screen codes are different from PETSCII keyboard codes
SCREEN_TO_ASCII = {
    # @ A-Z (0-26)
    0: '@', 1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G',
    8: 'H', 9: 'I', 10: 'J', 11: 'K', 12: 'L', 13: 'M', 14: 'N', 15: 'O',
    16: 'P', 17: 'Q', 18: 'R', 19: 'S', 20: 'T', 21: 'U', 22: 'V', 23: 'W',
    24: 'X', 25: 'Y', 26: 'Z',
    # Special chars (27-31)
    27: '[', 28: '\\', 29: ']', 30: '^', 31: '_',
    # Space and symbols (32-63)
    32: ' ', 33: '!', 34: '"', 35: '#', 36: '$', 37: '%', 38: '&', 39: "'",
    40: '(', 41: ')', 42: '*', 43: '+', 44: ',', 45: '-', 46: '.', 47: '/',
    48: '0', 49: '1', 50: '2', 51: '3', 52: '4', 53: '5', 54: '6', 55: '7',
    56: '8', 57: '9', 58: ':', 59: ';', 60: '<', 61: '=', 62: '>', 63: '?',
}

# ASCII to C64 keyboard matrix mapping: char -> (row, col)
# Reference: https://www.c64-wiki.com/wiki/Keyboard
ASCII_TO_KEY = {
    # Letters (directly mapped)
    'a': (1, 2), 'b': (3, 4), 'c': (2, 4), 'd': (2, 2), 'e': (1, 6),
    'f': (2, 5), 'g': (3, 2), 'h': (3, 5), 'i': (4, 1), 'j': (4, 2),
    'k': (4, 5), 'l': (5, 2), 'm': (4, 4), 'n': (4, 7), 'o': (4, 6),
    'p': (5, 1), 'q': (7, 6), 'r': (2, 1), 's': (1, 5), 't': (2, 6),
    'u': (3, 6), 'v': (3, 7), 'w': (1, 1), 'x': (2, 7), 'y': (3, 1),
    'z': (1, 4),
    # Numbers
    '0': (4, 3), '1': (7, 0), '2': (7, 3), '3': (1, 0), '4': (1, 3),
    '5': (2, 0), '6': (2, 3), '7': (3, 0), '8': (3, 3), '9': (4, 0),
    # Symbols
    ' ': (7, 4),  # SPACE
    '\r': (0, 1), '\n': (0, 1),  # RETURN
    ',': (5, 7), '.': (5, 4), '/': (6, 7), ';': (6, 2), ':': (5, 5),
    '=': (6, 5), '+': (5, 0), '-': (5, 3), '*': (6, 1), '@': (5, 6),
    # Special
    '\x7f': (0, 0),  # Backspace -> DEL
    '\x08': (0, 0),  # Backspace -> DEL
}


def petscii_to_ascii(code: int) -> str:
    """Convert a PETSCII screen code to ASCII character."""
    # Handle reversed characters (codes 128-255) - just use the base character
    if code >= 128:
        code -= 128
    return SCREEN_TO_ASCII.get(code, '?')


def render_screen(c64) -> None:
    """Render the C64 screen to serial output."""
    screen_start = 0x0400
    cols = 40
    rows = 25

    # Clear screen and move cursor to top (ANSI escape codes)
    sys.stdout.write("\033[2J\033[H")

    # Header
    print("=" * 42)
    print(" C64 PICO EMULATOR")
    print("=" * 42)

    # Render screen RAM
    for row in range(rows):
        line = ""
        for col in range(cols):
            addr = screen_start + (row * cols) + col
            code = int(c64.cpu.ram[addr])
            line += petscii_to_ascii(code)
        print(line)

    print("=" * 42)
    print(f"Cycles: {c64.cpu.cycles_executed:,}")


def check_keyboard(c64) -> bool:
    """Check for keyboard input from serial console.

    Returns:
        True if Ctrl+C was pressed (exit), False otherwise.
    """
    try:
        # MicroPython: use select.poll() for non-blocking I/O
        import select
        poll = select.poll()
        poll.register(sys.stdin, select.POLLIN)

        # Check if input is available (timeout=0 for non-blocking)
        events = poll.poll(0)
        if events:
            char = sys.stdin.read(1)
            if char:
                return handle_key(c64, char)
        poll.unregister(sys.stdin)
    except (ImportError, OSError):
        # Fallback: try to read without blocking (may not work on all platforms)
        pass

    return False


def handle_key(c64, char: str) -> bool:
    """Handle a keyboard character.

    Returns:
        True if should exit (Ctrl+C), False otherwise.
    """
    # Ctrl+C - exit
    if char == '\x03':
        return True

    # Convert to uppercase for C64 (C64 keyboard is uppercase by default)
    if 'a' <= char <= 'z':
        char_upper = char.upper()
        key = ASCII_TO_KEY.get(char)
    elif 'A' <= char <= 'Z':
        # Shift + letter
        char_lower = char.lower()
        key = ASCII_TO_KEY.get(char_lower)
        if key:
            # Press shift first
            c64.cia1.press_key(1, 7)  # Left SHIFT
    else:
        key = ASCII_TO_KEY.get(char)

    if key:
        row, col = key
        c64.cia1.press_key(row, col)
        # Schedule key release after a short delay (will be handled in main loop)
        # For simplicity, release immediately after some CPU cycles
        return False

    return False


def release_all_keys(c64) -> None:
    """Release all pressed keys."""
    # Reset the entire keyboard matrix
    for row in range(8):
        for col in range(8):
            c64.cia1.release_key(row, col)


def main():
    """Main entry point for Pico C64 emulator."""
    print("Initializing C64 emulator...")
    gc.collect()
    print(f"Free memory: {gc.mem_free():,} bytes")

    # Pre-allocate 64KB RAM buffer BEFORE creating C64
    # This ensures we get a contiguous block before heap fragmentation
    # from C64 initialization makes it impossible
    print("Pre-allocating 64KB RAM buffer...")
    try:
        ram_buffer = bytearray(131072)
    except MemoryError:
        print("ERROR: Not enough memory to allocate 64KB RAM buffer")
        print("Try using frozen firmware (build_firmware.py) instead")
        return

    gc.collect()
    print(f"After RAM alloc: {gc.mem_free():,} bytes")

    # ROMs: First tries embedded ROMs (baked into firmware by build_firmware.py)
    # Falls back to /roms/ filesystem if embedded ROMs not available
    print("Initializing C64 (embedded ROMs preferred, fallback: /roms/ filesystem)")

    # Create C64 instance with headless display (no pygame)
    # Use positional args - MicroPython frozen modules may not support kwargs
    try:
        # C64(rom_dir, display_mode, scale, enable_irq, video_chip, cpu_variant, verbose_cycles, preallocated_ram)
        c64 = C64(
            "/roms", # rom_dir
            "headless", # display_mode
            1, # scale
            True, # enable_irq
            "6569", # video_chip
            "6502", # cpu_variant
            False, # verbose_cycles
            ram_buffer # preallocated_ram
        )
        #c64 = C64(rom_dir="/roms", display_mode="headless", scale=1, enable_irq=True, video_chip="6569", cpu_variant="6502", verbose_cycles=False, preallocated_ram=ram_buffer)
    except OSError as e:
        # MicroPython uses OSError for file not found (no FileNotFoundError)
        print(f"ERROR: {e}")
        print("Please copy ROM files (basic, kernal, char) to /roms/ on the Pico")
        return
    except MemoryError as e:
        print(f"ERROR: Out of memory during C64 init: {e}")
        print("Try using frozen firmware (build_firmware.py) instead")
        return

    gc.collect()
    print(f"C64 initialized. Free memory: {gc.mem_free():,} bytes")
    print("Starting emulation... Press Ctrl+C to exit")
    print()

    # Main emulation loop
    cycles_per_iteration = 20000  # ~20ms worth of cycles at 1MHz
    render_interval = 0.1  # Render every 100ms (10 FPS for serial)
    last_render = 0
    key_release_countdown = 0

    try:
        while True:
            # Execute CPU cycles
            try:
                c64.cpu.execute(cycles=cycles_per_iteration)
                #c64.cpu.execute(cycles=cycles_per_iteration)
                pass
            except errors.CPUCycleExhaustionError:
                pass  # Normal - cycle budget exhausted

            # Check for keyboard input
            if check_keyboard(c64):
                break  # Ctrl+C pressed

            # Handle key release after some cycles
            if key_release_countdown > 0:
                key_release_countdown -= 1
                if key_release_countdown == 0:
                    release_all_keys(c64)
            else:
                # If a key was just pressed, schedule release
                key_release_countdown = 5  # Release after 5 iterations (~100ms)

            # Render screen periodically
            now = _ticks_ms() / 1000.0
            if now - last_render >= render_interval:
                render_screen(c64)
                last_render = now

                # Garbage collect periodically to avoid memory fragmentation
                gc.collect()

    except KeyboardInterrupt:
        pass

    print("\nEmulation stopped.")
    print(f"Total cycles: {c64.cpu.cycles_executed:,}")
    gc.collect()
    print(f"Free memory: {gc.mem_free():,} bytes")


if __name__ == "__main__":
    main()
