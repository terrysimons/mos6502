#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instruction set for the mos6502 CPU."""
import enum

from mos6502.exceptions import IllegalCPUInstructionException
import mos6502.flags as flags
from mos6502.memory import Byte, Word
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

# https://www.masswerk.at/6502/6502_instruction_set.html#ADC
#
# Add Memory to Accumulator with Carry
#
# A + M + C -> A, C
# N	Z	C	I	D	V
# +	+	+	-	-	+
# addressing	assembler	opc	bytes	cycles
# immediate	ADC #oper	69	2	2
# zeropage	ADC oper	65	2	3
# zeropage,X	ADC oper,X	75	2	4
# absolute	ADC oper	6D	3	4
# absolute,X	ADC oper,X	7D	3	4*
# absolute,Y	ADC oper,Y	79	3	4*
# (indirect,X)	ADC (oper,X)	61	2	6
# (indirect),Y	ADC (oper),Y	71	2	5*
ADC_IMMEDIATE_0x69 = 0x69
ADC_ZEROPAGE_0x65 = 0x65
ADC_ZEROPAGE_X_0x75 = 0x75
ADC_ABSOLUTE_0x6D = 0x6D
ADC_ABSOLUTE_X_0x7D = 0x7D
ADC_ABSOLUTE_Y_0x79 = 0x79
ADC_INDEXED_INDIRECT_X_0x61 = 0x61
ADC_INDIRECT_INDEXED_Y_0x71 = 0x71

# https://www.masswerk.at/6502/6502_instruction_set.html#AND
#
# AND Memory with Accumulator
#
# A AND M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	AND #oper	29	2	2
# zeropage	AND oper	25	2	3
# zeropage,X	AND oper,X	35	2	4
# absolute	AND oper	2D	3	4
# absolute,X	AND oper,X	3D	3	4*
# absolute,Y	AND oper,Y	39	3	4*
# (indirect,X)	AND (oper,X)	21	2	6
# (indirect),Y	AND (oper),Y	31	2	5*
AND_IMMEDIATE_0x29 = 0x29
AND_ZEROPAGE_0x25 = 0x25
AND_ZEROPAGE_X_0x35 = 0x35
AND_ABSOLUTE_0x2D = 0x2D
AND_ABSOLUTE_X_0x3D = 0x3D
AND_ABSOLUTE_Y_0x39 = 0x39
AND_INDEXED_INDIRECT_X_0x21 = 0x21
AND_INDIRECT_INDEXED_Y_0x31 = 0x31


# https://masswerk.at/6502/6502_instruction_set.html#ASL
#
# Shift Left One Bit (Memory or Accumulator)
#
# C <- [76543210] <- 0
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	ASL A	0A	1	2
# zeropage	ASL oper	06	2	5
# zeropage,X	ASL oper,X	16	2	6
# absolute	ASL oper	0E	3	6
# absolute,X	ASL oper,X	1E	3	7
ASL_ACCUMULATOR_0x0A = 0x0A
ASL_ZEROPAGE_0x06 = 0x06
ASL_ZEROPAGE_X_0x16 = 0x16
ASL_ABSOLUTE_0x0E = 0x0E
ASL_ABSOLUTE_X_0x1E = 0x1E


# https://masswerk.at/6502/6502_instruction_set.html#BCC
#
# Branch on Carry Clear
# branch on C = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BCC oper	90	2	2**
BBC_RELATIVE_0x90 = 0x90


# https://masswerk.at/6502/6502_instruction_set.html#BCS
#
# Branch on Carry Set
#
# branch on C = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BCS oper	B0	2	2**
BCS_RELATIVE_0xB0 = 0xB0


# https://masswerk.at/6502/6502_instruction_set.html#BEQ
#
# Branch on Result Zero
# branch on Z = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BEQ oper	F0	2	2**
BEQ_RELATIVE_0xF0 = 0xF0


# https://masswerk.at/6502/6502_instruction_set.html#BIT
#
# Test Bits in Memory with Accumulator
#
# bits 7 and 6 of operand are transfered to bit 7 and 6 of SR (N,V);
# the zero-flag is set to the result of operand AND accumulator.
#
# A AND M, M7 -> N, M6 -> V
# N	Z	C	I	D	V
# M7	+	-	-	-	M6
# addressing	assembler	opc	bytes	cycles
# zeropage	BIT oper	24	2	3
# absolute	BIT oper	2C	3	4
BIT_ZEROPAGE_0x24 = 0x24
BIT_ABSOLUTE_0x2C = 0x2C

# https://masswerk.at/6502/6502_instruction_set.html#BMI
# Branch on Result Minus
#
# branch on N = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BMI oper	30	2	2**
BMI_RELATIVE_0x30 = 0x30


# https://masswerk.at/6502/6502_instruction_set.html#BNE
# Branch on Result not Zero
#
# branch on Z = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BNE oper	D0	2	2**
BNE_RELATIVE_0xD0 = 0xD0

# https://masswerk.at/6502/6502_instruction_set.html#BPL
# Branch on Result Plus
#
# branch on N = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BPL oper	10	2	2**
BPL_RELATIVE_0x10 = 0x10

# https://masswerk.at/6502/6502_instruction_set.html#BRK
# Force Break
#
# BRK initiates a software interrupt similar to a hardware
# interrupt (IRQ). The return address pushed to the stack is
# PC+2, providing an extra byte of spacing for a break mark
# (identifying a reason for the break.)
# The status register will be pushed to the stack with the break
# flag set to 1. However, when retrieved during RTI or by a PLP
# instruction, the break flag will be ignored.
# The interrupt disable flag is not set automatically.
#
# interrupt,
# push PC+2, push SR
# N	Z	C	I	D	V
# -	-	-	1	-	-
# addressing	assembler	opc	bytes	cycles
# implied	BRK	00	1	7
BRK_IMPLIED_0x00 = 0x00

# https://masswerk.at/6502/6502_instruction_set.html#BVC
# Branch on Overflow Clear
#
# branch on V = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BVC oper	50	2	2**
BVC_RELATIVE_0x50 = 0x50


# https://masswerk.at/6502/6502_instruction_set.html#BVS
# Branch on Overflow Set
#
# branch on V = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BVS oper	70	2	2**
BVS_RELATIVE_0x70 = 0x70


# https://masswerk.at/6502/6502_instruction_set.html#CLC
# Clear Carry Flag
#
# 0 -> C
# N	Z	C	I	D	V
# -	-	0	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	CLC	18	1	2
CLC_IMPLIED_0x18 = 0x18

# https://masswerk.at/6502/6502_instruction_set.html#CLD
# Clear Decimal Mode
#
# 0 -> D
# N	Z	C	I	D	V
# -	-	-	-	0	-
# addressing	assembler	opc	bytes	cycles
# implied	CLD	D8	1	2
CLD_IMPLIED_0xD8 = 0xD8

# https://masswerk.at/6502/6502_instruction_set.html#CLI
# Clear Interrupt Disable Bit
#
# 0 -> I
# N	Z	C	I	D	V
# -	-	-	0	-	-
# addressing	assembler	opc	bytes	cycles
# implied	CLI	58	1	2
CLI_IMPLIED_0x58 = 0x58

# https://masswerk.at/6502/6502_instruction_set.html#CLV
# Clear Overflow Flag
#
# 0 -> V
# N	Z	C	I	D	V
# -	-	-	-	-	0
# addressing	assembler	opc	bytes	cycles
# implied	CLV	B8	1	2
CLV_IMPLIED_0xB8 = 0xB8

