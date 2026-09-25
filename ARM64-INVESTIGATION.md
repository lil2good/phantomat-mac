# Phantomat ARM64 port

**Current status:** the workspace-swipe crash was investigated and fixed below.
The patched build is running with manual activation; autostart remains disabled.
Earlier dated sections describe the investigation as it happened.

Local port for this machine, 2026-09-24. Source checkout:
`/home/thedev/phantomat-arm64`, branch `experiment/arm64-hooks`.

## Implementation

Hyprland 0.56.2 disables CFunctionHook on ARM64. This port uses a plugin-local
funchook adapter for Phantomat's 14 function hooks, without replacing Hyprland.
The x86-64 path still uses Hyprland's hook API; it has not been tested here.
Initialization failures release prepared ARM64 hooks, and active hooks are
released when the plugin exits. The X11 hook is enabled after initialization.

Base Phantomat revision: `2e33ec12e9d0`.
Pinned funchook revision: `b4991704add411ecbc492dae020f375124d51f45`.
Pinned Capstone revision: `097c04d9413c59a58b00d4d1c8d5dc0ac158ffaa`.

`make` builds both dependencies under `.build/deps` and links them statically.
The first build requires git, CMake, and network access. Subsequent builds reuse
these dependencies. ARM64 support currently uses the Makefile/installer path.

## Fixes found during verification

- Test desktop windows could be resized by the parent window manager. The
  harness can float and size its own windows with `NESTED_FIXED_SIZE=1`.
- The popup fixture assumed the whole button was below its parent. GTK overlaps
  it by two pixels. The test now targets the portion below the parent's edge
  and verifies pointer input there.
- The user's GTK theme overrode the fullscreen fixture's magenta bar. The
  fixture now gives its known test color precedence over the theme.
- X11 pointer tests used the requested output size instead of the actual size.
  They now measure it, including at 200% scaling.
- First installation could mistake automatic loading for an existing install
  and unnecessarily unload/reload the new plugin. The installer now records
  the old state before editing configuration. Updates still explicitly load
  the replacement because a config reload alone does not re-enable it.
- The session check now verifies the target compositor is reachable.

## Verification

Tested on aarch64, GCC 16.1.1, Hyprland 0.56.2. Tests use disposable compositors
and independent state directories.

| Check | Result |
| --- | --- |
| funchook CTest executable | Passed |
| Navigation and persistence | 19 assertions passed |
| Wayland popup positioning and input | 23 assertions passed |
| Fullscreen, bars, games, two monitors | 43 assertions passed |
| X11 input and menus, scale 1 | 7 assertions passed |
| X11 input and menus, scale 2 | 7 assertions passed |
| Chromium title-bar drag and release | 3 assertions passed |
| Activate/unload/reload | 3 cycles passed |
| Clean install/update/uninstall/purge | 19 assertions passed |

One exploratory fullscreen run lost its Wayland connection before compositor
logs were retained. The subsequent complete run passed; its cause was not
established. The harness now preserves compositor logs for diagnosis.

Logs are in `.build/arm64-results/`; screenshots are in `.build/arm64-shots/`
and `.build/shots-*`. This is a local port, not an upstream ARM64 release.

## Installed state

Installed using `scripts/install.sh` from this checkout. The live plugin loaded
and its canvas activated on eDP-1 at 200% scaling with no config errors.
The live zoomed-out search view and Super+Ctrl+G binding were verified. The
installer backed up `~/.config/hypr/hyprland.lua` before adding its marked block.

## Commands

Rebuild/install after a Hyprland update:

```sh
cd /home/thedev/phantomat-arm64
scripts/install.sh
```

Use this checkout, not the unmodified `/home/thedev/phantomat` checkout.

Remove the plugin and restore normal bindings:

```sh
/home/thedev/phantomat-arm64/scripts/uninstall.sh
```

Uninstall keeps settings. Add `--purge` only to delete settings and layout memory.

Repeat the relevant isolated checks:

