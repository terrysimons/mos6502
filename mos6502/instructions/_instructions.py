#!/usr/bin/env python3
"""Instruction set for the mos6502 CPU."""
import enum
from typing import Literal, NoReturn

from mos6502 import flags
from mos6502.exceptions import IllegalCPUInstructionError
from mos6502.memory import Byte

# https://www.masswerk.at/6502/6502_instruction_set.html
#
# Legend
#
# *
# add 1 to cycles if page boundary is crossed
# **
# add 1 to cycles if branch occurs on same page
# add 2 to cycles if branch occurs to different page
#
#
# Legend to Flags:
# +
# modified
# -
# not modified
# 1
# set
# 0
# cleared
# M6
# memory bit 6
# M7
# memory bit 7
# Note on assembler syntax:
# Some assemblers employ "OPC *oper" or a ".b" extension
# to the mneomonic for forced zeropage addressing.






















# https://masswerk.at/6502/6502_instruction_set.html#SEC
# Set Carry Flag
#
# 1 -> C
# N	Z	C	I	D	V
# -	-	1	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	SEC	38	1	2
SEC_IMPLIED_0x38: Literal[56] = 0x38

# https://masswerk.at/6502/6502_instruction_set.html#SED
# Set Decimal Flag
#
# 1 -> D
# N	Z	C	I	D	V
# -	-	-	-	1	-
# addressing	assembler	opc	bytes	cycles
# implied	SED	F8	1	2
SED_IMPLIED_0xF8: Literal[248] = 0xF8


# https://masswerk.at/6502/6502_instruction_set.html#SEI
# Set Interrupt Disable Status
#
# 1 -> I
# N	Z	C	I	D	V
# -	-	-	1	-	-
# addressing	assembler	opc	bytes	cycles
# implied	SEI	78	1	2
SEI_IMPLIED_0x78: Literal[120] = 0x78


""" Illegal Opcodes """
# https://masswerk.at/6502/6502_instruction_set.html
# Legend
# "Illegal" Opcodes in Details
# Legend to markers used in the instruction details:
#
# *
# add 1 to cycles if page boundary is crossed
# †
# unstable
# ††
# highly unstable

# https://masswerk.at/6502/6502_instruction_set.html#ALR
# AND oper + LSR
#
# A AND oper, 0 -> [76543210] -> C
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	ALR #oper	4B	2	2
ILL_ALR_IMMEDIATE_0x4B: Literal[75] = 0x4B

# https://masswerk.at/6502/6502_instruction_set.html#ANC
# AND oper + set C as ASL
#
# A AND oper, bit(7) -> C
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	ANC #oper	0B	2	2
ILL_ANC_IMMEDIATE_0x0B: Literal[11] = 0x0B

# https://masswerk.at/6502/6502_instruction_set.html#ANC2
# AND oper + set C as ROL
#
# effectively the same as instr. 0B
#
# A AND oper, bit(7) -> C
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	ANC #oper	2B	2	2
ILL_ANC2_IMMEDIATE_0x2B: Literal[43] = 0x2B

# https://masswerk.at/6502/6502_instruction_set.html#ANE
# * AND X + AND oper
#
# Highly unstable, do not use.
# A base value in A is determined based on the contets of A and a constant, which may be typically
# $00, $ff, $ee, etc.
# The value of this constant depends on temerature, the chip series, and maybe other factors,
# as well.
# In order to eliminate these uncertaincies from the equation, use either 0 as the operand
# or a value of $FF in the accumulator.
#
# (A OR CONST) AND X AND oper -> A
#
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	ANE #oper	8B	2	2  	††
ILL_ANE_IMMEDIATE_0x8B: Literal[139] = 0x8B

# https://masswerk.at/6502/6502_instruction_set.html#ARR
# AND oper + ROR
#
# This operation involves the adder:
# V-flag is set according to (A AND oper) + oper
# The carry is not set, but bit 7 (sign) is exchanged with the carry
#
# A AND oper, C -> [76543210] -> C
#
# N	Z	C	I	D	V
# +	+	+	-	-	+
# addressing	assembler	opc	bytes	cycles
# immediate	ARR #oper	6B	2	2
ILL_ARR_IMMEDIATE_0x6B: Literal[107] = 0x6B