# https://masswerk.at/6502/6502_instruction_set.html#CMP
# Compare Memory with Accumulator
#
# A - M
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	CMP #oper	C9	2	2
# zeropage	CMP oper	C5	2	3
# zeropage,X	CMP oper,X	D5	2	4
# absolute	CMP oper	CD	3	4
# absolute,X	CMP oper,X	DD	3	4*
# absolute,Y	CMP oper,Y	D9	3	4*
# (indirect,X)	CMP (oper,X)	C1	2	6
# (indirect),Y	CMP (oper),Y	D1	2	5*
CMP_IMMEDIATE_0xC9 = 0xC9
CMP_ZEROPAGE_0xC5 = 0xC5
CMP_ZEROPAGE_X_0xD5 = 0xD5
CMP_ABSOLUTE_0xCD = 0xCD
CMP_ABSOLUTE_X_0xDD = 0xDD
CMP_ABSOLUTE_Y_0xD9 = 0xD9
CMP_INDEXED_INDIRECT_X_0xC1 = 0xC1
CMP_INDIRECT_INDEXED_Y_0xD1 = 0xD1

# https://masswerk.at/6502/6502_instruction_set.html#CPX
# Compare Memory and Index X
#
# X - M
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	CPX #oper	E0	2	2
# zeropage	CPX oper	E4	2	3
# absolute	CPX oper	EC	3	4
CPX_IMMEDIATE_0xE0 = 0xE0
CPX_ZEROPAGE_0xE4 = 0xE4
CPX_ABSOLUTE_0xEC = 0xEC

# https://masswerk.at/6502/6502_instruction_set.html#CPY
# Compare Memory and Index Y
#
# Y - M
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	CPY #oper	C0	2	2
# zeropage	CPY oper	C4	2	3
# absolute	CPY oper	CC	3	4
CPY_IMMEDIATE_0xC0 = 0xC0
CPY_ZEROPAGE_0xC4 = 0xC4
CPY_ABSOLUTE_0xCC = 0xCC

# https://masswerk.at/6502/6502_instruction_set.html#DEC
# Decrement Memory by One
#
# M - 1 -> M
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	DEC oper	C6	2	5
# zeropage,X	DEC oper,X	D6	2	6
# absolute	DEC oper	CE	3	6
# absolute,X	DEC oper,X	DE	3	7
DEC_ZEROPAGE_0xC6 = 0xC6
DEC_ZEROPAGE_X_0xD6 = 0xD6
DEC_ABSOLUTE_0xCE = 0xCE
DEC_ABSOLUTE_X_0xDE = 0xDE

# https://masswerk.at/6502/6502_instruction_set.html#DEX
# Decrement Index X by One
#
# X - 1 -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	DEX	CA	1	2
DEX_IMPLIED_0xCA = 0xCA

# https://masswerk.at/6502/6502_instruction_set.html#DEY
# Decrement Index Y by One
#
# Y - 1 -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	DEY	88	1	2
DEY_IMPLIED_0x88 = 0x88

# https://masswerk.at/6502/6502_instruction_set.html#EOR
# Exclusive-OR Memory with Accumulator
#
# A EOR M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	EOR #oper	49	2	2
# zeropage	EOR oper	45	2	3
# zeropage,X	EOR oper,X	55	2	4
# absolute	EOR oper	4D	3	4
# absolute,X	EOR oper,X	5D	3	4*
# absolute,Y	EOR oper,Y	59	3	4*
# (indirect,X)	EOR (oper,X)	41	2	6
# (indirect),Y	EOR (oper),Y	51	2	5*
EOR_IMMEDIATE_0x49 = 0X49
EOR_ZEROPAGE_0x45 = 0X45
EOR_ZEROPAGE_X_0x55 = 0x55
EOR_ABSOLUTE_0x4D = 0x4D
EOR_ABSOLUTE_X_0x5D = 0x5D
EOR_ABSOLUTE_Y_0x59 = 0x59
EOR_INDEXED_INDIRECT_X_0x41 = 0x41
EOR_INDIRECT_INDEXED_Y_0x51 = 0x51

# https://masswerk.at/6502/6502_instruction_set.html#INC
# Increment Memory by One
#
# M + 1 -> M
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	INC oper	E6	2	5
# zeropage,X	INC oper,X	F6	2	6
# absolute	INC oper	EE	3	6
# absolute,X	INC oper,X	FE	3	7
INC_ZEROPAGE_0xE6 = 0xF6
INC_ZEROPAGE_X_0xF6 = 0xF6
INC_ABSOLUTE_0xEE = 0xEE
INC_ABSOLUTE_X_0xFE = 0xFE

# https://masswerk.at/6502/6502_instruction_set.html#INX
# Increment Index X by One
#
# X + 1 -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	INX	E8	1	2
INX_IMPLIED_0xE8 = 0xE8


# https://masswerk.at/6502/6502_instruction_set.html#INY
# Increment Index Y by One
#
# Y + 1 -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	INY	C8	1	2
INY_IMPLIED_0xC8 = 0xC8


# https://masswerk.at/6502/6502_instruction_set.html#JMP
# Jump to New Location
#
# (PC+1) -> PCL
# (PC+2) -> PCH
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolute	JMP oper	4C	3	3
# indirect	JMP (oper)	6C	3	5
JMP_ABSOLUTE_0x4C = 0x4C
JMP_INDIRECT_0x6C = 0x6C

# https://masswerk.at/6502/6502_instruction_set.html#JSR
#
# Jump to New Location Saving Return Address
#
# push (PC+2),
# (PC+1) -> PCL
# (PC+2) -> PCH
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolute	JSR oper	20	3	6
JSR_ABSOLUTE_0x20 = 0x20

# https://masswerk.at/6502/6502_instruction_set.html#LDA
#
# Load Accumulator with Memory
#
# M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	LDA #oper	A9	2	2
# zeropage	LDA oper	A5	2	3
# zeropage,X	LDA oper,X	B5	2	4
# absolute	LDA oper	AD	3	4
# absolute,X	LDA oper,X	BD	3	4*
# absolute,Y	LDA oper,Y	B9	3	4*
# (indirect,X)	LDA (oper,X)	A1	2	6
# (indirect),Y	LDA (oper),Y	B1	2	5*
LDA_IMMEDIATE_0xA9 = 0xA9
LDA_ZEROPAGE_0xA5 = 0xA5
LDA_ZEROPAGE_X_0xB5 = 0xB5
LDA_ABSOLUTE_0xAD = 0xAD
LDA_ABSOLUTE_X_0xBD = 0xBD
LDA_ABSOLUTE_Y_0xB9 = 0xB9
LDA_INDEXED_INDIRECT_X_0xA1 = 0xA1
LDA_INDIRECT_INDEXED_Y_0xB1 = 0xB1

# https://masswerk.at/6502/6502_instruction_set.html#LDX
#
# Load Index X with Memory
#
# M -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	LDX #oper	A2	2	2
# zeropage	LDX oper	A6	2	3
# zeropage,Y	LDX oper,Y	B6	2	4
# absolute	LDX oper	AE	3	4
# absolute,Y	LDX oper,Y	BE	3	4*
LDX_IMMEDIATE_0xA2 = 0xA2
LDX_ZEROPAGE_0xA6 = 0xA6
LDX_ZEROPAGE_Y_0xB6 = 0xB6
LDX_ABSOLUTE_0xAE = 0xAE
LDX_ABSOLUTE_Y_0xBE = 0xBE

# https://masswerk.at/6502/6502_instruction_set.html#LDY
#
# Load Index Y with Memory
#
# M -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	LDY #oper	A0	2	2
# zeropage	LDY oper	A4	2	3
# zeropage,X	LDY oper,X	B4	2	4
# absolute	LDY oper	AC	3	4
# absolute,X	LDY oper,X	BC	3	4*
LDY_IMMEDIATE_0xA0 = 0xA0
LDY_ZEROPAGE_0xA4 = 0xA4
LDY_ZEROPAGE_X_0xB4 = 0xB4
LDY_ABSOLUTE_0xAC = 0xAC
LDY_ABSOLUTE_X_0xBC = 0xBC

