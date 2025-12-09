#!/usr/bin/env python3
"""Create debug D64 disk images for testing disk loading.

Creates disk images:
1. simple-zone-test.d64 - Single-sector files on each speed zone
2. cross-track-test.d64 - Multi-sector files spanning tracks/zones
3. last-sector-test.d64 - Files using the last sector in each zone
4. sector-chain-test.d64 - Files with specific sector allocation patterns
5. file-size-test.d64 - Files of specific byte sizes
"""

from pathlib import Path

# D64 format constants
TRACKS = 35
SECTORS_PER_TRACK = [
    21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21,  # Tracks 1-17
    19, 19, 19, 19, 19, 19, 19,  # Tracks 18-24
    18, 18, 18, 18, 18, 18,      # Tracks 25-30
    17, 17, 17, 17, 17           # Tracks 31-35
]
SECTOR_SIZE = 256
D64_SIZE = 174848

BAM_TRACK = 18
BAM_SECTOR = 0
DIR_TRACK = 18
DIR_SECTOR = 1


def track_offset(track: int) -> int:
    """Get byte offset for start of track (1-indexed)."""
    offset = 0
    for t in range(1, track):
        offset += SECTORS_PER_TRACK[t - 1] * SECTOR_SIZE
    return offset


def sector_offset(track: int, sector: int) -> int:
    """Get byte offset for a specific sector."""
    return track_offset(track) + sector * SECTOR_SIZE


def create_bam(disk_name: str, used_sectors: list) -> bytes:
    """Create BAM with specified sectors marked as used."""
    bam = bytearray(256)

    bam[0] = DIR_TRACK
    bam[1] = DIR_SECTOR
    bam[2] = 0x41  # DOS version 'A'
    bam[3] = 0x00

    # Initialize all tracks as free
    offset = 4
    for track in range(1, 36):
        sectors = SECTORS_PER_TRACK[track - 1]
        bam[offset] = sectors
        bitmap = (1 << sectors) - 1
        bam[offset + 1] = bitmap & 0xFF
        bam[offset + 2] = (bitmap >> 8) & 0xFF
        bam[offset + 3] = (bitmap >> 16) & 0xFF
        offset += 4

    # Mark used sectors
    for track, sector in used_sectors:
        entry = 4 + (track - 1) * 4
        bam[entry] -= 1  # Decrement free count
        byte_idx = sector // 8
        bit_idx = sector % 8
        bam[entry + 1 + byte_idx] &= ~(1 << bit_idx)

    # Disk name
    name_bytes = disk_name.upper().encode('ascii')[:16]
    for i, b in enumerate(name_bytes):
        bam[144 + i] = b
    for i in range(len(name_bytes), 16):
        bam[144 + i] = 0xA0

    bam[162] = 0xA0
    bam[163] = 0xA0
    bam[164] = ord('D')
    bam[165] = ord('B')
    bam[166] = 0xA0
    bam[167] = ord('2')
    bam[168] = ord('A')

    for i in range(169, 256):
        bam[i] = 0xA0

    return bytes(bam)


def create_basic_program(track_num: int) -> bytes:
    """Create a BASIC program that prints which track it came from.

    10 PRINT "TRACK XX"
    """
    track_str = f"{track_num:02d}"

    # Build the BASIC line
    line_content = bytes([
        0x99,  # PRINT token
        0x20,  # space
        0x22,  # "
    ]) + f"TRACK {track_str}".encode('ascii') + bytes([
        0x22,  # "
        0x00,  # end of line
    ])

    # Calculate addresses
    load_addr = 0x0801
    next_line = load_addr + 2 + 2 + len(line_content)  # +2 for link, +2 for line number

    program = bytes([
        load_addr & 0xFF, (load_addr >> 8) & 0xFF,  # Load address
        next_line & 0xFF, (next_line >> 8) & 0xFF,  # Pointer to next line
        0x0A, 0x00,  # Line number 10
    ]) + line_content + bytes([
        0x00, 0x00,  # End of program (null pointer)
    ])

    return program