# https://masswerk.at/6502/6502_instruction_set.html#DCP
# DEC oper + CMP oper
#
# M - 1 -> M, A - M
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	DCP oper	C7	2	5
# zeropage,X	DCP oper,X	D7	2	6
# absolute	DCP oper	CF	3	6
# absolut,X	DCP oper,X	DF	3	7
# absolut,Y	DCP oper,Y	DB	3	7
# (indirect,X)	DCP (oper,X)	C3	2	8
# (indirect),Y	DCP (oper),Y	D3	2	8
ILL_DCP_ZEROPAGE_ZEROPAGE_0xC7: Literal[199] = 0xC7
ILL_DCP_ZEROPAGE_X_0xD7: Literal[215] = 0xD7
ILL_DCP_ABSOLUTE_0xCF: Literal[207] = 0xCF
ILL_DCP_ABSOLUTE_X_0xDF: Literal[223] = 0xDF
ILL_DCP_ABSOLUTE_Y_0xDB: Literal[219] = 0xDB
ILL_DCP_INDEXED_INDIRECT_X_0xC3: Literal[195] = 0xC3
ILL_DCP_INDIRECT_INDEXED_Y_0xD3: Literal[211] = 0xD3

# https://masswerk.at/6502/6502_instruction_set.html#ISC
# INC oper + SBC oper
#
# M + 1 -> M, A - M - C -> A
#
# N	Z	C	I	D	V
# +	+	+	-	-	+
# addressing	assembler	opc	bytes	cycles
# zeropage	ISC oper	E7	2	5
# zeropage,X	ISC oper,X	F7	2	6
# absolute	ISC oper	EF	3	6
# absolut,X	ISC oper,X	FF	3	7
# absolut,Y	ISC oper,Y	FB	3	7
# (indirect,X)	ISC (oper,X)	E3	2	8
# (indirect),Y	ISC (oper),Y	F3	2	8
ILL_ISC_ZEROPAGE_0xE7: Literal[231] = 0xE7
ILL_ISC_ZEROPAGE_X_0xF7: Literal[247] = 0xF7
ILL_ISC_ABSOLUTE_0xEF: Literal[239] = 0xEF
ILL_ISC_ABSOLUTE_X_0xFF: Literal[255] = 0xFF
ILL_ISC_ABSOLUTE_Y_0xFB: Literal[251] = 0xFB
ILL_ISC_INDEXED_INDIRECT_X_0xE3: Literal[227] = 0xE3
ILL_ISC_INDIRECT_INDEXED_Y_0xF3: Literal[243] = 0xF3

# https://masswerk.at/6502/6502_instruction_set.html#LAS
# LDA/TSX oper
#
# M AND S -> A, X, S
#
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolut,Y	LAS oper,Y	BB	3	4*
ILL_LAS_ABSOLUTE_0xBB: Literal[187] = 0xBB

# https://masswerk.at/6502/6502_instruction_set.html#LAX
# LDA oper + LDX oper
#
# M -> A -> X
#
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	LAX oper	A7	2	3
# zeropage,Y	LAX oper,Y	B7	2	4
# absolute	LAX oper	AF	3	4
# absolut,Y	LAX oper,Y	BF	3	4*
# (indirect,X)	LAX (oper,X)	A3	2	6
# (indirect),Y	LAX (oper),Y	B3	2	5*
ILL_LAX_ZEROPAGE_0xA7: Literal[167] = 0xA7
ILL_LAX_ZEROPAGE_X_0xB7: Literal[183] = 0xB7
ILL_LAX_ABSOLUTE_0xAF: Literal[175] = 0xAF
ILL_LAX_ABSOLUTE_Y_0xBF: Literal[191] = 0xBF
ILL_LAX_INDEXED_INDIRECT_X_0xA3: Literal[163] = 0xA3
ILL_LAX_INDIRECT_INDEXED_Y_0xB3: Literal[179] = 0xB3

