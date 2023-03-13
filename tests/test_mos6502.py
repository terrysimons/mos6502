#!/usr/bin/env python3
import mos6502
from mos6502 import __version__, flags


def test_version():
    assert __version__ == "0.1.0"

def test_mos6502_C_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Test initial state is 0
    assert (cpu.C & 1) == 0

    # Test flag is set
    cpu.C = 1
    assert flags.ProcessorStatusFlags.C[flags.C] == cpu.C

    # Test ZERO mask
    cpu.C = flags.ProcessorStatusFlags.SET_ZERO[flags.C]
    assert cpu.C == 0

    # Test ONE mask
    cpu.C = flags.ProcessorStatusFlags.SET_ONE[flags.C]
    assert cpu.C == 1

    # Test bitwise and
    cpu.C = 1
    assert (cpu.C & flags.ProcessorStatusFlags.C[flags.C]) == 1

    # Test bitwise or
    assert (cpu.C | flags.ProcessorStatusFlags.C[flags.C]) == 1
    assert (cpu.C | flags.ProcessorStatusFlags.SET_ZERO[flags.C]) == 1

    # Test bit flip (One's Compliment)
    assert (~cpu.C & flags.ProcessorStatusFlags.C[flags.C]) == 0
    cpu.C = 0
    assert (~cpu.C & flags.ProcessorStatusFlags.C[flags.C]) == 1

    # Test bitwise xor
    cpu.C = 0
    assert (cpu.C ^ flags.ProcessorStatusFlags.C[flags.C]) == \
           (flags.ProcessorStatusFlags.C[flags.C] ^ flags.ProcessorStatusFlags.SET_ZERO[flags.C])
    cpu.C = 1
    assert (cpu.C ^ flags.ProcessorStatusFlags.C[flags.C]) == \
           (flags.ProcessorStatusFlags.C[flags.C] ^ flags.ProcessorStatusFlags.C[flags.C])

def test_mos6502_Z_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Test initial state is 0
    assert (cpu.Z & 1) == 0

    # Test flag is set
    cpu.Z = 1
    assert flags.ProcessorStatusFlags.Z[flags.Z] == cpu.Z

    # Test ZERO mask
    cpu.Z = flags.ProcessorStatusFlags.SET_ZERO[flags.Z]
    assert cpu.Z == 0

    # Test ONE mask
    cpu.Z = flags.ProcessorStatusFlags.SET_ONE[flags.Z]
    assert cpu.Z == 1

    # Test bitwise and
    cpu.Z = 1
    assert (cpu.Z & flags.ProcessorStatusFlags.Z[flags.Z]) == 1

    # Test bitwise or
    assert (cpu.Z | flags.ProcessorStatusFlags.Z[flags.Z]) == 1
    assert (cpu.Z | flags.ProcessorStatusFlags.SET_ZERO[flags.Z]) == 1

    # Test bit flip (One's Compliment)
    assert (~cpu.Z & flags.ProcessorStatusFlags.Z[flags.Z]) == 0
    cpu.Z = 0
    assert (~cpu.Z & flags.ProcessorStatusFlags.Z[flags.Z]) == 1

    # Test bitwise xor
    cpu.Z = 0
    assert (cpu.Z ^ flags.ProcessorStatusFlags.Z[flags.Z]) == \
           (flags.ProcessorStatusFlags.Z[flags.Z] ^ flags.ProcessorStatusFlags.SET_ZERO[flags.Z])
    cpu.Z = 1
    assert (cpu.Z ^ flags.ProcessorStatusFlags.Z[flags.Z]) == \
           (flags.ProcessorStatusFlags.Z[flags.Z] ^ flags.ProcessorStatusFlags.Z[flags.Z])

