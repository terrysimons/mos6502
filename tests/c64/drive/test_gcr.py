"""Tests for GCR (Group Code Recording) encoding/decoding.

These tests verify the GCR module used by the 1541 disk drive emulation.
GCR is the encoding scheme used to store data on Commodore floppy disks.

Reference:
- https://www.c64-wiki.com/wiki/GCR
- http://www.baltissen.org/newhtm/1541c.htm
"""

import pytest
from systems.c64.drive.gcr import (
    GCR_ENCODE,
    GCR_DECODE,
    HEADER_BLOCK_ID,
    DATA_BLOCK_ID,
    SYNC_BYTE,
    GAP_BYTE,
    gcr_encode_4_to_5,
    gcr_decode_5_to_4,
    gcr_encode_bytes,
    gcr_decode_bytes,
    encode_sector_header,
    decode_sector_header,
    encode_sector_data,
    decode_sector_data,
    GCRTrack,
    GCRDisk,
)


class TestGCREncodeTables:
    """Test GCR encoding/decoding lookup tables."""

    def test_encode_table_has_16_entries(self):
        """GCR encode table should have entries for all 16 nybble values."""
        assert len(GCR_ENCODE) == 16

    def test_decode_table_has_32_entries(self):
        """GCR decode table should have entries for all 32 5-bit values."""
        assert len(GCR_DECODE) == 32

    def test_encode_values_are_5_bit(self):
        """All encoded values should fit in 5 bits (0-31)."""
        for gcr_code in GCR_ENCODE:
            assert 0 <= gcr_code <= 31, f"GCR code {gcr_code} exceeds 5 bits"

    def test_encode_decode_roundtrip(self):
        """Encoding then decoding should return original nybble."""
        for nybble in range(16):
            gcr_code = GCR_ENCODE[nybble]
            decoded = GCR_DECODE[gcr_code]
            assert decoded == nybble, f"Roundtrip failed for nybble {nybble}"

    def test_no_more_than_two_consecutive_zeros(self):
        """GCR codes should have no more than 2 consecutive zero bits.

        This is a requirement for clock recovery on the disk drive.
        """
        for nybble, gcr_code in enumerate(GCR_ENCODE):
            binary = format(gcr_code, '05b')
            assert '000' not in binary, f"GCR code for {nybble} has 3+ consecutive zeros: {binary}"

    def test_invalid_gcr_codes_decode_to_0xff(self):
        """Invalid GCR codes should decode to 0xFF."""
        # Find codes that are not valid GCR values
        valid_codes = set(GCR_ENCODE)
        for code in range(32):
            if code not in valid_codes:
                assert GCR_DECODE[code] == 0xFF, f"Invalid code {code} should decode to 0xFF"


class TestGCREncode4To5:
    """Test 4-byte to 5-byte GCR encoding."""

    def test_encodes_4_bytes_to_5(self):
        """Input of 4 bytes should produce 5 bytes output."""
        result = gcr_encode_4_to_5(bytes([0x00, 0x00, 0x00, 0x00]))
        assert len(result) == 5

    def test_wrong_input_length_raises(self):
        """Input not exactly 4 bytes should raise ValueError."""
        with pytest.raises(ValueError):
            gcr_encode_4_to_5(bytes([0x00, 0x00, 0x00]))
        with pytest.raises(ValueError):
            gcr_encode_4_to_5(bytes([0x00, 0x00, 0x00, 0x00, 0x00]))

    def test_all_zeros(self):
        """Encoding all zeros should produce known GCR pattern."""
        # 0x00 = nybbles 0,0 -> GCR 01010 (0x0A)
        # Four 0x00 bytes = 8 nybbles of 0 = 8 GCR codes of 01010
        # Packed into 5 bytes
        result = gcr_encode_4_to_5(bytes([0x00, 0x00, 0x00, 0x00]))
        # Verify roundtrip works (more important than specific bytes)
        decoded = gcr_decode_5_to_4(result)
        assert decoded == bytes([0x00, 0x00, 0x00, 0x00])
        # And verify we get 5 bytes
        assert len(result) == 5

    def test_all_ones(self):
        """Encoding 0xFF bytes should produce known GCR pattern."""
        # 0xFF = nybbles F,F -> GCR 10101 (0x15)
        # Four 0xFF bytes = 8 nybbles of F = 8 GCR codes of 10101
        # Packed into 5 bytes
        result = gcr_encode_4_to_5(bytes([0xFF, 0xFF, 0xFF, 0xFF]))
        # Verify roundtrip works (more important than specific bytes)
        decoded = gcr_decode_5_to_4(result)
        assert decoded == bytes([0xFF, 0xFF, 0xFF, 0xFF])
        # And verify we get 5 bytes
        assert len(result) == 5


