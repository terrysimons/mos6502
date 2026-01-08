"""D64 Disk Image Format Parser.

D64 is the standard disk image format for the Commodore 1541 disk drive.
It is a sector-for-sector copy of a 1541 disk, consisting of 35 tracks
with varying numbers of sectors per track (zone bit recording).

Track Layout:
    Tracks  1-17: 21 sectors each (zone 3, 307692 bit/s)
    Tracks 18-24: 19 sectors each (zone 2, 285714 bit/s)
    Tracks 25-30: 18 sectors each (zone 1, 266667 bit/s)
    Tracks 31-35: 17 sectors each (zone 0, 250000 bit/s)

Total: 683 sectors × 256 bytes = 174,848 bytes (standard D64)

Special Locations:
    Track 18, Sector 0: BAM (Block Allocation Map) and disk header
    Track 18, Sector 1+: Directory entries (8 per sector)

File Types:
    $00: DEL (Deleted)
    $80: DEL (Scratched)
    $81: SEQ (Sequential)
    $82: PRG (Program)
    $83: USR (User)
    $84: REL (Relative)

Reference:
- http://ist.uwaterloo.ca/~schepers/formats/D64.TXT
- https://www.c64-wiki.com/wiki/D64
"""


from mos6502.compat import logging
from mos6502.compat import Path
from mos6502.compat import List, Optional, Tuple, Union
from mos6502.compat import dataclass

log = logging.getLogger("d64")


# Sectors per track for each zone
# Tracks are 1-indexed in documentation but 0-indexed in arrays
SECTORS_PER_TRACK = [
    # Tracks 1-17 (21 sectors)
    21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21,
    # Tracks 18-24 (19 sectors)
    19, 19, 19, 19, 19, 19, 19,
    # Tracks 25-30 (18 sectors)
    18, 18, 18, 18, 18, 18,
    # Tracks 31-35 (17 sectors)
    17, 17, 17, 17, 17,
    # Tracks 36-40 (17 sectors) - extended format
    17, 17, 17, 17, 17,
]

# Speed zone for each track (determines bit rate)
# Zone 3 = fastest (tracks 1-17), Zone 0 = slowest (tracks 31-35)
TRACK_SPEED_ZONE = [
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,  # Tracks 1-17
    2, 2, 2, 2, 2, 2, 2,                                  # Tracks 18-24
    1, 1, 1, 1, 1, 1,                                     # Tracks 25-30
    0, 0, 0, 0, 0,                                        # Tracks 31-35
    0, 0, 0, 0, 0,                                        # Tracks 36-40 (extended)
]

# Standard D64 sizes
D64_35_TRACK_SIZE = 174848      # 683 sectors without errors
D64_35_TRACK_SIZE_ERR = 175531  # 683 sectors with error bytes
D64_40_TRACK_SIZE = 196608      # 768 sectors without errors
D64_40_TRACK_SIZE_ERR = 197376  # 768 sectors with error bytes

# BAM location
BAM_TRACK = 18
BAM_SECTOR = 0

# Directory location
DIR_TRACK = 18
DIR_SECTOR = 1

# File type values
FILE_TYPE_DEL = 0x00
FILE_TYPE_SEQ = 0x01
FILE_TYPE_PRG = 0x02
FILE_TYPE_USR = 0x03
FILE_TYPE_REL = 0x04
FILE_TYPE_MASK = 0x07
FILE_LOCKED = 0x40
FILE_CLOSED = 0x80


@dataclass
class DirectoryEntry:
    """A directory entry in a D64 disk image."""
    file_type: int
    filename: str
    track: int
    sector: int
    size_sectors: int
    locked: bool
    closed: bool

    @property
    def type_name(self) -> str:
        """Get human-readable file type name."""
        types = {
            FILE_TYPE_DEL: "DEL",
            FILE_TYPE_SEQ: "SEQ",
            FILE_TYPE_PRG: "PRG",
            FILE_TYPE_USR: "USR",
            FILE_TYPE_REL: "REL",
        }
        return types.get(self.file_type & FILE_TYPE_MASK, "???")

    @property
    def is_valid(self) -> bool:
        """Check if this is a valid (non-deleted) file."""
        return self.closed and (self.file_type & FILE_TYPE_MASK) != FILE_TYPE_DEL


