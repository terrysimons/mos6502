"""1541 Disk Drive Emulation.

This module provides full hardware emulation of the Commodore 1541 disk drive,
including:
- 6502 CPU (uses our existing core)
- Two 6522 VIA chips (VIA1 for IEC bus, VIA2 for disk mechanics)
- 2KB RAM ($0000-$07FF)
- 16KB ROM ($C000-$FFFF)
- D64 disk image support

The 1541 communicates with the C64 via the IEC serial bus using the ATN, CLK,
and DATA lines. This is a bit-banged protocol implemented in software on both
the C64 (via CIA2) and the 1541 (via VIA1).

Reference:
- https://www.c64-wiki.com/wiki/Commodore_1541
- https://sta.c64.org/cbm1541mem.html
"""

from .via6522 import VIA6522
from .d64 import D64Image
from .drive1541 import Drive1541
from .iec_bus import IECBus

# Threaded/multiprocess drive modules - optional for MicroPython/Pico
# These require threading/multiprocessing which aren't available on Pico
_THREADED_AVAILABLE = False
_MULTIPROCESS_AVAILABLE = False
try:
    from .threaded_iec_bus import ThreadedIECBus
    from .threaded_drive import ThreadedDrive1541
    _THREADED_AVAILABLE = True
except ImportError:
    ThreadedIECBus = None
    ThreadedDrive1541 = None

try:
    from .multiprocess_iec_bus import MultiprocessIECBus, SharedIECState
    from .multiprocess_drive import MultiprocessDrive1541
    _MULTIPROCESS_AVAILABLE = True
except ImportError:
    MultiprocessIECBus = None
    SharedIECState = None
    MultiprocessDrive1541 = None

__all__ = [
    "VIA6522",
    "D64Image",
    "Drive1541",
    "IECBus",
    "ThreadedIECBus",
    "ThreadedDrive1541",
    "MultiprocessIECBus",
    "SharedIECState",
    "MultiprocessDrive1541",
    "_THREADED_AVAILABLE",
    "_MULTIPROCESS_AVAILABLE",
]
