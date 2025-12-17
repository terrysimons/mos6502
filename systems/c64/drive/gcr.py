"""GCR (Group Code Recording) encoding/decoding for 1541 disk emulation.

The 1541 uses GCR encoding to store data on disk. Each 4-bit nybble is
encoded as a 5-bit GCR code, providing clock synchronization without
using special clock bits.

Sector Format on Disk:
    SYNC (10+ bytes of $FF)
    Header Block:
        $52 (Header block ID)
        Checksum (XOR of track, sector, ID1, ID2)
        Sector number
        Track number
        ID byte 2
        ID byte 1
        $0F $0F (header padding)
    Gap 1 (9 bytes of $55)
    SYNC (10+ bytes of $FF)
    Data Block:
        $55 (Data block ID)
        256 data bytes
        Checksum (XOR of all 256 data bytes)
        $00 $00 (data padding, makes 260 bytes total)
    Gap 2 (8-9 bytes of $55)

GCR Encoding Rules:
    - Each 4-bit nybble -> 5-bit GCR code
    - No more than 2 consecutive zeros (for clock recovery)
    - Always exactly 4 bytes -> 5 GCR bytes

Reference:
- https://www.c64-wiki.com/wiki/GCR
- http://www.baltissen.org/newhtm/1541c.htm
"""


from mos6502.compat import logging
from mos6502.compat import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .d64 import D64Image

log = logging.getLogger("gcr")


# GCR encoding table: 4-bit nybble -> 5-bit GCR code
# Each code has at most 2 consecutive zeros for clock recovery
GCR_ENCODE = [
    0x0A,  # 0 -> 01010
    0x0B,  # 1 -> 01011
    0x12,  # 2 -> 10010
    0x13,  # 3 -> 10011
    0x0E,  # 4 -> 01110
    0x0F,  # 5 -> 01111
    0x16,  # 6 -> 10110
    0x17,  # 7 -> 10111
    0x09,  # 8 -> 01001
    0x19,  # 9 -> 11001
    0x1A,  # A -> 11010
    0x1B,  # B -> 11011
    0x0D,  # C -> 01101
    0x1D,  # D -> 11101
    0x1E,  # E -> 11110
    0x15,  # F -> 10101
]

# GCR decoding table: 5-bit GCR code -> 4-bit nybble
# Invalid codes return 0xFF
GCR_DECODE = [0xFF] * 32
for nybble, gcr in enumerate(GCR_ENCODE):
    GCR_DECODE[gcr] = nybble


# Block header markers
HEADER_BLOCK_ID = 0x08  # After GCR encoding, appears as part of sync pattern end
DATA_BLOCK_ID = 0x07

# Sync mark - raw $FF bytes (all 1s, no GCR)
SYNC_BYTE = 0xFF
SYNC_LENGTH = 10  # Standard sync length in bytes

# Gap filler byte (GCR encoded $55, produces pattern with no ambiguous clock)
GAP_BYTE = 0x55


def gcr_encode_4_to_5(data: bytes) -> bytes:
    """Encode 4 bytes to 5 GCR bytes.

    Takes 4 bytes (8 nybbles) and encodes to 5 bytes (40 bits = 8 x 5-bit codes).

    Args:
        data: 4 bytes to encode

    Returns:
        5 GCR-encoded bytes
    """
    if len(data) != 4:
        raise ValueError(f"GCR encode requires exactly 4 bytes, got {len(data)}")

    # Extract 8 nybbles
    nybbles = []
    for byte in data:
        nybbles.append((byte >> 4) & 0x0F)
        nybbles.append(byte & 0x0F)

    # Encode each nybble to 5-bit GCR
    gcr_bits = 0
    for nybble in nybbles:
        gcr_bits = (gcr_bits << 5) | GCR_ENCODE[nybble]

    # Extract 5 bytes from 40 bits
    result = bytes([
        (gcr_bits >> 32) & 0xFF,
        (gcr_bits >> 24) & 0xFF,
        (gcr_bits >> 16) & 0xFF,
        (gcr_bits >> 8) & 0xFF,
        gcr_bits & 0xFF,
    ])

    return result


