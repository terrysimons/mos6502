#!/usr/bin/env python3
"""ANC instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the ANC opcodes act as NOPs with the same cycle counts as the
NMOS implementation, but without modifying any registers or flags.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ANC
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def anc_immediate_0x0b(cpu: "MOS6502CPU") -> None:
    """Execute ANC (AND with Carry) - Immediate addressing mode.

    Opcode: 0x0B
    Cycles: 2
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers or flags modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.log.info("i")


def anc_immediate_0x2b(cpu: "MOS6502CPU") -> None:
    """Execute ANC (AND with Carry) - Immediate addressing mode (duplicate).

    Opcode: 0x2B
    Cycles: 2
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers or flags modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.log.info("i")
