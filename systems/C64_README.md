# C64 Emulator Architecture

## Display Synchronization

The emulator uses a non-blocking frame synchronization model between the CPU/VIC emulation and the display renderer (pygame).

### Two Concurrent Threads

1. **CPU Thread** - Runs the 6502 CPU and VIC-II at full speed
2. **Pygame Thread** - Renders frames to the display when it can

### Frame Cycle

```
CPU Thread                          Pygame Thread
──────────                          ─────────────
    │                                    │
    ▼                                    │
[Execute instructions]                   │
    │                                    │
    ▼                                    │
[VIC updates raster position]            │
    │                                    │
    ▼                                    │
[Raster wraps to 0?]                     │
    │                                    │
   YES                                   │
    │                                    │
    ▼                                    │
[Set frame_complete = True] ─────────►  [Check: frame_complete?]
    │                                    │
    │ (keeps running)                   YES
    │                                    │
    ▼                                    ▼
[More instructions...]              [Snapshot RAM]
    │                                    │
    │                                    ▼
    │                              [Clear frame_complete]
    │                                    │
    │                                    ▼
    │                              [Render from snapshot]
    │                                    │
    ▼                                    ▼
  (loop)                              (loop)
```

### Key Design Points

1. **VIC signals "frame done"** - Sets `frame_complete` when the raster beam wraps from the last line (311 for PAL, 262/263 for NTSC) back to line 0. This is the vertical blank (VBlank) period.

2. **Pygame grabs what it can** - Checks the flag, takes a quick RAM snapshot, clears the flag, then renders at its leisure from the snapshot.

3. **No blocking** - CPU never waits for pygame, pygame never waits for CPU. They communicate through a single Event flag.

4. **Snapshot for consistency** - `bytes(self.cpu.ram)` creates a copy of RAM so pygame renders a frozen moment in time, not RAM that's changing mid-render. This prevents visual tearing and partial updates.

### Synchronization Primitive Choice

The `frame_complete` flag uses `multiprocessing.Event()` rather than `threading.Event()` or a plain boolean:

| Primitive | Cross-Thread | Cross-Process | Notes |
|-----------|--------------|---------------|-------|
| `bool` | No | No | Not memory-safe across threads |
| `threading.Event` | Yes | No | Only works within single process |
| `multiprocessing.Event` | Yes | Yes | Works everywhere, slight overhead |

We use `multiprocessing.Event` because:
- **Thread visibility**: Plain booleans may not be visible across threads due to CPU caching and memory barriers
- **Future-proofing**: If we later move CPU execution to a separate process for true parallelism (bypassing Python's GIL), the synchronization will still work
- **Consistency**: One primitive that works in all scenarios

The thread/process coordination (cpu_done, stop_display) uses `threading.Event` and `threading.Thread` because:
- They involve closures that capture `self` and local variables
- `multiprocessing.Process` requires pickling the target function and its closure, which fails for nested functions
- Threading is sufficient here since these are for coordination, not CPU-bound work

### Performance Characteristics

- If pygame is slow, it may miss frames - the emulation continues at full speed and pygame renders the next frame it catches
- If pygame is fast, it renders every frame
- Display may drop below 50/60 fps if rendering is slow, but emulation timing remains accurate
- Whatever pygame renders is always a consistent snapshot taken at or near VBlank

## Video Timing

The VIC-II chip has three variants with different timing:

| Chip | Region | Raster Lines | Cycles/Line | Cycles/Frame | Refresh |
|------|--------|--------------|-------------|--------------|---------|
| 6569 | PAL | 312 | 63 | 19,656 | ~50 Hz |
| 6567R8 | NTSC | 263 | 65 | 17,095 | ~60 Hz |
| 6567R56A | NTSC (old) | 262 | 64 | 16,768 | ~60 Hz |

## Cartridge Support

### Supported Types

- **Type 0: Normal Cartridge** - 8KB, 16KB, and Ultimax modes
- **Type 1: Action Replay** - 32KB banked cartridge with RAM

### Cartridge Auto-Detection

For raw `.bin` files, the loader auto-detects the cartridge type:

1. **8KB with CBM80 signature** at offset 4 → Standard 8K cartridge at $8000
2. **8KB with reset vector in $E000-$FFFF** → Ultimax cartridge at $E000
3. **16KB file** → 16K cartridge at $8000-$BFFF

CRT files contain header metadata specifying the exact hardware type and memory configuration.