```sh
cd /home/thedev/phantomat-arm64
NESTED_FIXED_SIZE=1 python3 tests/popup-nested.py spatialoverview.so
NESTED_FIXED_SIZE=1 python3 tests/fullscreen-nested.py spatialoverview.so
NESTED_FIXED_SIZE=1 NESTED_SCALE=2 python3 tests/x11-nested.py spatialoverview.so
python3 tests/install-nested.py
```

## Live crash and rollback

Hyprland PID 2082 aborted at 21:32:06 PDT. The core's signal-handler frame
points to CUnifiedWorkspaceSwipeGesture::end(), called by
CTrackpadGestures::gestureEnd and CInputManager::onSwipeEnd through libinput.
The user config enables three-finger horizontal workspace swipes. This path
was not covered by the earlier nested tests. An interaction with the canvas
is suspected but the exact cause has not yet been established.

Removed the marked Phantomat startup block from ~/.config/hypr/hyprland.lua.
Verified the new Hyprland session has no plugins loaded and no config errors.
Kept the source and compiled plugin for diagnosis; temporary extracted core
files were deleted. The systemd-managed crash core remains available.

## Manual swipe-fix candidate

The candidate at `.build/swipe-fixed/spatialoverview.so` owns three-or-more-finger
swipes from begin through end while the pointer is on a canvas. Updates pan
the camera in screen pixels, scaled by zoom. Native workspace gestures do not
receive these events. Ownership survives closing the canvas mid-gesture.
Opening a canvas during an existing native swipe is rejected until fingers lift.

The exact null-pointer crash has not been reproduced in the nested compositor.
The old build does allow native workspace swipe state to become active on the
canvas. The new regression checks that this cannot happen, verifies camera
movement, checks closing mid-swipe, and checks normal workspace swipes afterward.
All these checks pass, as does the navigator suite and session start/stop test.
This is a manual-test candidate, not proof that every live desktop crash is fixed.

Autostart remains disabled. Start and stop from a terminal in the current desktop:

```sh
~/phantomat-arm64/scripts/test-session.sh
~/phantomat-arm64/scripts/test-session.sh stop
```

The script applies existing settings and bindings only to the current session.
Stopping unloads the plugin and reloads normal configuration. It never writes a
startup entry. Do not use `install.sh` for this manual test, since it enables
persistent loading.

```sh
make -j4 OUT=.build/swipe-fixed/spatialoverview.so .build/swipe-probe.so
NESTED_FIXED_SIZE=1 python tests/swipe-nested.py .build/swipe-fixed/spatialoverview.so
NESTED_FIXED_SIZE=1 python tests/session-nested.py
```

## Software cursor above canvas controls, September 25

The built-in final screen shader painted the minimap, Tidy button and search
HUD over the software cursor, which Hyprland had already drawn into the input
frame. The lens could also displace that cursor from its actual click position.
Hardware cursors and screenshots that add a hardware cursor afterward hid the
problem in earlier tests.

The texture hook now recognizes Hyprland's current cursor texture and defers it
to the final shader. It is composited last at its original screen rectangle,
after the lens and HUD. Cursor uniforms reset per frame/output. Offscreen
rendering and custom shaders without cursor uniforms use the normal path.

`tests/cursor-nested.py` starts separate hardware- and software-cursor sessions,
compares visible cursor pixels above Tidy, the minimap and search, checks that
the old cursor clears when moved, and clicks Tidy. At 2x scaling and 15% zoom,
the old binary failed with 0% of reference cursor pixels visible over Tidy;
the fixed build matched 100% over all three controls and passed the click test.
Runtime cursor-backend toggles are insufficient for this regression: the old
backend can remain active, producing a false pass.

```sh
make -j4 OUT=.build/cursor-fixed/spatialoverview.so
NESTED_FIXED_SIZE=1 NESTED_SCALE=2 python tests/cursor-nested.py
NESTED_FIXED_SIZE=1 NESTED_SCALE=2 NESTED_SOFTWARE_CURSOR=1 python tests/fullscreen-nested.py .build/cursor-fixed/spatialoverview.so
```

### Navigator framing below search (2026-09-25)

The old selection camera reserved the maximum result-list height even when
only the search field was visible, then kept the existing zoom regardless of
window height. Large windows were shifted down and clipped at the bottom.

