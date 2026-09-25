Phantomat audit, 2026-09-24

Historical snapshot. The reload/settings and scrolling issues below were later
fixed; see ARM64-INVESTIGATION.md and the current source. Pinch lifecycle and
unhook failure handling remain open audit findings.

Machine: Apple MacBook Pro 16-inch, M1 Max, 2021; Arch/Omarchy, Hyprland
0.56.2, aarch64. This is the Linux installation on Apple hardware, not macOS.
Tested artifact: `.build/swipe-fixed/spatialoverview.so`, SHA256
`1d04c01cf46ea1cc97ec68bdb4dcd3c77c49d848fa19d437e319d8ae04bc5f56`.

The audit did not change the running plugin, user settings, or startup config.
All mutations and injected gestures were confined to disposable nested sessions.
The main compositor remained PID 1853 and reported no config errors afterward.

Confirmed issues

1. Session-only settings and bindings disappear on config reload.
   `scripts/test-session.sh:20` applies the settings through the Lua REPL only.
   The main config does not source that file. In an isolated session matching
   this setup, Super+Tab was bound before reload, absent afterward, while the
   manually loaded plugin remained loaded. On the real desktop the normal Vista
   binding would be restored instead. Merely running start again refuses because
   the plugin is already loaded. A conditional settings include, only when the
   plugin is already loaded, could retain settings without loading it at startup.
   A separate apply/reapply command would also make recovery easier.
   Evidence: `.build/audit-session.log`; reproducer `.build/audit-session.py`.

2. Pinch ownership is lost when the canvas closes during the gesture.
   `scrollOverview.cpp:2352` stores pinch state/listeners on the canvas object.
   Normal begin/update/end were all consumed. After a consumed begin followed
   by closing the canvas, the update and end were forwarded into Hyprland's
   normal gesture/client path. The matching begin never reached that path.
   No crash occurred in this reproduction. This is an event-sequencing bug,
   not proof of the original workspace-swipe crash's cause. Keep pinch ownership
   until end, like the swipe fix, independent of canvas object lifetime.
   Evidence: `.build/audit-session.log`; observer `.build/audit-gestures.cpp`.

3. Several advertised workspace shortcuts intentionally do nothing.
   Live `plugin:spatialoverview:canvas:places` is false. The settings file binds
   Super+digits, Shift+Super+Tab and Super+scroll to places, but
   `scrollOverview.cpp:10895` returns success without doing anything when places
   are disabled. This also prevents the normal workspace fallback from running.
   The key-guide descriptions should reflect this. Do not silently enable the
   experimental feature to make the labels true.

Other review findings and Mac ergonomics

- The swipe fix consumes all swipes with three or more fingers, including
  four-finger/vertical gestures, and does not expose sensitivity/direction as a
  setting. Restricting/configuring ownership would make future custom gestures
  possible. Existing configured three-finger horizontal swipes are covered.
- Help also opens with Ctrl+/, avoiding the Mac's media-function-key layer.
  The installed hid_apple fnmode is 1. The tuner expects forward Delete for
  reverting a setting; ordinary Backspace edits its search filter instead.
- Middle-drag is awkward on a trackpad. The new three-finger pan and dragging
  empty space in the overview are the available alternatives. Space-pan remains
  deliberately disabled so typing spaces in apps keeps working.
- ARM64 hook teardown logs uninstall failures but does not stop plugin unload:
  `Arm64Hook.hpp:34`. If unpatching ever fails, a target could still point into
  unloaded plugin code. This is a code-review risk only; no such failure was
  observed. The adapter needs failure-path design before treating it as a mature
  portable hook backend.

Verification performed during this audit

| Check | Result |
| --- | --- |
| Fullscreen/X11, two nested monitors, 2x scaling | 43 checks passed |
| Appearance tuner, 2x scaling | 19 checks passed |
| Frame pacing, 2x scaling | 3 checks passed |
| Ordinary pinch begin/update/end | All consumed by canvas |
| Close canvas during pinch | Event-ownership bug reproduced |
| Config reload after manual start | Binding-loss bug reproduced |

Frame probe: plain nested desktop 117.9 fps, canvas 117.7 fps, canvas drawing
an off-screen underlying window 116.1 fps. The respective p95 frame gaps were
16.6, 16.5 and 16.5 ms. These are synthetic nested-compositor measurements,
not battery-life, thermal, or sustained real-workload measurements.

Logs: `.build/audit-fullscreen.log`, `.build/audit-tuner.log`,
`.build/audit-framerate.log`. Tuner persistence passed with its explicit test
config loader; that does not invalidate the manual-start reload issue above.

Additional shutdown finding

Two older failed regression attempts, PIDs 26822 and 31301, had left synthetic
workspace swipes unfinished and crashed while their disposable compositor was
exiting. The test harness ignores the exit status in `Nested.stop`, so this was
not reported as a separate teardown failure. Both cores point to destruction
of a workspace retained by CUnifiedWorkspaceSwipeGesture during process exit.

Reproduced shutdown with an unfinished native swipe after unloading Phantomat.
Only the event-injection helper was loaded. PID 60565 exited with SIGSEGV (-11).
Evidence: `.build/audit-exit.log`, `.build/audit-exit.py`, systemd core metadata.
This establishes that this shutdown failure does not require Phantomat to be
loaded at the time of exit. It is separate from the original live swipe-end
crash. Tests should always end injected gestures, and report abnormal child
exit statuses rather than silently ignoring them.

Limits: no physical trackpad automation, suspend/resume, real external-display
hotplug, battery rundown, or hook-uninstall fault injection. The original live
null-pointer crash was not reproduced. Autostart remains disabled.