# https://masswerk.at/6502/6502_instruction_set.html#LSR
# Shift One Bit Right (Memory or Accumulator)
#
# 0 -> [76543210] -> C
# N	Z	C	I	D	V
# 0	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	LSR A	4A	1	2
# zeropage	LSR oper	46	2	5
# zeropage,X	LSR oper,X	56	2	6
# absolute	LSR oper	4E	3	6
# absolute,X	LSR oper,X	5E	3	7
LSR_ACCUMULATOR_0x4A = 0x4A
LSR_ZEROPAGE_0x46 = 0x46
LSR_ZEROPAGE_X_0x56 = 0x56
LSR_ABSOLUTE_0x4E = 0x4E
LSR_ABSOLUTE_X_0x5E = 0x5E


# https://masswerk.at/6502/6502_instruction_set.html#NOP
# No Operation
#
# ---
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	NOP	EA	1	2
NOP_IMPLIED_0xEA = 0xEA


# https://masswerk.at/6502/6502_instruction_set.html#ORA
# OR Memory with Accumulator
#
# A OR M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	ORA #oper	09	2	2
# zeropage	ORA oper	05	2	3
# zeropage,X	ORA oper,X	15	2	4
# absolute	ORA oper	0D	3	4
# absolute,X	ORA oper,X	1D	3	4*
# absolute,Y	ORA oper,Y	19	3	4*
# (indirect,X)	ORA (oper,X)	01	2	6
# (indirect),Y	ORA (oper),Y	11	2	5*
ORA_IMMEDIATE_0x09 = 0x09
ORA_ZEROPAGE_0x05 = 0x05
ORA_ZEROPAGE_X_0x15 = 0x15
ORA_ABSOLUTE_0x0D = 0x0D
ORA_ABSOLUTE_X_0x1D = 0x1D
ORA_ABSOLUTE_Y_0x19 = 0x19
ORA_INDEXED_INDIRECT_X_0x01 = 0x01
ORA_INDIRECT_INDEXED_Y_0x11 = 0x11

# https://masswerk.at/6502/6502_instruction_set.html#PHA
# Push Accumulator on Stack
#
# push A
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	PHA	48	1	3
PHA_IMPLIED_0x48 = 0x48

# https://masswerk.at/6502/6502_instruction_set.html#PHP
# Push Processor Status on Stack
#
# The status register will be pushed with the break
# flag and bit 5 set to 1.
#
# push SR
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	PHP	08	1	3
PHP_IMPLIED_0x08 = 0x08


# https://masswerk.at/6502/6502_instruction_set.html#PLA
# Pull Accumulator from Stack
#
# pull A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	PLA	68	1	4
PLA_IMPLIED_0x68 = 0x68

# https://masswerk.at/6502/6502_instruction_set.html#PLP
# Pull Processor Status from Stack
#
# The status register will be pulled with the break
# flag and bit 5 ignored.
#
# pull SR
# N	Z	C	I	D	V
# from stack
# addressing	assembler	opc	bytes	cycles
# implied	PLP	28	1	4
PLP_IMPLIED_0x28 = 0x28

# https://masswerk.at/6502/6502_instruction_set.html#ROL
# Rotate One Bit Left (Memory or Accumulator)
#
# C <- [76543210] <- C
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	ROL A	2A	1	2
# zeropage	ROL oper	26	2	5
# zeropage,X	ROL oper,X	36	2	6
# absolute	ROL oper	2E	3	6
# absolute,X	ROL oper,X	3E	3	7
ROL_ACCUMULATOR_0x2A = 0x2A
ROL_ZEROPAGE_0x26 = 0x26
ROL_ZEROPAGE_X_0x36 = 0x36
ROL_ABSOLUTE_0x2E = 0x2E
ROL_ABSOLUTE_X_0x3E = 0x3E

# https://masswerk.at/6502/6502_instruction_set.html#ROR
# Rotate One Bit Right (Memory or Accumulator)
#
# C -> [76543210] -> C
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	ROR A	6A	1	2
# zeropage	ROR oper	66	2	5
# zeropage,X	ROR oper,X	76	2	6
# absolute	ROR oper	6E	3	6
# absolute,X	ROR oper,X	7E	3	7
ROR_ACCUMULATOR_0x6A = 0x6A
ROR_ZEROPAGE_0x66 = 0x66
ROR_ZEROPAGE_X_0x76 = 0x76
ROR_ABSOLUTE_0x6E = 0x6E
ROR_ABSOLUTE_X_0x7E = 0x7E


# https://masswerk.at/6502/6502_instruction_set.html#RTI
# Return from Interrupt
#
# The status register is pulled with the break flag
# and bit 5 ignored. Then PC is pulled from the stack.
#
# pull SR, pull PC
# N	Z	C	I	D	V
# from stack
# addressing	assembler	opc	bytes	cycles
# implied	RTI	40	1	6
RTI_IMPLIED_0x40 = 0x40

# https://masswerk.at/6502/6502_instruction_set.html#RTS
# Return from Subroutine
#
# pull PC, PC+1 -> PC
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	RTS	60	1	6
RTS_IMPLIED_0x60 = 0x60

# https://masswerk.at/6502/6502_instruction_set.html#SBC
# Subtract Memory from Accumulator with Borrow
#
# A - M - C -> A
# N	Z	C	I	D	V
# +	+	+	-	-	+
# addressing	assembler	opc	bytes	cycles
# immediate	SBC #oper	E9	2	2
# zeropage	SBC oper	E5	2	3
# zeropage,X	SBC oper,X	F5	2	4
# absolute	SBC oper	ED	3	4
# absolute,X	SBC oper,X	FD	3	4*
# absolute,Y	SBC oper,Y	F9	3	4*
# (indirect,X)	SBC (oper,X)	E1	2	6
# (indirect),Y	SBC (oper),Y	F1	2	5*
SBC_IMMEDIATE_0xE9 = 0xE9
SBC_ZEROPAGE_0xE5 = 0xE5
SBC_ZEROPAGE_X_0xF5 = 0xF5
SBC_ABSOLUTE_0xED = 0xED
SBC_ABSOLUTE_X_0xFD = 0xFD
SBC_ABSOLUTE_Y_0xF9 = 0xF9
SBC_INDEXED_INDIRECT_X_0xE1 = 0xE1
SBC_INDIRECT_INDEXED_Y_0xF1 = 0xF1

# https://masswerk.at/6502/6502_instruction_set.html#SEC
# Set Carry Flag
#
# 1 -> C
# N	Z	C	I	D	V
# -	-	1	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	SEC	38	1	2
SEC_IMPLIED_0x38 = 0x38

# https://masswerk.at/6502/6502_instruction_set.html#SED
# Set Decimal Flag
#
# 1 -> D
# N	Z	C	I	D	V
# -	-	-	-	1	-
# addressing	assembler	opc	bytes	cycles
# implied	SED	F8	1	2
SED_IMPLIED_0xF8 = 0xF8


# https://masswerk.at/6502/6502_instruction_set.html#SEI
# Set Interrupt Disable Status
#
# 1 -> I
# N	Z	C	I	D	V
# -	-	-	1	-	-
# addressing	assembler	opc	bytes	cycles
# implied	SEI	78	1	2
SEI_IMPLIED_0x78 = 0x78

# https://masswerk.at/6502/6502_instruction_set.html#STA
# Store Accumulator in Memory
#
# A -> M
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	STA oper	85	2	3
# zeropage,X	STA oper,X	95	2	4
# absolute	STA oper	8D	3	4
# absolute,X	STA oper,X	9D	3	5
# absolute,Y	STA oper,Y	99	3	5
# (indirect,X)	STA (oper,X)	81	2	6
# (indirect),Y	STA (oper),Y	91	2	6
STA_ZEROPAGE_0x85 = 0x85
STA_ZEROPAGE_X_0x95 = 0x95
STA_ABSOLUTE_0x8D = 0x8D
STA_ABSOLUTE_X_0x9D = 0x9D
STA_ABSOLUTE_Y_0x99 = 0x99
STA_INDEXED_INDIRECT_X_0x81 = 0x81
STA_INDIRECT_INDEXED_Y_0x91 = 0x91

