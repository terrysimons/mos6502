"""High-resolution timing for 6502 system emulators.

Provides platform-specific high-resolution timers and a frame governor
for throttling emulation to real-time speed.

Platform support:
    - Linux: clock_nanosleep() via ctypes
    - macOS: nanosleep() via ctypes
    - Windows: CreateWaitableTimerExW with HIGH_RESOLUTION (Win10 1803+)
    - Fallback: time.sleep() (coarser but universal)

Usage:
    from mos6502.timing import create_timer, FrameGovernor

    # Low-level timer access
    timer = create_timer()
    timer.sleep(0.001)  # Sleep 1ms precisely

    # Frame-rate governing for emulators
    governor = FrameGovernor(fps=50.125)  # PAL C64
    while running:
        execute_one_frame()
        governor.throttle()  # Hold to real-time
"""

import ctypes
from mos6502.compat import logging
import sys
import time
from mos6502.compat import Protocol, Optional

log = logging.getLogger(__name__)


class Timer(Protocol):
    """Protocol for high-resolution timers."""

    def now(self) -> float:
        """Return current monotonic time in seconds."""
        ...

    def sleep(self, seconds: float) -> None:
        """Sleep for the specified duration in seconds."""
        ...

    @property
    def resolution(self) -> float:
        """Return timer resolution in seconds (for diagnostics)."""
        ...

    @property
    def name(self) -> str:
        """Return timer implementation name."""
        ...


class FallbackTimer:
    """Fallback timer using time.sleep().

    Works everywhere but has coarse resolution (typically 10-15ms on Windows,
    1-10ms on Unix systems).
    """

    @property
    def name(self) -> str:
        return "FallbackTimer (time.sleep)"

    @property
    def resolution(self) -> float:
        return time.get_clock_info('monotonic').resolution

    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


class LinuxTimer:
    """High-resolution timer for Linux using clock_nanosleep().

    Uses CLOCK_MONOTONIC with TIMER_ABSTIME for precise sleeping.
    Resolution is typically sub-microsecond.
    """

    CLOCK_MONOTONIC = 1
    TIMER_ABSTIME = 1

    def __init__(self):
        self._libc = ctypes.CDLL("libc.so.6", use_errno=True)

        # struct timespec { time_t tv_sec; long tv_nsec; }
        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

        self._timespec = timespec
        self._clock_nanosleep = self._libc.clock_nanosleep
        self._clock_nanosleep.argtypes = [
            ctypes.c_int,      # clockid
            ctypes.c_int,      # flags
            ctypes.POINTER(timespec),  # request
            ctypes.POINTER(timespec),  # remain (can be NULL)
        ]
        self._clock_nanosleep.restype = ctypes.c_int

        self._clock_gettime = self._libc.clock_gettime
        self._clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
        self._clock_gettime.restype = ctypes.c_int

        # Test that it works
        ts = timespec()
        if self._clock_gettime(self.CLOCK_MONOTONIC, ctypes.byref(ts)) != 0:
            raise OSError("clock_gettime failed")

    @property
    def name(self) -> str:
        return "LinuxTimer (clock_nanosleep)"

    @property
    def resolution(self) -> float:
        return 1e-9  # nanosecond resolution

    def now(self) -> float:
        ts = self._timespec()
        self._clock_gettime(self.CLOCK_MONOTONIC, ctypes.byref(ts))
        return ts.tv_sec + ts.tv_nsec * 1e-9

    def sleep(self, seconds: float) -> None:
        if seconds <= 0:
            return

        # Calculate absolute target time
        target = self.now() + seconds
        ts = self._timespec()
        ts.tv_sec = int(target)
        ts.tv_nsec = int((target - ts.tv_sec) * 1e9)

        # Sleep until absolute time (TIMER_ABSTIME)
        self._clock_nanosleep(
            self.CLOCK_MONOTONIC,
            self.TIMER_ABSTIME,
            ctypes.byref(ts),
            None
        )


