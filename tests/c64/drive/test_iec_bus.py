"""Tests for IEC Serial Bus emulation.

The IEC bus connects the C64 to disk drives using open-collector logic.
All lines are active-low: any device can pull a line low, and lines
go high only when all devices release them.
"""

import pytest
from unittest.mock import Mock, MagicMock
from systems.c64.drive.iec_bus import IECBus
from systems.c64.drive.via6522 import VIA6522
from systems.c64.drive.drive1541 import Drive1541


class MockCIA2:
    """Mock CIA2 for testing IEC bus."""

    def __init__(self):
        self.port_a = 0x00  # All bits low (outputs driving bus low)
        self.ddr_a = 0x3F   # Lower 6 bits output (default C64 setting)


class TestIECBusBasic:
    """Test basic IEC bus functionality."""

    def test_initial_state(self):
        """Bus starts with all lines high (released)."""
        bus = IECBus()
        assert bus.atn is True
        assert bus.clk is True
        assert bus.data is True

    def test_connect_c64(self):
        """C64 can be connected to bus."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)
        assert bus.cia2 is cia2

    def test_connect_drive(self):
        """Drive can be connected to bus."""
        bus = IECBus()
        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)
        assert drive in bus.drives

    def test_disconnect_drive(self):
        """Drive can be disconnected from bus."""
        bus = IECBus()
        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)
        bus.disconnect_drive(drive)
        assert drive not in bus.drives


class TestIECBusC64Output:
    """Test C64 output on IEC bus."""

    def test_c64_atn_output(self):
        """C64 can assert ATN line."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        # ATN OUT is bit 3, inverted: port bit 1 -> bus LOW
        cia2.port_a = 0x08  # Bit 3 set (ATN OUT driving bus LOW)
        cia2.ddr_a = 0x3F   # Bits 0-5 are outputs

        bus.update()
        assert bus.atn is False  # ATN asserted (low)

    def test_c64_atn_released(self):
        """C64 can release ATN line."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        # ATN OUT is bit 3: port bit 0 -> bus released (HIGH)
        cia2.port_a = 0x00  # Bit 3 clear (ATN OUT releasing bus)
        cia2.ddr_a = 0x3F

        bus.update()
        assert bus.atn is True  # ATN released (high)

    def test_c64_clk_output(self):
        """C64 can drive CLK line."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        # CLK OUT is bit 4, inverted: port bit 1 -> bus LOW
        cia2.port_a = 0x10  # Bit 4 set
        cia2.ddr_a = 0x3F

        bus.update()
        assert bus.clk is False  # CLK asserted (low)

    def test_c64_data_output(self):
        """C64 can drive DATA line."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        # DATA OUT is bit 5, inverted
        cia2.port_a = 0x20  # Bit 5 set
        cia2.ddr_a = 0x3F

        bus.update()
        assert bus.data is False  # DATA asserted (low)


class TestIECBusDriveOutput:
    """Test drive output on IEC bus."""

    def test_drive_clk_output(self):
        """Drive can drive CLK line."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # C64 releases CLK (bit 4 = 0)
        cia2.port_a = 0x00
        cia2.ddr_a = 0x3F

        # Drive asserts CLK (VIA1 PB3 = 1, inverted)
        drive.via1.ddrb = 0x08  # Bit 3 output
        drive.via1.orb = 0x08   # Bit 3 set (driving bus LOW)

        bus.update()
        assert bus.clk is False  # CLK pulled low by drive

    def test_drive_data_output(self):
        """Drive can drive DATA line."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # C64 releases DATA (bit 5 = 0)
        cia2.port_a = 0x00
        cia2.ddr_a = 0x3F

        # Drive asserts DATA (VIA1 PB1 = 1, inverted)
        drive.via1.ddrb = 0x02  # Bit 1 output
        drive.via1.orb = 0x02   # Bit 1 set (driving bus LOW)

        bus.update()
        assert bus.data is False  # DATA pulled low by drive


class TestIECBusOpenCollector:
    """Test open-collector logic on IEC bus."""

    def test_line_high_when_all_release(self):
        """Line goes high only when all devices release."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # Both C64 and drive release DATA
        cia2.port_a = 0x00
        cia2.ddr_a = 0x3F
        drive.via1.ddrb = 0x02
        drive.via1.orb = 0x00  # Not driving

        bus.update()
        assert bus.data is True

    def test_line_low_when_c64_pulls(self):
        """Line is low when C64 pulls, regardless of drive."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # C64 pulls DATA low, drive releases
        cia2.port_a = 0x20  # DATA OUT set
        cia2.ddr_a = 0x3F
        drive.via1.ddrb = 0x02
        drive.via1.orb = 0x00

        bus.update()
        assert bus.data is False

    def test_line_low_when_drive_pulls(self):
        """Line is low when drive pulls, regardless of C64."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # C64 releases DATA, drive pulls
        cia2.port_a = 0x00
        cia2.ddr_a = 0x3F
        drive.via1.ddrb = 0x02
        drive.via1.orb = 0x02

        bus.update()
        assert bus.data is False

    def test_line_low_when_both_pull(self):
        """Line is low when both C64 and drive pull."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # Both pull DATA low
        cia2.port_a = 0x20
        cia2.ddr_a = 0x3F
        drive.via1.ddrb = 0x02
        drive.via1.orb = 0x02

        bus.update()
        assert bus.data is False


class TestIECBusC64Input:
    """Test C64 reading bus state."""

    def test_c64_reads_clk_high(self):
        """C64 reads CLK=1 when line is high."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        # All lines released
        cia2.port_a = 0x00
        cia2.ddr_a = 0x3F
        bus.update()

        input_value = bus.get_c64_input()
        assert input_value & 0x40  # CLK IN (bit 6) is high

    def test_c64_reads_clk_low(self):
        """C64 reads CLK=0 when line is low."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # Drive pulls CLK low
        cia2.port_a = 0x00
        cia2.ddr_a = 0x3F
        drive.via1.ddrb = 0x08
        drive.via1.orb = 0x08
        bus.update()

        input_value = bus.get_c64_input()
        assert not (input_value & 0x40)  # CLK IN (bit 6) is low

    def test_c64_reads_data_high(self):
        """C64 reads DATA=1 when line is high."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        cia2.port_a = 0x00
        cia2.ddr_a = 0x3F
        bus.update()

        input_value = bus.get_c64_input()
        assert input_value & 0x80  # DATA IN (bit 7) is high

    def test_c64_reads_data_low(self):
        """C64 reads DATA=0 when line is low."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # Drive pulls DATA low
        cia2.port_a = 0x00
        cia2.ddr_a = 0x3F
        drive.via1.ddrb = 0x02
        drive.via1.orb = 0x02
        bus.update()

        input_value = bus.get_c64_input()
        assert not (input_value & 0x80)  # DATA IN (bit 7) is low


class TestIECBusDriveInput:
    """Test drive reading bus state."""

    def test_drive_receives_atn(self):
        """Drive receives ATN state from C64."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # C64 asserts ATN
        cia2.port_a = 0x08
        cia2.ddr_a = 0x3F
        bus.update()

        # Drive should see ATN low (asserted)
        assert drive.iec_atn is False

    def test_drive_receives_clk(self):
        """Drive receives CLK state from C64."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # C64 asserts CLK
        cia2.port_a = 0x10
        cia2.ddr_a = 0x3F
        bus.update()

        assert drive.iec_clk is False

    def test_drive_receives_data(self):
        """Drive receives DATA state from C64."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive = Drive1541(device_number=8)
        bus.connect_drive(drive)

        # C64 asserts DATA
        cia2.port_a = 0x20
        cia2.ddr_a = 0x3F
        bus.update()

        assert drive.iec_data is False


class TestIECBusMultipleDrives:
    """Test IEC bus with multiple drives."""

    def test_multiple_drives_connect(self):
        """Multiple drives can connect to bus."""
        bus = IECBus()
        drive8 = Drive1541(device_number=8)
        drive9 = Drive1541(device_number=9)

        bus.connect_drive(drive8)
        bus.connect_drive(drive9)

        assert len(bus.drives) == 2
        assert drive8 in bus.drives
        assert drive9 in bus.drives

    def test_one_drive_pulls_line_low(self):
        """One drive pulling line low affects all devices."""
        bus = IECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)

        drive8 = Drive1541(device_number=8)
        drive9 = Drive1541(device_number=9)
        bus.connect_drive(drive8)
        bus.connect_drive(drive9)

        # C64 releases DATA
        cia2.port_a = 0x00
        cia2.ddr_a = 0x3F

        # Only drive 8 pulls DATA low
        drive8.via1.ddrb = 0x02
        drive8.via1.orb = 0x02
        drive9.via1.ddrb = 0x02
        drive9.via1.orb = 0x00

        bus.update()

        # DATA should be low
        assert bus.data is False
        # Both drives and C64 should see DATA low
        assert drive8.iec_data is False
        assert drive9.iec_data is False
