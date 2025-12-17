#!/usr/bin/env python3
"""Pydantic model for 6502 instruction metadata."""

from mos6502.compat import Literal, List

from pydantic import BaseModel, Field, computed_field, model_validator


# Addressing mode type alias
AddressingMode = Literal[
    "implied",
    "accumulator",
    "immediate",
    "zeropage",
    "zeropage,X",
    "zeropage,Y",
    "absolute",
    "absolute,X",
    "absolute,Y",
    "(indirect,X)",
    "(indirect),Y",
    "indirect",
    "relative",
]


class Instruction(BaseModel):
    """Pydantic model representing a 6502 instruction's metadata.

    This provides structured, validated metadata for each instruction opcode,
    replacing the untyped dictionaries previously used in instruction_map.

    Attributes
    ----------
        opcode: The instruction opcode byte (0x00-0xFF)
        mnemonic: The instruction mnemonic (e.g., "LDA", "STA", "ADC")
        addressing: The addressing mode used by this opcode variant
        assembler: Format string for disassembly (e.g., "LDA #{oper}")
        bytes: Number of bytes this instruction occupies (1-3)
        base_cycles: Base cycle count for this instruction
        page_boundary_penalty: True if crossing page boundary adds a cycle
        affected_flags: String of flag letters affected (e.g., "NZ", "NVZC")
        package: Python package path for variant dispatch
        function: Function name for variant dispatch

    Example
    -------
        >>> lda_imm = Instruction(
        ...     opcode=0xA9,
        ...     mnemonic="LDA",
        ...     addressing="immediate",
        ...     assembler="LDA #{oper}",
        ...     bytes=2,
        ...     base_cycles=2,
        ...     affected_flags="NZ",
        ...     package="mos6502.instructions.load._lda",
        ...     function="lda_immediate_0xa9",
        ... )
    """

    opcode: int = Field(ge=0x00, le=0xFF, description="Instruction opcode (0x00-0xFF)")
    mnemonic: str = Field(min_length=2, max_length=4, description="Instruction mnemonic")
    addressing: AddressingMode = Field(description="Addressing mode")
    assembler: str = Field(description="Assembly format string with {oper} placeholder")
    bytes: int = Field(ge=1, le=3, description="Instruction size in bytes")
    base_cycles: int = Field(ge=1, le=8, description="Base cycle count")
    page_boundary_penalty: bool = Field(
        default=False,
        description="True if page boundary crossing adds +1 cycle",
    )
    affected_flags: str = Field(
        default="",
        pattern=r"^[NVBDIZC]*$",
        description="Flags affected (subset of NVBDIZC)",
    )
    package: str = Field(description="Python package for variant dispatch")
    function: str = Field(description="Function name for variant dispatch")

    model_config = {
        "frozen": True,  # Make instances immutable/hashable
        "str_strip_whitespace": True,
    }

    @model_validator(mode="after")
    def validate_assembler_format(self) -> "Instruction":
        """Validate assembler format string matches addressing mode."""
        # Implied and accumulator modes shouldn't have {oper}
        if self.addressing in ("implied", "accumulator"):
            if "{oper}" in self.assembler:
                msg = f"Implied/accumulator addressing shouldn't have {{oper}}: {self.assembler}"
                raise ValueError(msg)
        else:
            # All other modes should have {oper}
            if "{oper}" not in self.assembler:
                msg = f"Addressing mode {self.addressing} should have {{oper}}: {self.assembler}"
                raise ValueError(msg)
        return self

    @computed_field
    @property
    def name(self) -> str:
        """Generate canonical name like LDA_IMMEDIATE_0xA9."""
        # Convert addressing mode to name format
        addr_map = {
            "implied": "IMPLIED",
            "accumulator": "ACCUMULATOR",
            "immediate": "IMMEDIATE",
            "zeropage": "ZEROPAGE",
            "zeropage,X": "ZEROPAGE_X",
            "zeropage,Y": "ZEROPAGE_Y",
            "absolute": "ABSOLUTE",
            "absolute,X": "ABSOLUTE_X",
            "absolute,Y": "ABSOLUTE_Y",
            "(indirect,X)": "INDEXED_INDIRECT_X",
            "(indirect),Y": "INDIRECT_INDEXED_Y",
            "indirect": "INDIRECT",
            "relative": "RELATIVE",
        }
        addr_name = addr_map.get(self.addressing, self.addressing.upper())
        return f"{self.mnemonic}_{addr_name}_0x{self.opcode:02X}"

    @computed_field
    @property
    def cycles_display(self) -> str:
        """Return cycles as display string (e.g., '4' or '4*' for page penalty)."""
        if self.page_boundary_penalty:
            return f"{self.base_cycles}*"
        return str(self.base_cycles)

    @computed_field
    @property
    def affects_n(self) -> bool:
        """True if instruction affects Negative flag."""
        return "N" in self.affected_flags

    @computed_field
    @property
    def affects_v(self) -> bool:
        """True if instruction affects Overflow flag."""
        return "V" in self.affected_flags

    @computed_field
    @property
    def affects_z(self) -> bool:
        """True if instruction affects Zero flag."""
        return "Z" in self.affected_flags

    @computed_field
    @property
    def affects_c(self) -> bool:
        """True if instruction affects Carry flag."""
        return "C" in self.affected_flags

    @computed_field
    @property
    def affects_i(self) -> bool:
        """True if instruction affects Interrupt Disable flag."""
        return "I" in self.affected_flags

    @computed_field
    @property
    def affects_d(self) -> bool:
        """True if instruction affects Decimal flag."""
        return "D" in self.affected_flags

    def to_legacy_dict(self) -> dict:
        """Convert to legacy instruction_map dictionary format.

        This allows gradual migration by supporting the old dict-based API.
        """
        from mos6502 import flags
        from mos6502.memory import Byte

        # Build flags byte
        flags_byte = Byte()
        if self.affects_n:
            flags_byte[flags.N] = 1
        if self.affects_v:
            flags_byte[flags.V] = 1
        if self.affects_z:
            flags_byte[flags.Z] = 1
        if self.affects_c:
            flags_byte[flags.C] = 1
        if self.affects_i:
            flags_byte[flags.I] = 1
        if self.affects_d:
            flags_byte[flags.D] = 1

        return {
            "addressing": self.addressing,
            "assembler": self.assembler,
            "opc": self.opcode,
            "bytes": str(self.bytes),
            "cycles": self.cycles_display,
            "flags": flags_byte,
        }

    def __hash__(self) -> int:
        """Hash by opcode for use in sets and as dict keys."""
        return hash(self.opcode)

    def __int__(self) -> int:
        """Allow using Instruction where an int opcode is expected."""
        return self.opcode