def test_mos6502_I_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Test initial state is 0
    assert (cpu.I & 1) == 0

    # Test flag is set
    cpu.I = 1
    assert flags.ProcessorStatusFlags.I[flags.I] == cpu.I

    # Test ZERO mask
    cpu.I = flags.ProcessorStatusFlags.SET_ZERO[flags.I]
    assert cpu.I == 0

    # Test ONE mask
    cpu.I = flags.ProcessorStatusFlags.SET_ONE[flags.I]
    assert cpu.I == 1

    # Test bitwise and
    cpu.I = 1
    assert (cpu.I & flags.ProcessorStatusFlags.I[flags.I]) == 1

    # Test bitwise or
    assert (cpu.I | flags.ProcessorStatusFlags.I[flags.I]) == 1
    assert (cpu.I | flags.ProcessorStatusFlags.SET_ZERO[flags.I]) == 1

    # Test bit flip (One's Compliment)
    assert (~cpu.I & flags.ProcessorStatusFlags.I[flags.I]) == 0
    cpu.I = 0
    assert (~cpu.I & flags.ProcessorStatusFlags.I[flags.I]) == 1

    # Test bitwise xor
    cpu.I = 0
    assert (cpu.I ^ flags.ProcessorStatusFlags.I[flags.I]) == \
           (flags.ProcessorStatusFlags.I[flags.I] ^ flags.ProcessorStatusFlags.SET_ZERO[flags.I])
    cpu.I = 1
    assert (cpu.I ^ flags.ProcessorStatusFlags.I[flags.I]) == \
           (flags.ProcessorStatusFlags.I[flags.I] ^ flags.ProcessorStatusFlags.I[flags.I])

def test_mos6502_D_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Test initial state is 0
    assert (cpu.D & 1) == 0

    # Test flag is set
    cpu.D = 1
    assert flags.ProcessorStatusFlags.D[flags.D] == cpu.D

    # Test ZERO mask
    cpu.D = flags.ProcessorStatusFlags.SET_ZERO[flags.D]
    assert cpu.D == 0

    # Test ONE mask
    cpu.D = flags.ProcessorStatusFlags.SET_ONE[flags.D]
    assert cpu.D == 1

    # Test bitwise and
    cpu.D = 1
    assert (cpu.D & flags.ProcessorStatusFlags.D[flags.D]) == 1

    # Test bitwise or
    assert (cpu.D | flags.ProcessorStatusFlags.D[flags.D]) == 1
    assert (cpu.D | flags.ProcessorStatusFlags.SET_ZERO[flags.D]) == 1

    # Test bit flip (One's Compliment)
    assert (~cpu.D & flags.ProcessorStatusFlags.D[flags.D]) == 0
    cpu.D = 0
    assert (~cpu.D & flags.ProcessorStatusFlags.D[flags.D]) == 1

    # Test bitwise xor
    cpu.D = 0
    assert (cpu.D ^ flags.ProcessorStatusFlags.D[flags.D]) == \
           (flags.ProcessorStatusFlags.D[flags.D] ^ flags.ProcessorStatusFlags.SET_ZERO[flags.D])
    cpu.D = 1
    assert (cpu.D ^ flags.ProcessorStatusFlags.D[flags.D]) == \
           (flags.ProcessorStatusFlags.D[flags.D] ^ flags.ProcessorStatusFlags.D[flags.D])

def test_mos6502_B_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Test initial state is 0
    assert (cpu.B & 1) == 0

    # Test flag is set
    cpu.B = 1
    assert flags.ProcessorStatusFlags.B[flags.B] == cpu.B

    # Test ZERO mask
    cpu.B = flags.ProcessorStatusFlags.SET_ZERO[flags.B]
    assert cpu.B == 0

    # Test ONE mask
    cpu.B = flags.ProcessorStatusFlags.SET_ONE[flags.B]
    assert cpu.B == 1

    # Test bitwise and
    cpu.B = 1
    assert (cpu.B & flags.ProcessorStatusFlags.B[flags.B]) == 1

    # Test bitwise or
    assert (cpu.B | flags.ProcessorStatusFlags.B[flags.B]) == 1
    assert (cpu.B | flags.ProcessorStatusFlags.SET_ZERO[flags.B]) == 1

    # Test bit flip (One's Compliment)
    assert (~cpu.B & flags.ProcessorStatusFlags.B[flags.B]) == 0
    cpu.B = 0
    assert (~cpu.B & flags.ProcessorStatusFlags.B[flags.B]) == 1

    # Test bitwise xor
    cpu.B = 0
    assert (cpu.B ^ flags.ProcessorStatusFlags.B[flags.B]) == \
           (flags.ProcessorStatusFlags.B[flags.B] ^ flags.ProcessorStatusFlags.SET_ZERO[flags.B])
    cpu.B = 1
    assert (cpu.B ^ flags.ProcessorStatusFlags.B[flags.B]) == \
           (flags.ProcessorStatusFlags.B[flags.B] ^ flags.ProcessorStatusFlags.B[flags.B])