# https://masswerk.at/6502/6502_instruction_set.html#STX
# Store Index X in Memory
#
# X -> M
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	STX oper	86	2	3
# zeropage,Y	STX oper,Y	96	2	4
# absolute	STX oper	8E	3	4
STX_ZEROPAGE_0x86 = 0x86
STX_ZEROPAGE_X_0x96 = 0x96
STX_ABSOLUTE_0x8E = 0x8E

# https://masswerk.at/6502/6502_instruction_set.html#STY
# Sore Index Y in Memory
#
# Y -> M
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	STY oper	84	2	3
# zeropage,X	STY oper,X	94	2	4
# absolute	STY oper	8C	3	4
STY_ZEROPAGE_0x84 = 0x84
STY_ZEROPAGE_X_0x94 = 0x94
STY_ABSOLUTE_0x8C = 0x8C

# https://masswerk.at/6502/6502_instruction_set.html#TAX
# Transfer Accumulator to Index X
#
# A -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TAX	AA	1	2
TAX_IMPLIED_0xAA = 0xAA

# https://masswerk.at/6502/6502_instruction_set.html#TAY
# Transfer Accumulator to Index Y
#
# A -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TAY	A8	1	2
TAY_IMPLIED_0xA8 = 0xA8

# https://masswerk.at/6502/6502_instruction_set.html#TSX
# Transfer Stack Pointer to Index X
#
# SP -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TSX	BA	1	2
TSX_IMPLIED_0xBA = 0xBA

# https://masswerk.at/6502/6502_instruction_set.html#TXA
# Transfer Index X to Accumulator
#
# X -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TXA	8A	1	2
TXA_IMPLIED_0x8A = 0x8A

# https://masswerk.at/6502/6502_instruction_set.html#TXS
# Transfer Index X to Stack Register
#
# X -> SP
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TXS	9A	1	2
TXS_IMPLIED_0x9A = 0x9A

# https://masswerk.at/6502/6502_instruction_set.html#TYA
# Transfer Index Y to Accumulator
#
# Y -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TYA	98	1	2
TYA_IMPLIED_0x98 = 0x98

''' Illegal Opcodes '''
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
# (ASR)
# AND oper + LSR
#
# A AND oper, 0 -> [76543210] -> C
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	ALR #oper	4B	2	2
ILL_ALR_IMMEDIATE_0x4B = 0x4B

# https://masswerk.at/6502/6502_instruction_set.html#ANC
# AND oper + set C as ASL
#
# A AND oper, bit(7) -> C
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	ANC #oper	0B	2	2
ILL_ANC_IMMEDIATE_0x0B = 0x0B

# https://masswerk.at/6502/6502_instruction_set.html#ANC2
# (ANC2)
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
ILL_ANC2_IMMEDIATE_0x2B = 0x2B

# https://masswerk.at/6502/6502_instruction_set.html#ANE
# (XAA)
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
ILL_ANE_IMMEDIATE_0x8B = 0x8B

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
ILL_ARR_IMMEDIATE_0x6B = 0x6B


# https://masswerk.at/6502/6502_instruction_set.html#DCP
# (DCM)
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
ILL_DCP_ZEROPAGE_ZEROPAGE_0xC7 = 0xC7
ILL_DCP_ZEROPAGE_X_0xD7 = 0xD7
ILL_DCP_ABSOLUTE_0xCF = 0xCF
ILL_DCP_ABSOLUTE_X_0xDF = 0xDF
ILL_DCP_ABSOLUTE_Y_0xDB = 0xDB
ILL_DCP_INDEXED_INDIRECT_X_0xC3 = 0xC3
ILL_DCP_INDIRECT_INDEXED_Y_0xD3 = 0xD3

# https://masswerk.at/6502/6502_instruction_set.html#ISC
# (ISB, INS)
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
ILL_ISC_ZEROPAGE_0xE7 = 0xE7
ILL_ISC_ZEROPAGE_X_0xF7 = 0xF7
ILL_ISC_ABSOLUTE_0xEF = 0xEF
ILL_ISC_ABSOLUTE_X_0xFF = 0xFF
ILL_ISC_ABSOLUTE_Y_0xFB = 0xFB
ILL_ISC_INDEXED_INDIRECT_X_0xE3 = 0xE3
ILL_ISC_INDIRECT_INDEXED_Y_0xF3 = 0xF3

# https://masswerk.at/6502/6502_instruction_set.html#LAS
# (LAR)
# LDA/TSX oper
#
# M AND SP -> A, X, SP
#
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolut,Y	LAS oper,Y	BB	3	4*
ILL_LAS_ABSOLUTE_0xBB = 0xBB

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
ILL_LAX_ZEROPAGE_0xA7 = 0xA7
ILL_LAX_ZEROPAGE_X_0xB7 = 0xB7
ILL_LAX_ABSOLUTE_0xAF = 0xAF
ILL_LAX_ABSOLUTE_Y_0xBF = 0xBF
ILL_LAX_INDEXED_INDIRECT_X_0xA3 = 0xA3
ILL_LAX_INDIRECT_INDEXED_Y_0xB3 = 0xB3

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
ILL_LXA_IMMEDIATE_0xAB = 0xAB

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
ILL_RLA_ZEROPAGE_0x27 = 0x27
ILL_RLA_ZEROPAGE_X_0x37 = 0x37
ILL_RLA_ABSOLUTE_0x2F = 0x2F
ILL_RLA_ABSOLUTE_X_0x3F = 0x3F
ILL_RLA_ABSOLUTE_Y_0x3B = 0x3B
ILL_RLA_INDEXED_INDIRECT_X_0x23 = 0x23
ILL_RLA_INDIRECT_INDEXED_Y_0x33 = 0x33

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
ILL_RRA_ZEROPAGE_0x67 = 0x67
ILL_RRA_ZEROPAGE_X_0x77 = 0x77
ILL_RRA_ABSOLUTE_0x6F = 0x6F
ILL_RRA_ABSOLUTE_X_0x7F = 0x7F
ILL_RRA_ABSOLUTE_Y_0x7B = 0x7B
ILL_RRA_INDEXED_INDIRECT_X_0x63 = 0x63
ILL_RRA_INDIRECT_INDEXED_Y_0x73 = 0x73

# https://masswerk.at/6502/6502_instruction_set.html#SAX
# (AXS, AAX)
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
ILL_SAX_ZEROPAGE_0x87 = 0x87
ILL_SAX_ZEROPAGE_Y_0x97 = 0x97
ILL_SAX_ABSOLUTE_0x8F = 0x8F
ILL_SAX_INDEXED_INDIRECT_X_0x83 = 0x83


# https://masswerk.at/6502/6502_instruction_set.html#SBX
# (AXS, SAX)
# CMP and DEX at once, sets flags like CMP
#
# (A AND X) - oper -> X
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	SBX #oper	CB	2	2
ILL_SBX_IMMEDIATE_0xCB = 0xCB

# https://masswerk.at/6502/6502_instruction_set.html#SHA
# (AHX, AXA)
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
ILL_SHA_ABSOLUTE_Y_0x9F = 0x9F
ILL_SHA_INDIRECT_INDEXED_Y_0x93 = 0x93

# https://masswerk.at/6502/6502_instruction_set.html#SHX
# (A11, SXA, XAS)
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
ILL_SHX_ABSOLUTE_Y_0x9E = 0x9E

# https://masswerk.at/6502/6502_instruction_set.html#SHY
# SHY (A11, SYA, SAY)
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
ILL_SHY_ABSOLUTE_X_0x9C = 0x9C