class PseudoEnumMember:
    """Allows dynamic addition of members to IntEnum classes.

    This class is used to add instruction opcodes to the InstructionSet enum
    at runtime, since Python's IntEnum doesn't support dynamic member addition.

    Note: Does not inherit from int for MicroPython compatibility.
    """

    __slots__ = ('_value_', '_name')

    def __init__(self, value: int, name: str) -> None:
        """Create a pseudo-enum member with the given value and name."""
        self._value_ = value
        self._name = name

    @property
    def name(self) -> str:
        """Return the member name."""
        return self._name

    @property
    def value(self) -> int:
        """Return the member value."""
        return self._value_

    def __int__(self) -> int:
        """Return the integer value."""
        return self._value_

    def __eq__(self, other: object) -> bool:
        """Compare equality with int or another PseudoEnumMember."""
        if isinstance(other, int):
            return self._value_ == other
        return NotImplemented

    def __hash__(self) -> int:
        """Hash by value."""
        return hash(self._value_)


def register_instruction(
    instruction: Instruction,
    instruction_set_class: type,
    instruction_map: dict,
) -> None:
    """Register a single instruction in the InstructionSet enum and map.

    Arguments
    ---------
        instruction: The Instruction model to register
        instruction_set_class: The InstructionSet enum class
        instruction_map: The instruction metadata dictionary

    """
    # Add to enum
    member = PseudoEnumMember(instruction.opcode, instruction.name)
    instruction_set_class._value2member_map_[instruction.opcode] = member
    setattr(instruction_set_class, instruction.name, instruction.opcode)

    # Add to instruction map (using legacy dict format for compatibility)
    instruction_map[instruction.opcode] = instruction.to_legacy_dict()


def register_instructions(
    instructions: List[Instruction],
    instruction_set_class: type,
    instruction_map: dict,
) -> None:
    """Register multiple instructions in the InstructionSet enum and map.

    Arguments
    ---------
        instructions: List of Instruction models to register
        instruction_set_class: The InstructionSet enum class
        instruction_map: The instruction metadata dictionary

    """
    for instruction in instructions:
        register_instruction(instruction, instruction_set_class, instruction_map)
