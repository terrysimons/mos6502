"""Tests for ThreadedIECBus and ThreadedDrive1541."""

import pytest
import threading
import time
from unittest.mock import MagicMock

from c64.drive.threaded_iec_bus import ThreadedIECBus
from c64.drive.threaded_drive import ThreadedDrive1541


class MockCIA2:
    """Mock CIA2 for testing IEC bus."""

    def __init__(self):
        self.port_a = 0x00
        self.ddr_a = 0x3F  # ATN, CLK, DATA as outputs


class TestThreadedIECBusBasic:
    """Test basic ThreadedIECBus functionality."""

    def test_initial_state(self):
        """Test initial bus state is all lines released."""
        bus = ThreadedIECBus()
        atn, clk, data = bus.get_bus_state()
        assert atn is True, "ATN should be released (high)"
        assert clk is True, "CLK should be released (high)"
        assert data is True, "DATA should be released (high)"

    def test_connect_c64(self):
        """Test connecting C64 to bus."""
        bus = ThreadedIECBus()
        cia2 = MockCIA2()
        bus.connect_c64(cia2)
        assert bus.cia2 is cia2

    def test_c64_output_atn(self):
        """Test C64 can drive ATN low."""
        bus = ThreadedIECBus()
        bus.set_c64_outputs(atn_out=True, clk_out=False, data_out=False)
        atn, clk, data = bus.get_bus_state()
        assert atn is False, "ATN should be asserted (low)"
        assert clk is True, "CLK should be released"
        assert data is True, "DATA should be released"

    def test_c64_output_clk(self):
        """Test C64 can drive CLK low."""
        bus = ThreadedIECBus()
        bus.set_c64_outputs(atn_out=False, clk_out=True, data_out=False)
        atn, clk, data = bus.get_bus_state()
        assert atn is True, "ATN should be released"
        assert clk is False, "CLK should be asserted (low)"
        assert data is True, "DATA should be released"

    def test_c64_output_data(self):
        """Test C64 can drive DATA low."""
        bus = ThreadedIECBus()
        bus.set_c64_outputs(atn_out=False, clk_out=False, data_out=True)
        atn, clk, data = bus.get_bus_state()
        assert atn is True, "ATN should be released"
        assert clk is True, "CLK should be released"
        assert data is False, "DATA should be asserted (low)"

    def test_c64_input_reflects_bus_state(self):
        """Test get_c64_input returns correct bus state."""
        bus = ThreadedIECBus()

        # All lines high
        result = bus.get_c64_input()
        assert result & 0x40, "CLK IN (bit 6) should be high"
        assert result & 0x80, "DATA IN (bit 7) should be high"

        # CLK low
        bus.set_c64_outputs(atn_out=False, clk_out=True, data_out=False)
        result = bus.get_c64_input()
        assert not (result & 0x40), "CLK IN (bit 6) should be low"
        assert result & 0x80, "DATA IN (bit 7) should be high"


class TestThreadedIECBusDriveOutput:
    """Test drive output through ThreadedIECBus with real drive VIA."""

    def test_drive_output_clk(self):
        """Test drive can drive CLK low via VIA register."""
        bus = ThreadedIECBus()
        drive = ThreadedDrive1541(device_number=8)
        drive.connect_to_threaded_bus(bus)

        # Configure VIA1 Port B bit 3 (CLK OUT) as output and set high (drives bus LOW)
        drive.via1.ddrb = 0x08  # Bit 3 as output
        drive.via1.orb = 0x08   # Bit 3 = 1 means drive bus LOW (inverted)

        atn, clk, data = bus.get_bus_state()
        assert clk is False, "CLK should be asserted (low) by drive"
        assert data is True, "DATA should be released"

    def test_drive_output_data(self):
        """Test drive can drive DATA low via VIA register."""
        bus = ThreadedIECBus()
        drive = ThreadedDrive1541(device_number=8)
        drive.connect_to_threaded_bus(bus)

        # Configure VIA1 Port B bit 1 (DATA OUT) as output and set high (drives bus LOW)
        drive.via1.ddrb = 0x02  # Bit 1 as output
        drive.via1.orb = 0x02   # Bit 1 = 1 means drive bus LOW (inverted)

        atn, clk, data = bus.get_bus_state()
        assert clk is True, "CLK should be released"
        assert data is False, "DATA should be asserted (low) by drive"

    def test_open_collector_both_drive_clk(self):
        """Test open-collector: line low when both C64 and drive pull."""
        bus = ThreadedIECBus()
        drive = ThreadedDrive1541(device_number=8)
        drive.connect_to_threaded_bus(bus)

        # C64 pulls CLK
        bus.set_c64_outputs(atn_out=False, clk_out=True, data_out=False)

        # Drive also pulls CLK via VIA
        drive.via1.ddrb = 0x08  # Bit 3 as output
        drive.via1.orb = 0x08   # Bit 3 = 1 means drive bus LOW

        atn, clk, data = bus.get_bus_state()
        assert clk is False, "CLK should still be low"

        # Now C64 releases
        bus.set_c64_outputs(atn_out=False, clk_out=False, data_out=False)
        atn, clk, data = bus.get_bus_state()
        assert clk is False, "CLK should still be low (drive still pulling)"

        # Drive releases too
        drive.via1.orb = 0x00  # Clear CLK OUT bit
        atn, clk, data = bus.get_bus_state()
        assert clk is True, "CLK should now be high (both released)"


