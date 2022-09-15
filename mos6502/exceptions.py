#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mos6502 Exceptions."""


class IllegalCPUInstructionException(Exception):
    """Raise when an illegal CPU instruction is encountered."""

    pass


class CPUCycleExhaustionException(Exception):
    """Raise when the expected number of CPU cycles is exhausted."""

    pass


class InvalidMemoryLocationException(Exception):
    """Raise when an invalid memory location is accessed."""

    pass


class InvalidMemoryAssignmentException(Exception):
    """Raise when an invalid memory location is assigned to."""

    pass