def gcr_decode_5_to_4(gcr_data: bytes) -> bytes:
    """Decode 5 GCR bytes to 4 data bytes.

    Takes 5 GCR-encoded bytes and decodes to 4 data bytes.

    Args:
        gcr_data: 5 GCR-encoded bytes

    Returns:
        4 decoded data bytes
    """
    if len(gcr_data) != 5:
        raise ValueError(f"GCR decode requires exactly 5 bytes, got {len(gcr_data)}")

    # Combine 5 bytes into 40 bits
    gcr_bits = (
        (gcr_data[0] << 32) |
        (gcr_data[1] << 24) |
        (gcr_data[2] << 16) |
        (gcr_data[3] << 8) |
        gcr_data[4]
    )

    # Extract 8 x 5-bit GCR codes and decode each to a nybble
    nybbles = []
    for i in range(7, -1, -1):
        gcr_code = (gcr_bits >> (i * 5)) & 0x1F
        nybble = GCR_DECODE[gcr_code]
        if nybble == 0xFF:
            log.warning(f"Invalid GCR code {gcr_code:05b}")
            nybble = 0
        nybbles.append(nybble)

    # Combine nybbles into 4 bytes
    result = bytes([
        (nybbles[0] << 4) | nybbles[1],
        (nybbles[2] << 4) | nybbles[3],
        (nybbles[4] << 4) | nybbles[5],
        (nybbles[6] << 4) | nybbles[7],
    ])

    return result


def gcr_encode_bytes(data: bytes) -> bytes:
    """Encode arbitrary length data to GCR.

    Data length must be a multiple of 4 bytes.

    Args:
        data: Data to encode (length must be multiple of 4)

    Returns:
        GCR-encoded data (5/4 ratio)
    """
    if len(data) % 4 != 0:
        raise ValueError(f"Data length must be multiple of 4, got {len(data)}")

    result = bytearray()
    for i in range(0, len(data), 4):
        result.extend(gcr_encode_4_to_5(data[i:i+4]))

    return bytes(result)


def gcr_decode_bytes(gcr_data: bytes) -> bytes:
    """Decode GCR data back to original bytes.

    Args:
        gcr_data: GCR-encoded data (length must be multiple of 5)

    Returns:
        Decoded data (4/5 ratio)
    """
    if len(gcr_data) % 5 != 0:
        raise ValueError(f"GCR data length must be multiple of 5, got {len(gcr_data)}")

    result = bytearray()
    for i in range(0, len(gcr_data), 5):
        result.extend(gcr_decode_5_to_4(gcr_data[i:i+5]))

    return bytes(result)


def decode_sector_header(gcr_header: bytes) -> Tuple[int, int, int, bytes, bool]:
    """Decode a GCR-encoded sector header block.

    Header format (8 bytes after GCR decoding):
        $08 (Header block ID)
        Checksum (XOR of track, sector, ID1, ID2)
        Sector
        Track
        ID2
        ID1
        $0F
        $0F

    Args:
        gcr_header: 10 GCR-encoded header bytes

    Returns:
        Tuple of (track, sector, checksum, disk_id, checksum_valid)
    """
    if len(gcr_header) != 10:
        raise ValueError(f"GCR header must be 10 bytes, got {len(gcr_header)}")

    # Decode GCR to get 8 raw bytes
    raw_header = gcr_decode_bytes(gcr_header)

    block_id = raw_header[0]
    checksum = raw_header[1]
    sector = raw_header[2]
    track = raw_header[3]
    id2 = raw_header[4]
    id1 = raw_header[5]
    # raw_header[6] and raw_header[7] are padding ($0F)

    disk_id = bytes([id1, id2])

    # Verify checksum
    expected_checksum = track ^ sector ^ id1 ^ id2
    checksum_valid = (checksum == expected_checksum) and (block_id == HEADER_BLOCK_ID)

    return (track, sector, checksum, disk_id, checksum_valid)


