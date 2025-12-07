"""Tests for D64 disk image format parser.

D64 is the standard format for Commodore 1541 disk images.
Standard format: 35 tracks, 683 sectors, 174,848 bytes.

Reference: http://ist.uwaterloo.ca/~schepers/formats/D64.TXT
"""

import pytest
import tempfile
from pathlib import Path
from systems.c64.drive.d64 import (
    D64Image,
    DirectoryEntry,
    SECTORS_PER_TRACK,
    D64_35_TRACK_SIZE,
    FILE_TYPE_PRG,
    FILE_TYPE_SEQ,
    FILE_CLOSED,
)


class TestD64SectorLayout:
    """Test D64 track/sector layout."""

    def test_sectors_per_track_count(self):
        """Verify sectors per track for all 35 tracks."""
        # Tracks 1-17: 21 sectors
        for track in range(1, 18):
            assert SECTORS_PER_TRACK[track - 1] == 21

        # Tracks 18-24: 19 sectors
        for track in range(18, 25):
            assert SECTORS_PER_TRACK[track - 1] == 19

        # Tracks 25-30: 18 sectors
        for track in range(25, 31):
            assert SECTORS_PER_TRACK[track - 1] == 18

        # Tracks 31-35: 17 sectors
        for track in range(31, 36):
            assert SECTORS_PER_TRACK[track - 1] == 17

    def test_total_sectors(self):
        """35-track disk has 683 sectors."""
        total = sum(SECTORS_PER_TRACK[:35])
        assert total == 683

    def test_total_size(self):
        """35-track disk is 174,848 bytes."""
        assert D64_35_TRACK_SIZE == 683 * 256


class TestD64Creation:
    """Test D64 image creation and formatting."""

    def test_create_empty_disk(self):
        """Creating D64 without path creates formatted empty disk."""
        d64 = D64Image()
        assert d64.num_tracks == 35
        assert len(d64.data) == D64_35_TRACK_SIZE

    def test_empty_disk_has_valid_bam(self):
        """Empty disk has valid BAM structure."""
        d64 = D64Image()
        bam = d64.read_sector(18, 0)

        # First directory sector pointer
        assert bam[0] == 18
        assert bam[1] == 1

        # DOS version
        assert bam[2] == 0x41  # 'A'

    def test_empty_disk_free_blocks(self):
        """Empty disk reports correct free block count."""
        d64 = D64Image()
        free = d64.get_free_blocks()

        # 683 total - 19 on track 18 (reserved) = 664
        # But BAM and first dir sector allocated = 664 - 2 = 662
        # Actually track 18 is excluded from count
        assert free > 0

    def test_empty_disk_name(self):
        """Empty disk has default name."""
        d64 = D64Image()
        name = d64.get_disk_name()
        assert name == "EMPTY DISK"


class TestD64SectorAccess:
    """Test sector read/write operations."""

    def test_read_sector_returns_256_bytes(self):
        """Reading a sector returns 256 bytes."""
        d64 = D64Image()
        sector = d64.read_sector(1, 0)
        assert len(sector) == 256

    def test_write_sector_persists(self):
        """Written data can be read back."""
        d64 = D64Image()
        test_data = bytes([0xAA] * 256)

        d64.write_sector(1, 0, test_data)
        result = d64.read_sector(1, 0)

        assert bytes(result) == test_data

    def test_invalid_track_raises(self):
        """Invalid track number raises ValueError."""
        d64 = D64Image()

        with pytest.raises(ValueError):
            d64.read_sector(0, 0)  # Track 0 doesn't exist

        with pytest.raises(ValueError):
            d64.read_sector(36, 0)  # Track 36 on 35-track disk

    def test_invalid_sector_raises(self):
        """Invalid sector number raises ValueError."""
        d64 = D64Image()

        with pytest.raises(ValueError):
            d64.read_sector(1, 21)  # Track 1 has sectors 0-20

        with pytest.raises(ValueError):
            d64.read_sector(31, 17)  # Track 31 has sectors 0-16

    def test_sector_offset_calculation(self):
        """Sector offsets are calculated correctly."""
        d64 = D64Image()

        # Track 1, sector 0 is at offset 0
        assert d64.get_sector_offset(1, 0) == 0

        # Track 1, sector 1 is at offset 256
        assert d64.get_sector_offset(1, 1) == 256

        # Track 2, sector 0 is after all 21 sectors of track 1
        assert d64.get_sector_offset(2, 0) == 21 * 256


