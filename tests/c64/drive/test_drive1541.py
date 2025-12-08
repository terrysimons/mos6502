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


class TestDrive1541SyncDetection:
    """Test GCR sync detection with look-ahead.

    The 1541 drive uses SYNC marks (10+ consecutive $FF bytes) to mark the
    start of sector headers and data blocks. However, isolated $FF bytes
    can naturally occur in GCR-encoded data - these should NOT be treated
    as sync marks.

    The fix uses look-ahead: when encountering $FF, peek at the next byte.
    If next byte is also $FF, this is a sync mark; otherwise it's data.
    """

    def test_isolated_ff_byte_is_signaled(self):
        """Isolated $FF byte in data should be signaled (not treated as sync)."""
        from systems.c64.drive.gcr import GCRTrack

        drive = Drive1541()
        drive.motor_on = True

        # Create minimal GCR track with isolated $FF surrounded by non-$FF
        gcr_track = GCRTrack(1, 21, 3)
        # Pattern: $55, $FF, $55 - the $FF is isolated data, not sync
        gcr_track.data[0] = 0x55
        gcr_track.data[1] = 0xFF  # Isolated $FF - should be signaled
        gcr_track.data[2] = 0x55
        gcr_track.byte_position = 0

        drive.gcr_disk = type('MockGCRDisk', (), {'get_track': lambda self, t: gcr_track})()

        # Track byte-ready signals
        bytes_signaled = []
        original_signal = drive._signal_byte_ready

        def track_signal():
            bytes_signaled.append(drive._last_gcr_byte)
            original_signal()

        drive._signal_byte_ready = track_signal

        # Process enough cycles to read 3 bytes
        cycles_per_byte = drive._cycles_per_byte[3]  # Speed zone 3
        drive._update_gcr_read(cycles_per_byte * 3)

        # All 3 bytes should be signaled (including the isolated $FF)
        assert len(bytes_signaled) == 3
        assert bytes_signaled == [0x55, 0xFF, 0x55]

    def test_consecutive_ff_bytes_start_sync(self):
        """Two or more consecutive $FF bytes should start a sync mark."""
        from systems.c64.drive.gcr import GCRTrack

        drive = Drive1541()
        drive.motor_on = True

        # Create GCR track with sync mark (consecutive $FF bytes)
        gcr_track = GCRTrack(1, 21, 3)
        # Pattern: $55, $FF, $FF, $FF, $52 - the $FF bytes are sync, $52 is first data
        gcr_track.data[0] = 0x55
        gcr_track.data[1] = 0xFF  # Sync start
        gcr_track.data[2] = 0xFF  # Sync continue
        gcr_track.data[3] = 0xFF  # Sync continue
        gcr_track.data[4] = 0x52  # Header block marker (first byte after sync)
        gcr_track.byte_position = 0

        drive.gcr_disk = type('MockGCRDisk', (), {'get_track': lambda self, t: gcr_track})()

        bytes_signaled = []
        original_signal = drive._signal_byte_ready

        def track_signal():
            bytes_signaled.append(drive._last_gcr_byte)
            original_signal()

        drive._signal_byte_ready = track_signal

        # Process enough cycles to read 5 bytes
        cycles_per_byte = drive._cycles_per_byte[3]
        drive._update_gcr_read(cycles_per_byte * 5)

        # Only $55 and $52 should be signaled - the $FF bytes are sync (not signaled)
        assert len(bytes_signaled) == 2
        assert bytes_signaled == [0x55, 0x52]

    def test_sync_state_cleared_on_first_non_ff(self):
        """Sync state should be cleared when first non-$FF byte is encountered."""
        from systems.c64.drive.gcr import GCRTrack

        drive = Drive1541()
        drive.motor_on = True

        gcr_track = GCRTrack(1, 21, 3)
        # Sync mark followed by data
        gcr_track.data[0] = 0xFF
        gcr_track.data[1] = 0xFF
        gcr_track.data[2] = 0x55  # First data byte after sync
        gcr_track.data[3] = 0xAA
        gcr_track.byte_position = 0

        drive.gcr_disk = type('MockGCRDisk', (), {'get_track': lambda self, t: gcr_track})()

        bytes_signaled = []
        original_signal = drive._signal_byte_ready

        def track_signal():
            bytes_signaled.append(drive._last_gcr_byte)
            original_signal()

        drive._signal_byte_ready = track_signal

        cycles_per_byte = drive._cycles_per_byte[3]
        drive._update_gcr_read(cycles_per_byte * 4)

        # Only $55 and $AA should be signaled (sync bytes suppressed)
        assert len(bytes_signaled) == 2
        assert bytes_signaled == [0x55, 0xAA]
        assert drive._sync_detected is False

    def test_isolated_ff_does_not_set_sync_state(self):
        """Isolated $FF byte should not set the sync_detected flag."""
        from systems.c64.drive.gcr import GCRTrack

        drive = Drive1541()
        drive.motor_on = True

        gcr_track = GCRTrack(1, 21, 3)
        gcr_track.data[0] = 0x55
        gcr_track.data[1] = 0xFF  # Isolated
        gcr_track.data[2] = 0x55
        gcr_track.byte_position = 0

        drive.gcr_disk = type('MockGCRDisk', (), {'get_track': lambda self, t: gcr_track})()

        cycles_per_byte = drive._cycles_per_byte[3]
        drive._update_gcr_read(cycles_per_byte * 3)

        # Sync should NOT be detected for isolated $FF
        assert drive._sync_detected is False

    def test_sync_via2_port_b_bit7(self):
        """VIA2 Port B bit 7 should reflect sync state."""
        from systems.c64.drive.gcr import GCRTrack

        drive = Drive1541()
        drive.motor_on = True

        gcr_track = GCRTrack(1, 21, 3)
        # Start with sync mark
        gcr_track.data[0] = 0xFF
        gcr_track.data[1] = 0xFF
        gcr_track.data[2] = 0xFF
        gcr_track.data[3] = 0x55  # End of sync
        gcr_track.byte_position = 0

        drive.gcr_disk = type('MockGCRDisk', (), {'get_track': lambda self, t: gcr_track})()

        cycles_per_byte = drive._cycles_per_byte[3]

        # Process first $FF (sync start)
        drive._update_gcr_read(cycles_per_byte)
        # VIA2 PB7 = 0 when sync detected (active low)
        port_b = drive.via2.read(0x00)  # Port B register
        assert (port_b & 0x80) == 0, "PB7 should be low during sync"

        # Process until sync ends
        drive._update_gcr_read(cycles_per_byte * 3)
        # VIA2 PB7 = 1 when no sync (released)
        port_b = drive.via2.read(0x00)
        assert (port_b & 0x80) == 0x80, "PB7 should be high when not in sync"