class TestThreadedIECBusATNAck:
    """Test ATN acknowledge logic in ThreadedIECBus."""

    def test_atn_ack_pulls_data_when_different(self):
        """Test ATN ACK XOR logic pulls DATA when states differ."""
        bus = ThreadedIECBus()
        drive = ThreadedDrive1541(device_number=8)
        drive.connect_to_threaded_bus(bus)

        # C64 asserts ATN
        bus.set_c64_outputs(atn_out=True, clk_out=False, data_out=False)

        # Drive's ATNA is clear (False), ATN logical is True (asserted)
        # Different states → DATA pulled low
        drive.via1.ddrb = 0x10  # Bit 4 (ATNA) as output
        drive.via1.orb = 0x00   # ATNA = 0 (doesn't match ATN = asserted)

        atn, clk, data = bus.get_bus_state()
        assert atn is False, "ATN should be asserted"
        assert data is False, "DATA should be pulled low by ATN ACK mismatch"

    def test_atn_ack_releases_data_when_matching(self):
        """Test ATN ACK releases DATA when states match."""
        bus = ThreadedIECBus()
        drive = ThreadedDrive1541(device_number=8)
        drive.connect_to_threaded_bus(bus)

        # C64 asserts ATN
        bus.set_c64_outputs(atn_out=True, clk_out=False, data_out=False)

        # Drive sets ATNA to match ATN state (both "true"/asserted)
        drive.via1.ddrb = 0x10  # Bit 4 (ATNA) as output
        drive.via1.orb = 0x10   # ATNA = 1 (matches ATN = asserted)

        atn, clk, data = bus.get_bus_state()
        assert atn is False, "ATN should be asserted"
        assert data is True, "DATA should be released (ATN ACK matches ATN)"


class TestThreadedDrive1541:
    """Test ThreadedDrive1541 class."""

    def test_create_threaded_drive(self):
        """Test creating a ThreadedDrive1541."""
        drive = ThreadedDrive1541(device_number=8)
        assert drive.device_number == 8
        assert drive._thread is None
        assert drive._running is False

    def test_start_stop_thread(self, tmp_path):
        """Test starting and stopping drive thread."""
        drive = ThreadedDrive1541(device_number=8)

        # Create minimal CPU mock
        drive.cpu = MagicMock()
        drive.cpu.execute = MagicMock(return_value=None)

        # Start thread
        drive.start_thread()
        assert drive._running is True
        assert drive._thread is not None
        assert drive._thread.is_alive()

        # Let it run briefly
        time.sleep(0.1)

        # Stop thread
        drive.stop_thread(timeout=1.0)
        assert drive._running is False

    def test_connect_to_threaded_bus(self):
        """Test connecting drive to threaded bus."""
        bus = ThreadedIECBus()
        drive = ThreadedDrive1541(device_number=8)

        drive.connect_to_threaded_bus(bus)

        assert drive._threaded_iec_bus is bus
        assert drive.iec_bus is bus
        assert 8 in bus._drive_outputs

    def test_tick_is_noop_in_threaded_mode(self):
        """Test that tick() does nothing in threaded mode."""
        drive = ThreadedDrive1541(device_number=8)
        drive.cpu = MagicMock()

        # In threaded mode, tick() should not call cpu.execute
        drive.tick(100)
        drive.cpu.execute.assert_not_called()


class TestThreadedIECBusThreadSafety:
    """Test thread safety of ThreadedIECBus."""

    def test_concurrent_read_write(self):
        """Test concurrent reads and writes don't cause errors."""
        bus = ThreadedIECBus()
        errors = []
        stop_event = threading.Event()

        def writer():
            try:
                for _ in range(1000):
                    if stop_event.is_set():
                        break
                    bus.set_c64_outputs(
                        atn_out=True,
                        clk_out=False,
                        data_out=True
                    )
                    bus.set_c64_outputs(
                        atn_out=False,
                        clk_out=True,
                        data_out=False
                    )
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(1000):
                    if stop_event.is_set():
                        break
                    bus.get_bus_state()
                    bus.get_c64_input()
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        stop_event.set()

        assert len(errors) == 0, f"Errors occurred: {errors}"
