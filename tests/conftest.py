#!/usr/bin/env python3
"""Pytest configuration and fixtures for MOS 6502 CPU tests."""

import pytest

from mos6502 import CPU, CPUVariant


# List of all CPU variants to test
ALL_CPU_VARIANTS = [
    CPUVariant.NMOS_6502,
    CPUVariant.NMOS_6502A,
    CPUVariant.NMOS_6502C,
    CPUVariant.CMOS_65C02,
]

# NMOS variants only (for tests where behavior differs between NMOS/CMOS)
NMOS_CPU_VARIANTS = [
    CPUVariant.NMOS_6502,
    CPUVariant.NMOS_6502A,
    CPUVariant.NMOS_6502C,
]

# CMOS variants only
CMOS_CPU_VARIANTS = [
    CPUVariant.CMOS_65C02,
]


@pytest.fixture(params=ALL_CPU_VARIANTS)
def cpu_variant(request) -> str:
    """Fixture that provides each CPU variant.

    Tests using this fixture will automatically run for all CPU variants.
    """
    return request.param


@pytest.fixture(params=NMOS_CPU_VARIANTS)
def nmos_cpu_variant(request) -> str:
    """Fixture that provides only NMOS CPU variants.

    Use this for tests that should only run on NMOS variants.
    """
    return request.param


@pytest.fixture(params=CMOS_CPU_VARIANTS)
def cmos_cpu_variant(request) -> str:
    """Fixture that provides only CMOS CPU variants.

    Use this for tests that should only run on CMOS variants.
    """
    return request.param


@pytest.fixture
def cpu(cpu_variant) -> CPU:
    """Fixture that provides a fresh CPU instance for each variant.

    The CPU is already reset and ready to use.
    """
    cpu_instance = CPU(cpu_variant=cpu_variant)
    cpu_instance.reset()
    return cpu_instance


@pytest.fixture
def nmos_cpu(nmos_cpu_variant) -> CPU:
    """Fixture that provides a fresh NMOS CPU instance for each NMOS variant.

    The CPU is already reset and ready to use.
    """
    cpu_instance = CPU(cpu_variant=nmos_cpu_variant)
    cpu_instance.reset()
    return cpu_instance


@pytest.fixture
def cmos_cpu(cmos_cpu_variant) -> CPU:
    """Fixture that provides a fresh CMOS CPU instance for each CMOS variant.

    The CPU is already reset and ready to use.
    """
    cpu_instance = CPU(cpu_variant=cmos_cpu_variant)
    cpu_instance.reset()
    return cpu_instance