# https://masswerk.at/6502/6502_instruction_set.html#LXA
# (LAX immediate)
# Store * AND oper in A and X
#
# Highly unstable, involves a 'magic' constant, see ANE
#
# (A OR CONST) AND oper -> A -> X
#
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	LXA #oper	AB	2	2  	††
ILL_LXA_IMMEDIATE_0xAB: Literal[171] = 0xAB

# https://masswerk.at/6502/6502_instruction_set.html#RLA
# ROL oper + AND oper
#
# M = C <- [76543210] <- C, A AND M -> A
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	RLA oper	27	2	5
# zeropage,X	RLA oper,X	37	2	6
# absolute	RLA oper	2F	3	6
# absolut,X	RLA oper,X	3F	3	7
# absolut,Y	RLA oper,Y	3B	3	7
# (indirect,X)	RLA (oper,X)	23	2	8
# (indirect),Y	RLA (oper),Y	33	2	8
ILL_RLA_ZEROPAGE_0x27: Literal[39] = 0x27
ILL_RLA_ZEROPAGE_X_0x37: Literal[55] = 0x37
ILL_RLA_ABSOLUTE_0x2F: Literal[47] = 0x2F
ILL_RLA_ABSOLUTE_X_0x3F: Literal[63] = 0x3F
ILL_RLA_ABSOLUTE_Y_0x3B: Literal[59] = 0x3B
ILL_RLA_INDEXED_INDIRECT_X_0x23: Literal[35] = 0x23
ILL_RLA_INDIRECT_INDEXED_Y_0x33: Literal[51] = 0x33

# https://masswerk.at/6502/6502_instruction_set.html#RRA
# ROR oper + ADC oper
#
# M = C -> [76543210] -> C, A + M + C -> A, C
#
# N	Z	C	I	D	V
# +	+	+	-	-	+
# addressing	assembler	opc	bytes	cycles
# zeropage	RRA oper	67	2	5
# zeropage,X	RRA oper,X	77	2	6
# absolute	RRA oper	6F	3	6
# absolut,X	RRA oper,X	7F	3	7
# absolut,Y	RRA oper,Y	7B	3	7
# (indirect,X)	RRA (oper,X)	63	2	8
# (indirect),Y	RRA (oper),Y	73	2	8
ILL_RRA_ZEROPAGE_0x67: Literal[103] = 0x67
ILL_RRA_ZEROPAGE_X_0x77: Literal[119] = 0x77
ILL_RRA_ABSOLUTE_0x6F: Literal[111] = 0x6F
ILL_RRA_ABSOLUTE_X_0x7F: Literal[127] = 0x7F
ILL_RRA_ABSOLUTE_Y_0x7B: Literal[123] = 0x7B
ILL_RRA_INDEXED_INDIRECT_X_0x63: Literal[99] = 0x63
ILL_RRA_INDIRECT_INDEXED_Y_0x73: Literal[115] = 0x73

# https://masswerk.at/6502/6502_instruction_set.html#SAX
# A and X are put on the bus at the same time (resulting effectively in an AND operation)
# and stored in M
#
# A AND X -> M
#
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	SAX oper	87	2	3
# zeropage,Y	SAX oper,Y	97	2	4
# absolute	SAX oper	8F	3	4
# (indirect,X)	SAX (oper,X)	83	2	6
ILL_SAX_ZEROPAGE_0x87: Literal[135] = 0x87
ILL_SAX_ZEROPAGE_Y_0x97: Literal[151] = 0x97
ILL_SAX_ABSOLUTE_0x8F: Literal[143] = 0x8F
ILL_SAX_INDEXED_INDIRECT_X_0x83: Literal[131] = 0x83


# https://masswerk.at/6502/6502_instruction_set.html#SBX
# CMP and DEX at once, sets flags like CMP
#
# (A AND X) - oper -> X
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	SBX #oper	CB	2	2
ILL_SBX_IMMEDIATE_0xCB: Literal[203] = 0xCB

# https://masswerk.at/6502/6502_instruction_set.html#SHA
# Stores A AND X AND (high-byte of addr. + 1) at addr.
#
# unstable: sometimes 'AND (H+1)' is dropped, page boundary crossings may not work
# (with the high-byte of the value used as the high-byte of the address)
#
# A AND X AND (H+1) -> M
#
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolut,Y	SHA oper,Y	9F	3	5  	†
# (indirect),Y	SHA (oper),Y	93	2	6  	†
ILL_SHA_ABSOLUTE_Y_0x9F: Literal[159] = 0x9F
ILL_SHA_INDIRECT_INDEXED_Y_0x93: Literal[147] = 0x93

