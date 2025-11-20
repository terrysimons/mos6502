#!/usr/bin/env python3
import copy
import logging

import mos6502
from mos6502 import CPU, flags, instructions

from .test_helpers import (
    check_noop_flags,
    verify_load_immediate,
    verify_load_zeropage,
    verify_load_absolute
)

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


""" LDX """
def test_cpu_instruction_LDX_IMMEDIATE_0xA2_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0xFF, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDX_IMMEDIATE_0xA2,
        register_name="X", # Load into register X
        expected_flags=expected_flags,
        expected_cycles=2,
    )

def test_cpu_instruction_LDX_IMMEDIATE_0xA2_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x01, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDX_IMMEDIATE_0xA2,
        register_name="X", # Load into register X
        expected_flags=expected_flags,
        expected_cycles=2,
    )

def test_cpu_instruction_LDX_IMMEDIATE_0xA2_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x00, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDX_IMMEDIATE_0xA2,
        register_name="X", # Load into register X
        expected_flags=expected_flags,
        expected_cycles=2,
    )

def test_cpu_instruction_LDX_ZEROPAGE_0xA6_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDX_ZEROPAGE_0xA6,
        register_name="X", # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDX_ZEROPAGE_0xA6_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDX_ZEROPAGE_0xA6,
        register_name="X", # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDX_ZEROPAGE_0xA6_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDX_ZEROPAGE_0xA6,
        register_name="X", # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDX_ZEROPAGE_Y_0xB6_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDX_ZEROPAGE_Y_0xB6,
        offset=0x42,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x08,
    )

def test_cpu_instruction_LDX_ZEROPAGE_Y_0xB6_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDX_ZEROPAGE_Y_0xB6,
        offset=0x42,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x08,
    )

def test_cpu_instruction_LDX_ZEROPAGE_Y_0xB6_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDX_ZEROPAGE_Y_0xB6,
        offset=0x42,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x08,
    )

def test_cpu_instruction_LDX_ABSOLUTE_0xAE_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDX_ABSOLUTE_0xAE,
        offset=0x4222,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDX_ABSOLUTE_0xAE_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDX_ABSOLUTE_0xAE,
        offset=0x4222,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDX_ABSOLUTE_0xAE_with_zero_flag(cpu: CPU) -> None: # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDX_ABSOLUTE_0xAE,
        offset=0x4222,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4222,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x01,
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4222,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x01,
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4222,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x01,
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_with_negative_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4223,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="Y",
        offset_value=0xFF,
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_without_negative_flag_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    cpu.reset()
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4223,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="Y",
        offset_value=0xFF,
    )

def test_cpu_instruction_LDX_ABSOLUTE_Y_0xBE_with_zero_flag_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDX_ABSOLUTE_Y_0xBE,
        offset=0x4223,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="Y",
        offset_value=0xFF,
    )
