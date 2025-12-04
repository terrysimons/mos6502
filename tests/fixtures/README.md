# Test Fixtures

This directory contains test data files for the MOS 6502 emulator tests.

## Cartridge Test Files

### 8KB Cartridge (`test_cart_8k.bin`, `test_cart_8k.crt`)

A minimal 8KB cartridge (ROML only) that:
1. Clears the screen
2. Sets border and background to blue
3. Displays test information:
   - "8K CARTRIDGE TEST"
   - "ROML AT $8000-$9FFF"
   - "EXROM=0 GAME=1"
4. Loops forever

**Memory Layout:**
- `$8000-$8001`: Cold start vector → `$8009`
- `$8002-$8003`: Warm start vector → `$8009`
- `$8004-$8008`: CBM80 signature for auto-start
- `$8009+`: Executable code

**Banking Mode:** EXROM=0, GAME=1 (8KB mode)

**Usage:**
```bash
python systems/c64.py --rom-dir systems/roms --cartridge tests/fixtures/test_cart_8k.bin
python systems/c64.py --rom-dir systems/roms --cartridge tests/fixtures/test_cart_8k.crt
```

### 16KB Cartridge (`test_cart_16k.bin`, `test_cart_16k.crt`)

A 16KB cartridge (ROML + ROMH) that demonstrates both ROM regions are accessible:
1. Clears the screen
2. Sets border and background to dark gray
3. Displays messages from ROML ($8000):
   - "16K CARTRIDGE TEST"
   - "CODE IN ROML $8000"
4. Calls subroutine at ROMH ($A000) which displays:
   - "HELLO FROM ROMH $A000"
5. Returns from ROMH and displays:
   - "RETURNED FROM ROMH!"
   - "EXROM=0 GAME=0"
6. Loops forever

**Memory Layout:**
- ROML ($8000-$9FFF): Main code with CBM80 header
- ROMH ($A000-$BFFF): Subroutine code (replaces BASIC ROM)

**Banking Mode:** EXROM=0, GAME=0 (16KB mode)

**Usage:**
```bash
python systems/c64.py --rom-dir systems/roms --cartridge tests/fixtures/test_cart_16k.bin
python systems/c64.py --rom-dir systems/roms --cartridge tests/fixtures/test_cart_16k.crt
```

## Regenerating Test Fixtures

The cartridge files can be regenerated using:

```bash
python scripts/create_test_cart.py
```