class D64Image:
    """Parser and accessor for D64 disk image files.

    This class provides read access to D64 disk images, including:
    - Reading individual sectors
    - Parsing the directory
    - Reading file contents
    - Access to BAM (Block Allocation Map)
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        """Initialize D64 image.

        Args:
            path: Path to D64 file, or None for empty/formatted disk
        """
        self.path = path
        self.data = bytearray()
        self.num_tracks = 35
        self.has_errors = False
        self.error_bytes: Optional[bytes] = None

        if path is not None:
            self.load(path)
        else:
            # Create empty formatted disk
            self._format_empty()

    def load(self, path: Path) -> None:
        """Load D64 image from file.

        Args:
            path: Path to D64 file

        Raises:
            ValueError: If file size is not a valid D64 format
        """
        self.path = path
        with open(path, "rb") as f:
            raw_data = f.read()

        size = len(raw_data)

        if size == D64_35_TRACK_SIZE:
            self.num_tracks = 35
            self.has_errors = False
            self.data = bytearray(raw_data)
        elif size == D64_35_TRACK_SIZE_ERR:
            self.num_tracks = 35
            self.has_errors = True
            self.data = bytearray(raw_data[:D64_35_TRACK_SIZE])
            self.error_bytes = raw_data[D64_35_TRACK_SIZE:]
        elif size == D64_40_TRACK_SIZE:
            self.num_tracks = 40
            self.has_errors = False
            self.data = bytearray(raw_data)
        elif size == D64_40_TRACK_SIZE_ERR:
            self.num_tracks = 40
            self.has_errors = True
            self.data = bytearray(raw_data[:D64_40_TRACK_SIZE])
            self.error_bytes = raw_data[D64_40_TRACK_SIZE:]
        else:
            raise ValueError(
                f"Invalid D64 file size: {size} bytes. "
                f"Expected {D64_35_TRACK_SIZE}, {D64_35_TRACK_SIZE_ERR}, "
                f"{D64_40_TRACK_SIZE}, or {D64_40_TRACK_SIZE_ERR}."
            )

        log.info(f"Loaded D64: {path.name}, {self.num_tracks} tracks, errors={self.has_errors}")

    def save(self, path: Optional[Path] = None) -> None:
        """Save D64 image to file.

        Args:
            path: Path to save to, or None to use original path
        """
        save_path = path or self.path
        if save_path is None:
            raise ValueError("No path specified for save")

        with open(save_path, "wb") as f:
            f.write(self.data)
            if self.has_errors and self.error_bytes:
                f.write(self.error_bytes)

    def _format_empty(self) -> None:
        """Create a blank formatted 35-track disk."""
        self.num_tracks = 35
        self.has_errors = False
        total_sectors = sum(SECTORS_PER_TRACK[:35])
        self.data = bytearray(total_sectors * 256)

        # Initialize BAM
        bam = self.read_sector(BAM_TRACK, BAM_SECTOR)

        # First directory track/sector
        bam[0] = DIR_TRACK
        bam[1] = DIR_SECTOR

        # DOS version
        bam[2] = 0x41  # 'A' for standard DOS 2.6

        # Initialize BAM entries for all tracks
        offset = 4
        for track in range(1, 36):
            if track <= 35:
                sectors = SECTORS_PER_TRACK[track - 1]
                bam[offset] = sectors  # Free sector count

                # Set all sectors as free (1 = free, 0 = allocated)
                bitmap = (1 << sectors) - 1
                bam[offset + 1] = bitmap & 0xFF
                bam[offset + 2] = (bitmap >> 8) & 0xFF
                bam[offset + 3] = (bitmap >> 16) & 0xFF

                # Mark track 18 sectors 0-1 as allocated (BAM and directory)
                if track == 18:
                    bam[offset] = sectors - 2
                    bam[offset + 1] &= ~0x03  # Clear bits 0 and 1

            offset += 4

        # Disk name (16 chars, padded with $A0)
        disk_name = b"EMPTY DISK      "
        bam[0x90:0xA0] = disk_name[:16].replace(b" ", b"\xA0")

        # Disk ID
        bam[0xA2] = 0x30  # '0'
        bam[0xA3] = 0x30  # '0'

        # DOS type
        bam[0xA5] = 0x32  # '2'
        bam[0xA6] = 0x41  # 'A'

        # Padding with $A0
        bam[0xA0:0xA2] = b"\xA0\xA0"
        bam[0xA4] = 0xA0
        bam[0xA7:0xAB] = b"\xA0\xA0\xA0\xA0"

        self.write_sector(BAM_TRACK, BAM_SECTOR, bytes(bam))

        # Initialize first directory sector
        dir_sector = bytearray(256)
        dir_sector[0] = 0x00  # No next track
        dir_sector[1] = 0xFF  # End of directory chain
        self.write_sector(DIR_TRACK, DIR_SECTOR, bytes(dir_sector))

    def get_sector_offset(self, track: int, sector: int) -> int:
        """Calculate byte offset in image for a track/sector.

        Args:
            track: Track number (1-35 or 1-40)
            sector: Sector number (0-based)

        Returns:
            Byte offset in the D64 image

        Raises:
            ValueError: If track/sector is out of range
        """
        if track < 1 or track > self.num_tracks:
            raise ValueError(f"Track {track} out of range (1-{self.num_tracks})")

        max_sector = SECTORS_PER_TRACK[track - 1] - 1
        if sector < 0 or sector > max_sector:
            raise ValueError(f"Sector {sector} out of range (0-{max_sector}) for track {track}")

        # Sum sectors of all previous tracks
        offset = sum(SECTORS_PER_TRACK[:track - 1]) * 256
        offset += sector * 256
        return offset

    def read_sector(self, track: int, sector: int) -> bytearray:
        """Read a 256-byte sector from the disk image.

        Args:
            track: Track number (1-35/40)
            sector: Sector number (0-based)

        Returns:
            256-byte sector data
        """
        offset = self.get_sector_offset(track, sector)
        return bytearray(self.data[offset:offset + 256])

    def write_sector(self, track: int, sector: int, data: bytes) -> None:
        """Write a 256-byte sector to the disk image.

        Args:
            track: Track number (1-35/40)
            sector: Sector number (0-based)
            data: 256 bytes of sector data
        """
        if len(data) != 256:
            raise ValueError(f"Sector data must be 256 bytes, got {len(data)}")

        offset = self.get_sector_offset(track, sector)
        self.data[offset:offset + 256] = data

    def get_speed_zone(self, track: int) -> int:
        """Get the speed zone for a track (affects bit rate).

        Args:
            track: Track number (1-35/40)

        Returns:
            Speed zone (0-3)
        """
        if track < 1 or track > 40:
            return 0
        return TRACK_SPEED_ZONE[track - 1]

    def get_disk_name(self) -> str:
        """Get the disk name from the BAM."""
        bam = self.read_sector(BAM_TRACK, BAM_SECTOR)
        # Disk name is at offset $90-$9F, PETSCII padded with $A0
        name_bytes = bam[0x90:0xA0]
        # Convert PETSCII to ASCII
        # Note: $A0 is used for both padding AND represents spaces within names
        # We convert all bytes first, then strip trailing spaces
        name = ""
        for b in name_bytes:
            if b == 0xA0:
                name += " "  # PETSCII shifted space / padding
            elif 0x41 <= b <= 0x5A:
                name += chr(b)  # Uppercase
            elif 0x61 <= b <= 0x7A:
                name += chr(b - 0x20)  # Lowercase -> uppercase
            elif 0x20 <= b <= 0x7E:
                name += chr(b)
            else:
                name += "?"
        # Strip trailing spaces (padding)
        return name.rstrip()

    def get_disk_id(self) -> str:
        """Get the 2-character disk ID."""
        bam = self.read_sector(BAM_TRACK, BAM_SECTOR)
        return chr(bam[0xA2]) + chr(bam[0xA3])

    def get_free_blocks(self) -> int:
        """Get total number of free blocks on disk."""
        bam = self.read_sector(BAM_TRACK, BAM_SECTOR)
        total = 0
        for track in range(1, self.num_tracks + 1):
            if track == 18:
                continue  # Skip directory track
            offset = 4 + (track - 1) * 4
            if offset < len(bam):
                total += bam[offset]
        return total

    def read_directory(self) -> List[DirectoryEntry]:
        """Read all directory entries.

        Returns:
            List of DirectoryEntry objects for all valid files

        D64 directory format (per 32-byte entry):
            $00-$01: Track/sector of next dir sector (only valid in entry 0)
            $02: File type
            $03-$04: Track/sector of first data sector
            $05-$14: Filename (16 bytes, PETSCII, padded with $A0)
            $15-$16: Side sector track/sector (REL files)
            $17: REL record length
            $18-$1D: Unused
            $1E-$1F: File size in sectors (low/high byte)
        """
        entries = []
        track = DIR_TRACK
        sector = DIR_SECTOR

        while track != 0:
            data = self.read_sector(track, sector)

            # Each sector has 8 directory entries of 32 bytes each
            # Bytes 0-1 of sector are the link to next directory sector
            for i in range(8):
                base = i * 32

                # File type is at offset 2 within each 32-byte entry
                file_type = data[base + 2]

                # Skip empty/deleted entries
                if file_type == 0x00:
                    continue

                # Parse entry - all entries use the same layout
                file_track = data[base + 3]
                file_sector = data[base + 4]
                filename_bytes = data[base + 5:base + 21]
                size_lo = data[base + 30]
                size_hi = data[base + 31]

                # Convert filename (PETSCII with $A0 padding)
                filename = ""
                for b in filename_bytes:
                    if b == 0xA0:
                        break
                    elif 0x41 <= b <= 0x5A:
                        filename += chr(b)
                    elif 0x61 <= b <= 0x7A:
                        filename += chr(b - 0x20)
                    elif 0x20 <= b <= 0x7E:
                        filename += chr(b)
                    else:
                        filename += "?"

                entry = DirectoryEntry(
                    file_type=file_type & FILE_TYPE_MASK,
                    filename=filename,
                    track=file_track,
                    sector=file_sector,
                    size_sectors=size_lo | (size_hi << 8),
                    locked=bool(file_type & FILE_LOCKED),
                    closed=bool(file_type & FILE_CLOSED),
                )
                entries.append(entry)

            # Follow chain to next directory sector
            track = data[0]
            sector = data[1]

        return entries

    def read_file(self, entry: Union[DirectoryEntry, str]) -> bytes:
        """Read complete file data following the sector chain.

        Args:
            entry: Directory entry for the file, or filename string

        Returns:
            Raw file data (for PRG, first 2 bytes are load address)

        Raises:
            FileNotFoundError: If filename string doesn't match any file
        """
        # If a string was passed, look up the directory entry
        if isinstance(entry, str):
            filename = entry.upper()
            for dir_entry in self.read_directory():
                if dir_entry.filename == filename:
                    entry = dir_entry
                    break
            else:
                raise FileNotFoundError(f"File not found: {filename}")

        data = bytearray()
        track = entry.track
        sector = entry.sector

        while track != 0:
            sector_data = self.read_sector(track, sector)
            next_track = sector_data[0]
            next_sector = sector_data[1]

            if next_track == 0:
                # Last sector - next_sector indicates bytes used
                bytes_used = next_sector
                data.extend(sector_data[2:2 + bytes_used])
            else:
                # Full sector
                data.extend(sector_data[2:])

            track = next_track
            sector = next_sector

        return bytes(data)

    def find_file(self, filename: str) -> Optional[DirectoryEntry]:
        """Find a file by name (case-insensitive).

        Args:
            filename: Filename to search for

        Returns:
            DirectoryEntry if found, None otherwise
        """
        filename_upper = filename.upper()
        for entry in self.read_directory():
            if entry.filename.upper() == filename_upper and entry.is_valid:
                return entry
        return None
