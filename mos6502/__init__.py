#!/usr/bin/env python3
"""CPU package for the mos6502."""
__version__ = "0.1.0"
__all__ = ["core", "memory", "exceptions", "flags", "instructions", "variants", "add_cpu_arguments"]

from mos6502.core import MOS6502CPU as CPU  # noqa: F401
from mos6502.variants import CPUVariant  # noqa: F401


def add_cpu_arguments(parser, group_name: str = "CPU Options") -> None:
    """Add CPU-related command-line arguments to an argument parser.

    This allows any system using the mos6502 core to easily add CPU variant
    selection to their command-line interface.

    Arguments:
        parser: An argparse.ArgumentParser instance
        group_name: Name for the argument group (default: "CPU Options")

    Example:
        import argparse
        from mos6502 import add_cpu_arguments, CPUVariant

        parser = argparse.ArgumentParser()
        add_cpu_arguments(parser)
        args = parser.parse_args()

        # Use the parsed variant
        variant = CPUVariant.from_string(args.cpu)
        cpu = CPU(cpu_variant=variant)
    """
    cpu_group = parser.add_argument_group(group_name)
    cpu_group.add_argument(
        "--cpu",
        type=str,
        choices=["6502", "6502A", "6502C", "65C02"],
        default="6502",
        help="CPU variant to emulate: 6502 (default), 6502A, 6502C, or 65C02",
    )
