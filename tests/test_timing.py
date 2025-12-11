"""Tests for mos6502.timing module."""

import os
import time
import pytest
from mos6502.timing import (
    create_timer,
    FallbackTimer,
    FrameGovernor,
    Timer,
)

# CI environments have degraded timer accuracy due to shared VMs/containers
IN_CI = os.environ.get('CI') == 'true' or os.environ.get('CIRCLECI') == 'true'


class TestCreateTimer:
    """Test timer factory function."""

    def test_create_timer_returns_timer(self):
        """create_timer() should return a Timer-compatible object."""
        timer = create_timer()
        assert hasattr(timer, 'now')
        assert hasattr(timer, 'sleep')
        assert hasattr(timer, 'resolution')
        assert hasattr(timer, 'name')

    def test_timer_has_name(self):
        """Timer should have a descriptive name."""
        timer = create_timer()
        assert isinstance(timer.name, str)
        assert len(timer.name) > 0

    def test_timer_has_resolution(self):
        """Timer should report its resolution."""
        timer = create_timer()
        assert isinstance(timer.resolution, float)
        assert timer.resolution > 0
        assert timer.resolution < 1.0  # Should be sub-second


class TestFallbackTimer:
    """Test FallbackTimer implementation."""

    def test_now_returns_float(self):
        """now() should return a float."""
        timer = FallbackTimer()
        assert isinstance(timer.now(), float)

    def test_now_is_monotonic(self):
        """now() should be monotonically increasing."""
        timer = FallbackTimer()
        t1 = timer.now()
        t2 = timer.now()
        assert t2 >= t1

    def test_sleep_positive_duration(self):
        """sleep() should wait approximately the requested time."""
        timer = FallbackTimer()
        duration = 0.01  # 10ms

        start = timer.now()
        timer.sleep(duration)
        elapsed = timer.now() - start

        # Allow 50% tolerance for FallbackTimer
        assert elapsed >= duration * 0.5
        assert elapsed < duration * 3.0

    def test_sleep_zero_duration(self):
        """sleep(0) should return immediately."""
        timer = FallbackTimer()
        start = timer.now()
        timer.sleep(0)
        elapsed = timer.now() - start
        assert elapsed < 0.01  # Should be nearly instant

    def test_sleep_negative_duration(self):
        """sleep() with negative duration should return immediately."""
        timer = FallbackTimer()
        start = timer.now()
        timer.sleep(-1.0)
        elapsed = timer.now() - start
        assert elapsed < 0.01


class TestPlatformTimer:
    """Test the platform-specific timer (whichever is available)."""

    @pytest.fixture
    def timer(self):
        """Get the best available timer for this platform."""
        return create_timer()

    def test_now_returns_float(self, timer):
        """now() should return a float."""
        assert isinstance(timer.now(), float)

    def test_now_is_monotonic(self, timer):
        """now() should be monotonically increasing."""
        t1 = timer.now()
        t2 = timer.now()
        assert t2 >= t1

    @pytest.mark.skipif(IN_CI, reason="Sleep timing unreliable in CI environments")
    def test_sleep_accuracy_10ms(self, timer):
        """sleep(0.01) should be reasonably accurate."""
        duration = 0.01
        start = timer.now()
        timer.sleep(duration)
        elapsed = timer.now() - start

        # Platform timer should be within 50% of target
        assert elapsed >= duration * 0.5
        assert elapsed < duration * 2.0

    def test_sleep_accuracy_1ms(self, timer):
        """sleep(0.001) should work (though may oversleep)."""
        duration = 0.001
        start = timer.now()
        timer.sleep(duration)
        elapsed = timer.now() - start

        # 1ms sleep may oversleep significantly, just ensure it waits
        assert elapsed >= duration * 0.5

    @pytest.mark.skipif(IN_CI, reason="Sleep timing unreliable in CI environments")
    def test_multiple_short_sleeps(self, timer):
        """Multiple short sleeps should accumulate correctly."""
        count = 10
        duration = 0.005  # 5ms each

        start = timer.now()
        for _ in range(count):
            timer.sleep(duration)
        elapsed = timer.now() - start

        expected = count * duration
        # Allow 50% tolerance
        assert elapsed >= expected * 0.5
        assert elapsed < expected * 2.0