def create_debug_disk():
    """Create disk with files testing all 4 speed zones.

    Speed zones:
    - Zone 3: Tracks 1-17 (21 sectors/track)
    - Zone 2: Tracks 18-24 (19 sectors/track) - Track 18 is directory
    - Zone 1: Tracks 25-30 (18 sectors/track)
    - Zone 0: Tracks 31-35 (17 sectors/track)
    """
    disk = bytearray(D64_SIZE)

    # Files on first and last track of each zone (avoiding track 18)
    # Format: (track, zone, position)
    file_info = [
        (1, 3, "first"),   # Zone 3 first
        (17, 3, "last"),   # Zone 3 last (before directory)
        (19, 2, "first"),  # Zone 2 first (after directory)
        (24, 2, "last"),   # Zone 2 last
        (25, 1, "first"),  # Zone 1 first
        (30, 1, "last"),   # Zone 1 last
        (31, 0, "first"),  # Zone 0 first
        (35, 0, "last"),   # Zone 0 last
    ]

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    for test_num, (track, zone, position) in enumerate(file_info, start=1):
        # Create program for this track
        program = create_basic_program(track)

        # Store on sector 0 of this track
        sector = 0

        # Create data sector
        data = bytearray(256)
        data[0] = 0  # Last sector
        data[1] = len(program) + 1  # Bytes used
        data[2:2 + len(program)] = program

        # Write to disk
        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = data

        # Track usage
        used_sectors.append((track, sector))

        # Create directory entry with zone info
        filename = f"TEST{test_num}-Z{zone}-T{track:02d}"
        directory_entries.append((filename, track, sector))

    # Create and write BAM
    bam = create_bam("DEBUG DISK", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector
    dir_sector = bytearray(256)
    dir_sector[0] = 0  # No next directory sector
    dir_sector[1] = 0xFF

    for i, (filename, track, sector) in enumerate(directory_entries):
        entry_offset = i * 32
        if i == 0:
            # First entry uses bytes 0-1 for directory link
            pass

        # File type (PRG, closed)
        dir_sector[entry_offset + 2] = 0x82

        # First data track/sector
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector

        # Filename (16 chars, padded)
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0

        # File size (1 block)
        dir_sector[entry_offset + 30] = 1
        dir_sector[entry_offset + 31] = 0

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


def create_multi_sector_program(num_sectors: int, identifier: str) -> bytes:
    """Create a BASIC program that spans multiple sectors.

    Creates a program with DATA statements to pad it to the desired size.
    The program prints an identifier when run.

    Args:
        num_sectors: Approximate number of 254-byte sectors to span
        identifier: String identifier to print when program runs
    """
    load_addr = 0x0801

    # Build lines of BASIC
    lines = []

    # Line 10: PRINT identifier
    line_10 = bytes([
        0x99,  # PRINT token
        0x20,  # space
        0x22,  # "
    ]) + identifier.encode('ascii') + bytes([
        0x22,  # "
        0x00,  # end of line
    ])
    lines.append((10, line_10))

    # Line 20: END
    line_20 = bytes([
        0x80,  # END token
        0x00,  # end of line
    ])
    lines.append((20, line_20))

    # Add DATA lines to pad the program
    # Each sector holds 254 bytes of data (256 - 2 for link bytes)
    # We need roughly num_sectors * 254 bytes total
    target_size = num_sectors * 254

    # Start adding DATA lines at line 100
    line_num = 100
    current_size = 0

    # Calculate size of header lines
    for ln, content in lines:
        current_size += 2 + 2 + len(content)  # link ptr + line num + content

    # Add padding DATA lines
    while current_size < target_size - 100:
        # DATA line with numbers: DATA 1,2,3,4,5,6,7,8,9,0,1,2,3,4,5,6,7,8,9,0
        data_content = bytes([0x83, 0x20]) + b"1,2,3,4,5,6,7,8,9,0,1,2,3,4,5,6,7,8,9,0" + bytes([0x00])
        lines.append((line_num, data_content))
        current_size += 2 + 2 + len(data_content)
        line_num += 10

    # Build the complete program
    program = bytearray()
    program.append(load_addr & 0xFF)
    program.append((load_addr >> 8) & 0xFF)

    current_addr = load_addr
    for i, (line_num, content) in enumerate(lines):
        # Calculate next line address
        line_size = 2 + 2 + len(content)  # link ptr + line num + content
        if i < len(lines) - 1:
            next_addr = current_addr + line_size
        else:
            next_addr = 0  # End of program

        # Write line
        program.append(next_addr & 0xFF)
        program.append((next_addr >> 8) & 0xFF)
        program.append(line_num & 0xFF)
        program.append((line_num >> 8) & 0xFF)
        program.extend(content)

        current_addr += line_size

    # End of program marker
    program.append(0x00)
    program.append(0x00)

    return bytes(program)


def create_cross_track_disk():
    """Create disk with files spanning multiple tracks.

    Files:
    1. SPAN1-2: Spans tracks 1-2 (like Tank Wars, ~40 sectors, Zone 3 only)
    2. SPAN17-19: Spans tracks 17-19 (crosses Zone 3 to Zone 2 boundary)
    3. SPAN24-26: Spans tracks 24-26 (crosses Zone 2 to Zone 1 boundary)
    4. SPAN30-32: Spans tracks 30-32 (crosses Zone 1 to Zone 0 boundary)
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    # File definitions: (name, start_track, num_sectors, description)
    files = [
        ("SPAN1-2", 1, 40, "Tracks 1-2, Zone 3 only"),
        ("SPAN17-19", 17, 42, "Tracks 17-19, Zone 3->2 boundary"),
        ("SPAN24-26", 24, 38, "Tracks 24-26, Zone 2->1 boundary"),
        ("SPAN30-32", 30, 36, "Tracks 30-32, Zone 1->0 boundary"),
    ]

    for filename, start_track, num_sectors, description in files:
        # Create program data
        program = create_multi_sector_program(num_sectors, filename)

        # Write file across sectors
        track = start_track
        sector = 0
        data_offset = 0
        sectors_written = 0
        file_sectors = []

        while data_offset < len(program):
            # Skip track 18 (directory track)
            if track == 18:
                track = 19
                sector = 0

            # Check if track is valid
            if track > 35:
                print(f"Warning: {filename} exceeds disk capacity")
                break

            # Calculate how much data fits in this sector
            remaining = len(program) - data_offset
            if remaining > 254:
                # More data follows
                bytes_in_sector = 254
                next_track = track
                next_sector = sector + 1
                if next_sector >= SECTORS_PER_TRACK[track - 1]:
                    next_track = track + 1
                    next_sector = 0
                    # Skip track 18
                    if next_track == 18:
                        next_track = 19
            else:
                # Last sector
                bytes_in_sector = remaining
                next_track = 0
                next_sector = bytes_in_sector + 1  # Bytes used indicator

            # Create sector data
            sector_data = bytearray(256)
            sector_data[0] = next_track
            sector_data[1] = next_sector
            sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

            # Write to disk
            offset = sector_offset(track, sector)
            disk[offset:offset + 256] = sector_data

            # Track usage
            used_sectors.append((track, sector))
            file_sectors.append((track, sector))

            # Move to next sector
            data_offset += bytes_in_sector
            sectors_written += 1

            if next_track != 0:
                track = next_track
                sector = next_sector

        # Create directory entry
        directory_entries.append((filename, file_sectors[0][0], file_sectors[0][1], sectors_written))
        print(f"  {filename}: {sectors_written} sectors across tracks {file_sectors[0][0]}-{file_sectors[-1][0]}")

    # Create and write BAM
    bam = create_bam("CROSS TRACK", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector
    dir_sector = bytearray(256)
    dir_sector[0] = 0  # No next directory sector
    dir_sector[1] = 0xFF

    for i, (filename, track, sector, size) in enumerate(directory_entries):
        entry_offset = i * 32

        # File type (PRG, closed)
        dir_sector[entry_offset + 2] = 0x82

        # First data track/sector
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector

        # Filename (16 chars, padded)
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0

        # File size in blocks
        dir_sector[entry_offset + 30] = size & 0xFF
        dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


def create_last_sector_test_disk():
    """Create disk with files that use the last sector in each zone.

    Each zone has a different number of sectors per track:
    - Zone 3 (tracks 1-17): 21 sectors (0-20), last = S20
    - Zone 2 (tracks 18-24): 19 sectors (0-18), last = S18
    - Zone 1 (tracks 25-30): 18 sectors (0-17), last = S17
    - Zone 0 (tracks 31-35): 17 sectors (0-16), last = S16

    Creates files that fill exactly one track in each zone (except Zone 3
    which is already tested in cross-track-test.d64 via SPAN1-2).
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    # File definitions: (name, track, num_sectors, last_sector, zone)
    # Each file fills exactly one track to ensure last sector is used
    files = [
        ("LASTZ2-T19", 19, 19, 18, 2),   # Zone 2: 19 sectors, last is S18
        ("LASTZ1-T25", 25, 18, 17, 1),   # Zone 1: 18 sectors, last is S17
        ("LASTZ0-T31", 31, 17, 16, 0),   # Zone 0: 17 sectors, last is S16
    ]

    for filename, track, num_sectors, last_sector, zone in files:
        # Create program data sized to fill the track
        program = create_multi_sector_program(num_sectors, filename)

        # Write file across all sectors on this track
        sector = 0
        data_offset = 0
        sectors_written = 0
        file_sectors = []

        while data_offset < len(program) and sector < num_sectors:
            # Calculate how much data fits in this sector
            remaining = len(program) - data_offset
            if remaining > 254:
                # More data follows
                bytes_in_sector = 254
                next_sector = sector + 1
                if next_sector >= num_sectors:
                    # End of track - this shouldn't happen if program sized correctly
                    next_track = 0
                    next_sector = bytes_in_sector + 1
                else:
                    next_track = track
            else:
                # Last sector
                bytes_in_sector = remaining
                next_track = 0
                next_sector = bytes_in_sector + 1

            # Create sector data
            sector_data = bytearray(256)
            sector_data[0] = next_track
            sector_data[1] = next_sector
            sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

            # Write to disk
            offset = sector_offset(track, sector)
            disk[offset:offset + 256] = sector_data

            # Track usage
            used_sectors.append((track, sector))
            file_sectors.append((track, sector))

            data_offset += bytes_in_sector
            sectors_written += 1
            sector += 1

        # Verify we used the last sector
        last_used = file_sectors[-1][1] if file_sectors else -1
        print(f"  {filename}: {sectors_written} sectors on track {track}, "
              f"last sector used: S{last_used} (expected S{last_sector})")

        directory_entries.append((filename, track, 0, sectors_written))

    # Create and write BAM
    bam = create_bam("LAST SECTOR", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector
    dir_sector = bytearray(256)
    dir_sector[0] = 0
    dir_sector[1] = 0xFF

    for i, (filename, track, sector, size) in enumerate(directory_entries):
        entry_offset = i * 32
        dir_sector[entry_offset + 2] = 0x82  # PRG, closed
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0
        dir_sector[entry_offset + 30] = size & 0xFF
        dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


def create_sector_chain_test_disk():
    """Create disk with files that have specific sector allocation patterns.

    Files:
    1. INTERLEAVE - Sectors allocated with interleave pattern (S0,S10,S20,S9...)
    2. WRAPAROUND - Sector chain wraps within track (S15,S16,S17,...,S20,S0,S1...)
    3. FRAGMENTED - Non-contiguous sectors across multiple tracks
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    # --- File 1: INTERLEAVE (standard 1541 interleave pattern) ---
    # Interleave 10: S0, S10, S20, S9, S19, S8, S18, S7, S17, S6, S16, S5, S15, S4, S14, S3, S13, S2, S12, S1, S11
    filename = "INTERLEAVE"
    track = 1
    num_sectors = 21
    interleave_order = []
    sector = 0
    for _ in range(num_sectors):
        interleave_order.append(sector)
        sector = (sector + 10) % num_sectors
        # Handle when we've visited all
        while sector in interleave_order and len(interleave_order) < num_sectors:
            sector = (sector + 1) % num_sectors

    program = create_multi_sector_program(num_sectors, filename)
    data_offset = 0
    file_sectors = []

    for i, sector in enumerate(interleave_order):
        remaining = len(program) - data_offset
        if remaining <= 0:
            break

        if remaining > 254:
            bytes_in_sector = 254
            if i + 1 < len(interleave_order):
                next_track = track
                next_sector = interleave_order[i + 1]
            else:
                next_track = 0
                next_sector = bytes_in_sector + 1
        else:
            bytes_in_sector = remaining
            next_track = 0
            next_sector = bytes_in_sector + 1

        sector_data = bytearray(256)
        sector_data[0] = next_track
        sector_data[1] = next_sector
        sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        file_sectors.append((track, sector))
        data_offset += bytes_in_sector

    print(f"  {filename}: {len(file_sectors)} sectors, chain: {[s for _, s in file_sectors[:10]]}...")
    directory_entries.append((filename, track, interleave_order[0], len(file_sectors)))

    # --- File 2: WRAPAROUND (starts at sector 15, wraps around) ---
    filename = "WRAPAROUND"
    track = 2
    num_sectors = 21
    start_sector = 15
    wraparound_order = [(start_sector + i) % num_sectors for i in range(num_sectors)]

    program = create_multi_sector_program(num_sectors, filename)
    data_offset = 0
    file_sectors = []

    for i, sector in enumerate(wraparound_order):
        remaining = len(program) - data_offset
        if remaining <= 0:
            break

        if remaining > 254:
            bytes_in_sector = 254
            if i + 1 < len(wraparound_order):
                next_track = track
                next_sector = wraparound_order[i + 1]
            else:
                next_track = 0
                next_sector = bytes_in_sector + 1
        else:
            bytes_in_sector = remaining
            next_track = 0
            next_sector = bytes_in_sector + 1

        sector_data = bytearray(256)
        sector_data[0] = next_track
        sector_data[1] = next_sector
        sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        file_sectors.append((track, sector))
        data_offset += bytes_in_sector

    print(f"  {filename}: {len(file_sectors)} sectors, chain: {[s for _, s in file_sectors]}")
    directory_entries.append((filename, track, start_sector, len(file_sectors)))

    # --- File 3: FRAGMENTED (scattered across multiple tracks) ---
    filename = "FRAGMENTED"
    # Use sectors scattered across tracks 3, 4, 5 in non-sequential order
    fragmented_sectors = [
        (3, 5), (4, 10), (5, 2), (3, 15), (4, 0), (5, 18),
        (3, 10), (4, 5), (5, 12), (3, 0), (4, 15), (5, 7),
    ]

    program = create_multi_sector_program(len(fragmented_sectors), filename)
    data_offset = 0
    file_sectors = []

    for i, (track, sector) in enumerate(fragmented_sectors):
        remaining = len(program) - data_offset
        if remaining <= 0:
            break

        if remaining > 254:
            bytes_in_sector = 254
            if i + 1 < len(fragmented_sectors):
                next_track, next_sector = fragmented_sectors[i + 1]
            else:
                next_track = 0
                next_sector = bytes_in_sector + 1
        else:
            bytes_in_sector = remaining
            next_track = 0
            next_sector = bytes_in_sector + 1

        sector_data = bytearray(256)
        sector_data[0] = next_track
        sector_data[1] = next_sector
        sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        file_sectors.append((track, sector))
        data_offset += bytes_in_sector

    print(f"  {filename}: {len(file_sectors)} sectors across tracks {sorted(set(t for t, s in file_sectors))}")
    directory_entries.append((filename, fragmented_sectors[0][0], fragmented_sectors[0][1], len(file_sectors)))

    # --- File 4: BACKWARD (includes backward track references) ---
    filename = "BACKWARD"
    # Chain goes: T6/S0 -> T5/S0 -> T4/S0 -> T6/S1 -> T5/S1 -> T4/S1 ...
    backward_sectors = []
    for s in range(7):  # 7 sectors per track group
        for t in [6, 5, 4]:  # Backward track order
            backward_sectors.append((t, s))

    program = create_multi_sector_program(len(backward_sectors), filename)
    data_offset = 0
    file_sectors = []

    for i, (track, sector) in enumerate(backward_sectors):
        remaining = len(program) - data_offset
        if remaining <= 0:
            break

        if remaining > 254:
            bytes_in_sector = 254
            if i + 1 < len(backward_sectors):
                next_track, next_sector = backward_sectors[i + 1]
            else:
                next_track = 0
                next_sector = bytes_in_sector + 1
        else:
            bytes_in_sector = remaining
            next_track = 0
            next_sector = bytes_in_sector + 1

        sector_data = bytearray(256)
        sector_data[0] = next_track
        sector_data[1] = next_sector
        sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        file_sectors.append((track, sector))
        data_offset += bytes_in_sector

    # Show track transitions
    transitions = []
    for i in range(1, len(file_sectors)):
        if file_sectors[i][0] != file_sectors[i-1][0]:
            transitions.append(f"T{file_sectors[i-1][0]}->T{file_sectors[i][0]}")
    print(f"  {filename}: {len(file_sectors)} sectors, transitions: {transitions[:5]}...")
    directory_entries.append((filename, backward_sectors[0][0], backward_sectors[0][1], len(file_sectors)))

    # Create and write BAM
    bam = create_bam("SECTOR CHAIN", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector
    dir_sector = bytearray(256)
    dir_sector[0] = 0
    dir_sector[1] = 0xFF

    for i, (filename, track, sector, size) in enumerate(directory_entries):
        entry_offset = i * 32
        dir_sector[entry_offset + 2] = 0x82
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0
        dir_sector[entry_offset + 30] = size & 0xFF
        dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


def create_file_size_test_disk():
    """Create disk with files of specific byte sizes for boundary testing.

    Files test boundaries around 254 bytes (sector data capacity):
    - SIZE-0: Empty file (0 bytes, just directory entry)
    - SIZE-1: 1 byte file
    - SIZE-254: Exactly 254 bytes (fills one sector's data area)
    - SIZE-255: 255 bytes (1 byte into second sector)
    - SIZE-256: 256 bytes (2 bytes into second sector)
    - TRACK-FILL: Fills exactly one Zone 3 track (21 sectors = 5334 bytes)
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    # Helper to create a program of exact size (after load address)
    def create_exact_size_program(size: int, identifier: str) -> bytes:
        """Create a minimal program of exactly the specified size."""
        if size == 0:
            return bytes([0x01, 0x08])  # Just load address

        # Load address (2 bytes) + content
        load_addr = 0x0801

        if size <= 10:
            # Very small: just load address + padding
            content = bytearray(size)
            for i in range(size):
                content[i] = 0x00
            return bytes([load_addr & 0xFF, (load_addr >> 8) & 0xFF]) + bytes(content)

        # Build a minimal BASIC program
        # Line 10: REM followed by padding to reach exact size
        # Structure: load_addr(2) + next_ptr(2) + line_num(2) + REM(1) + padding + null(1) + end(2)
        # Total overhead: 2 + 2 + 2 + 1 + 1 + 2 = 10 bytes

        overhead = 10
        padding_size = size - overhead
        if padding_size < 0:
            padding_size = 0

        next_line = load_addr + 2 + 2 + 1 + padding_size + 1  # After REM line
        padding = bytes([0x20] * padding_size)  # Space characters

        program = bytes([
            load_addr & 0xFF, (load_addr >> 8) & 0xFF,  # Load address
            next_line & 0xFF, (next_line >> 8) & 0xFF,  # Next line pointer
            0x0A, 0x00,  # Line number 10
            0x8F,  # REM token
        ]) + padding + bytes([
            0x00,  # End of line
            0x00, 0x00,  # End of program
        ])

        # Trim or pad to exact size (after load address)
        content = program[2:]  # Skip load address
        if len(content) > size:
            content = content[:size]
        elif len(content) < size:
            content = content + bytes([0x00] * (size - len(content)))

        return bytes([load_addr & 0xFF, (load_addr >> 8) & 0xFF]) + content

    # File definitions: (name, data_size, track, start_sector)
    # Note: data_size is program content AFTER the 2-byte load address
    # Each sector holds 254 bytes of file data (256 - 2 for track/sector link)
    # So total file bytes = data_size + 2 (load address)
    # - 252 content + 2 load addr = 254 total = exactly 1 sector
    # - 253 content + 2 load addr = 255 total = 2 sectors (1 byte overflow)
    # - 254 content + 2 load addr = 256 total = 2 sectors (2 bytes overflow)
    files = [
        ("SIZE-0", 0, 7, 0),        # 0 content bytes = 2 total (just load addr)
        ("SIZE-1", 1, 7, 1),        # 1 content byte = 3 total
        ("SIZE-252", 252, 7, 2),    # 252 content = 254 total = exactly 1 sector
        ("SIZE-253", 253, 7, 3),    # 253 content = 255 total = 2 sectors (1 byte overflow)
        ("SIZE-254", 254, 7, 5),    # 254 content = 256 total = 2 sectors (2 bytes overflow)
        ("TRACK-FILL", 21 * 254 - 2, 8, 0),  # Content to fill exactly 21 sectors
    ]

    for filename, data_size, start_track, start_sector in files:
        program = create_exact_size_program(data_size, filename)
        actual_size = len(program) - 2  # Subtract load address

        if data_size == 0:
            # Empty file - just a directory entry pointing to an empty sector
            sector_data = bytearray(256)
            sector_data[0] = 0  # No next sector
            sector_data[1] = 2  # 0 data bytes (just load address marker)

            offset = sector_offset(start_track, start_sector)
            disk[offset:offset + 256] = sector_data

            used_sectors.append((start_track, start_sector))
            directory_entries.append((filename, start_track, start_sector, 1))
            print(f"  {filename}: 0 bytes, 1 sector")
            continue

        # Write file data
        track = start_track
        sector = start_sector
        data_offset = 0
        sectors_written = 0
        file_sectors = []

        while data_offset < len(program):
            remaining = len(program) - data_offset

            if remaining > 254:
                bytes_in_sector = 254
                next_sector = sector + 1
                if next_sector >= SECTORS_PER_TRACK[track - 1]:
                    next_track = track + 1
                    next_sector = 0
                else:
                    next_track = track
            else:
                bytes_in_sector = remaining
                next_track = 0
                next_sector = bytes_in_sector + 1

            sector_data = bytearray(256)
            sector_data[0] = next_track
            sector_data[1] = next_sector
            sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

            offset = sector_offset(track, sector)
            disk[offset:offset + 256] = sector_data

            used_sectors.append((track, sector))
            file_sectors.append((track, sector))

            data_offset += bytes_in_sector
            sectors_written += 1

            if next_track != 0:
                track = next_track
                sector = next_sector

        directory_entries.append((filename, start_track, start_sector, sectors_written))
        print(f"  {filename}: {actual_size} bytes, {sectors_written} sectors")

    # Create and write BAM
    bam = create_bam("FILE SIZE", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector
    dir_sector = bytearray(256)
    dir_sector[0] = 0
    dir_sector[1] = 0xFF

    for i, (filename, track, sector, size) in enumerate(directory_entries):
        entry_offset = i * 32
        dir_sector[entry_offset + 2] = 0x82
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0
        dir_sector[entry_offset + 30] = size & 0xFF
        dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


def create_directory_edge_case_disk():
    """Create disk with directory edge cases.

    Tests:
    1. Multi-sector directory (>8 files, requires 2+ directory sectors)
    2. Deleted file entries ($00 file type)
    3. Various file positions in directory
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR), (DIR_TRACK, 2)]
    directory_entries = []

    # Create 12 files to span 2 directory sectors (8 per sector)
    # Plus 2 deleted entries to test directory parsing
    for i in range(12):
        filename = f"FILE-{i + 1:02d}"
        track = 1 + (i % 8)
        sector = i // 8

        # Create a proper BASIC program with actual content
        # 10 REM FILE-XX
        load_addr = 0x0801
        file_id = f"FILE-{i + 1:02d}"
        line_content = bytes([0x8F, 0x20]) + file_id.encode('ascii') + bytes([0x00])
        next_line = load_addr + 2 + 2 + len(line_content)
        program = bytes([
            load_addr & 0xFF, (load_addr >> 8) & 0xFF,  # Load address
            next_line & 0xFF, (next_line >> 8) & 0xFF,  # Next line ptr
            0x0A, 0x00,  # Line number 10
        ]) + line_content + bytes([
            0x00, 0x00,  # End of program
        ])

        # Create sector data
        sector_data = bytearray(256)
        sector_data[0] = 0  # Last sector
        sector_data[1] = len(program) + 1
        sector_data[2:2 + len(program)] = program

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        # Mark some files as deleted (file type $00)
        if i == 4 or i == 9:  # FILE-05 and FILE-10 will be deleted
            directory_entries.append((filename, track, sector, 1, True))  # deleted=True
            print(f"  {filename}: DELETED")
        else:
            directory_entries.append((filename, track, sector, 1, False))
            print(f"  {filename}: active")

    # Create and write BAM
    bam = create_bam("DIR EDGE CASE", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create first directory sector (entries 0-7)
    dir_sector1 = bytearray(256)
    dir_sector1[0] = DIR_TRACK  # Next directory sector
    dir_sector1[1] = 2  # Sector 2

    for i, (filename, track, sector, size, deleted) in enumerate(directory_entries[:8]):
        entry_offset = i * 32
        if deleted:
            dir_sector1[entry_offset + 2] = 0x00  # Deleted file type
        else:
            dir_sector1[entry_offset + 2] = 0x82  # PRG, closed
        dir_sector1[entry_offset + 3] = track
        dir_sector1[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector1[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector1[entry_offset + 5 + j] = 0xA0
        dir_sector1[entry_offset + 30] = size & 0xFF
        dir_sector1[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector1

    # Create second directory sector (entries 8-11)
    dir_sector2 = bytearray(256)
    dir_sector2[0] = 0  # No more directory sectors
    dir_sector2[1] = 0xFF

    for i, (filename, track, sector, size, deleted) in enumerate(directory_entries[8:]):
        entry_offset = i * 32
        if deleted:
            dir_sector2[entry_offset + 2] = 0x00  # Deleted file type
        else:
            dir_sector2[entry_offset + 2] = 0x82  # PRG, closed
        dir_sector2[entry_offset + 3] = track
        dir_sector2[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector2[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector2[entry_offset + 5 + j] = 0xA0
        dir_sector2[entry_offset + 30] = size & 0xFF
        dir_sector2[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, 2):sector_offset(DIR_TRACK, 2) + 256] = dir_sector2

    return bytes(disk)


def create_wildcard_test_disk():
    """Create disk with files for testing wildcard and load mode operations.

    Files:
    1. FIRST - First file in directory (for LOAD"*",8 test)
    2. TEST-A - File with TEST prefix (for pattern matching)
    3. TEST-B - Another TEST file (for pattern matching)
    4. OTHER - Non-TEST file
    5. HIGHLOAD - File with load address $C000 (for ,8,1 test)
    6. MAXFILENAME1234 - 16-char filename (maximum length)
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    def create_program_with_load_addr(load_addr: int, identifier: str) -> bytes:
        """Create a program that loads at the specified address."""
        # Build a minimal BASIC program
        # Line 10: REM <identifier>
        line_content = bytes([
            0x8F,  # REM token
            0x20,  # space
        ]) + identifier.encode('ascii') + bytes([
            0x00,  # end of line
        ])

        next_line = load_addr + 2 + 2 + len(line_content)

        program = bytes([
            load_addr & 0xFF, (load_addr >> 8) & 0xFF,  # Load address
            next_line & 0xFF, (next_line >> 8) & 0xFF,  # Pointer to next line
            0x0A, 0x00,  # Line number 10
        ]) + line_content + bytes([
            0x00, 0x00,  # End of program
        ])

        return program

    # File definitions: (name, load_addr, track, sector, content_identifier)
    files = [
        ("FIRST", 0x0801, 1, 0, "FIRST FILE"),
        ("TEST-A", 0x0801, 1, 1, "TEST-A"),
        ("TEST-B", 0x0801, 1, 2, "TEST-B"),
        ("OTHER", 0x0801, 1, 3, "OTHER FILE"),
        ("HIGHLOAD", 0xC000, 1, 4, "HIGH MEMORY"),  # Load to $C000
        ("MAXFILENAME1234", 0x0801, 1, 5, "MAX NAME"),  # 16 chars
    ]

    for filename, load_addr, track, sector, identifier in files:
        program = create_program_with_load_addr(load_addr, identifier)

        # Create sector data
        sector_data = bytearray(256)
        sector_data[0] = 0  # Last sector
        sector_data[1] = len(program) + 1  # Bytes used
        sector_data[2:2 + len(program)] = program

        # Write to disk
        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        directory_entries.append((filename, track, sector, 1))
        print(f"  {filename}: load addr ${load_addr:04X}")

    # Create and write BAM
    bam = create_bam("WILDCARD TEST", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector
    dir_sector = bytearray(256)
    dir_sector[0] = 0
    dir_sector[1] = 0xFF

    for i, (filename, track, sector, size) in enumerate(directory_entries):
        entry_offset = i * 32
        dir_sector[entry_offset + 2] = 0x82  # PRG, closed
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0
        dir_sector[entry_offset + 30] = size & 0xFF
        dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


def create_multi_zone_span_disk():
    """Create disk with files spanning multiple zone boundaries.

    Files:
    1. SPAN-3ZONES: Spans Zone 3 -> Zone 2 -> Zone 1 (tracks 17, 19-25)
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    # SPAN-3ZONES: Start on track 17 (Zone 3), cross into Zone 2, then Zone 1
    # Track 17: 21 sectors (Zone 3)
    # Track 18: Skip (directory)
    # Track 19-24: 19 sectors each (Zone 2)
    # Track 25: 18 sectors (Zone 1)
    # Total: 21 + 19*6 + 10 = 21 + 114 + 10 = 145 sectors (we'll use ~80)

    filename = "SPAN-3ZONES"
    # Track 17: 21 sectors (Zone 3)
    # Track 19-24: 19 * 6 = 114 sectors (Zone 2)
    # We need to reach track 25+ (Zone 1), so need 21 + 114 + some = 135+ sectors
    num_sectors = 150  # Enough to span Zone 3 -> Zone 2 -> Zone 1

    program = create_multi_sector_program(num_sectors, filename)

    track = 17
    sector = 0
    data_offset = 0
    file_sectors = []

    while data_offset < len(program):
        # Skip track 18
        if track == 18:
            track = 19
            sector = 0

        if track > 35:
            break

        remaining = len(program) - data_offset

        if remaining > 254:
            bytes_in_sector = 254
            next_sector = sector + 1
            if next_sector >= SECTORS_PER_TRACK[track - 1]:
                next_track = track + 1
                next_sector = 0
                if next_track == 18:
                    next_track = 19
            else:
                next_track = track
        else:
            bytes_in_sector = remaining
            next_track = 0
            next_sector = bytes_in_sector + 1

        sector_data = bytearray(256)
        sector_data[0] = next_track
        sector_data[1] = next_sector
        sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        file_sectors.append((track, sector))

        data_offset += bytes_in_sector

        if next_track != 0:
            track = next_track
            sector = next_sector

    # Analyze zones used
    zones_used = set()
    for t, s in file_sectors:
        if t <= 17:
            zones_used.add(3)
        elif t <= 24:
            zones_used.add(2)
        elif t <= 30:
            zones_used.add(1)
        else:
            zones_used.add(0)

    print(f"  {filename}: {len(file_sectors)} sectors, zones: {sorted(zones_used, reverse=True)}")
    print(f"    Tracks: {file_sectors[0][0]} to {file_sectors[-1][0]}")

    directory_entries.append((filename, 17, 0, len(file_sectors)))

    # Create and write BAM
    bam = create_bam("MULTI ZONE", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector
    dir_sector = bytearray(256)
    dir_sector[0] = 0
    dir_sector[1] = 0xFF

    for i, (filename, track, sector, size) in enumerate(directory_entries):
        entry_offset = i * 32
        dir_sector[entry_offset + 2] = 0x82
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0
        dir_sector[entry_offset + 30] = size & 0xFF
        dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


# Create and save
print("Creating debug disk image...")
disk_data = create_debug_disk()

output_path = Path("tests/fixtures/c64/disks/simple-zone-test.d64")
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_bytes(disk_data)
print(f"Saved to: {output_path}")
print(f"Size: {len(disk_data)} bytes")

# Verify
import sys
sys.path.insert(0, 'systems/c64')
from systems.c64.drive.d64 import D64Image

print("\nVerifying disk image...")
disk = D64Image(output_path)

print(f"Disk name: {disk.get_disk_name()}")

print("\nDirectory:")
for entry in disk.read_directory():
    print(f"  {entry}")

print("\nFile locations:")
for entry in disk.read_directory():
    print(f"  {entry.filename}: Track {entry.track}, Sector {entry.sector}")

# Show first data byte of each file
print("\nFirst bytes of each file:")
for track in [1, 17, 19, 24, 25, 30, 31, 35]:
    sector_data = disk.read_sector(track, 0)
    print(f"  Track {track:2d}: {' '.join(f'{b:02X}' for b in sector_data[:16])}")

# Create cross-track test disk
print("\n" + "=" * 60)
print("Creating cross-track test disk...")
cross_track_data = create_cross_track_disk()

cross_track_path = Path("tests/fixtures/c64/disks/cross-track-test.d64")
cross_track_path.write_bytes(cross_track_data)
print(f"Saved to: {cross_track_path}")
print(f"Size: {len(cross_track_data)} bytes")

print("\nVerifying cross-track disk...")
cross_disk = D64Image(cross_track_path)
print(f"Disk name: {cross_disk.get_disk_name()}")

print("\nDirectory:")
for entry in cross_disk.read_directory():
    print(f"  {entry}")

print("\nFile sector chains:")
for entry in cross_disk.read_directory():
    print(f"\n  {entry.filename}:")
    track = entry.track
    sector = entry.sector
    tracks_used = {}
    total = 0

    while track != 0 and total < 100:
        if track not in tracks_used:
            tracks_used[track] = []
        tracks_used[track].append(sector)
        total += 1

        data = cross_disk.read_sector(track, sector)
        track = data[0]
        sector = data[1]

    for t in sorted(tracks_used.keys()):
        zone = cross_disk.get_speed_zone(t)
        print(f"    Track {t:2d} (Zone {zone}): {len(tracks_used[t])} sectors")

# Create last-sector test disk
print("\n" + "=" * 60)
print("Creating last-sector test disk...")
last_sector_data = create_last_sector_test_disk()

last_sector_path = Path("tests/fixtures/c64/disks/last-sector-test.d64")
last_sector_path.write_bytes(last_sector_data)
print(f"Saved to: {last_sector_path}")

print("\nVerifying last-sector disk...")
last_sector_disk = D64Image(last_sector_path)
print(f"Disk name: {last_sector_disk.get_disk_name()}")
print("\nDirectory:")
for entry in last_sector_disk.read_directory():
    print(f"  {entry}")

# Create sector-chain test disk
print("\n" + "=" * 60)
print("Creating sector-chain test disk...")
sector_chain_data = create_sector_chain_test_disk()

sector_chain_path = Path("tests/fixtures/c64/disks/sector-chain-test.d64")
sector_chain_path.write_bytes(sector_chain_data)
print(f"Saved to: {sector_chain_path}")

print("\nVerifying sector-chain disk...")
sector_chain_disk = D64Image(sector_chain_path)
print(f"Disk name: {sector_chain_disk.get_disk_name()}")
print("\nDirectory:")
for entry in sector_chain_disk.read_directory():
    print(f"  {entry}")

# Create file-size test disk
print("\n" + "=" * 60)
print("Creating file-size test disk...")
file_size_data = create_file_size_test_disk()

file_size_path = Path("tests/fixtures/c64/disks/file-size-test.d64")
file_size_path.write_bytes(file_size_data)
print(f"Saved to: {file_size_path}")

print("\nVerifying file-size disk...")
file_size_disk = D64Image(file_size_path)
print(f"Disk name: {file_size_disk.get_disk_name()}")
print("\nDirectory:")
for entry in file_size_disk.read_directory():
    print(f"  {entry}")

# Create multi-zone span test disk
print("\n" + "=" * 60)
print("Creating multi-zone span test disk...")
multi_zone_data = create_multi_zone_span_disk()

multi_zone_path = Path("tests/fixtures/c64/disks/multi-zone-span.d64")
multi_zone_path.write_bytes(multi_zone_data)
print(f"Saved to: {multi_zone_path}")

print("\nVerifying multi-zone disk...")
multi_zone_disk = D64Image(multi_zone_path)
print(f"Disk name: {multi_zone_disk.get_disk_name()}")
print("\nDirectory:")
for entry in multi_zone_disk.read_directory():
    print(f"  {entry}")

# Create directory edge case test disk
print("\n" + "=" * 60)
print("Creating directory edge case test disk...")
dir_edge_data = create_directory_edge_case_disk()

dir_edge_path = Path("tests/fixtures/c64/disks/directory-edge-test.d64")
dir_edge_path.write_bytes(dir_edge_data)
print(f"Saved to: {dir_edge_path}")

print("\nVerifying directory edge case disk...")
dir_edge_disk = D64Image(dir_edge_path)
print(f"Disk name: {dir_edge_disk.get_disk_name()}")
print("\nDirectory:")
for entry in dir_edge_disk.read_directory():
    print(f"  {entry}")

# Create wildcard test disk
print("\n" + "=" * 60)
print("Creating wildcard test disk...")
wildcard_data = create_wildcard_test_disk()

wildcard_path = Path("tests/fixtures/c64/disks/wildcard-test.d64")
wildcard_path.write_bytes(wildcard_data)
print(f"Saved to: {wildcard_path}")

print("\nVerifying wildcard disk...")
wildcard_disk = D64Image(wildcard_path)
print(f"Disk name: {wildcard_disk.get_disk_name()}")
print("\nDirectory:")
for entry in wildcard_disk.read_directory():
    print(f"  {entry}")

def create_full_disk():
    """Create a completely full disk (0 blocks free).

    Tests that the emulator handles disks with no free space.
    Creates a file that fills BASIC memory ($0801-$A000 = ~153 sectors),
    plus additional dummy files to use all remaining disk sectors.
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    # Calculate total usable sectors (excluding track 18)
    total_usable = sum(SECTORS_PER_TRACK[:17]) + sum(SECTORS_PER_TRACK[18:])

    # BASIC memory limit: $0801 to $A000 = 38911 bytes
    # Each sector holds 254 bytes, so max ~153 sectors for a loadable file
    max_basic_sectors = 153

    filename = "FULLFILE"
    target_sectors = max_basic_sectors

    program = create_multi_sector_program(target_sectors, filename)

    # Allocate all available sectors
    track = 1
    sector = 0
    data_offset = 0
    file_sectors = []

    while data_offset < len(program):
        if track == 18:
            track = 19
            sector = 0

        if track > 35:
            break

        remaining = len(program) - data_offset

        if remaining > 254:
            bytes_in_sector = 254
            next_sector = sector + 1
            if next_sector >= SECTORS_PER_TRACK[track - 1]:
                next_track = track + 1
                next_sector = 0
                if next_track == 18:
                    next_track = 19
            else:
                next_track = track
        else:
            bytes_in_sector = remaining
            next_track = 0
            next_sector = bytes_in_sector + 1

        sector_data = bytearray(256)
        sector_data[0] = next_track
        sector_data[1] = next_sector
        sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        file_sectors.append((track, sector))

        data_offset += bytes_in_sector

        if next_track != 0:
            track = next_track
            sector = next_sector

    print(f"  {filename}: {len(file_sectors)} sectors used")
    directory_entries.append((filename, 1, 0, len(file_sectors)))

    # Fill remaining sectors with dummy data to make disk completely full
    # Advance past the last used sector to the next free one
    sector += 1
    if sector >= SECTORS_PER_TRACK[track - 1]:
        track += 1
        sector = 0

    dummy_sectors = []
    while True:
        if track == 18:
            track = 19
            sector = 0

        if track > 35:
            break

        # Write dummy sector (just zeros with end-of-chain marker)
        sector_data = bytearray(256)
        sector_data[0] = 0  # End of chain
        sector_data[1] = 0xFF  # No more data

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        dummy_sectors.append((track, sector))

        # Move to next sector
        sector += 1
        if sector >= SECTORS_PER_TRACK[track - 1]:
            track += 1
            sector = 0

    print(f"  DUMMY: {len(dummy_sectors)} sectors filled (disk now full)")

    # Create and write BAM
    bam = create_bam("FULL DISK", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector (only FULLFILE entry - dummy sectors aren't files)
    dir_sector = bytearray(256)
    dir_sector[0] = 0
    dir_sector[1] = 0xFF

    for i, (filename, track, sector, size) in enumerate(directory_entries):
        entry_offset = i * 32
        dir_sector[entry_offset + 2] = 0x82
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0
        dir_sector[entry_offset + 30] = size & 0xFF
        dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


def create_overflow_disk():
    """Create a disk with a file that overflows BASIC memory.

    Creates a 154-sector file that exceeds the BASIC memory limit ($0801-$A000).
    This should cause the load to fail or corrupt memory when loaded.
    Used as a negative test to verify expected failure behavior.
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    # 154 sectors = 1 more than fits in BASIC memory
    overflow_sectors = 154

    filename = "OVERFLOW"
    program = create_multi_sector_program(overflow_sectors, filename)

    # Allocate sectors for the file
    track = 1
    sector = 0
    data_offset = 0
    file_sectors = []

    while data_offset < len(program):
        if track == 18:
            track = 19
            sector = 0

        if track > 35:
            break

        remaining = len(program) - data_offset

        if remaining > 254:
            bytes_in_sector = 254
            next_sector = sector + 1
            if next_sector >= SECTORS_PER_TRACK[track - 1]:
                next_track = track + 1
                next_sector = 0
                if next_track == 18:
                    next_track = 19
            else:
                next_track = track
        else:
            bytes_in_sector = remaining
            next_track = 0
            next_sector = bytes_in_sector + 1

        sector_data = bytearray(256)
        sector_data[0] = next_track
        sector_data[1] = next_sector
        sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        file_sectors.append((track, sector))

        data_offset += bytes_in_sector

        if next_track != 0:
            track = next_track
            sector = next_sector

    print(f"  {filename}: {len(file_sectors)} sectors (exceeds BASIC memory limit)")
    directory_entries.append((filename, 1, 0, len(file_sectors)))

    # Create and write BAM
    bam = create_bam("OVERFLOW TEST", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector
    dir_sector = bytearray(256)
    dir_sector[0] = 0
    dir_sector[1] = 0xFF

    for i, (filename, track, sector, size) in enumerate(directory_entries):
        entry_offset = i * 32
        dir_sector[entry_offset + 2] = 0x82
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0
        dir_sector[entry_offset + 30] = size & 0xFF
        dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


def create_max_directory_disk():
    """Create a disk with maximum 144 directory entries.

    Tests that the emulator can handle a full directory.
    144 files = 18 directory sectors (8 entries per sector).
    """
    disk = bytearray(D64_SIZE)

    # We need 18 directory sectors on track 18
    dir_sectors_needed = 18
    used_sectors = [(BAM_TRACK, BAM_SECTOR)]

    # Mark directory sectors as used
    for s in range(1, dir_sectors_needed + 1):
        used_sectors.append((DIR_TRACK, s))

    directory_entries = []

    # Create 144 small files
    # Each file will be 1 sector, placed on tracks 1-17 and 19-35
    file_track = 1
    file_sector = 0

    for i in range(144):
        filename = f"F{i + 1:03d}"

        # Skip to next available sector
        if file_track == 18:
            file_track = 19
            file_sector = 0

        if file_sector >= SECTORS_PER_TRACK[file_track - 1]:
            file_track += 1
            file_sector = 0
            if file_track == 18:
                file_track = 19

        if file_track > 35:
            print(f"  Warning: Not enough sectors for all 144 files")
            break

        # Create minimal program
        load_addr = 0x0801
        file_id = f"FILE {i + 1:03d}"
        line_content = bytes([0x8F, 0x20]) + file_id.encode('ascii') + bytes([0x00])
        next_line = load_addr + 2 + 2 + len(line_content)
        program = bytes([
            load_addr & 0xFF, (load_addr >> 8) & 0xFF,
            next_line & 0xFF, (next_line >> 8) & 0xFF,
            0x0A, 0x00,
        ]) + line_content + bytes([0x00, 0x00])

        # Create sector data
        sector_data = bytearray(256)
        sector_data[0] = 0
        sector_data[1] = len(program) + 1
        sector_data[2:2 + len(program)] = program

        offset = sector_offset(file_track, file_sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((file_track, file_sector))
        directory_entries.append((filename, file_track, file_sector, 1))

        file_sector += 1

    print(f"  Created {len(directory_entries)} files (max 144)")

    # Create and write BAM
    bam = create_bam("MAX DIRECTORY", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sectors (18 sectors, 8 entries each)
    entries_per_sector = 8
    for dir_sec_num in range(dir_sectors_needed):
        dir_sector = bytearray(256)

        # Link to next directory sector
        if dir_sec_num < dir_sectors_needed - 1:
            dir_sector[0] = DIR_TRACK
            dir_sector[1] = dir_sec_num + 2  # Next sector
        else:
            dir_sector[0] = 0
            dir_sector[1] = 0xFF

        # Fill entries for this sector
        start_entry = dir_sec_num * entries_per_sector
        end_entry = min(start_entry + entries_per_sector, len(directory_entries))

        for i, entry_idx in enumerate(range(start_entry, end_entry)):
            filename, track, sector, size = directory_entries[entry_idx]
            entry_offset = i * 32
            dir_sector[entry_offset + 2] = 0x82
            dir_sector[entry_offset + 3] = track
            dir_sector[entry_offset + 4] = sector
            name = filename.upper().encode('ascii')[:16]
            for j, b in enumerate(name):
                dir_sector[entry_offset + 5 + j] = b
            for j in range(len(name), 16):
                dir_sector[entry_offset + 5 + j] = 0xA0
            dir_sector[entry_offset + 30] = size & 0xFF
            dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

        offset = sector_offset(DIR_TRACK, dir_sec_num + 1)
        disk[offset:offset + 256] = dir_sector

    return bytes(disk)


def create_reverse_zone_span_disk():
    """Create a disk with a file that spans zones in reverse order.

    Tests that the emulator handles backward zone transitions correctly.
    File starts on track 25 (Zone 1) and jumps back to track 24 (Zone 2).
    """
    disk = bytearray(D64_SIZE)

    used_sectors = [(BAM_TRACK, BAM_SECTOR), (DIR_TRACK, DIR_SECTOR)]
    directory_entries = []

    filename = "REVERSE"

    # Create sector chain that goes from Zone 1 back to Zone 2
    # T25 (Zone 1) -> T24 (Zone 2) -> T23 (Zone 2) etc.
    reverse_sectors = []

    # Start with some sectors on track 25 (Zone 1, 18 sectors)
    for s in range(10):
        reverse_sectors.append((25, s))

    # Jump back to track 24 (Zone 2, 19 sectors)
    for s in range(19):
        reverse_sectors.append((24, s))

    # Then track 23
    for s in range(10):
        reverse_sectors.append((23, s))

    program = create_multi_sector_program(len(reverse_sectors), filename)
    data_offset = 0
    file_sectors = []

    for i, (track, sector) in enumerate(reverse_sectors):
        remaining = len(program) - data_offset
        if remaining <= 0:
            break

        if remaining > 254:
            bytes_in_sector = 254
            if i + 1 < len(reverse_sectors):
                next_track, next_sector = reverse_sectors[i + 1]
            else:
                next_track = 0
                next_sector = bytes_in_sector + 1
        else:
            bytes_in_sector = remaining
            next_track = 0
            next_sector = bytes_in_sector + 1

        sector_data = bytearray(256)
        sector_data[0] = next_track
        sector_data[1] = next_sector
        sector_data[2:2 + bytes_in_sector] = program[data_offset:data_offset + bytes_in_sector]

        offset = sector_offset(track, sector)
        disk[offset:offset + 256] = sector_data

        used_sectors.append((track, sector))
        file_sectors.append((track, sector))
        data_offset += bytes_in_sector

    # Show zone transitions
    transitions = []
    for i in range(1, len(file_sectors)):
        prev_track = file_sectors[i - 1][0]
        curr_track = file_sectors[i][0]
        if prev_track != curr_track:
            prev_zone = 1 if prev_track <= 30 else 0
            if prev_track <= 24:
                prev_zone = 2
            if prev_track <= 17:
                prev_zone = 3
            curr_zone = 1 if curr_track <= 30 else 0
            if curr_track <= 24:
                curr_zone = 2
            if curr_track <= 17:
                curr_zone = 3
            if prev_zone != curr_zone:
                transitions.append(f"T{prev_track}(Z{prev_zone})->T{curr_track}(Z{curr_zone})")

    print(f"  {filename}: {len(file_sectors)} sectors")
    print(f"    Zone transitions: {transitions}")

    directory_entries.append((filename, reverse_sectors[0][0], reverse_sectors[0][1], len(file_sectors)))

    # Create and write BAM
    bam = create_bam("REVERSE ZONE", used_sectors)
    disk[sector_offset(BAM_TRACK, BAM_SECTOR):sector_offset(BAM_TRACK, BAM_SECTOR) + 256] = bam

    # Create directory sector
    dir_sector = bytearray(256)
    dir_sector[0] = 0
    dir_sector[1] = 0xFF

    for i, (filename, track, sector, size) in enumerate(directory_entries):
        entry_offset = i * 32
        dir_sector[entry_offset + 2] = 0x82
        dir_sector[entry_offset + 3] = track
        dir_sector[entry_offset + 4] = sector
        name = filename.upper().encode('ascii')[:16]
        for j, b in enumerate(name):
            dir_sector[entry_offset + 5 + j] = b
        for j in range(len(name), 16):
            dir_sector[entry_offset + 5 + j] = 0xA0
        dir_sector[entry_offset + 30] = size & 0xFF
        dir_sector[entry_offset + 31] = (size >> 8) & 0xFF

    disk[sector_offset(DIR_TRACK, DIR_SECTOR):sector_offset(DIR_TRACK, DIR_SECTOR) + 256] = dir_sector

    return bytes(disk)


# Create full disk
print("\n" + "=" * 60)
print("Creating full disk (0 blocks free)...")
full_data = create_full_disk()

full_path = Path("tests/fixtures/c64/disks/full-disk.d64")
full_path.write_bytes(full_data)
print(f"Saved to: {full_path}")

print("\nVerifying full disk...")
full_disk = D64Image(full_path)
print(f"Disk name: {full_disk.get_disk_name()}")
print("\nDirectory:")
for entry in full_disk.read_directory():
    print(f"  {entry}")

# Create overflow disk (negative test)
print("\n" + "=" * 60)
print("Creating overflow disk (154 sectors - exceeds BASIC memory)...")
overflow_data = create_overflow_disk()

overflow_path = Path("tests/fixtures/c64/disks/overflow-test.d64")
overflow_path.write_bytes(overflow_data)
print(f"Saved to: {overflow_path}")

print("\nVerifying overflow disk...")
overflow_disk = D64Image(overflow_path)
print(f"Disk name: {overflow_disk.get_disk_name()}")
print("\nDirectory:")
for entry in overflow_disk.read_directory():
    print(f"  {entry}")

# Create max directory disk
print("\n" + "=" * 60)
print("Creating max directory disk (144 files)...")
max_dir_data = create_max_directory_disk()

max_dir_path = Path("tests/fixtures/c64/disks/max-directory.d64")
max_dir_path.write_bytes(max_dir_data)
print(f"Saved to: {max_dir_path}")

print("\nVerifying max directory disk...")
max_dir_disk = D64Image(max_dir_path)
print(f"Disk name: {max_dir_disk.get_disk_name()}")
print(f"\nDirectory (first 5 and last 5 entries):")
entries = list(max_dir_disk.read_directory())
for entry in entries[:5]:
    print(f"  {entry}")
print("  ...")
for entry in entries[-5:]:
    print(f"  {entry}")
print(f"Total entries: {len(entries)}")

# Create reverse zone span disk
print("\n" + "=" * 60)
print("Creating reverse zone span disk...")
reverse_data = create_reverse_zone_span_disk()

reverse_path = Path("tests/fixtures/c64/disks/reverse-zone-span.d64")
reverse_path.write_bytes(reverse_data)
print(f"Saved to: {reverse_path}")

print("\nVerifying reverse zone disk...")
reverse_disk = D64Image(reverse_path)
print(f"Disk name: {reverse_disk.get_disk_name()}")
print("\nDirectory:")
for entry in reverse_disk.read_directory():
    print(f"  {entry}")

print("\n" + "=" * 60)
print("All test disks created successfully!")