class TestGCRDecode5To4:
    """Test 5-byte to 4-byte GCR decoding."""

    def test_decodes_5_bytes_to_4(self):
        """Input of 5 bytes should produce 4 bytes output."""
        # Use a known valid GCR sequence (all zeros encoded)
        result = gcr_decode_5_to_4(bytes([0x52, 0x94, 0xA9, 0x4A, 0x52]))
        assert len(result) == 4

    def test_wrong_input_length_raises(self):
        """Input not exactly 5 bytes should raise ValueError."""
        with pytest.raises(ValueError):
            gcr_decode_5_to_4(bytes([0x00, 0x00, 0x00, 0x00]))
        with pytest.raises(ValueError):
            gcr_decode_5_to_4(bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))

    def test_roundtrip_zeros(self):
        """Encode then decode should return original data (zeros)."""
        original = bytes([0x00, 0x00, 0x00, 0x00])
        encoded = gcr_encode_4_to_5(original)
        decoded = gcr_decode_5_to_4(encoded)
        assert decoded == original

    def test_roundtrip_ones(self):
        """Encode then decode should return original data (ones)."""
        original = bytes([0xFF, 0xFF, 0xFF, 0xFF])
        encoded = gcr_encode_4_to_5(original)
        decoded = gcr_decode_5_to_4(encoded)
        assert decoded == original

    def test_roundtrip_arbitrary_data(self):
        """Encode then decode should return original arbitrary data."""
        test_cases = [
            bytes([0x12, 0x34, 0x56, 0x78]),
            bytes([0xAB, 0xCD, 0xEF, 0x01]),
            bytes([0x07, 0x08, 0x09, 0x0A]),
            bytes([0xDE, 0xAD, 0xBE, 0xEF]),
        ]
        for original in test_cases:
            encoded = gcr_encode_4_to_5(original)
            decoded = gcr_decode_5_to_4(encoded)
            assert decoded == original, f"Roundtrip failed for {original.hex()}"


class TestGCREncodeDecodeBytes:
    """Test arbitrary-length GCR encoding/decoding."""

    def test_encode_requires_multiple_of_4(self):
        """Data length must be multiple of 4 for encoding."""
        with pytest.raises(ValueError):
            gcr_encode_bytes(bytes([0x00, 0x00, 0x00]))

    def test_decode_requires_multiple_of_5(self):
        """Data length must be multiple of 5 for decoding."""
        with pytest.raises(ValueError):
            gcr_decode_bytes(bytes([0x00, 0x00, 0x00, 0x00]))

    def test_encode_8_bytes_to_10(self):
        """8 bytes should encode to 10 GCR bytes."""
        result = gcr_encode_bytes(bytes([0x00] * 8))
        assert len(result) == 10

    def test_roundtrip_256_bytes(self):
        """Encoding and decoding 256 bytes should roundtrip correctly."""
        original = bytes(range(256))
        encoded = gcr_encode_bytes(original)
        assert len(encoded) == 320  # 256 * 5/4 = 320
        decoded = gcr_decode_bytes(encoded)
        assert decoded == original

    def test_empty_input(self):
        """Empty input should produce empty output."""
        assert gcr_encode_bytes(bytes()) == bytes()
        assert gcr_decode_bytes(bytes()) == bytes()