# https://masswerk.at/6502/6502_instruction_set.html#SLO
# (ASO)
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
ILL_SLO_ZEROPAGE_0x07 = 0x07
ILL_SLO_ZEROPAGE_X_0x17 = 0x17
ILL_SLO_ABSOLUTE_0x0F = 0x0F
ILL_SLO_ABSOLUTE_X_0x1F = 0x1F
ILL_SLO_ABSOLUTE_Y_0x1B = 0x1B
ILL_SLO_INDEXED_INDIRECT_X_0x03 = 0x03
ILL_SLO_INDIRECT_INDEXED_Y_0x13 = 0x13

# https://masswerk.at/6502/6502_instruction_set.html#SRE
# (LSE)
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
ILL_SRE_ZEROPAGE_0x47 = 0x47
ILL_SRE_ZEROPAGE_X_0x57 = 0x57
ILL_SRE_ABSOLUTE_0x4F = 0x4F
ILL_SRE_ABSOLUTE_X_0x4F = 0x5F
ILL_SRE_ABSOLUTE_Y_0x5B = 0x5B
ILL_SRE_INDEXED_INDIRECT_X_0x43 = 0x43
ILL_SRE_INDIRECT_INDEXED_Y_0x53 = 0x53


# https://masswerk.at/6502/6502_instruction_set.html#TAS
# TAS (XAS, SHS)
# Puts A AND X in SP and stores A AND X AND (high-byte of addr. + 1) at addr.
#
# unstable: sometimes 'AND (H+1)' is dropped, page boundary crossings may not work
# (with the high-byte of the value used as the high-byte of the address)
#
# A AND X -> SP, A AND X AND (H+1) -> M
#
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolut,Y	TAS oper,Y	9B	3	5  	†
ILL_TAS_ABSOLUTE_0x9B = 0x9B

# https://masswerk.at/6502/6502_instruction_set.html#USBC
# (SBC)
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
# (KIL, HLT)
# These instructions freeze the CPU.
#
# The processor will be trapped infinitely in T1 phase with $FF on the data bus. — Reset required.
#
# Instruction codes: 02, 12, 22, 32, 42, 52, 62, 72, 92, B2, D2, F2