class DarwinTimer:
    """High-resolution timer for macOS using nanosleep().

    macOS nanosleep() has good resolution (typically ~100μs).
    We use mach_absolute_time() for high-resolution time reading.
    """

    def __init__(self):
        self._libc = ctypes.CDLL("/usr/lib/libc.dylib", use_errno=True)

        # struct timespec { time_t tv_sec; long tv_nsec; }
        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

        self._timespec = timespec
        self._nanosleep = self._libc.nanosleep
        self._nanosleep.argtypes = [ctypes.POINTER(timespec), ctypes.POINTER(timespec)]
        self._nanosleep.restype = ctypes.c_int

        # Use mach_absolute_time for high-res monotonic time
        self._libsystem = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        self._mach_absolute_time = self._libsystem.mach_absolute_time
        self._mach_absolute_time.restype = ctypes.c_uint64

        # Get timebase info for converting mach time to nanoseconds
        class mach_timebase_info(ctypes.Structure):
            _fields_ = [("numer", ctypes.c_uint32), ("denom", ctypes.c_uint32)]

        self._mach_timebase_info_t = mach_timebase_info
        self._mach_timebase_info = self._libsystem.mach_timebase_info
        self._mach_timebase_info.argtypes = [ctypes.POINTER(mach_timebase_info)]

        info = mach_timebase_info()
        self._mach_timebase_info(ctypes.byref(info))
        self._timebase = info.numer / info.denom  # Convert to nanoseconds

    @property
    def name(self) -> str:
        return "DarwinTimer (nanosleep + mach_absolute_time)"

    @property
    def resolution(self) -> float:
        return 1e-9  # nanosecond resolution for time reading

    def now(self) -> float:
        return self._mach_absolute_time() * self._timebase * 1e-9

    def sleep(self, seconds: float) -> None:
        if seconds <= 0:
            return

        ts = self._timespec()
        ts.tv_sec = int(seconds)
        ts.tv_nsec = int((seconds - ts.tv_sec) * 1e9)

        # nanosleep may return early on signal, loop until done
        remain = self._timespec()
        while self._nanosleep(ctypes.byref(ts), ctypes.byref(remain)) != 0:
            ts.tv_sec = remain.tv_sec
            ts.tv_nsec = remain.tv_nsec


class WindowsTimer:
    """High-resolution timer for Windows.

    Uses CreateWaitableTimerExW with CREATE_WAITABLE_TIMER_HIGH_RESOLUTION
    on Windows 10 1803+. Falls back to standard waitable timer with
    timeBeginPeriod(1) on older versions.
    """

    CREATE_WAITABLE_TIMER_HIGH_RESOLUTION = 0x00000002
    TIMER_ALL_ACCESS = 0x1F0003
    INFINITE = 0xFFFFFFFF

    def __init__(self):
        self._kernel32 = ctypes.windll.kernel32
        self._winmm = ctypes.windll.winmm

        # Try to create high-resolution timer (Win10 1803+)
        self._high_res = False
        self._timer_handle = self._kernel32.CreateWaitableTimerExW(
            None,  # security attributes
            None,  # name
            self.CREATE_WAITABLE_TIMER_HIGH_RESOLUTION,
            self.TIMER_ALL_ACCESS
        )

        if self._timer_handle:
            self._high_res = True
        else:
            # Fall back to standard waitable timer
            self._timer_handle = self._kernel32.CreateWaitableTimerW(
                None, True, None
            )
            if not self._timer_handle:
                raise OSError("Failed to create waitable timer")

            # Set system timer resolution to 1ms
            self._winmm.timeBeginPeriod(1)

        # QueryPerformanceCounter for high-res time
        self._qpc = ctypes.c_int64()
        self._qpf = ctypes.c_int64()
        self._kernel32.QueryPerformanceFrequency(ctypes.byref(self._qpf))

    def __del__(self):
        if hasattr(self, '_timer_handle') and self._timer_handle:
            self._kernel32.CloseHandle(self._timer_handle)
        if hasattr(self, '_high_res') and not self._high_res:
            self._winmm.timeEndPeriod(1)

    @property
    def name(self) -> str:
        if self._high_res:
            return "WindowsTimer (HIGH_RESOLUTION waitable timer)"
        return "WindowsTimer (waitable timer + timeBeginPeriod)"

    @property
    def resolution(self) -> float:
        if self._high_res:
            return 0.5e-3  # ~0.5ms for high-res timer
        return 1e-3  # 1ms with timeBeginPeriod(1)

    def now(self) -> float:
        self._kernel32.QueryPerformanceCounter(ctypes.byref(self._qpc))
        return self._qpc.value / self._qpf.value

    def sleep(self, seconds: float) -> None:
        if seconds <= 0:
            return

        # SetWaitableTimer uses 100-nanosecond intervals, negative = relative
        due_time = ctypes.c_int64(int(-seconds * 10_000_000))

        self._kernel32.SetWaitableTimer(
            self._timer_handle,
            ctypes.byref(due_time),
            0,     # period (0 = one-shot)
            None,  # completion routine
            None,  # arg to completion routine
            False  # resume from suspend
        )

        self._kernel32.WaitForSingleObject(self._timer_handle, self.INFINITE)


