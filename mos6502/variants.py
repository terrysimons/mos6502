#!/usr/bin/env python3
"""CPU variant definitions for the MOS 6502 family."""

import enum
from typing import Self


class CPUVariant(enum.Enum):
    """Supported 6502 CPU variants."""

    NMOS_6502 = "6502"  # Original NMOS 6502
    NMOS_6502A = "6502A"  # NMOS 6502A (faster binned version)
    NMOS_6502C = "6502C"  # NMOS 6502C variant
    CMOS_65C02 = "65C02"  # CMOS 65C02 with bug fixes and new instructions

    @classmethod
    def from_string(cls: type[Self], variant: str) -> Self:
        """Parse variant string to enum value.

        Arguments:
        ---------
            variant: String representation of CPU variant

        Returns:
        -------
            CPUVariant enum value

        Raises:
        ------
            ValueError: If variant string is not recognized
        """
        variant_map = {v.value: v for v in cls}
        if variant not in variant_map:
            valid_variants = ", ".join(variant_map.keys())
            raise ValueError(f"Unknown CPU variant: {variant}. Valid variants: {valid_variants}")
        return variant_map[variant]

    def __str__(self: Self) -> str:
        """Return string representation of variant."""
        return self.value