# https://masswerk.at/6502/6502_instruction_set.html#SHX
# Stores X AND (high-byte of addr. + 1) at addr.
#
# unstable: sometimes 'AND (H+1)' is dropped, page boundary crossings may not work
# (with the high-byte of the value used as the high-byte of the address)
#
# X AND (H+1) -> M
#
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolut,Y	SHX oper,Y	9E	3	5  	†
ILL_SHX_ABSOLUTE_Y_0x9E: Literal[158] = 0x9E

# https://masswerk.at/6502/6502_instruction_set.html#SHY
# Stores Y AND (high-byte of addr. + 1) at addr.
#
# unstable: sometimes 'AND (H+1)' is dropped, page boundary crossings may not work
# (with the high-byte of the value used as the high-byte of the address)
#
# Y AND (H+1) -> M
#
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolut,X	SHY oper,X	9C	3	5  	†
ILL_SHY_ABSOLUTE_X_0x9C: Literal[156] = 0x9C


# https://masswerk.at/6502/6502_instruction_set.html#SLO
# ASL oper + ORA oper
#
# M = C <- [76543210] <- 0, A OR M -> A
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	SLO oper	07	2	5
# zeropage,X	SLO oper,X	17	2	6
# absolute	SLO oper	0F	3	6
# absolut,X	SLO oper,X	1F	3	7
# absolut,Y	SLO oper,Y	1B	3	7
# (indirect,X)	SLO (oper,X)	03	2	8
# (indirect),Y	SLO (oper),Y	13	2	8
ILL_SLO_ZEROPAGE_0x07: Literal[7] = 0x07
ILL_SLO_ZEROPAGE_X_0x17: Literal[23] = 0x17
ILL_SLO_ABSOLUTE_0x0F: Literal[15] = 0x0F
ILL_SLO_ABSOLUTE_X_0x1F: Literal[31] = 0x1F
ILL_SLO_ABSOLUTE_Y_0x1B: Literal[27] = 0x1B
ILL_SLO_INDEXED_INDIRECT_X_0x03: Literal[3] = 0x03
ILL_SLO_INDIRECT_INDEXED_Y_0x13: Literal[19] = 0x13

# https://masswerk.at/6502/6502_instruction_set.html#SRE
# LSR oper + EOR oper
#
# M = 0 -> [76543210] -> C, A EOR M -> A
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	SRE oper	47	2	5
# zeropage,X	SRE oper,X	57	2	6
# absolute	SRE oper	4F	3	6
# absolut,X	SRE oper,X	5F	3	7
# absolut,Y	SRE oper,Y	5B	3	7
# (indirect,X)	SRE (oper,X)	43	2	8
# (indirect),Y	SRE (oper),Y	53	2	8
ILL_SRE_ZEROPAGE_0x47: Literal[71] = 0x47
ILL_SRE_ZEROPAGE_X_0x57: Literal[87] = 0x57
ILL_SRE_ABSOLUTE_0x4F: Literal[79] = 0x4F
ILL_SRE_ABSOLUTE_X_0x4F: Literal[95] = 0x5F
ILL_SRE_ABSOLUTE_Y_0x5B: Literal[91] = 0x5B
ILL_SRE_INDEXED_INDIRECT_X_0x43: Literal[67] = 0x43
ILL_SRE_INDIRECT_INDEXED_Y_0x53: Literal[83] = 0x53


# https://masswerk.at/6502/6502_instruction_set.html#TAS
# Puts A AND X in S and stores A AND X AND (high-byte of addr. + 1) at addr.
#
# unstable: sometimes 'AND (H+1)' is dropped, page boundary crossings may not work
# (with the high-byte of the value used as the high-byte of the address)
#
# A AND X -> S, A AND X AND (H+1) -> M
#
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolut,Y	TAS oper,Y	9B	3	5  	†
ILL_TAS_ABSOLUTE_0x9B: Literal[155] = 0x9B

