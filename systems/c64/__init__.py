"""Commodore 64 Emulator using the mos6502 CPU package.

This module provides a complete C64 emulator including:
- 6510 CPU emulation (via mos6502 package)
- VIC-II video chip emulation
- SID sound chip (stub)
- CIA1/CIA2 I/O chips
- Keyboard matrix
- 1541 disk drive emulation
- Cartridge support (multiple types)
"""

# Re-export everything from c64.py
from c64.c64 import (
    # Main class
    C64,
    # Logging
    log,
    # Debug flags
    DEBUG_CIA,
    DEBUG_VIC,
    DEBUG_JIFFY,
    DEBUG_KEYBOARD,
    DEBUG_SCREEN,
    DEBUG_CURSOR,
    DEBUG_KERNAL,
    DEBUG_BASIC,
)

# Re-export commonly used items from submodules for convenience
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
from c64.cia1 import (
    CIA1,
    PADDLE_1_FIRE,
    PADDLE_2_FIRE,
    MOUSE_LEFT_BUTTON,
    MOUSE_RIGHT_BUTTON,
    LIGHTPEN_BUTTON,
    JOYSTICK_UP,
    JOYSTICK_DOWN,
    JOYSTICK_LEFT,
    JOYSTICK_RIGHT,
    JOYSTICK_FIRE,
)
from c64.cia2 import CIA2
from c64.sid import SID
from c64.vic import (
    VideoTiming,
    ScreenDirtyTracker,
    C64VIC,
    COLORS,
    c64_to_ansi_fg,
    c64_to_ansi_bg,
    ANSI_RESET,
    PAL,
    NTSC,
)
from c64.memory import (
    C64Memory,
    BASIC_ROM_START,
    BASIC_ROM_END,
    BASIC_ROM_SIZE,
    KERNAL_ROM_START,
    KERNAL_ROM_END,
    KERNAL_ROM_SIZE,
    CHAR_ROM_START,
    CHAR_ROM_END,
    CHAR_ROM_SIZE,
    VIC_START,
    VIC_END,
    SID_START,
    SID_END,
    COLOR_RAM_START,
    COLOR_RAM_END,
    CIA1_START,
    CIA1_END,
    CIA2_START,
    CIA2_END,
    BASIC_PROGRAM_START,
)

# Drive module is optional (not available on Pico)
try:
    from c64.drive import (
        Drive1541,
        IECBus,
        D64Image,
        ThreadedDrive1541,
        ThreadedIECBus,
        MultiprocessDrive1541,
        MultiprocessIECBus,
        SharedIECState,
    )
except ImportError:
    # Drive module not available
    Drive1541 = None
    IECBus = None
    D64Image = None
    ThreadedDrive1541 = None
    ThreadedIECBus = None
    MultiprocessDrive1541 = None
    MultiprocessIECBus = None
    SharedIECState = None

__all__ = [
    # Main class
    "C64",
    # Cartridge-related
    "Cartridge",
    "CartridgeTestResults",
    "StaticROMCartridge",
    "ErrorCartridge",
    "CARTRIDGE_TYPES",
    "create_cartridge",
    "create_error_cartridge_rom",
    # Memory constants
    "ROML_START",
    "ROML_END",
    "ROML_SIZE",
    "ROMH_START",
    "ROMH_END",
    "IO1_START",
    "IO1_END",
    "IO2_START",
    "IO2_END",
    "BASIC_ROM_START",
    "BASIC_ROM_END",
    "BASIC_ROM_SIZE",
    "KERNAL_ROM_START",
    "KERNAL_ROM_END",
    "KERNAL_ROM_SIZE",
    "CHAR_ROM_START",
    "CHAR_ROM_END",
    "CHAR_ROM_SIZE",
    "VIC_START",
    "VIC_END",
    "SID_START",
    "SID_END",
    "COLOR_RAM_START",
    "COLOR_RAM_END",
    "CIA1_START",
    "CIA1_END",
    "CIA2_START",
    "CIA2_END",
    "BASIC_PROGRAM_START",
    # Chip emulation
    "CIA1",
    "CIA2",
    "SID",
    "C64VIC",
    "C64Memory",
    # Video
    "VideoTiming",
    "ScreenDirtyTracker",
    "COLORS",
    "c64_to_ansi_fg",
    "c64_to_ansi_bg",
    "ANSI_RESET",
    "PAL",
    "NTSC",
    # Input constants
    "PADDLE_1_FIRE",
    "PADDLE_2_FIRE",
    "MOUSE_LEFT_BUTTON",
    "MOUSE_RIGHT_BUTTON",
    "LIGHTPEN_BUTTON",
    "JOYSTICK_UP",
    "JOYSTICK_DOWN",
    "JOYSTICK_LEFT",
    "JOYSTICK_RIGHT",
    "JOYSTICK_FIRE",
    # Drive
    "Drive1541",
    "IECBus",
    "D64Image",
    "ThreadedDrive1541",
    "ThreadedIECBus",
    "MultiprocessDrive1541",
    "MultiprocessIECBus",
    "SharedIECState",
]