class InstructionSet(enum.IntEnum):
    """Instruction set for the mos6502 CPU."""

    '''ADC'''
    ADC_IMMEDIATE_0x69 = ADC_IMMEDIATE_0x69
    ADC_ZEROPAGE_0x65 = ADC_ZEROPAGE_0x65
    ADC_ZEROPAGE_X_0x75 = ADC_ZEROPAGE_X_0x75
    ADC_ABSOLUTE_0x6D = ADC_ABSOLUTE_0x6D
    ADC_ABSOLUTE_X_0x7D = ADC_ABSOLUTE_X_0x7D
    ADC_ABSOLUTE_Y_0x79 = ADC_ABSOLUTE_Y_0x79
    ADC_INDEXED_INDIRECT_X_0x61 = ADC_INDEXED_INDIRECT_X_0x61
    ADC_INDIRECT_INDEXED_Y_0x71 = ADC_INDIRECT_INDEXED_Y_0x71

    '''AND'''
    AND_IMMEDIATE_0x29 = AND_IMMEDIATE_0x29
    AND_ZEROPAGE_0x25 = AND_ZEROPAGE_0x25
    AND_ZEROPAGE_X_0x35 = AND_ZEROPAGE_X_0x35
    AND_ABSOLUTE_0x2D = AND_ABSOLUTE_0x2D
    AND_ABSOLUTE_X_0x3D = AND_ABSOLUTE_X_0x3D
    AND_ABSOLUTE_Y_0x39 = AND_ABSOLUTE_Y_0x39
    AND_INDEXED_INDIRECT_X_0x21 = AND_INDEXED_INDIRECT_X_0x21
    AND_INDIRECT_INDEXED_Y_0x31 = AND_INDIRECT_INDEXED_Y_0x31

    '''ASL'''
    ASL_ACCUMULATOR_0x0A = ASL_ACCUMULATOR_0x0A
    ASL_ZEROPAGE_0x06 = ASL_ZEROPAGE_0x06
    ASL_ZEROPAGE_X_0x16 = ASL_ZEROPAGE_X_0x16
    ASL_ABSOLUTE_0x0E = ASL_ABSOLUTE_0x0E
    ASL_ABSOLUTE_X_0x1E = ASL_ABSOLUTE_X_0x1E

    '''BCC'''
    BBC_RELATIVE_0x90 = BBC_RELATIVE_0x90

    '''BCS'''
    BCS_RELATIVE_0xB0 = BCS_RELATIVE_0xB0

    '''BEQ'''
    BEQ_RELATIVE_0xF0 = BEQ_RELATIVE_0xF0

    '''BIT'''
    BIT_ZEROPAGE_0x24 = BIT_ZEROPAGE_0x24
    BIT_ABSOLUTE_0x2C = BIT_ABSOLUTE_0x2C

    '''BMI'''
    BMI_RELATIVE_0x30 = BMI_RELATIVE_0x30

    '''BNE'''
    BNE_RELATIVE_0xD0 = BNE_RELATIVE_0xD0

    '''BPL'''
    BPL_RELATIVE_0x10 = BPL_RELATIVE_0x10

    '''BRK'''
    BRK_IMPLIED_0x00 = BRK_IMPLIED_0x00

    '''BVC'''
    BVC_RELATIVE_0x50 = BVC_RELATIVE_0x50

    '''BVS'''
    BVS_RELATIVE_0x70 = BVS_RELATIVE_0x70

    '''CLC'''
    CLC_IMPLIED_0x18 = CLC_IMPLIED_0x18

    '''CLD'''
    CLD_IMPLIED_0xD8 = CLD_IMPLIED_0xD8

    '''CLI'''
    CLI_IMPLIED_0x58 = CLI_IMPLIED_0x58

    '''CLV'''
    CLV_IMPLIED_0xB8 = CLV_IMPLIED_0xB8

    '''CMP'''
    CMP_IMMEDIATE_0xC9 = CMP_IMMEDIATE_0xC9
    CMP_ZEROPAGE_0xC5 = CMP_ZEROPAGE_0xC5
    CMP_ZEROPAGE_X_0xD5 = CMP_ZEROPAGE_X_0xD5
    CMP_ABSOLUTE_0xCD = CMP_ABSOLUTE_0xCD
    CMP_ABSOLUTE_X_0xDD = CMP_ABSOLUTE_X_0xDD
    CMP_ABSOLUTE_Y_0xD9 = CMP_ABSOLUTE_Y_0xD9
    CMP_INDEXED_INDIRECT_X_0xC1 = CMP_INDEXED_INDIRECT_X_0xC1
    CMP_INDIRECT_INDEXED_Y_0xD1 = CMP_INDIRECT_INDEXED_Y_0xD1

    '''CPX'''
    CPX_IMMEDIATE_0xE0 = CPX_IMMEDIATE_0xE0
    CPX_ZEROPAGE_0xE4 = CPX_ZEROPAGE_0xE4
    CPX_ABSOLUTE_0xEC = CPX_ABSOLUTE_0xEC

    '''CPY'''
    CPY_IMMEDIATE_0xC0 = CPY_IMMEDIATE_0xC0
    CPY_ZEROPAGE_0xC4 = CPY_ZEROPAGE_0xC4
    CPY_ABSOLUTE_0xCC = CPY_ABSOLUTE_0xCC

    '''DEC'''
    DEC_ZEROPAGE_0xC6 = DEC_ZEROPAGE_0xC6
    DEC_ZEROPAGE_X_0xD6 = DEC_ZEROPAGE_X_0xD6
    DEC_ABSOLUTE_0xCE = DEC_ABSOLUTE_0xCE
    DEC_ABSOLUTE_X_0xDE = DEC_ABSOLUTE_X_0xDE

    '''DEX'''
    DEX_IMPLIED_0xCA = DEX_IMPLIED_0xCA

    '''DEY'''
    DEY_IMPLIED_0x88 = DEY_IMPLIED_0x88

    '''EOR'''
    EOR_IMMEDIATE_0x49 = EOR_IMMEDIATE_0x49
    EOR_ZEROPAGE_0x45 = EOR_ZEROPAGE_0x45
    EOR_ZEROPAGE_X_0x55 = EOR_ZEROPAGE_X_0x55
    EOR_ABSOLUTE_0x4D = EOR_ABSOLUTE_0x4D
    EOR_ABSOLUTE_X_0x5D = EOR_ABSOLUTE_X_0x5D
    EOR_ABSOLUTE_Y_0x59 = EOR_ABSOLUTE_Y_0x59
    EOR_INDEXED_INDIRECT_X_0x41 = EOR_INDEXED_INDIRECT_X_0x41
    EOR_INDIRECT_INDEXED_Y_0x51 = EOR_INDIRECT_INDEXED_Y_0x51

    '''INC'''
    INC_ZEROPAGE_0xE6 = INC_ZEROPAGE_0xE6
    INC_ZEROPAGE_X_0xF6 = INC_ZEROPAGE_X_0xF6
    INC_ABSOLUTE_0xEE = INC_ABSOLUTE_0xEE
    INC_ABSOLUTE_X_0xFE = INC_ABSOLUTE_X_0xFE

    '''INX'''
    INX_IMPLIED_0xE8 = INX_IMPLIED_0xE8

    '''INY'''
    INY_IMPLIED_0xC8 = INY_IMPLIED_0xC8

    '''JMP'''
    JMP_ABSOLUTE_0x4C = JMP_ABSOLUTE_0x4C
    JMP_INDIRECT_0x6C = JMP_INDIRECT_0x6C

    '''JSR'''
    JSR_ABSOLUTE_0x20 = JSR_ABSOLUTE_0x20

    '''LDA'''
    LDA_IMMEDIATE_0xA9 = LDA_IMMEDIATE_0xA9
    LDA_ZEROPAGE_0xA5 = LDA_ZEROPAGE_0xA5
    LDA_ZEROPAGE_X_0xB5 = LDA_ZEROPAGE_X_0xB5
    LDA_ABSOLUTE_0xAD = LDA_ABSOLUTE_0xAD
    LDA_ABSOLUTE_X_0xBD = LDA_ABSOLUTE_X_0xBD
    LDA_ABSOLUTE_Y_0xB9 = LDA_ABSOLUTE_Y_0xB9
    LDA_INDEXED_INDIRECT_X_0xA1 = LDA_INDEXED_INDIRECT_X_0xA1
    LDA_INDIRECT_INDEXED_Y_0xB1 = LDA_INDIRECT_INDEXED_Y_0xB1

    '''LDX'''
    LDX_IMMEDIATE_0xA2 = LDX_IMMEDIATE_0xA2
    LDX_ZEROPAGE_0xA6 = LDX_ZEROPAGE_0xA6
    LDX_ZEROPAGE_Y_0xB6 = LDX_ZEROPAGE_Y_0xB6
    LDX_ABSOLUTE_0xAE = LDX_ABSOLUTE_0xAE
    LDX_ABSOLUTE_Y_0xBE = LDX_ABSOLUTE_Y_0xBE

    '''LDY'''
    LDY_IMMEDIATE_0xA0 = LDY_IMMEDIATE_0xA0
    LDY_ZEROPAGE_0xA4 = LDY_ZEROPAGE_0xA4
    LDY_ZEROPAGE_X_0xB4 = LDY_ZEROPAGE_X_0xB4
    LDY_ABSOLUTE_0xAC = LDY_ABSOLUTE_0xAC
    LDY_ABSOLUTE_X_0xBC = LDY_ABSOLUTE_X_0xBC

    '''LSR'''
    LSR_ACCUMULATOR_0x4A = LSR_ACCUMULATOR_0x4A
    LSR_ZEROPAGE_0x46 = LSR_ZEROPAGE_0x46
    LSR_ZEROPAGE_X_0x56 = LSR_ZEROPAGE_X_0x56
    LSR_ABSOLUTE_0x4E = LSR_ABSOLUTE_0x4E
    LSR_ABSOLUTE_X_0x5E = LSR_ABSOLUTE_X_0x5E

    '''NOP'''
    NOP_IMPLIED_0xEA = NOP_IMPLIED_0xEA

    '''ORA'''
    ORA_IMMEDIATE_0x09 = ORA_IMMEDIATE_0x09
    ORA_ZEROPAGE_0x05 = ORA_ZEROPAGE_0x05
    ORA_ZEROPAGE_X_0x15 = ORA_ZEROPAGE_X_0x15
    ORA_ABSOLUTE_0x0D = ORA_ABSOLUTE_0x0D
    ORA_ABSOLUTE_X_0x1D = ORA_ABSOLUTE_X_0x1D
    ORA_ABSOLUTE_Y_0x19 = ORA_ABSOLUTE_Y_0x19
    ORA_INDEXED_INDIRECT_X_0x01 = ORA_INDEXED_INDIRECT_X_0x01
    ORA_INDIRECT_INDEXED_Y_0x11 = ORA_INDIRECT_INDEXED_Y_0x11

    '''PHA'''
    PHA_IMPLIED_0x48 = PHA_IMPLIED_0x48

    '''PHP'''
    PHP_IMPLIED_0x08 = PHP_IMPLIED_0x08

    '''PLA'''
    PLA_IMPLIED_0x68 = PLA_IMPLIED_0x68

    '''PLP'''
    PLP_IMPLIED_0x28 = PLP_IMPLIED_0x28

    '''ROL'''
    ROL_ACCUMULATOR_0x2A = ROL_ACCUMULATOR_0x2A
    ROL_ZEROPAGE_0x26 = ROL_ZEROPAGE_0x26
    ROL_ZEROPAGE_X_0x36 = ROL_ZEROPAGE_X_0x36
    ROL_ABSOLUTE_0x2E = ROL_ABSOLUTE_0x2E
    ROL_ABSOLUTE_X_0x3E = ROL_ABSOLUTE_X_0x3E

    '''ROR'''
    ROR_ACCUMULATOR_0x6A = ROR_ACCUMULATOR_0x6A
    ROR_ZEROPAGE_0x66 = ROR_ZEROPAGE_0x66
    ROR_ZEROPAGE_X_0x76 = ROR_ZEROPAGE_X_0x76
    ROR_ABSOLUTE_0x6E = ROR_ABSOLUTE_0x6E
    ROR_ABSOLUTE_X_0x7E = ROR_ABSOLUTE_X_0x7E

    '''RTI'''
    RTI_IMPLIED_0x40 = RTI_IMPLIED_0x40

    '''RTS'''
    RTS_IMPLIED_0x60 = RTS_IMPLIED_0x60

    '''SBC'''
    SBC_IMMEDIATE_0xE9 = SBC_IMMEDIATE_0xE9
    SBC_ZEROPAGE_0xE5 = SBC_ZEROPAGE_0xE5
    SBC_ZEROPAGE_X_0xF5 = SBC_ZEROPAGE_X_0xF5
    SBC_ABSOLUTE_0xED = SBC_ABSOLUTE_0xED
    SBC_ABSOLUTE_X_0xFD = SBC_ABSOLUTE_X_0xFD
    SBC_ABSOLUTE_Y_0xF9 = SBC_ABSOLUTE_Y_0xF9
    SBC_INDEXED_INDIRECT_X_0xE1 = SBC_INDEXED_INDIRECT_X_0xE1
    SBC_INDIRECT_INDEXED_Y_0xF1 = SBC_INDIRECT_INDEXED_Y_0xF1

    '''SEC'''
    SEC_IMPLIED_0x38 = 0x38

    '''SED'''
    SED_IMPLIED_0xF8 = SED_IMPLIED_0xF8

    '''SEI'''
    SEI_IMPLIED_0x78 = SEI_IMPLIED_0x78

    '''STA'''
    STA_ZEROPAGE_0x85 = STA_ZEROPAGE_0x85
    STA_ZEROPAGE_X_0x95 = STA_ZEROPAGE_X_0x95
    STA_ABSOLUTE_0x8D = STA_ABSOLUTE_0x8D
    STA_ABSOLUTE_X_0x9D = STA_ABSOLUTE_X_0x9D
    STA_ABSOLUTE_Y_0x99 = STA_ABSOLUTE_Y_0x99
    STA_INDEXED_INDIRECT_X_0x81 = STA_INDEXED_INDIRECT_X_0x81
    STA_INDIRECT_INDEXED_Y_0x91 = STA_INDIRECT_INDEXED_Y_0x91

    '''STX'''
    STX_ZEROPAGE_0x86 = STX_ZEROPAGE_0x86
    STX_ZEROPAGE_X_0x96 = STX_ZEROPAGE_X_0x96
    STX_ABSOLUTE_0x8E = STX_ABSOLUTE_0x8E

    '''STY'''
    STY_ZEROPAGE_0x84 = STY_ZEROPAGE_0x84
    STY_ZEROPAGE_X_0x94 = STY_ZEROPAGE_X_0x94
    STY_ABSOLUTE_0x8C = STY_ABSOLUTE_0x8C

    '''TAX'''
    TAX_IMPLIED_0xAA = TAX_IMPLIED_0xAA

    '''TAY'''
    TAY_IMPLIED_0xA8 = TAY_IMPLIED_0xA8

    '''TSX'''
    TSX_IMPLIED_0xBA = TSX_IMPLIED_0xBA

    '''TXA'''
    TXA_IMPLIED_0x8A = TXA_IMPLIED_0x8A

    '''TXS'''
    TXS_IMPLIED_0x9A = TXS_IMPLIED_0x9A

    '''TYA'''
    TYA_IMPLIED_0x98 = TYA_IMPLIED_0x98

    '''Illegal Opcodes'''
    '''ALR'''
    ILL_ALR_IMMEDIATE_0x4B = ILL_ALR_IMMEDIATE_0x4B

    '''ANC'''
    ILL_ANC_IMMEDIATE_0x0B = ILL_ANC_IMMEDIATE_0x0B

    '''ANC2'''
    ILL_ANC2_IMMEDIATE_0x2B = ILL_ANC2_IMMEDIATE_0x2B

    '''ANE'''
    ILL_ANE_IMMEDIATE_0x8B = ILL_ANE_IMMEDIATE_0x8B

    '''ARR'''
    ILL_ARR_IMMEDIATE_0x6B = ILL_ARR_IMMEDIATE_0x6B

    '''DCP'''
    ILL_DCP_ZEROPAGE_ZEROPAGE_0xC7 = ILL_DCP_ZEROPAGE_ZEROPAGE_0xC7
    ILL_DCP_ZEROPAGE_X_0xD7 = ILL_DCP_ZEROPAGE_X_0xD7
    ILL_DCP_ABSOLUTE_0xCF = ILL_DCP_ABSOLUTE_0xCF
    ILL_DCP_ABSOLUTE_X_0xDF = ILL_DCP_ABSOLUTE_X_0xDF
    ILL_DCP_ABSOLUTE_Y_0xDB = ILL_DCP_ABSOLUTE_Y_0xDB
    ILL_DCP_INDEXED_INDIRECT_X_0xC3 = ILL_DCP_INDEXED_INDIRECT_X_0xC3
    ILL_DCP_INDIRECT_INDEXED_Y_0xD3 = ILL_DCP_INDIRECT_INDEXED_Y_0xD3

    '''ISC'''
    ILL_ISC_ZEROPAGE_0xE7 = ILL_ISC_ZEROPAGE_0xE7
    ILL_ISC_ZEROPAGE_X_0xF7 = ILL_ISC_ZEROPAGE_X_0xF7
    ILL_ISC_ABSOLUTE_0xEF = ILL_ISC_ABSOLUTE_0xEF
    ILL_ISC_ABSOLUTE_X_0xFF = ILL_ISC_ABSOLUTE_X_0xFF
    ILL_ISC_ABSOLUTE_Y_0xFB = ILL_ISC_ABSOLUTE_Y_0xFB
    ILL_ISC_INDEXED_INDIRECT_X_0xE3 = ILL_ISC_INDEXED_INDIRECT_X_0xE3
    ILL_ISC_INDIRECT_INDEXED_Y_0xF3 = ILL_ISC_INDIRECT_INDEXED_Y_0xF3

    '''LAS'''
    ILL_LAS_ABSOLUTE_0xBB = ILL_LAS_ABSOLUTE_0xBB

    '''LAX'''
    ILL_LAX_ZEROPAGE_0xA7 = ILL_LAX_ZEROPAGE_0xA7
    ILL_LAX_ZEROPAGE_X_0xB7 = ILL_LAX_ZEROPAGE_X_0xB7
    ILL_LAX_ABSOLUTE_0xAF = ILL_LAX_ABSOLUTE_0xAF
    ILL_LAX_ABSOLUTE_Y_0xBF = ILL_LAX_ABSOLUTE_Y_0xBF
    ILL_LAX_INDEXED_INDIRECT_X_0xA3 = ILL_LAX_INDEXED_INDIRECT_X_0xA3
    ILL_LAX_INDIRECT_INDEXED_Y_0xB3 = ILL_LAX_INDIRECT_INDEXED_Y_0xB3

    '''LXA'''
    ILL_LXA_IMMEDIATE_0xAB = ILL_LXA_IMMEDIATE_0xAB

    '''RLA'''
    ILL_RLA_ZEROPAGE_0x27 = ILL_RLA_ZEROPAGE_0x27
    ILL_RLA_ZEROPAGE_X_0x37 = ILL_RLA_ZEROPAGE_X_0x37
    ILL_RLA_ABSOLUTE_0x2F = ILL_RLA_ABSOLUTE_0x2F
    ILL_RLA_ABSOLUTE_X_0x3F = ILL_RLA_ABSOLUTE_X_0x3F
    ILL_RLA_ABSOLUTE_Y_0x3B = ILL_RLA_ABSOLUTE_Y_0x3B
    ILL_RLA_INDEXED_INDIRECT_X_0x23 = ILL_RLA_INDEXED_INDIRECT_X_0x23
    ILL_RLA_INDIRECT_INDEXED_Y_0x33 = ILL_RLA_INDIRECT_INDEXED_Y_0x33

    '''RRA'''
    ILL_RRA_ZEROPAGE_0x67 = ILL_RRA_ZEROPAGE_0x67
    ILL_RRA_ZEROPAGE_X_0x77 = ILL_RRA_ZEROPAGE_X_0x77
    ILL_RRA_ABSOLUTE_0x6F = ILL_RRA_ABSOLUTE_0x6F
    ILL_RRA_ABSOLUTE_X_0x7F = ILL_RRA_ABSOLUTE_X_0x7F
    ILL_RRA_ABSOLUTE_Y_0x7B = ILL_RRA_ABSOLUTE_Y_0x7B
    ILL_RRA_INDEXED_INDIRECT_X_0x63 = ILL_RRA_INDEXED_INDIRECT_X_0x63
    ILL_RRA_INDIRECT_INDEXED_Y_0x73 = ILL_RRA_INDIRECT_INDEXED_Y_0x73

    '''SAX'''
    ILL_SAX_ZEROPAGE_0x87 = ILL_SAX_ZEROPAGE_0x87
    ILL_SAX_ZEROPAGE_Y_0x97 = ILL_SAX_ZEROPAGE_Y_0x97
    ILL_SAX_ABSOLUTE_0x8F = ILL_SAX_ABSOLUTE_0x8F
    ILL_SAX_INDEXED_INDIRECT_X_0x83 = ILL_SAX_INDEXED_INDIRECT_X_0x83

    '''SBX'''
    ILL_SBX_IMMEDIATE_0xCB = ILL_SBX_IMMEDIATE_0xCB

    '''SHA'''
    ILL_SHA_ABSOLUTE_Y_0x9F = ILL_SHA_ABSOLUTE_Y_0x9F
    ILL_SHA_INDIRECT_INDEXED_Y_0x93 = ILL_SHA_INDIRECT_INDEXED_Y_0x93

    '''SHX'''
    ILL_SHX_ABSOLUTE_Y_0x9E = ILL_SHX_ABSOLUTE_Y_0x9E

    '''SHY'''
    ILL_SHY_ABSOLUTE_X_0x9C = ILL_SHY_ABSOLUTE_X_0x9C

    '''SLO'''
    ILL_SLO_ZEROPAGE_0x07 = ILL_SLO_ZEROPAGE_0x07
    ILL_SLO_ZEROPAGE_X_0x17 = ILL_SLO_ZEROPAGE_X_0x17
    ILL_SLO_ABSOLUTE_0x0F = ILL_SLO_ABSOLUTE_0x0F
    ILL_SLO_ABSOLUTE_X_0x1F = ILL_SLO_ABSOLUTE_X_0x1F
    ILL_SLO_ABSOLUTE_Y_0x1B = ILL_SLO_ABSOLUTE_Y_0x1B
    ILL_SLO_INDEXED_INDIRECT_X_0x03 = ILL_SLO_INDEXED_INDIRECT_X_0x03
    ILL_SLO_INDIRECT_INDEXED_Y_0x13 = ILL_SLO_INDIRECT_INDEXED_Y_0x13

    '''SRE'''
    ILL_SRE_ZEROPAGE_0x47 = ILL_SRE_ZEROPAGE_0x47
    ILL_SRE_ZEROPAGE_X_0x57 = ILL_SRE_ZEROPAGE_X_0x57
    ILL_SRE_ABSOLUTE_0x4F = ILL_SRE_ABSOLUTE_0x4F
    ILL_SRE_ABSOLUTE_X_0x4F = ILL_SRE_ABSOLUTE_X_0x4F
    ILL_SRE_ABSOLUTE_Y_0x5B = ILL_SRE_ABSOLUTE_Y_0x5B
    ILL_SRE_INDEXED_INDIRECT_X_0x43 = ILL_SRE_INDEXED_INDIRECT_X_0x43
    ILL_SRE_INDIRECT_INDEXED_Y_0x53 = ILL_SRE_INDIRECT_INDEXED_Y_0x53

    '''TAS'''
    ILL_TAS_ABSOLUTE_0x9B = ILL_TAS_ABSOLUTE_0x9B

    '''USBC'''
    '''NOPS'''
    '''JAM'''

    @classmethod
    def _missing_(cls, value):
        raise IllegalCPUInstructionException(fr'{value}' + f' ({value:02X}) is not a valid {cls}.')