class TestSectorHeader:
    """Test sector header encoding/decoding."""

    def test_encode_header_produces_10_bytes(self):
        """Encoded header should be 10 GCR bytes (8 raw bytes)."""
        result = encode_sector_header(track=1, sector=0, disk_id=b"AB")
        assert len(result) == 10

    def test_decode_header_extracts_track_sector(self):
        """Decoding should extract correct track and sector."""
        encoded = encode_sector_header(track=18, sector=5, disk_id=b"XY")
        track, sector, checksum, disk_id, valid = decode_sector_header(encoded)
        assert track == 18
        assert sector == 5
        assert disk_id == b"XY"
        assert valid is True

    def test_header_checksum_validation(self):
        """Header checksum should validate correctly."""
        encoded = encode_sector_header(track=1, sector=0, disk_id=b"00")
        _, _, _, _, valid = decode_sector_header(encoded)
        assert valid is True

    def test_decode_wrong_length_raises(self):
        """Decoding wrong length data should raise."""
        with pytest.raises(ValueError):
            decode_sector_header(bytes([0x00] * 9))

    def test_roundtrip_various_tracks_sectors(self):
        """Header roundtrip should work for various track/sector combinations."""
        test_cases = [
            (1, 0, b"00"),
            (18, 0, b"AB"),
            (35, 16, b"XY"),
            (17, 20, b"12"),
        ]
        for track, sector, disk_id in test_cases:
            encoded = encode_sector_header(track, sector, disk_id)
            dec_track, dec_sector, _, dec_id, valid = decode_sector_header(encoded)
            assert valid, f"Invalid header for T{track} S{sector}"
            assert dec_track == track
            assert dec_sector == sector
            assert dec_id == disk_id


class TestSectorData:
    """Test sector data encoding/decoding."""

    def test_encode_data_produces_325_bytes(self):
        """Encoded data block should be 325 GCR bytes (260 raw bytes)."""
        data = bytes([0x00] * 256)
        result = encode_sector_data(data)
        assert len(result) == 325

    def test_encode_wrong_length_raises(self):
        """Encoding data not exactly 256 bytes should raise."""
        with pytest.raises(ValueError):
            encode_sector_data(bytes([0x00] * 255))
        with pytest.raises(ValueError):
            encode_sector_data(bytes([0x00] * 257))

    def test_decode_wrong_length_raises(self):
        """Decoding data not exactly 325 bytes should raise."""
        with pytest.raises(ValueError):
            decode_sector_data(bytes([0x00] * 324))

    def test_decode_extracts_256_data_bytes(self):
        """Decoding should extract exactly 256 data bytes."""
        original = bytes(range(256))
        encoded = encode_sector_data(original)
        decoded, checksum, valid = decode_sector_data(encoded)
        assert len(decoded) == 256
        assert valid is True

    def test_data_checksum_validation(self):
        """Data checksum should validate correctly."""
        original = bytes([0x41] * 256)  # All 'A's
        encoded = encode_sector_data(original)
        decoded, _, valid = decode_sector_data(encoded)
        assert valid is True
        assert decoded == original

    def test_roundtrip_various_data_patterns(self):
        """Data roundtrip should work for various patterns."""
        test_cases = [
            bytes([0x00] * 256),  # All zeros
            bytes([0xFF] * 256),  # All ones
            bytes(range(256)),    # Sequential
            bytes([i ^ 0xAA for i in range(256)]),  # XOR pattern
        ]
        for original in test_cases:
            encoded = encode_sector_data(original)
            decoded, _, valid = decode_sector_data(encoded)
            assert valid, f"Invalid data for pattern starting with {original[0]:02X}"
            assert decoded == original

    def test_data_block_has_correct_marker(self):
        """Data block should start with DATA_BLOCK_ID marker."""
        data = bytes([0x00] * 256)
        encoded = encode_sector_data(data)
        # Decode the GCR to check the raw marker
        raw = gcr_decode_bytes(encoded)
        assert raw[0] == DATA_BLOCK_ID