def create_timer() -> Timer:
    """Create the best available timer for the current platform.

    Returns:
        A Timer instance appropriate for the current OS.
    """
    if sys.platform == 'linux':
        try:
            timer = LinuxTimer()
            log.debug(f"Using {timer.name}")
            return timer
        except (OSError, AttributeError) as e:
            log.debug(f"LinuxTimer unavailable: {e}")

    elif sys.platform == 'darwin':
        try:
            timer = DarwinTimer()
            log.debug(f"Using {timer.name}")
            return timer
        except (OSError, AttributeError) as e:
            log.debug(f"DarwinTimer unavailable: {e}")

    elif sys.platform == 'win32':
        try:
            timer = WindowsTimer()
            log.debug(f"Using {timer.name}")
            return timer
        except (OSError, AttributeError) as e:
            log.debug(f"WindowsTimer unavailable: {e}")

    timer = FallbackTimer()
    log.debug(f"Using {timer.name}")
    return timer


class FrameGovernor:
    """Frame-rate governor for throttling emulation to real-time.

    Tracks frame timing and sleeps as needed to maintain target frame rate.

    Usage:
        governor = FrameGovernor(fps=50.125)  # PAL
        while running:
            execute_one_frame()
            governor.throttle()

    Args:
        fps: Target frames per second
        enabled: If False, throttle() returns immediately (for benchmarks)
        timer: Timer instance (auto-detected if None)
    """

    def __init__(
        self,
        fps: float,
        enabled: bool = True,
        timer: Optional[Timer] = None
    ):
        self.fps = fps
        self.frame_time = 1.0 / fps
        self.enabled = enabled
        self.timer = timer or create_timer()

        # Frame tracking
        self._next_frame = self.timer.now()
        self._frame_count = 0

        # Stats
        self._total_sleep_time = 0.0
        self._total_drift = 0.0
        self._frames_dropped = 0

    def throttle(self) -> None:
        """Wait until it's time for the next frame.

        If emulation is running fast, sleeps to maintain real-time.
        If emulation is running slow, returns immediately.
        If we've fallen more than one frame behind, resets timing.
        """
        if not self.enabled:
            self._frame_count += 1
            return

        now = self.timer.now()
        remaining = self._next_frame - now

        if remaining > 0:
            self.timer.sleep(remaining)
            self._total_sleep_time += remaining
        else:
            # We're behind - track the drift
            self._total_drift += -remaining

        # Schedule next frame (accumulate to prevent drift)
        self._next_frame += self.frame_time
        self._frame_count += 1

        # If we've fallen more than one frame behind, reset
        # This prevents "catch-up sprint" after a long pause
        current = self.timer.now()
        if self._next_frame < current - self.frame_time:
            dropped = int((current - self._next_frame) / self.frame_time)
            self._frames_dropped += dropped
            self._next_frame = current

    def reset(self) -> None:
        """Reset timing (call after pause/resume)."""
        self._next_frame = self.timer.now()

    @property
    def frame_count(self) -> int:
        """Total frames processed."""
        return self._frame_count

    @property
    def total_sleep_time(self) -> float:
        """Total time spent sleeping (seconds)."""
        return self._total_sleep_time

    @property
    def total_drift(self) -> float:
        """Total accumulated drift when running behind (seconds)."""
        return self._total_drift

    @property
    def frames_dropped(self) -> int:
        """Number of frames dropped due to falling behind."""
        return self._frames_dropped

    def stats(self) -> dict:
        """Return timing statistics."""
        return {
            "timer": self.timer.name,
            "timer_resolution": self.timer.resolution,
            "target_fps": self.fps,
            "frame_time": self.frame_time,
            "enabled": self.enabled,
            "frame_count": self._frame_count,
            "total_sleep_time": self._total_sleep_time,
            "total_drift": self._total_drift,
            "frames_dropped": self._frames_dropped,
            "avg_sleep_per_frame": self._total_sleep_time / max(1, self._frame_count),
        }
