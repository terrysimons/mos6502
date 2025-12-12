#!/usr/bin/env python3
"""mos6502 Exceptions."""


class MachineCodeExecutionError(Exception):
    """Raise when something unexpected happens trying to execute a machine code op."""


class IllegalCPUInstructionError(Exception):
    """Raise when an illegal CPU instruction is encountered."""


class CPUCycleExhaustionError(Exception):
    """Raise when the expected number of CPU cycles is exhausted."""


class InvalidMemoryLocationError(Exception):
    """Raise when an invalid memory location is accessed."""


class InvalidMemoryAssignmentError(Exception):
    """Raise when an invalid memory location is assigned to."""


class CPUBreakError(Exception):
    """Raise when BRK instruction is executed."""


class QuitRequestError(Exception):
    """Raise when user requests to quit (window close, Ctrl+C, etc.)."""


class CPUHaltError(Exception):
    """Raise when JAM/KIL/HLT instruction halts the CPU.

    On real 6502 hardware, this requires a hardware reset to recover.
    The PC does not advance and the CPU stops executing.

    Attributes:
    ----------
        opcode: The JAM opcode that caused the halt (0x02, 0x12, etc.)
        address: The address where the JAM instruction was executed
    """

    def __init__(self, opcode: int, address: int, message: str = None) -> None:
        """Initialize CPUHaltError.

        Arguments:
        ---------
            opcode: The JAM opcode that caused the halt
            address: The address where the JAM instruction was executed
            message: Optional custom message
        """
        self.opcode = opcode
        self.address = address
        if message is None:
            message = f"CPU halted by JAM instruction ${opcode:02X} at ${address:04X}"
        super().__init__(message)
