"""Tests for Word address wrapping behavior.

The 6502 has 16-bit addressing, so addresses naturally wrap around
at the 64KB boundary. This test ensures our Word class handles
overflow values correctly by wrapping to 16 bits.
"""

import pytest
from mos6502.memory import Word


def test_word_wraps_at_64k() -> None:
    """Test that Word wraps addresses above 0xFFFF to 16 bits."""
    # 0x10000 should wrap to 0x0000
    word = Word(0x10000)
    assert word.value == 0x0000, f"Expected 0x0000, got 0x{word.value:04X}"

    # 0x10001 should wrap to 0x0001
    word = Word(0x10001)
    assert word.value == 0x0001, f"Expected 0x0001, got 0x{word.value:04X}"

    # 0x1FFFF should wrap to 0xFFFF
    word = Word(0x1FFFF)
    assert word.value == 0xFFFF, f"Expected 0xFFFF, got 0x{word.value:04X}"


def test_word_handles_large_overflow() -> None:
    """Test Word with large overflow values."""
    # 65776 (from the bug report) = 0x100F0 should wrap to 0x00F0
    word = Word(65776)
    assert word.value == 0x00F0, f"Expected 0x00F0, got 0x{word.value:04X}"

    # 0xFFFF + 0xFF = 0x100FE should wrap to 0x00FE
    word = Word(0xFFFF + 0xFF)
    assert word.value == 0x00FE, f"Expected 0x00FE, got 0x{word.value:04X}"


def test_word_handles_indexed_addressing_overflow() -> None:
    """Test Word wrapping in indexed addressing mode scenarios.

    This simulates what happens when an absolute address + index
    overflows 16 bits, like: $FFFF + X where X=$F1.
    """
    base_addr = 0xFFFF
    index = 0xF1  # 241 in decimal

    # This should wrap: 0xFFFF + 0xF1 = 0x100F0 → 0x00F0
    effective_addr = Word(base_addr + index)
    assert effective_addr.value == 0x00F0, \
        f"Expected wrapped address 0x00F0, got 0x{effective_addr.value:04X}"


def test_word_preserves_valid_addresses() -> None:
    """Test that Word doesn't modify valid 16-bit addresses."""
    test_addresses = [0x0000, 0x0001, 0x1000, 0x8000, 0xFFFF, 0xFFFE]

    for addr in test_addresses:
        word = Word(addr)
        assert word.value == addr, \
            f"Expected address 0x{addr:04X} to be preserved, got 0x{word.value:04X}"


def test_word_wraps_negative_overflow() -> None:
    """Test that negative values are handled correctly."""
    # -1 should become 0xFFFF
    word = Word(-1)
    assert word.value == 0xFFFF, f"Expected 0xFFFF for -1, got 0x{word.value:04X}"

    # -256 should become 0xFF00
    word = Word(-256)
    assert word.value == 0xFF00, f"Expected 0xFF00 for -256, got 0x{word.value:04X}"


def test_word_arithmetic_with_wrapping() -> None:
    """Test that Word arithmetic wraps correctly."""
    # Create a word at the boundary
    word = Word(0xFFF0)

    # Add 0x20, should wrap to 0x0010
    result = Word(word.value + 0x20)
    assert result.value == 0x0010, \
        f"Expected 0x0010 from 0xFFF0 + 0x20, got 0x{result.value:04X}"


def test_word_pc_increment_at_boundary() -> None:
    """Test PC increment wrapping at 64KB boundary.

    This simulates what happens when PC wraps around, though in
    practice this rarely happens on real 6502 systems.
    """
    # PC at last byte of memory
    pc = Word(0xFFFF)

    # Increment should wrap to 0x0000
    pc_next = Word(pc.value + 1)
    assert pc_next.value == 0x0000, \
        f"Expected PC to wrap to 0x0000, got 0x{pc_next.value:04X}"


def test_word_stack_pointer_page_wrapping() -> None:
    """Test stack pointer calculations don't overflow Word.

    Stack is at $0100-$01FF, and SP is the low byte.
    Full stack address is 0x0100 + SP, which should never overflow
    but test boundary conditions.
    """
    # SP at 0xFF (top of stack)
    sp = 0xFF
    stack_addr = Word(0x0100 + sp)
    assert stack_addr.value == 0x01FF, \
        f"Expected stack address 0x01FF, got 0x{stack_addr.value:04X}"

    # SP at 0x00 (bottom of stack)
    sp = 0x00
    stack_addr = Word(0x0100 + sp)
    assert stack_addr.value == 0x0100, \
        f"Expected stack address 0x0100, got 0x{stack_addr.value:04X}"