# It would be possible to store the assembly instructions mnemonics as format specifiers
# as well as generate the machine code using the enumeration and a little bit of hackery
InstructionSet.map = {}

'''LDA'''
lda_immediate_0xa9_can_modify_flags: Byte = Byte()
lda_immediate_0xa9_can_modify_flags[flags.C] = False
lda_immediate_0xa9_can_modify_flags[flags.B] = False
lda_immediate_0xa9_can_modify_flags[flags.D] = False
lda_immediate_0xa9_can_modify_flags[flags.I] = False
lda_immediate_0xa9_can_modify_flags[flags.V] = False
lda_immediate_0xa9_can_modify_flags[flags.N] = True
lda_immediate_0xa9_can_modify_flags[flags.Z] = True

InstructionSet.map[InstructionSet.LDA_IMMEDIATE_0xA9] = {
    'addressing': 'immediate',
    'assembler': 'LDA #{oper}',
    'opc': InstructionSet.LDA_IMMEDIATE_0xA9,
    'bytes': '2',
    'cycles': '2',
    'flags': lda_immediate_0xa9_can_modify_flags
}

lda_zeropage_0xa5_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
InstructionSet.map[InstructionSet.LDA_ZEROPAGE_0xA5] = {
    'addressing': 'zeropage',
    'assembler': 'LDA {oper}',
    'opc': InstructionSet.LDA_ZEROPAGE_0xA5,
    'bytes': '2',
    'cycles': '3',
    'flags': lda_zeropage_0xa5_can_modify_flags
}