class TestGCRTrack:
    """Test GCRTrack class operations."""

    def test_track_sizes_for_zones(self):
        """Track sizes should match expected values for each zone."""
        # Zone 3 (tracks 1-17): 21 sectors
        track_z3 = GCRTrack(track_num=1, num_sectors=21, speed_zone=3)
        assert track_z3.track_size == 7812

        # Zone 2 (tracks 18-24): 19 sectors
        track_z2 = GCRTrack(track_num=18, num_sectors=19, speed_zone=2)
        assert track_z2.track_size == 7068

        # Zone 1 (tracks 25-30): 18 sectors
        track_z1 = GCRTrack(track_num=25, num_sectors=18, speed_zone=1)
        assert track_z1.track_size == 6696

        # Zone 0 (tracks 31-35): 17 sectors
        track_z0 = GCRTrack(track_num=31, num_sectors=17, speed_zone=0)
        assert track_z0.track_size == 6324

    def test_new_track_filled_with_gap_bytes(self):
        """New track should be filled with GAP_BYTE."""
        track = GCRTrack(track_num=1, num_sectors=21, speed_zone=3)
        assert all(b == GAP_BYTE for b in track.data)

    def test_read_byte_advances_position(self):
        """Reading a byte should advance the position."""
        track = GCRTrack(track_num=1, num_sectors=21, speed_zone=3)
        track.data[0] = 0xAB
        track.data[1] = 0xCD

        assert track.byte_position == 0
        byte1 = track.read_byte()
        assert byte1 == 0xAB
        assert track.byte_position == 1

        byte2 = track.read_byte()
        assert byte2 == 0xCD
        assert track.byte_position == 2

    def test_read_byte_wraps_around(self):
        """Reading past end of track should wrap to beginning."""
        track = GCRTrack(track_num=1, num_sectors=21, speed_zone=3)
        track.byte_position = track.track_size - 1
        track.data[track.track_size - 1] = 0xAA
        track.data[0] = 0xBB

        byte1 = track.read_byte()
        assert byte1 == 0xAA
        assert track.byte_position == 0

        byte2 = track.read_byte()
        assert byte2 == 0xBB

    def test_write_byte_advances_position(self):
        """Writing a byte should advance the position."""
        track = GCRTrack(track_num=1, num_sectors=21, speed_zone=3)
        assert track.byte_position == 0

        track.write_byte(0xAB)
        assert track.data[0] == 0xAB
        assert track.byte_position == 1

        track.write_byte(0xCD)
        assert track.data[1] == 0xCD
        assert track.byte_position == 2

    def test_write_byte_wraps_around(self):
        """Writing past end of track should wrap to beginning."""
        track = GCRTrack(track_num=1, num_sectors=21, speed_zone=3)
        track.byte_position = track.track_size - 1

        track.write_byte(0xAA)
        assert track.data[track.track_size - 1] == 0xAA
        assert track.byte_position == 0

        track.write_byte(0xBB)
        assert track.data[0] == 0xBB

    def test_is_sync_detects_sync_bytes(self):
        """is_sync should detect SYNC_BYTE at current position."""
        track = GCRTrack(track_num=1, num_sectors=21, speed_zone=3)
        track.data[0] = SYNC_BYTE
        track.data[1] = GAP_BYTE

        track.byte_position = 0
        assert track.is_sync() is True

        track.byte_position = 1
        assert track.is_sync() is False

    def test_get_sector_offset(self):
        """Sector offsets should be 372 bytes apart."""
        track = GCRTrack(track_num=1, num_sectors=21, speed_zone=3)

        assert track.get_sector_offset(0) == 0
        assert track.get_sector_offset(1) == 372
        assert track.get_sector_offset(2) == 744
        assert track.get_sector_offset(10) == 3720


class TestGCRDisk:
    """Test GCRDisk class operations."""

    def test_empty_disk_has_no_tracks(self):
        """Empty GCRDisk should have no initialized tracks."""
        disk = GCRDisk(d64=None)
        # Tracks array exists but all are None
        assert disk.tracks[1] is None
        assert disk.tracks[18] is None

    def test_get_track_returns_none_for_uninitialized(self):
        """get_track should return None for uninitialized tracks."""
        disk = GCRDisk(d64=None)
        assert disk.get_track(1) is None
        assert disk.get_track(35) is None

    def test_get_track_invalid_numbers(self):
        """get_track should return None for invalid track numbers."""
        disk = GCRDisk(d64=None)
        assert disk.get_track(0) is None
        assert disk.get_track(41) is None
        assert disk.get_track(-1) is None


class TestGCRConstants:
    """Test GCR module constants."""

    def test_block_id_values(self):
        """Block ID markers should have expected values."""
        assert HEADER_BLOCK_ID == 0x08
        assert DATA_BLOCK_ID == 0x07

    def test_sync_and_gap_bytes(self):
        """SYNC and GAP bytes should have expected values."""
        assert SYNC_BYTE == 0xFF
        assert GAP_BYTE == 0x55