def decode_sector_data(gcr_data: bytes) -> Tuple[bytes, int, bool]:
    """Decode a GCR-encoded sector data block.

    Data format (260 bytes after GCR decoding):
        $07 (Data block ID)
        256 data bytes
        Checksum (XOR of all 256 data bytes)
        $00
        $00

    Args:
        gcr_data: 325 GCR-encoded data bytes

    Returns:
        Tuple of (256_data_bytes, checksum, checksum_valid)
    """
    if len(gcr_data) != 325:
        raise ValueError(f"GCR data block must be 325 bytes, got {len(gcr_data)}")

    # Decode GCR to get 260 raw bytes
    raw_data = gcr_decode_bytes(gcr_data)

    block_id = raw_data[0]
    data = raw_data[1:257]  # 256 bytes of actual data
    checksum = raw_data[257]
    # raw_data[258] and raw_data[259] are padding ($00)

    # Verify checksum
    expected_checksum = 0
    for byte in data:
        expected_checksum ^= byte
    checksum_valid = (checksum == expected_checksum) and (block_id == DATA_BLOCK_ID)

    return (bytes(data), checksum, checksum_valid)


def encode_sector_header(track: int, sector: int, disk_id: bytes) -> bytes:
    """Encode a sector header block.

    Header format (8 bytes before GCR encoding):
        $08 (Header block ID)
        Checksum (XOR of track, sector, ID1, ID2)
        Sector
        Track
        ID2
        ID1
        $0F
        $0F

    Args:
        track: Track number (1-35)
        sector: Sector number
        disk_id: 2-byte disk ID

    Returns:
        GCR-encoded header (10 bytes)
    """
    id1 = disk_id[0] if len(disk_id) > 0 else 0x30
    id2 = disk_id[1] if len(disk_id) > 1 else 0x30

    checksum = track ^ sector ^ id1 ^ id2

    header = bytes([
        HEADER_BLOCK_ID,
        checksum,
        sector,
        track,
        id2,
        id1,
        0x0F,
        0x0F,
    ])

    return gcr_encode_bytes(header)


def encode_sector_data(data: bytes) -> bytes:
    """Encode a 256-byte sector data block.

    Data format (260 bytes before GCR encoding):
        $07 (Data block ID)
        256 data bytes
        Checksum (XOR of all 256 data bytes)
        $00
        $00

    Args:
        data: 256 bytes of sector data

    Returns:
        GCR-encoded data block (325 bytes)
    """
    if len(data) != 256:
        raise ValueError(f"Sector data must be 256 bytes, got {len(data)}")

    # Calculate checksum
    checksum = 0
    for byte in data:
        checksum ^= byte

    # Build data block
    block = bytearray()
    block.append(DATA_BLOCK_ID)
    block.extend(data)
    block.append(checksum)
    block.append(0x00)
    block.append(0x00)

    return gcr_encode_bytes(bytes(block))


