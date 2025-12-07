"""Tests for 1541 Disk Drive emulation."""

import pytest
import tempfile
from pathlib import Path
from systems.c64.drive.drive1541 import (
    Drive1541,
    Drive1541Memory,
    ROM_SIZE,
    RAM_SIZE,
    VIA1_START,
    VIA2_START,
)


class TestDrive1541Creation:
    """Test 1541 drive creation and initialization."""

    def test_default_device_number(self):
        """Default device number is 8."""
        drive = Drive1541()
        assert drive.device_number == 8

    def test_custom_device_number(self):
        """Can specify device number 8-11."""
        for num in [8, 9, 10, 11]:
            drive = Drive1541(device_number=num)
            assert drive.device_number == num

    def test_initial_state(self):
        """Drive starts in correct initial state."""
        drive = Drive1541()
        assert drive.motor_on is False
        assert drive.led_on is False
        assert drive.current_track == 1
        assert drive.rom_loaded is False
        assert drive.disk is None

    def test_via_chips_created(self):
        """Both VIA chips are created."""
        drive = Drive1541()
        assert drive.via1 is not None
        assert drive.via2 is not None
        assert drive.via1.name == "1541-VIA1"
        assert drive.via2.name == "1541-VIA2"


class TestDrive1541Memory:
    """Test 1541 memory map."""

    def test_ram_read_write(self):
        """RAM is readable and writable at $0000-$07FF."""
        drive = Drive1541()
        # Write to RAM
        drive.memory.write(0x0000, 0xAA)
        drive.memory.write(0x07FF, 0x55)
        # Read back
        assert drive.memory.read(0x0000) == 0xAA
        assert drive.memory.read(0x07FF) == 0x55

    def test_via1_access(self):
        """VIA1 is accessible at $1800-$180F."""
        drive = Drive1541()
        # Write to VIA1 DDR
        drive.memory.write(VIA1_START + 0x02, 0xFF)  # DDRB
        assert drive.via1.ddrb == 0xFF

    def test_via2_access(self):
        """VIA2 is accessible at $1C00-$1C0F."""
        drive = Drive1541()
        # Write to VIA2 DDR
        drive.memory.write(VIA2_START + 0x02, 0xAA)  # DDRB
        assert drive.via2.ddrb == 0xAA

    def test_unmapped_returns_ff(self):
        """Unmapped areas return $FF."""
        drive = Drive1541()
        # Area between RAM and VIA1
        assert drive.memory.read(0x1000) == 0xFF