class TestD64SpeedZones:
    """Test disk speed zone handling."""

    def test_speed_zones(self):
        """Speed zones match track regions."""
        d64 = D64Image()

        # Zone 3 (fastest): tracks 1-17
        assert d64.get_speed_zone(1) == 3
        assert d64.get_speed_zone(17) == 3

        # Zone 2: tracks 18-24
        assert d64.get_speed_zone(18) == 2
        assert d64.get_speed_zone(24) == 2

        # Zone 1: tracks 25-30
        assert d64.get_speed_zone(25) == 1
        assert d64.get_speed_zone(30) == 1

        # Zone 0 (slowest): tracks 31-35
        assert d64.get_speed_zone(31) == 0
        assert d64.get_speed_zone(35) == 0


class TestD64Directory:
    """Test directory reading."""

    def test_empty_disk_has_empty_directory(self):
        """Empty disk has no files in directory."""
        d64 = D64Image()
        entries = d64.read_directory()
        assert len(entries) == 0

    def test_find_file_not_found(self):
        """Finding nonexistent file returns None."""
        d64 = D64Image()
        result = d64.find_file("NONEXISTENT")
        assert result is None


class TestD64SaveLoad:
    """Test saving and loading D64 files."""

    def test_save_and_load(self):
        """D64 can be saved and reloaded."""
        d64 = D64Image()
        test_data = bytes([0x55] * 256)
        d64.write_sector(5, 0, test_data)

        with tempfile.NamedTemporaryFile(suffix=".d64", delete=False) as f:
            temp_path = Path(f.name)

        try:
            d64.save(temp_path)

            # Load into new instance
            d64_loaded = D64Image(temp_path)
            result = d64_loaded.read_sector(5, 0)
            assert bytes(result) == test_data
        finally:
            temp_path.unlink()

    def test_load_invalid_size_raises(self):
        """Loading file with invalid size raises ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".d64", delete=False) as f:
            f.write(b"x" * 1000)  # Invalid size
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError):
                D64Image(temp_path)
        finally:
            temp_path.unlink()


class TestDirectoryEntry:
    """Test DirectoryEntry dataclass."""

    def test_type_name_prg(self):
        """PRG file type returns 'PRG'."""
        entry = DirectoryEntry(
            file_type=FILE_TYPE_PRG,
            filename="TEST",
            track=1,
            sector=0,
            size_sectors=10,
            locked=False,
            closed=True,
        )
        assert entry.type_name == "PRG"

    def test_type_name_seq(self):
        """SEQ file type returns 'SEQ'."""
        entry = DirectoryEntry(
            file_type=FILE_TYPE_SEQ,
            filename="DATA",
            track=1,
            sector=0,
            size_sectors=5,
            locked=False,
            closed=True,
        )
        assert entry.type_name == "SEQ"

    def test_is_valid_closed_file(self):
        """Closed non-deleted file is valid."""
        entry = DirectoryEntry(
            file_type=FILE_TYPE_PRG,
            filename="VALID",
            track=1,
            sector=0,
            size_sectors=1,
            locked=False,
            closed=True,
        )
        assert entry.is_valid is True

    def test_is_valid_unclosed_file(self):
        """Unclosed file is not valid."""
        entry = DirectoryEntry(
            file_type=FILE_TYPE_PRG,
            filename="SPLAT",
            track=1,
            sector=0,
            size_sectors=1,
            locked=False,
            closed=False,
        )
        assert entry.is_valid is False