class GCRTrack:
    """GCR-encoded track data for 1541 emulation.

    This class generates and manages the raw GCR data for a single track,
    simulating what the drive head would read from the physical disk.
    """

    # Track sizes in bytes (raw GCR data) for each speed zone
    #
    # Per-sector GCR structure:
    #   SYNC: 10 bytes, Header GCR: 10 bytes, Header gap: 9 bytes,
    #   SYNC: 10 bytes, Data GCR: 325 bytes, Data gap: 8 bytes
    #   Total: 372 bytes per sector
    #
    # Buffer must hold: sectors_per_zone × 372 bytes
    TRACK_SIZE_ZONE = {
        0: 6324,   # Zone 0 (tracks 31-35): 17 sectors × 372 = 6324
        1: 6696,   # Zone 1 (tracks 25-30): 18 sectors × 372 = 6696
        2: 7068,   # Zone 2 (tracks 18-24): 19 sectors × 372 = 7068
        3: 7812,   # Zone 3 (tracks 1-17): 21 sectors × 372 = 7812
    }

    def __init__(self, track_num: int, num_sectors: int, speed_zone: int) -> None:
        """Initialize GCR track.

        Args:
            track_num: Track number (1-35)
            num_sectors: Number of sectors on this track
            speed_zone: Speed zone (0-3)
        """
        self.track_num = track_num
        self.num_sectors = num_sectors
        self.speed_zone = speed_zone

        # Track data is a circular buffer of GCR bytes
        self.track_size = self.TRACK_SIZE_ZONE[speed_zone]
        self.data = bytearray(self.track_size)

        # Current read position (byte and bit within byte)
        self.byte_position = 0
        self.bit_position = 0

        # Initialize with gap bytes (no valid data yet)
        for i in range(self.track_size):
            self.data[i] = GAP_BYTE

    def build_from_d64(self, d64: "D64Image", disk_id: bytes) -> None:
        """Build GCR track data from D64 image.

        Args:
            d64: D64 disk image
            disk_id: 2-byte disk ID
        """
        track_data = bytearray()

        for sector in range(self.num_sectors):
            # Read sector data from D64
            sector_data = d64.read_sector(self.track_num, sector)

            # Add sync before header
            track_data.extend([SYNC_BYTE] * SYNC_LENGTH)

            # Add GCR-encoded header
            header_gcr = encode_sector_header(self.track_num, sector, disk_id)
            track_data.extend(header_gcr)

            # Add gap between header and data
            track_data.extend([GAP_BYTE] * 9)

            # Add sync before data block
            track_data.extend([SYNC_BYTE] * SYNC_LENGTH)

            # Add GCR-encoded data block
            data_gcr = encode_sector_data(bytes(sector_data))
            track_data.extend(data_gcr)

            # Add inter-sector gap
            track_data.extend([GAP_BYTE] * 8)

        # Copy to track buffer, wrapping if necessary
        # If track data is shorter than buffer, fill rest with gaps
        # If track data is longer, truncate (shouldn't happen with correct calculations)
        if len(track_data) <= self.track_size:
            self.data[:len(track_data)] = track_data
            # Fill remaining with gaps
            for i in range(len(track_data), self.track_size):
                self.data[i] = GAP_BYTE
        else:
            log.warning(f"Track {self.track_num} data ({len(track_data)} bytes) exceeds buffer ({self.track_size} bytes)")
            self.data[:] = track_data[:self.track_size]

    def read_byte(self) -> int:
        """Read next byte from track (advancing position).

        Returns:
            Next GCR byte from track
        """
        byte = self.data[self.byte_position]
        self.byte_position = (self.byte_position + 1) % self.track_size
        return byte

    def read_bit(self) -> int:
        """Read next bit from track (advancing position).

        Returns:
            0 or 1
        """
        byte = self.data[self.byte_position]
        bit = (byte >> (7 - self.bit_position)) & 1

        self.bit_position += 1
        if self.bit_position >= 8:
            self.bit_position = 0
            self.byte_position = (self.byte_position + 1) % self.track_size

        return bit

    def is_sync(self) -> bool:
        """Check if current position is in a sync mark.

        SYNC is detected when we see a long string of 1 bits (0xFF bytes).
        The 1541 hardware detects when 10+ bits of 1s have been seen.

        Returns:
            True if at a sync position
        """
        # Check if current byte is a sync byte (0xFF)
        return self.data[self.byte_position] == SYNC_BYTE

    def advance_to_sync(self) -> bool:
        """Advance read position until we find a sync mark.

        Returns:
            True if sync found, False if wrapped around without finding sync
        """
        start_pos = self.byte_position

        while True:
            if self.data[self.byte_position] == SYNC_BYTE:
                return True

            self.byte_position = (self.byte_position + 1) % self.track_size

            if self.byte_position == start_pos:
                # Wrapped around without finding sync
                return False

    def skip_sync(self) -> None:
        """Skip past a sync mark to the first non-sync byte."""
        while self.data[self.byte_position] == SYNC_BYTE:
            self.byte_position = (self.byte_position + 1) % self.track_size

    def write_byte(self, value: int) -> None:
        """Write a byte to the track at current position (advancing position).

        Args:
            value: GCR byte to write (0-255)
        """
        self.data[self.byte_position] = value & 0xFF
        self.byte_position = (self.byte_position + 1) % self.track_size

    def get_sector_offset(self, sector: int) -> int:
        """Get the byte offset where a sector starts in the track data.

        Each sector is 372 bytes:
            SYNC: 10 bytes, Header GCR: 10 bytes, Header gap: 9 bytes,
            SYNC: 10 bytes, Data GCR: 325 bytes, Data gap: 8 bytes

        Args:
            sector: Sector number (0 to num_sectors-1)

        Returns:
            Byte offset in track data
        """
        return sector * 372

    def update_sector_from_d64(self, d64: "D64Image", sector: int, disk_id: bytes) -> None:
        """Update a single sector from D64 image data.

        This re-encodes just the specified sector, preserving the rest of the track.
        Used after a D64 write operation to keep GCR data in sync.

        Args:
            d64: D64 disk image
            sector: Sector number to update
            disk_id: 2-byte disk ID
        """
        # Read sector data from D64
        sector_data = d64.read_sector(self.track_num, sector)

        # Build the sector's GCR data
        sector_gcr = bytearray()

        # Add sync before header
        sector_gcr.extend([SYNC_BYTE] * SYNC_LENGTH)

        # Add GCR-encoded header
        header_gcr = encode_sector_header(self.track_num, sector, disk_id)
        sector_gcr.extend(header_gcr)

        # Add gap between header and data
        sector_gcr.extend([GAP_BYTE] * 9)

        # Add sync before data block
        sector_gcr.extend([SYNC_BYTE] * SYNC_LENGTH)

        # Add GCR-encoded data block
        data_gcr = encode_sector_data(bytes(sector_data))
        sector_gcr.extend(data_gcr)

        # Add inter-sector gap
        sector_gcr.extend([GAP_BYTE] * 8)

        # Copy to track at sector's offset
        offset = self.get_sector_offset(sector)
        for i, byte in enumerate(sector_gcr):
            pos = (offset + i) % self.track_size
            self.data[pos] = byte


