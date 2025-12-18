"""C64 mixin classes for modular functionality.

These mixins split the C64 class into logical components for better
maintainability and smaller file sizes (important for MicroPython/Pico).
"""

from .drive import C64DriveMixin
from .cartridge import C64CartridgeMixin
from .display import C64DisplayMixin
from .keyboard import C64KeyboardMixin
from .input_devices import C64InputDevicesMixin
from .debug import C64DebugMixin
from .program import C64ProgramMixin
from .runner import C64RunnerMixin

__all__ = [
    "C64DriveMixin",
    "C64CartridgeMixin",
    "C64DisplayMixin",
    "C64KeyboardMixin",
    "C64InputDevicesMixin",
    "C64DebugMixin",
    "C64ProgramMixin",
    "C64RunnerMixin",
]