def test_mos6502_V_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Test initial state is 0
    assert (cpu.V & 1) == 0

    # Test flag is set
    cpu.V = 1
    assert flags.ProcessorStatusFlags.V[flags.V] == cpu.V

    # Test ZERO mask
    cpu.V = flags.ProcessorStatusFlags.SET_ZERO[flags.V]
    assert cpu.V == 0

    # Test ONE mask
    cpu.V = flags.ProcessorStatusFlags.SET_ONE[flags.V]
    assert cpu.V == 1

    # Test bitwise and
    cpu.V = 1
    assert (cpu.V & flags.ProcessorStatusFlags.V[flags.V]) == 1

    # Test bitwise or
    assert (cpu.V | flags.ProcessorStatusFlags.V[flags.V]) == 1
    assert (cpu.V | flags.ProcessorStatusFlags.SET_ZERO[flags.V]) == 1

    # Test bit flip (One's Compliment)
    assert (~cpu.V & flags.ProcessorStatusFlags.V[flags.V]) == 0
    cpu.V = 0
    assert (~cpu.V & flags.ProcessorStatusFlags.V[flags.V]) == 1

    # Test bitwise xor
    cpu.V = 0
    assert (cpu.V ^ flags.ProcessorStatusFlags.V[flags.V]) == \
           (flags.ProcessorStatusFlags.V[flags.V] ^ flags.ProcessorStatusFlags.SET_ZERO[flags.V])
    cpu.V = 1
    assert (cpu.V ^ flags.ProcessorStatusFlags.V[flags.V]) == \
           (flags.ProcessorStatusFlags.V[flags.V] ^ flags.ProcessorStatusFlags.V[flags.V])

def test_mos6502_N_flag():
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Test initial state is 0
    assert (cpu.N & 1) == 0

    # Test flag is set
    cpu.N = 1
    assert flags.ProcessorStatusFlags.N[flags.N] == cpu.N

    # Test ZERO mask
    cpu.N = flags.ProcessorStatusFlags.SET_ZERO[flags.N]
    assert cpu.N == 0

    # Test ONE mask
    cpu.N = flags.ProcessorStatusFlags.SET_ONE[flags.N]
    assert cpu.N == 1

    # Test bitwise and
    cpu.N = 1
    assert (cpu.N & flags.ProcessorStatusFlags.N[flags.N]) == 1

    # Test bitwise or
    assert (cpu.N | flags.ProcessorStatusFlags.N[flags.N]) == 1
    assert (cpu.N | flags.ProcessorStatusFlags.SET_ZERO[flags.N]) == 1

    # Test bit flip (One's Compliment)
    assert (~cpu.N & flags.ProcessorStatusFlags.N[flags.N]) == 0
    cpu.N = 0
    assert (~cpu.N & flags.ProcessorStatusFlags.N[flags.N]) == 1

    # Test bitwise xor
    cpu.N = 0
    assert (cpu.N ^ flags.ProcessorStatusFlags.N[flags.N]) == \
           (flags.ProcessorStatusFlags.N[flags.N] ^ flags.ProcessorStatusFlags.SET_ZERO[flags.N])
    cpu.N = 1
    assert (cpu.N ^ flags.ProcessorStatusFlags.N[flags.N]) == \
           (flags.ProcessorStatusFlags.N[flags.N] ^ flags.ProcessorStatusFlags.N[flags.N])

def test_all_flags() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    assert cpu._flags == flags.ProcessorStatusFlags.SET_ZERO

    cpu.C = flags.ProcessorStatusFlags.C[flags.C]
    cpu.Z = flags.ProcessorStatusFlags.Z[flags.Z]
    cpu.I = flags.ProcessorStatusFlags.I[flags.I]
    cpu.D = flags.ProcessorStatusFlags.D[flags.D]
    cpu.B = flags.ProcessorStatusFlags.B[flags.B]
    cpu.V = flags.ProcessorStatusFlags.V[flags.V]
    cpu.N = flags.ProcessorStatusFlags.N[flags.N]

    assert cpu._flags == (
        flags.ProcessorStatusFlags.C[flags.C] << flags.C |
        flags.ProcessorStatusFlags.Z[flags.Z] << flags.Z |
        flags.ProcessorStatusFlags.I[flags.I] << flags.I |
        flags.ProcessorStatusFlags.D[flags.D] << flags.D |
        flags.ProcessorStatusFlags.B[flags.B] << flags.B |
        flags.ProcessorStatusFlags.V[flags.V] << flags.V |
        flags.ProcessorStatusFlags.N[flags.N] << flags.N
    )

# def test_cpu_context_manager():

#     with mos6502.CPU() as cpu:
#         assert False