class GCRDisk:
    """Complete GCR-encoded disk for 1541 emulation.

    Manages all tracks and provides the interface for the drive emulation
    to read/write data.
    """

    def __init__(self, d64: Optional["D64Image"] = None) -> None:
        """Initialize GCR disk.

        Args:
            d64: D64 disk image to convert, or None for empty disk
        """
        from .d64 import SECTORS_PER_TRACK, TRACK_SPEED_ZONE

        self.tracks: List[Optional[GCRTrack]] = [None] * 40  # Tracks 1-40 (index 0 unused)
        self.d64 = d64

        # Get disk ID from BAM
        if d64:
            bam = d64.read_sector(18, 0)
            self.disk_id = bytes([bam[0xA2], bam[0xA3]])
        else:
            self.disk_id = b"00"

        # Build GCR tracks from D64
        if d64:
            for track in range(1, d64.num_tracks + 1):
                num_sectors = SECTORS_PER_TRACK[track - 1]
                speed_zone = TRACK_SPEED_ZONE[track - 1]

                gcr_track = GCRTrack(track, num_sectors, speed_zone)
                gcr_track.build_from_d64(d64, self.disk_id)
                self.tracks[track] = gcr_track

    def get_track(self, track_num: int) -> Optional[GCRTrack]:
        """Get GCR track data.

        Args:
            track_num: Track number (1-35/40)

        Returns:
            GCRTrack object or None if track doesn't exist
        """
        if 1 <= track_num <= 40:
            return self.tracks[track_num]
        return None

    def read_byte_at(self, track: int) -> int:
        """Read a byte from the specified track.

        Args:
            track: Track number (1-35)

        Returns:
            GCR byte, or 0x00 if no disk/invalid track
        """
        gcr_track = self.get_track(track)
        if gcr_track:
            return gcr_track.read_byte()
        return 0x00

    def is_sync_at(self, track: int) -> bool:
        """Check if we're at a sync position on the specified track.

        Args:
            track: Track number (1-35)

        Returns:
            True if at sync position
        """
        gcr_track = self.get_track(track)
        if gcr_track:
            return gcr_track.is_sync()
        return False

    def update_sector(self, track: int, sector: int) -> None:
        """Update a sector's GCR data from the D64 image.

        Call this after modifying a sector in the D64 to keep GCR in sync.

        Args:
            track: Track number (1-35)
            sector: Sector number
        """
        gcr_track = self.get_track(track)
        if gcr_track and self.d64:
            gcr_track.update_sector_from_d64(self.d64, sector, self.disk_id)

    def write_byte_at(self, track: int, value: int) -> None:
        """Write a byte to the specified track at current position.

        Args:
            track: Track number (1-35)
            value: GCR byte to write
        """
        gcr_track = self.get_track(track)
        if gcr_track:
            gcr_track.write_byte(value)
