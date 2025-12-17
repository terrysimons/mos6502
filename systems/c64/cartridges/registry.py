"""Cartridge registry and factory function.

This module provides the mapping of hardware types to cartridge classes
and the factory function for creating cartridge instances.
"""


from mos6502.compat import Optional, Union, Dict, List

from .base import Cartridge, CartridgeType
from .type_00_normal import StaticROMCartridge
from .type_01_action_replay import ActionReplayCartridge
from .type_03_final_cartridge_iii import FinalCartridgeIIICartridge
from .type_04_simons_basic import SimonsBasicCartridge
from .type_05_ocean import OceanType1Cartridge
from .type_10_epyx_fastload import EpyxFastloadCartridge
from .type_13_final_cartridge_i import FinalCartridgeICartridge
from .type_15_c64gs import C64GSCartridge
from .type_17_dinamic import DinamicCartridge
from .type_19_magic_desk import MagicDeskCartridge


# Registry of cartridge classes by hardware type
CARTRIDGE_TYPES: Union[Dict[int, CartridgeType], type[Cartridge]] = {
    CartridgeType.NORMAL: StaticROMCartridge,
    CartridgeType.ACTION_REPLAY: ActionReplayCartridge,
    CartridgeType.FINAL_CARTRIDGE_III: FinalCartridgeIIICartridge,
    CartridgeType.SIMONS_BASIC: SimonsBasicCartridge,
    CartridgeType.OCEAN_TYPE_1: OceanType1Cartridge,
    CartridgeType.EPYX_FASTLOAD: EpyxFastloadCartridge,
    CartridgeType.FINAL_CARTRIDGE_I: FinalCartridgeICartridge,
    CartridgeType.C64_GAME_SYSTEM: C64GSCartridge,
    CartridgeType.DINAMIC: DinamicCartridge,
    CartridgeType.MAGIC_DESK: MagicDeskCartridge,
}


def create_cartridge(
    hardware_type: int,
    roml_data: Optional[bytes] = None,
    romh_data: Optional[bytes] = None,
    ultimax_romh_data: Optional[bytes] = None,
    banks: Optional[List[bytes]] = None,
    name: str = "",
) -> Cartridge:
    """Factory function to create appropriate cartridge instance.

    Args:
        hardware_type: CRT hardware type ID
        roml_data: ROM data for ROML region ($8000-$9FFF) - for type 0
        romh_data: ROM data for ROMH region ($A000-$BFFF) - for type 0 16KB mode
        ultimax_romh_data: ROM data for Ultimax ROMH ($E000-$FFFF) - for type 0
        banks: List of ROM banks - for banked cartridges (type 1+)
        name: Cartridge name

    Returns:
        Cartridge instance of appropriate type

    Raises:
        ValueError: If hardware type is not supported
    """
    if hardware_type not in CARTRIDGE_TYPES:
        raise ValueError(f"Unsupported cartridge hardware type: {hardware_type}")

    cart_class = CARTRIDGE_TYPES[hardware_type]

    if cart_class == StaticROMCartridge:
        return StaticROMCartridge(roml_data, romh_data, ultimax_romh_data, name)
    elif cart_class == ActionReplayCartridge:
        if banks is None:
            raise ValueError("ActionReplayCartridge requires banks parameter")
        return ActionReplayCartridge(banks, name)
    elif cart_class == FinalCartridgeIIICartridge:
        if banks is None:
            raise ValueError("FinalCartridgeIIICartridge requires banks parameter")
        return FinalCartridgeIIICartridge(banks, name)
    elif cart_class == SimonsBasicCartridge:
        if roml_data is None or romh_data is None:
            raise ValueError("SimonsBasicCartridge requires roml_data and romh_data")
        return SimonsBasicCartridge(roml_data, romh_data, name)
    elif cart_class == OceanType1Cartridge:
        if banks is None:
            raise ValueError("OceanType1Cartridge requires banks parameter")
        return OceanType1Cartridge(banks, name)
    elif cart_class == DinamicCartridge:
        if banks is None:
            raise ValueError("DinamicCartridge requires banks parameter")
        return DinamicCartridge(banks, name)
    elif cart_class == MagicDeskCartridge:
        if banks is None:
            raise ValueError("MagicDeskCartridge requires banks parameter")
        return MagicDeskCartridge(banks, name)
    elif cart_class == EpyxFastloadCartridge:
        # Epyx FastLoad is a single-bank 8KB cartridge
        # Accept either roml_data directly or banks[0]
        rom_data = roml_data
        if rom_data is None and banks is not None and len(banks) > 0:
            rom_data = banks[0]
        if rom_data is None:
            raise ValueError("EpyxFastloadCartridge requires roml_data or banks parameter")
        return EpyxFastloadCartridge(rom_data, name)
    elif cart_class == FinalCartridgeICartridge:
        # FC1 uses roml_data and optionally romh_data
        # Accept either direct data or banks[0]/banks[1]
        fc1_roml = roml_data
        fc1_romh = romh_data
        if fc1_roml is None and banks is not None and len(banks) > 0:
            fc1_roml = banks[0]
            if len(banks) > 1:
                fc1_romh = banks[1]
        if fc1_roml is None:
            raise ValueError("FinalCartridgeICartridge requires roml_data or banks parameter")
        return FinalCartridgeICartridge(fc1_roml, fc1_romh, name)
    elif cart_class == C64GSCartridge:
        if banks is None:
            raise ValueError("C64GSCartridge requires banks parameter")
        return C64GSCartridge(banks, name)
    else:
        raise ValueError(f"Cartridge type {hardware_type} not yet implemented")