# https://masswerk.at/6502/6502_instruction_set.html#USBC
# SBC oper + NOP
#
# effectively same as normal SBC immediate, instr. E9.
#
# A - M - C -> A
#
# N	Z	C	I	D	V
# +	+	+	-	-	+
# addressing	assembler	opc	bytes	cycles
# immediate	USBC #oper	EB	2	2
#
#
# https://masswerk.at/6502/6502_instruction_set.html#NOPs (various)
# (including DOP, TOP)
# Instructions effecting in 'no operations' in various address modes. Operands are ignored.
#
# N	Z	C	I	D	V
# -	-	-	-	-	-
# opc	addressing	bytes	cycles
# 1A	implied	1	2
# 3A	implied	1	2
# 5A	implied	1	2
# 7A	implied	1	2
# DA	implied	1	2
# FA	implied	1	2
# 80	immediate	2	2
# 82	immediate	2	2
# 89	immediate	2	2
# C2	immediate	2	2
# E2	immediate	2	2
# 04	zeropage	2	3
# 44	zeropage	2	3
# 64	zeropage	2	3
# 14	zeropage,X	2	4
# 34	zeropage,X	2	4
# 54	zeropage,X	2	4
# 74	zeropage,X	2	4
# D4	zeropage,X	2	4
# F4	zeropage,X	2	4
# 0C	absolute	3	4
# 1C	absolut,X	3	4*
# 3C	absolut,X	3	4*
# 5C	absolut,X	3	4*
# 7C	absolut,X	3	4*
# DC	absolut,X	3	4*
# FC	absolut,X	3	4*
# _IMMEDIATE_
# _ZEROPAGE_
# _ZEROPAGE_X_
# _ABSOLUTE_
# _ABSOLUTE_X_
# _ABSOLUTE_Y_
# _INDEXED_INDIRECT_X_
# _INDIRECT_INDEXED_Y_

# https://masswerk.at/6502/6502_instruction_set.html#JAM (various)
# These instructions freeze the CPU.
#
# The processor will be trapped infinitely in T1 phase with $FF on the data bus. — Reset required.
#
# Instruction codes: 02, 12, 22, 32, 42, 52, 62, 72, 92, B2, D2, F2