lda_zeropage_x_0xb5_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
InstructionSet.map[InstructionSet.LDA_ZEROPAGE_X_0xB5] = {
    'addressing': 'zeropage,X',
    'assembler': 'LDA {oper},X',
    'opc': InstructionSet.LDA_ZEROPAGE_X_0xB5,
    'bytes': '2',
    'cycles': '4',
    'flags': lda_zeropage_x_0xb5_can_modify_flags
}

lda_absolute_0xad_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
InstructionSet.map[InstructionSet.LDA_ABSOLUTE_0xAD] = {
    'addressing': 'absolute',
    'assembler': 'LDA {oper}',
    'opc': InstructionSet.LDA_ABSOLUTE_0xAD,
    'bytes': '3',
    'cycles': '4',
    'flags': lda_absolute_0xad_can_modify_flags
}

lda_absolute_x_0xbd_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
InstructionSet.map[InstructionSet.LDA_ABSOLUTE_X_0xBD] = {
    'addressing': 'absolute,X',
    'assembler': 'LDA {oper},X',
    'opc': InstructionSet.LDA_ABSOLUTE_X_0xBD,
    'bytes': '3',
    'cycles': '4*',
    'flags': lda_absolute_x_0xbd_can_modify_flags
}

lda_absolute_y_0xb9_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
InstructionSet.map[InstructionSet.LDA_ABSOLUTE_Y_0xB9] = {
    'addressing': 'absolute,Y',
    'assembler': 'LDA {oper},Y',
    'opc': InstructionSet.LDA_ABSOLUTE_Y_0xB9,
    'bytes': '3',
    'cycles': '4*',
    'flags': lda_absolute_y_0xb9_can_modify_flags
}

lda_indexed_indirect_x_0xa1_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
InstructionSet.map[InstructionSet.LDA_INDEXED_INDIRECT_X_0xA1] = {
    'addressing': '(indirect, X)',
    'assembler': 'LDA ({oper},X)',
    'opc': InstructionSet.LDA_INDEXED_INDIRECT_X_0xA1,
    'bytes': '2',
    'cycles': '6',
    'flags': lda_indexed_indirect_x_0xa1_can_modify_flags
}

lda_indirect_indexed_y_0xb1_can_modify_flags: Byte = lda_immediate_0xa9_can_modify_flags
InstructionSet.map[InstructionSet.LDA_INDIRECT_INDEXED_Y_0xB1] = {
    'addressing': '({indirect}),Y',
    'assembler': 'LDA (oper),Y',
    'opc': LDA_INDIRECT_INDEXED_Y_0xB1,
    'bytes': '2',
    'cycles': '5*',
    'flags': lda_indirect_indexed_y_0xb1_can_modify_flags
}

'''JSR'''
jsr_absolute_0x20_can_modify_flags: Byte = Byte()
InstructionSet.map[InstructionSet.JSR_ABSOLUTE_0x20] = {
    'addressing': 'absolute',
    'assembler': 'JSR {oper}',
    'opc': InstructionSet.JSR_ABSOLUTE_0x20,
    'bytes': '3',
    'cycles': '6',
    'flags': jsr_absolute_0x20_can_modify_flags
}

'''NOP'''
nop_implied_0xea_can_modify_flags: Byte = Byte()
InstructionSet.map[NOP_IMPLIED_0xEA] = {
    'addressing': 'implied',
    'assembler': 'NOP',
    'opc': NOP_IMPLIED_0xEA,
    'bytes': '1',
    'cycles': '2',
    'flags': nop_implied_0xea_can_modify_flags
}

# Template
# InstructionSet.map[] = {
#     'addressing': '',
#     'assembler': '',
#     'opc': ,
#     'bytes': '',
#     'cycles': '',
#     'flags':
# }
