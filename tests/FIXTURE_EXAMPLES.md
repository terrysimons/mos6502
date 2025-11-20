# CPU Variant Test Fixtures - Usage Guide

## Overview

The `conftest.py` provides fixtures that automatically test all CPU variants without code duplication.

## Available Fixtures

### 1. `cpu` - Tests ALL Variants (Default)
Use this for instructions that work the same across all CPU variants.

```python
def test_clc_instruction(cpu: CPU) -> None:
    """This test will run 4 times: once for each CPU variant."""
    cpu.flags[flags.C] = 1
    cpu.ram[0xFFFC] = instructions.CLC_IMPLIED_0x18

    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    assert cpu.flags[flags.C] == 0
```

**Result:** 4 test runs (6502, 6502A, 6502C, 65C02)

### 2. `nmos_cpu` - Tests NMOS Variants Only
Use this for behavior specific to NMOS chips (6502, 6502A, 6502C).

```python
def test_brk_preserves_d_flag(nmos_cpu: CPU) -> None:
    """This test will run 3 times: once for each NMOS variant."""
    nmos_cpu.D = flags.ProcessorStatusFlags.D[flags.D]
    nmos_cpu.ram[0xFFFC] = instructions.BRK_IMPLIED_0x00

    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.CPUBreakError):
        nmos_cpu.execute(cycles=7)

    # NMOS variants preserve D flag
    assert nmos_cpu.D, "D flag should be preserved on NMOS variants"
```

**Result:** 3 test runs (6502, 6502A, 6502C)

### 3. `cmos_cpu` - Tests CMOS Variants Only
Use this for behavior specific to CMOS chips (65C02).

```python
def test_brk_clears_d_flag(cmos_cpu: CPU) -> None:
    """This test will run 1 time: for the CMOS variant."""
    cmos_cpu.D = flags.ProcessorStatusFlags.D[flags.D]
    cmos_cpu.ram[0xFFFC] = instructions.BRK_IMPLIED_0x00

    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.CPUBreakError):
        cmos_cpu.execute(cycles=7)

    # CMOS variants clear D flag
    assert not cmos_cpu.D, "D flag should be cleared on CMOS variants"
```

**Result:** 1 test run (65C02)

## Testing Strategy

### For variant-agnostic instructions (most cases):
```python
def test_instruction(cpu: CPU) -> None:
    # Uses the 'cpu' fixture - runs on ALL 4 variants
    ...
```

### For variant-specific behavior:
```python
def test_nmos_behavior(nmos_cpu: CPU) -> None:
    # Uses 'nmos_cpu' fixture - runs on 3 NMOS variants
    ...

def test_cmos_behavior(cmos_cpu: CPU) -> None:
    # Uses 'cmos_cpu' fixture - runs on 1 CMOS variant
    ...
```

## Coverage Guarantee

Every test using `cpu` fixture ensures:
- ✅ NMOS 6502 is tested
- ✅ NMOS 6502A is tested
- ✅ NMOS 6502C is tested
- ✅ CMOS 65C02 is tested

This guarantees **100% CPU family coverage** with **zero code duplication**.

## Migration Example

**Before (manual creation, no variant coverage):**
```python
def test_clc() -> None:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    # ... test code ...
```

**After (automatic variant coverage):**
```python
def test_clc(cpu: CPU) -> None:
    # cpu is already created and reset by fixture
    # Automatically runs for all 4 variants!
    # ... test code ...
```

## Running Tests

```bash
# Run a single test file and see all variant executions
pytest instructions/flags/test_clc.py -v

# Output shows all variants tested:
# test_cpu_instruction_CLC_IMPLIED_0x18[6502] PASSED
# test_cpu_instruction_CLC_IMPLIED_0x18[6502A] PASSED
# test_cpu_instruction_CLC_IMPLIED_0x18[6502C] PASSED
# test_cpu_instruction_CLC_IMPLIED_0x18[65C02] PASSED
```
