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
