#!/usr/bin/env python3
import copy
import logging

import mos6502
from mos6502 import CPU, flags, instructions

from .test_helpers import (
    check_noop_flags,
    verify_load_immediate,
    verify_load_zeropage,
    verify_load_absolute,
    verify_load_indexed_indirect,
    verify_load_indirect_indexed
)

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


""" LDA """
def test_cpu_instruction_LDA_IMMEDIATE_0xA9_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0xFF, # Load 0xFF directly from 0xFFFD
        instruction=instructions.LDA_IMMEDIATE_0xA9,
        register_name="A", # Load into register A
        expected_flags=expected_flags,
        expected_cycles=2,
    )

def test_cpu_instruction_LDA_IMMEDIATE_0xA9_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x01, # Load 0x01 directly from 0xFFFD
        instruction=instructions.LDA_IMMEDIATE_0xA9,
        register_name="A", # Load into register A
        expected_flags=expected_flags,
        expected_cycles=2,
    )

def test_cpu_instruction_LDA_IMMEDIATE_0xA9_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_immediate(
        cpu=cpu,
        data=0x00, # Load 0x00 directly from 0xFFFD
        instruction=instructions.LDA_IMMEDIATE_0xA9,
        register_name="A", # Load into register A
        expected_flags=expected_flags,
        expected_cycles=2,
    )

def test_cpu_instruction_LDA_ZEROPAGE_0xA5_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF, # Load 0xFF from [zeropage]@0xFFFD offset
        offset=0x42, # 0xFFFD == 0x42 zeropage offset
        instruction=instructions.LDA_ZEROPAGE_0xA5,
        register_name="A", # Load into register A
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDA_ZEROPAGE_0xA5_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01,
        offset=0x42,
        instruction=instructions.LDA_ZEROPAGE_0xA5,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDA_ZEROPAGE_0xA5_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00,
        offset=0x42,
        instruction=instructions.LDA_ZEROPAGE_0xA5,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x42,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="X",
        offset_value=0x08,
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x42,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="X",
        offset_value=0x08,
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x42,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="X",
        offset_value=0x08,
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_wrap_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x80,
        register_name="A",
        expected_flags=expected_flags,
        offset_register_name="X",
        expected_cycles=4,
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_wrap_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x80,
        register_name="A",
        expected_flags=expected_flags,
        offset_register_name="X",
        expected_cycles=4,
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_ZEROPAGE_X_0xB5_wrap_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_zeropage(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ZEROPAGE_X_0xB5,
        offset=0x80,
        register_name="A",
        expected_flags=expected_flags,
        offset_register_name="X",
        expected_cycles=4,
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_ABSOLUTE_0xAD_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_0xAD,
        offset=0x4222,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDA_ABSOLUTE_0xAD_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_0xAD,
        offset=0x4222,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDA_ABSOLUTE_0xAD_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_0xAD,
        offset=0x4222,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4222,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="X",
        offset_value=0x01,
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4222,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="X",
        offset_value=0x01,
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4220,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="X",
        offset_value=0x01,
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_with_negative_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4223,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="X",
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_without_negative_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4223,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="X",
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_ABSOLUTE_X_0xBD_with_zero_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_X_0xBD,
        offset=0x4223,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="X",
        offset_value=0xFF,
    )


def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x01,
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x01,
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x01,
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_with_negative_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0xFF,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="Y",
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_without_negative_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x01,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="Y",
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_ABSOLUTE_Y_0xB9_with_zero_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_absolute(
        cpu=cpu,
        data=0x00,
        instruction=instructions.LDA_ABSOLUTE_Y_0xB9,
        offset=0x4223,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="Y",
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_INDEXED_INDIRECT_X_0xA1_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indexed_indirect(
        cpu=cpu,
        pc_value=0x02,
        data=0xFF,
        instruction=instructions.LDA_INDEXED_INDIRECT_X_0xA1,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0x04,
    )

def test_cpu_instruction_LDA_INDEXED_INDIRECT_X_0xA1_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indexed_indirect(
        cpu=cpu,
        pc_value=0x02,
        data=0x01,
        instruction=instructions.LDA_INDEXED_INDIRECT_X_0xA1,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0x04,
    )

def test_cpu_instruction_LDA_INDEXED_INDIRECT_X_0xA1_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indexed_indirect(
        cpu=cpu,
        pc_value=0x02,
        data=0x00,
        instruction=instructions.LDA_INDEXED_INDIRECT_X_0xA1,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0x04,
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_with_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indirect_indexed(
        cpu=cpu,
        pc_value=0x80,
        data=0xFF,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_value=0x04,
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_without_negative_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indirect_indexed(
        cpu=cpu,
        pc_value=0x80,
        data=0x01,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_value=0x04,
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_with_zero_flag(cpu: CPU) -> None:  # noqa: N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indirect_indexed(
        cpu=cpu,
        pc_value=0x80,
        data=0x00,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_value=0x04,
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_with_negative_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = True
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indirect_indexed(
        cpu=cpu,
        pc_value=0xFF,
        data=0xFF,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x80FF,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_without_negative_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = False
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indirect_indexed(
        cpu=cpu,
        pc_value=0xFF,
        data=0x01,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x80FF,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0xFF,
    )

def test_cpu_instruction_LDA_INDIRECT_INDEXED_Y_0xB1_with_zero_flag_crossing_page_boundary(cpu: CPU) -> None:  # noqa: E501, N802
    expected_flags: mos6502.flags.ProcessorStatusFlags = copy.deepcopy(cpu.flags)

    expected_flags[flags.Z] = True
    expected_flags[flags.N] = False
    cpu.flags[flags.Z] = not expected_flags[flags.Z]
    cpu.flags[flags.N] = not expected_flags[flags.N]

    verify_load_indirect_indexed(
        cpu=cpu,
        pc_value=0xFF,
        data=0x00,
        instruction=instructions.LDA_INDIRECT_INDEXED_Y_0xB1,
        offset=0x80FF,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0xFF,
    )
