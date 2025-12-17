#!/usr/bin/env python3
"""CPU variant definitions for the MOS 6502 family."""

from mos6502.compat import enum
from mos6502.compat import Union, Dict


# =============================================================================
# Unstable Opcode Configuration
# =============================================================================
# These values configure the behavior of unstable/highly unstable illegal opcodes.
# Real hardware behavior varies between chips, even within the same batch.
#
# ANE_CONST: The "magic" constant used in ANE (XAA) instruction.
#   Formula: A = (A | CONST) & X & immediate
#   Common values: 0xFF (most common), 0xEE, 0xEF, 0x00
#   Reference: https://www.nesdev.org/wiki/CPU_unofficial_opcodes#Highly_unstable_opcodes
#
# SHA/SHX/SHY/TAS: These use (high_byte + 1) in their calculations.
#   On page boundary crossing, behavior may vary. We use the most common interpretation.

class UnstableOpcodeConfig:
    """Configuration for unstable opcode behavior per CPU variant.

    Attributes:
    ----------
        ane_const: The constant used in ANE (XAA) instruction. None for CMOS (acts as NOP).
        unstable_stores_enabled: Whether SHA/SHX/SHY/TAS are enabled (False for CMOS).
    """

    __slots__ = ('ane_const', 'unstable_stores_enabled')

    def __init__(self, ane_const: Union[int, None], unstable_stores_enabled: bool = True) -> None:
        """Initialize unstable opcode configuration.

        Arguments:
        ---------
            ane_const: The constant for ANE instruction (0x00-0xFF), or None for NOP behavior.
            unstable_stores_enabled: Whether unstable store instructions do their thing.
        """
        self.ane_const = ane_const
        self.unstable_stores_enabled = unstable_stores_enabled


# Default configurations for each CPU variant
# Users can override these by modifying cpu.unstable_config after creation
UNSTABLE_OPCODE_DEFAULTS: Dict[str, UnstableOpcodeConfig] = {
    "6502": UnstableOpcodeConfig(ane_const=0xFF, unstable_stores_enabled=True),
    "6502A": UnstableOpcodeConfig(ane_const=0xFF, unstable_stores_enabled=True),
    "6502C": UnstableOpcodeConfig(ane_const=0xEE, unstable_stores_enabled=True),  # Some 6502C chips use 0xEE
    "65C02": UnstableOpcodeConfig(ane_const=None, unstable_stores_enabled=False),  # CMOS: all illegal opcodes are NOPs
}


class CPUVariant(enum.Enum):
    """Supported 6502 CPU variants."""

    NMOS_6502 = "6502"  # Original NMOS 6502
    NMOS_6502A = "6502A"  # NMOS 6502A (faster binned version)
    NMOS_6502C = "6502C"  # NMOS 6502C variant
    CMOS_65C02 = "65C02"  # CMOS 65C02 with bug fixes and new instructions

    @classmethod
    def from_string(cls, variant: str) -> "CPUVariant":
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

    def __str__(self) -> str:
        """Return string representation of variant."""
        return self.value
