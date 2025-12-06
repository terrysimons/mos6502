"""Error cartridge for unsupported cartridge types.

When an unsupported cartridge type is loaded, an error cartridge
is created to display information about the unsupported type.
"""

from __future__ import annotations

from .type_00_normal import StaticROMCartridge


class ErrorCartridge(StaticROMCartridge):
    """Special cartridge that displays an error message.

    Used when an unsupported cartridge type is loaded. Displays
    the cartridge type and name on screen with a red background.
    """

    HARDWARE_TYPE = -1  # Not a real hardware type

    def __init__(self, roml_data: bytes, original_type: int, original_name: str):
        """Initialize error cartridge.

        Args:
            roml_data: Pre-generated error display ROM
            original_type: The unsupported hardware type that was attempted
            original_name: Name of the original cartridge
        """
        super().__init__(roml_data, romh_data=None, name=f"Error: {original_name}")
        self.original_type = original_type
        self.original_name = original_name