class InstructionSet(enum.IntEnum):
    """Instruction set for the mos6502 CPU."""

    """ADC"""

    """AND"""




    """DEC"""

    """DEX"""

    """DEY"""

    """EOR"""

    """INC"""

    """INX"""

    """INY"""

    """JMP"""

    """JSR"""

    """LDA"""

    """LDX"""

    """LDY"""


    """ORA"""

    """PHA"""

    """PHP"""

    """PLA"""

    """PLP"""



    """RTI"""

    """RTS"""

    """SBC"""

    """SEC"""
    SEC_IMPLIED_0x38 = 0x38

    """SED"""
    SED_IMPLIED_0xF8 = SED_IMPLIED_0xF8

    """SEI"""
    SEI_IMPLIED_0x78 = SEI_IMPLIED_0x78

    """STA"""

    """STX"""

    """STY"""

    """TAX"""

    """TAY"""

    """TSX"""

    """TXA"""

    """TXS"""

    """TYA"""

    """Illegal Opcodes"""
    """ALR"""
    ILL_ALR_IMMEDIATE_0x4B = ILL_ALR_IMMEDIATE_0x4B

    """ANC"""
    ILL_ANC_IMMEDIATE_0x0B = ILL_ANC_IMMEDIATE_0x0B

    """ANC2"""
    ILL_ANC2_IMMEDIATE_0x2B = ILL_ANC2_IMMEDIATE_0x2B

    """ANE"""
    ILL_ANE_IMMEDIATE_0x8B = ILL_ANE_IMMEDIATE_0x8B

    """ARR"""
    ILL_ARR_IMMEDIATE_0x6B = ILL_ARR_IMMEDIATE_0x6B

    """DCP"""
    ILL_DCP_ZEROPAGE_ZEROPAGE_0xC7 = ILL_DCP_ZEROPAGE_ZEROPAGE_0xC7
    ILL_DCP_ZEROPAGE_X_0xD7 = ILL_DCP_ZEROPAGE_X_0xD7
    ILL_DCP_ABSOLUTE_0xCF = ILL_DCP_ABSOLUTE_0xCF
    ILL_DCP_ABSOLUTE_X_0xDF = ILL_DCP_ABSOLUTE_X_0xDF
    ILL_DCP_ABSOLUTE_Y_0xDB = ILL_DCP_ABSOLUTE_Y_0xDB
    ILL_DCP_INDEXED_INDIRECT_X_0xC3 = ILL_DCP_INDEXED_INDIRECT_X_0xC3
    ILL_DCP_INDIRECT_INDEXED_Y_0xD3 = ILL_DCP_INDIRECT_INDEXED_Y_0xD3

    """ISC"""
    ILL_ISC_ZEROPAGE_0xE7 = ILL_ISC_ZEROPAGE_0xE7
    ILL_ISC_ZEROPAGE_X_0xF7 = ILL_ISC_ZEROPAGE_X_0xF7
    ILL_ISC_ABSOLUTE_0xEF = ILL_ISC_ABSOLUTE_0xEF
    ILL_ISC_ABSOLUTE_X_0xFF = ILL_ISC_ABSOLUTE_X_0xFF
    ILL_ISC_ABSOLUTE_Y_0xFB = ILL_ISC_ABSOLUTE_Y_0xFB
    ILL_ISC_INDEXED_INDIRECT_X_0xE3 = ILL_ISC_INDEXED_INDIRECT_X_0xE3
    ILL_ISC_INDIRECT_INDEXED_Y_0xF3 = ILL_ISC_INDIRECT_INDEXED_Y_0xF3

    """LAS"""
    ILL_LAS_ABSOLUTE_0xBB = ILL_LAS_ABSOLUTE_0xBB

    """LAX"""
    ILL_LAX_ZEROPAGE_0xA7 = ILL_LAX_ZEROPAGE_0xA7
    ILL_LAX_ZEROPAGE_X_0xB7 = ILL_LAX_ZEROPAGE_X_0xB7
    ILL_LAX_ABSOLUTE_0xAF = ILL_LAX_ABSOLUTE_0xAF
    ILL_LAX_ABSOLUTE_Y_0xBF = ILL_LAX_ABSOLUTE_Y_0xBF
    ILL_LAX_INDEXED_INDIRECT_X_0xA3 = ILL_LAX_INDEXED_INDIRECT_X_0xA3
    ILL_LAX_INDIRECT_INDEXED_Y_0xB3 = ILL_LAX_INDIRECT_INDEXED_Y_0xB3

    """LXA"""
    ILL_LXA_IMMEDIATE_0xAB = ILL_LXA_IMMEDIATE_0xAB

    """RLA"""
    ILL_RLA_ZEROPAGE_0x27 = ILL_RLA_ZEROPAGE_0x27
    ILL_RLA_ZEROPAGE_X_0x37 = ILL_RLA_ZEROPAGE_X_0x37
    ILL_RLA_ABSOLUTE_0x2F = ILL_RLA_ABSOLUTE_0x2F
    ILL_RLA_ABSOLUTE_X_0x3F = ILL_RLA_ABSOLUTE_X_0x3F
    ILL_RLA_ABSOLUTE_Y_0x3B = ILL_RLA_ABSOLUTE_Y_0x3B
    ILL_RLA_INDEXED_INDIRECT_X_0x23 = ILL_RLA_INDEXED_INDIRECT_X_0x23
    ILL_RLA_INDIRECT_INDEXED_Y_0x33 = ILL_RLA_INDIRECT_INDEXED_Y_0x33

    """RRA"""
    ILL_RRA_ZEROPAGE_0x67 = ILL_RRA_ZEROPAGE_0x67
    ILL_RRA_ZEROPAGE_X_0x77 = ILL_RRA_ZEROPAGE_X_0x77
    ILL_RRA_ABSOLUTE_0x6F = ILL_RRA_ABSOLUTE_0x6F
    ILL_RRA_ABSOLUTE_X_0x7F = ILL_RRA_ABSOLUTE_X_0x7F
    ILL_RRA_ABSOLUTE_Y_0x7B = ILL_RRA_ABSOLUTE_Y_0x7B
    ILL_RRA_INDEXED_INDIRECT_X_0x63 = ILL_RRA_INDEXED_INDIRECT_X_0x63
    ILL_RRA_INDIRECT_INDEXED_Y_0x73 = ILL_RRA_INDIRECT_INDEXED_Y_0x73

    """SAX"""
    ILL_SAX_ZEROPAGE_0x87 = ILL_SAX_ZEROPAGE_0x87
    ILL_SAX_ZEROPAGE_Y_0x97 = ILL_SAX_ZEROPAGE_Y_0x97
    ILL_SAX_ABSOLUTE_0x8F = ILL_SAX_ABSOLUTE_0x8F
    ILL_SAX_INDEXED_INDIRECT_X_0x83 = ILL_SAX_INDEXED_INDIRECT_X_0x83

    """SBX"""
    ILL_SBX_IMMEDIATE_0xCB = ILL_SBX_IMMEDIATE_0xCB

    """SHA"""
    ILL_SHA_ABSOLUTE_Y_0x9F = ILL_SHA_ABSOLUTE_Y_0x9F
    ILL_SHA_INDIRECT_INDEXED_Y_0x93 = ILL_SHA_INDIRECT_INDEXED_Y_0x93

    """SHX"""
    ILL_SHX_ABSOLUTE_Y_0x9E = ILL_SHX_ABSOLUTE_Y_0x9E

    """SHY"""
    ILL_SHY_ABSOLUTE_X_0x9C = ILL_SHY_ABSOLUTE_X_0x9C

    """SLO"""
    ILL_SLO_ZEROPAGE_0x07 = ILL_SLO_ZEROPAGE_0x07
    ILL_SLO_ZEROPAGE_X_0x17 = ILL_SLO_ZEROPAGE_X_0x17
    ILL_SLO_ABSOLUTE_0x0F = ILL_SLO_ABSOLUTE_0x0F
    ILL_SLO_ABSOLUTE_X_0x1F = ILL_SLO_ABSOLUTE_X_0x1F
    ILL_SLO_ABSOLUTE_Y_0x1B = ILL_SLO_ABSOLUTE_Y_0x1B
    ILL_SLO_INDEXED_INDIRECT_X_0x03 = ILL_SLO_INDEXED_INDIRECT_X_0x03
    ILL_SLO_INDIRECT_INDEXED_Y_0x13 = ILL_SLO_INDIRECT_INDEXED_Y_0x13

    """SRE"""
    ILL_SRE_ZEROPAGE_0x47 = ILL_SRE_ZEROPAGE_0x47
    ILL_SRE_ZEROPAGE_X_0x57 = ILL_SRE_ZEROPAGE_X_0x57
    ILL_SRE_ABSOLUTE_0x4F = ILL_SRE_ABSOLUTE_0x4F
    ILL_SRE_ABSOLUTE_X_0x4F = ILL_SRE_ABSOLUTE_X_0x4F
    ILL_SRE_ABSOLUTE_Y_0x5B = ILL_SRE_ABSOLUTE_Y_0x5B
    ILL_SRE_INDEXED_INDIRECT_X_0x43 = ILL_SRE_INDEXED_INDIRECT_X_0x43
    ILL_SRE_INDIRECT_INDEXED_Y_0x53 = ILL_SRE_INDIRECT_INDEXED_Y_0x53

    """TAS"""
    ILL_TAS_ABSOLUTE_0x9B = ILL_TAS_ABSOLUTE_0x9B

    """USBC"""
    """NOPS"""
    """JAM"""

    @classmethod
    def _missing_(cls: type["InstructionSet"], value: int) -> NoReturn:
        raise IllegalCPUInstructionError(f"{value} ({value:02X}) is not a valid {cls}.")


# It would be possible to store the assembly instructions mnemonics as format specifiers
# as well as generate the machine code using the enumeration and a little bit of hackery
InstructionSet.map = {}

"""LDA"""

"""JSR"""

"""STA"""

"""STX"""

"""STY"""

# Template
# InstructionSet.map[] = {
#     'flags':
