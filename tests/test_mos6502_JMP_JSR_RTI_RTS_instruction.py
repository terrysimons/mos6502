#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log: logging.Logger = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)

def check_noop_flags(expected_cpu: mos6502.CPU, actual_cpu: mos6502.CPU) -> None:
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]

# def test_cpu_instruction_JSR_ABSOLUTE_0x20():

#     # Jump to 0x4242
#     # Should be 8 cycles

#         pass



#         pass



def test_cpu_instruction_JSR_ABSOLUTE_0x20_and_RTS_IMPLIED_0x60() -> None:  # noqa: N802
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    copy.deepcopy(cpu)

    # Jump to 0x4242
    # Should be 8 cycles
    cpu.ram[0xFFFC] = instructions.JSR_ABSOLUTE_0x20
    cpu.ram[0xFFFD] = 0x43
    cpu.ram[0xFFFE] = 0x42
    cpu.ram[0xFFFF] = instructions.NOP_IMPLIED_0xEA

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then:
    assert cpu.cycles_executed == 6

    # JSR to 0x2223
    cpu.ram[0x4243] = instructions.JSR_ABSOLUTE_0x20
    cpu.ram[0x4244] = 0x22
    cpu.ram[0x4245] = 0x23
    cpu.ram[0x4246] = instructions.RTS_IMPLIED_0x60


    #     pass


    #     pass




# def test_cpu_insruction_JMP_ABSOLUTE_0x4C():
#     instructions.JMP_ABSOLUTE_0x4C
#     assert False

# def test_cpu_instructions_JMP_0x6C():
#     instructions.JMP_INDIRECT_0x6C
#     assert False