The HUD now provides the available rectangle below the visible search/results
panel. Following a selection fits it inside that rectangle, capped at the
configured initial zoom. Opening navigation and clearing or hiding results also
reframe the selection. Fit-all uses the same available dimensions. Desktop
landing at 100% and manual pan/zoom remain separate from selection framing.

`tests/framing-nested.py` exercises tall, wide and small windows, with search
results and after clearing search. It checks actual camera/window geometry and
saves screenshots. The previous cursor-fixed build fails the bottom-clipping
check. Logs are `.build/framing-test.log`, `.build/framing-baseline.log` and
`.build/framing-2x.log`.

### Touchpad app scrolling and direct three-finger panning (2026-09-25)

The canvas forwarded finger-axis deltas before Hyprland applied the configured
scroll factor. With Omarchy's 0.4 touchpad factor, that made application scrolling
2.5 times faster than normal. The app-input path now applies the native touchpad
factor and per-window touchpad override. Continuous non-wheel input uses the
mouse factor and corresponding window override. Wheel handling is unchanged.

Three-finger pan updates now warp the camera directly rather than repeatedly
retargeting its animation. Keyboard panning still animates. Gesture ownership,
including cancellation when the canvas closes mid-swipe, is unchanged.

`tests/scroll-nested.py` injects finger-axis events into an isolated compositor
and compares their delivery to Chromium with and without the canvas. The page
handles wheel events itself to exclude Chromium fling acceleration from the
comparison. The old build delivers 600 browser units for a native 240; the new
build delivers 240 in both modes. The same test verifies immediate camera
movement and no trailing movement after the swipe ends. Test logs live in
`.build/scroll-baseline.log`, `.build/scroll-test.log` and `.build/scroll-2x.log`.

### Browser momentum correction (2026-09-25)

The scroll-factor change did not fix normal browser momentum. Its first test
prevented the browser's default wheel behavior, which hid a second bug. A fresh
native/canvas comparison with default Chromium scrolling reproduced a 4.2x
increase in travel despite identical axis deltas and the corrected factor.

Wayland traces showed a stationary mouse-motion event and frame immediately
before every axis event, including axis-stop. These redundant motion frames
changed Chromium's fling velocity calculation. Pointer forwarding now records
the last surface-local coordinate and emits motion only when the coordinate or
focused surface changes. Real movement and popup/surface transitions still
send motion normally.

`tests/momentum-nested.py` uses separate fresh browser sessions, leaves default
scrolling enabled, measures final page displacement, and checks protocol traces
for injected motion during stationary scrolling. At 1x, native scrolling moved
441 px and the corrected canvas moved 448 px (1.016 ratio), versus 4.204 before.
Logs: `.build/momentum-baseline.log`, `.build/momentum-test.log`, and
`.build/momentum-2x.log`. The old pointer trace is retained as
`.build/momentum-baseline-pointer.log`.

At 2x scaling, default Chromium momentum moved 462 px natively and 444 px on
the corrected canvas (0.961 ratio). Both protocol traces contain no synthetic
motion between axis events. The test uses a tiny explicit pointer move before
the gesture to establish page focus in the nested compositor.

### Hold Shift to snap and preview a drop (2026-09-25)

Dragging is now free unless Shift is held when the mouse button is released.
Shift uses the existing world grid and respects canvas.snap_enabled. Automatic
placement and keyboard nudging retain their existing grid behavior.

While Shift is held during a drag, the target shows an accent-colored tinted
fill, soft outer border, crisp outline and corner markers. The preview uses the
same screen-to-world conversion and snap operation as the committed drop,
including the destination canvas when crossing outputs. Shift press/release
requests redraws even with a stationary pointer; releasing Shift clears the
preview and restores free placement immediately.

`tests/shift-snap-nested.py` exercises real pointer and modifier input, validates
exact free/snapped positions, and captures preview appearance and disappearance.
The three drop modes pass at 1x, 2x and 50% overview zoom. For the numeric zoom
check, lens distortion is disabled in the isolated test configuration.
Artifacts: `.build/shift-snap-test.log`, `.build/shift-snap-2x.log`,
`.build/shift-snap-overview.log` and `.build/shift-snap-shots/`.