class TestFrameGovernor:
    """Test FrameGovernor throttling."""

    def test_init_defaults(self):
        """FrameGovernor should initialize with correct defaults."""
        governor = FrameGovernor(fps=60.0)
        assert governor.fps == 60.0
        assert governor.frame_time == pytest.approx(1.0 / 60.0)
        assert governor.enabled is True
        assert governor.frame_count == 0

    def test_init_disabled(self):
        """FrameGovernor can be initialized disabled."""
        governor = FrameGovernor(fps=60.0, enabled=False)
        assert governor.enabled is False

    def test_throttle_increments_frame_count(self):
        """throttle() should increment frame count."""
        governor = FrameGovernor(fps=1000.0)  # High FPS for fast test
        assert governor.frame_count == 0
        governor.throttle()
        assert governor.frame_count == 1
        governor.throttle()
        assert governor.frame_count == 2

    def test_throttle_disabled_returns_immediately(self):
        """throttle() with enabled=False should return immediately."""
        governor = FrameGovernor(fps=1.0, enabled=False)  # 1 FPS = 1 second frames

        start = time.perf_counter()
        for _ in range(10):
            governor.throttle()
        elapsed = time.perf_counter() - start

        # Should complete almost instantly when disabled
        assert elapsed < 0.1
        assert governor.frame_count == 10

    @pytest.mark.skipif(IN_CI, reason="Sleep timing unreliable in CI environments")
    def test_throttle_maintains_frame_rate(self):
        """throttle() should maintain approximately correct frame rate."""
        fps = 100.0  # 100 FPS = 10ms frames
        frames = 20
        governor = FrameGovernor(fps=fps)

        start = time.perf_counter()
        for _ in range(frames):
            governor.throttle()
        elapsed = time.perf_counter() - start

        expected = frames / fps
        # Allow 20% tolerance
        assert elapsed >= expected * 0.8
        assert elapsed < expected * 1.5

    def test_reset_clears_timing(self):
        """reset() should reset frame timing."""
        governor = FrameGovernor(fps=100.0)

        # Run a few frames
        for _ in range(5):
            governor.throttle()

        # Simulate a pause
        time.sleep(0.1)

        # Reset and verify next throttle doesn't try to catch up
        governor.reset()

        start = time.perf_counter()
        governor.throttle()
        elapsed = time.perf_counter() - start

        # Should be close to one frame time, not trying to catch up
        assert elapsed < governor.frame_time * 2

    def test_stats_returns_dict(self):
        """stats() should return a dictionary with timing info."""
        governor = FrameGovernor(fps=50.0)
        governor.throttle()

        stats = governor.stats()
        assert isinstance(stats, dict)
        assert 'timer' in stats
        assert 'target_fps' in stats
        assert stats['target_fps'] == 50.0
        assert 'frame_count' in stats
        assert stats['frame_count'] == 1
        assert 'enabled' in stats
        assert stats['enabled'] is True

    def test_frames_dropped_on_slow_execution(self):
        """Governor should drop frames when falling behind."""
        governor = FrameGovernor(fps=100.0)  # 10ms frames

        # Simulate being way behind by manipulating internal state
        governor._next_frame = governor.timer.now() - 0.5  # 500ms behind

        governor.throttle()

        # Should have dropped frames and reset
        assert governor.frames_dropped > 0

    def test_custom_timer(self):
        """FrameGovernor should accept a custom timer."""
        custom_timer = FallbackTimer()
        governor = FrameGovernor(fps=60.0, timer=custom_timer)
        assert governor.timer is custom_timer


class TestFrameGovernorAccuracy:
    """Test FrameGovernor timing accuracy over longer runs."""

    @pytest.mark.slow
    @pytest.mark.skipif(IN_CI, reason="Sleep timing unreliable in CI environments")
    def test_50hz_accuracy_1_second(self):
        """50Hz governor should maintain accuracy over 1 second."""
        fps = 50.0
        frames = 50
        governor = FrameGovernor(fps=fps)

        start = time.perf_counter()
        for _ in range(frames):
            governor.throttle()
        elapsed = time.perf_counter() - start

        expected = frames / fps  # 1.0 second
        error_percent = abs(elapsed - expected) / expected * 100

        # Should be within 5% over 1 second
        assert error_percent < 5.0, f"Error: {error_percent:.2f}%"

    @pytest.mark.slow
    @pytest.mark.skipif(IN_CI, reason="Sleep timing unreliable in CI environments")
    def test_60hz_accuracy_1_second(self):
        """60Hz governor should maintain accuracy over 1 second."""
        fps = 60.0
        frames = 60
        governor = FrameGovernor(fps=fps)

        start = time.perf_counter()
        for _ in range(frames):
            governor.throttle()
        elapsed = time.perf_counter() - start

        expected = frames / fps  # 1.0 second
        error_percent = abs(elapsed - expected) / expected * 100

        # Should be within 5% over 1 second
        assert error_percent < 5.0, f"Error: {error_percent:.2f}%"

    @pytest.mark.slow
    @pytest.mark.skipif(IN_CI, reason="Sleep timing unreliable in CI environments")
    def test_with_simulated_work(self):
        """Governor should compensate for varying work times."""
        fps = 50.0
        frames = 50
        work_time = 0.005  # 5ms of "work" per frame
        governor = FrameGovernor(fps=fps)
        timer = governor.timer

        start = timer.now()
        for _ in range(frames):
            # Simulate emulation work
            busy_until = timer.now() + work_time
            while timer.now() < busy_until:
                pass
            governor.throttle()
        elapsed = timer.now() - start

        expected = frames / fps  # 1.0 second
        error_percent = abs(elapsed - expected) / expected * 100

        # Should be within 5% even with work
        assert error_percent < 5.0, f"Error: {error_percent:.2f}%"