class TestDrive1541ROMLoading:
    """Test ROM loading functionality."""

    def test_load_16kb_rom(self):
        """Can load a single 16KB ROM file."""
        drive = Drive1541()

        # Create a fake 16KB ROM
        rom_data = bytes([i & 0xFF for i in range(ROM_SIZE)])

        with tempfile.NamedTemporaryFile(suffix=".rom", delete=False) as f:
            f.write(rom_data)
            temp_path = Path(f.name)

        try:
            drive.load_rom(temp_path)
            assert drive.rom_loaded is True
            # Verify ROM contents
            assert drive.memory.rom[0] == 0x00
            assert drive.memory.rom[0x2000] == 0x00  # Second half starts
        finally:
            temp_path.unlink()

    def test_load_8kb_split_roms(self):
        """Can load two 8KB ROM files."""
        drive = Drive1541()

        # Create fake 8KB ROMs
        rom_c000 = bytes([0xC0 + (i & 0x0F) for i in range(ROM_SIZE // 2)])
        rom_e000 = bytes([0xE0 + (i & 0x0F) for i in range(ROM_SIZE // 2)])

        with tempfile.NamedTemporaryFile(suffix="-c000.bin", delete=False) as f:
            f.write(rom_c000)
            c000_path = Path(f.name)

        with tempfile.NamedTemporaryFile(suffix="-e000.bin", delete=False) as f:
            f.write(rom_e000)
            e000_path = Path(f.name)

        try:
            drive.load_rom(c000_path, e000_path)
            assert drive.rom_loaded is True
            # Verify ROM contents - C000 ROM in first half
            assert drive.memory.rom[0] == 0xC0
            # E000 ROM in second half
            assert drive.memory.rom[0x2000] == 0xE0
        finally:
            c000_path.unlink()
            e000_path.unlink()

    def test_load_invalid_size_raises(self):
        """Loading ROM with invalid size raises ValueError."""
        drive = Drive1541()

        # Create a ROM with invalid size
        invalid_data = bytes([0x00] * 1000)

        with tempfile.NamedTemporaryFile(suffix=".rom", delete=False) as f:
            f.write(invalid_data)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="must be 16KB or 8KB"):
                drive.load_rom(temp_path)
        finally:
            temp_path.unlink()

    def test_load_8kb_without_e000_raises(self):
        """Loading 8KB ROM without E000 ROM raises ValueError."""
        drive = Drive1541()

        # Create a single 8KB ROM
        rom_data = bytes([0x00] * (ROM_SIZE // 2))

        with tempfile.NamedTemporaryFile(suffix=".rom", delete=False) as f:
            f.write(rom_data)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="no \\$E000 ROM specified"):
                drive.load_rom(temp_path)
        finally:
            temp_path.unlink()


class TestDrive1541DiskOperations:
    """Test disk insertion and basic operations."""

    def test_insert_disk(self):
        """Can insert a D64 disk image."""
        drive = Drive1541()

        # Create an empty D64 image
        from systems.c64.drive.d64 import D64Image
        d64 = D64Image()

        with tempfile.NamedTemporaryFile(suffix=".d64", delete=False) as f:
            temp_path = Path(f.name)
            d64.save(temp_path)

        try:
            drive.insert_disk(temp_path)
            assert drive.disk is not None
            assert drive.disk.get_disk_name() == "EMPTY DISK"
        finally:
            temp_path.unlink()

    def test_eject_disk(self):
        """Can eject a disk."""
        drive = Drive1541()

        from systems.c64.drive.d64 import D64Image
        d64 = D64Image()

        with tempfile.NamedTemporaryFile(suffix=".d64", delete=False) as f:
            temp_path = Path(f.name)
            d64.save(temp_path)

        try:
            drive.insert_disk(temp_path)
            assert drive.disk is not None
            drive.eject_disk()
            assert drive.disk is None
        finally:
            temp_path.unlink()


class TestDrive1541IECBus:
    """Test IEC bus interface."""

    def test_initial_iec_state(self):
        """IEC lines start in released state."""
        drive = Drive1541()
        assert drive.iec_atn is True
        assert drive.iec_clk is True
        assert drive.iec_data is True

    def test_set_iec_atn(self):
        """Can set ATN line state."""
        drive = Drive1541()
        drive.set_iec_atn(False)
        assert drive.iec_atn is False
        drive.set_iec_atn(True)
        assert drive.iec_atn is True

    def test_get_iec_clk_output(self):
        """Can read drive's CLK output state."""
        drive = Drive1541()
        # Initially, CLK OUT is not driven (output register is 0)
        assert drive.get_iec_clk() is True  # Released

        # Set VIA1 to drive CLK OUT low
        drive.via1.ddrb = 0x08  # PB3 as output
        drive.via1.orb = 0x08   # PB3 high (inverted = bus low)
        assert drive.get_iec_clk() is False  # Driven low

    def test_get_iec_data_output(self):
        """Can read drive's DATA output state."""
        drive = Drive1541()
        # Initially, DATA OUT is not driven
        assert drive.get_iec_data() is True  # Released

        # Set VIA1 to drive DATA OUT low
        drive.via1.ddrb = 0x02  # PB1 as output
        drive.via1.orb = 0x02   # PB1 high (inverted = bus low)
        assert drive.get_iec_data() is False  # Driven low


class TestDrive1541Reset:
    """Test drive reset behavior."""

    def test_reset_clears_state(self):
        """Reset returns drive to initial state."""
        drive = Drive1541()

        # Modify some state
        drive.motor_on = True
        drive.led_on = True
        drive.current_track = 18
        drive.via1.ora = 0xFF
        drive.via2.orb = 0xFF

        drive.reset()

        assert drive.motor_on is False
        assert drive.led_on is False
        assert drive.current_track == 1
        assert drive.via1.ora == 0x00
        assert drive.via2.orb == 0x00
