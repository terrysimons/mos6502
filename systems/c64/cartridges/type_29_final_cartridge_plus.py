"""Type 29: Final Cartridge Plus cartridge.

NOT YET IMPLEMENTED - This is a placeholder that generates error cartridges.
"""

from __future__ import annotations

from .base import (
    Cartridge,
    CartridgeVariant,
    CartridgeImage,
    ROML_SIZE,
    create_error_cartridge_rom,
)


class FinalCartridgePlusCartridge(Cartridge):
    """Type 29: Final Cartridge Plus.

    NOT YET IMPLEMENTED.
    """

    HARDWARE_TYPE = 29

    def __init__(self, rom_data: bytes = b"", name: str = ""):
        """Initialize cartridge (stub)."""
        super().__init__(rom_data or bytes(ROML_SIZE), name)
        self._exrom = False
        self._game = True

    def read_roml(self, addr: int) -> int:
        """Read from ROML region."""
        return 0xFF

    @classmethod
    def get_cartridge_variants(cls) -> list[CartridgeVariant]:
        """Return single variant for error cart generation."""
        return [CartridgeVariant("", exrom=0, game=1)]

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create error cartridge showing NOT YET IMPLEMENTED."""
        error_lines = [
            "TYPE 29: Final Cartridge Plus",
            "",
            "{r}NOT YET IMPLEMENTED{/}",
            "",
            "This cartridge type is not",
            "currently supported.",
        ]
        rom_data = create_error_cartridge_rom(error_lines, border_color=0x02)
        return CartridgeImage(
            description=variant.description,
            exrom=variant.exrom,
            game=variant.game,
            extra=variant.extra,
            rom_data={"roml": rom_data},
            hardware_type=cls.HARDWARE_TYPE,
        )
