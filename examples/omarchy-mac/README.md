# Session-only setup on Apple Silicon Linux

This fork targets Linux on Apple Silicon, not macOS. It was tested with
Hyprland 0.56.2 on ARM64. Compile against the exact running compositor's headers.
Keep an existing working build available before changing a loaded plugin.

Build from the repository root:

```sh
make -j4 OUT=.build/swipe-fixed/spatialoverview.so
```

The first ARM64 build downloads pinned funchook and Capstone sources. The
historical output directory name is retained by `scripts/test-session.sh`.

Back up `~/.config/hypr/spatialoverview.lua`, then copy the example here to that
path. Add this conditional block to the end of `~/.config/hypr/hyprland.lua`:

```lua
for _, plugin in ipairs(hl.get_loaded_plugins()) do
  if plugin.name == "spatialoverview" then
    dofile(os.getenv("HOME") .. "/.config/hypr/spatialoverview.lua")
    break
  end
end
```

This reapplies settings on theme/config reload without loading Phantomat at login.
Start and stop manually from a terminal in the desktop session:

```sh
scripts/test-session.sh start
scripts/test-session.sh stop
```

`install.sh` uses the upstream automatic-start installation flow. Use the manual
steps above if you want startup to remain disabled.

## Behavior

- Super+Tab opens the searchable canvas. Three-finger swipes pan it.
- New app windows fill the usable screen while leaving the bar visible, and
  occupy the nearest free grid position. Super+T restores the smaller size.
- Hold Shift while dragging to preview and drop onto the grid. Release Shift
  for free placement.
- Apps remain independent windows. Optional tiled groups are not implemented.

## Canvas-aware Omarchy bar

The stock workspace tabs switch native Hyprland workspaces underneath the canvas.
The widget in `workspaces/` instead shows a Canvas button while Phantomat is
active and restores native workspace tabs when it stops. It checks live state
again on every click so a stale tab cannot switch a native workspace.

Copy `workspaces/` to `~/.config/omarchy/plugins/thedev.workspaces/`, then replace
`omarchy.workspaces` with `thedev.workspaces` in the bar layout in
`~/.config/omarchy/shell.json`. Preserve the other layout entries and settings.
Run `omarchy-shell shell rescanPlugins`; if the old widget remains cached, run
`omarchy restart shell`.

## Validation

The ARM64 work includes nested-compositor checks for swipe ownership, cursor
visibility, navigator framing, browser scrolling, Shift snapping, and automatic
placement. `tests/auto-place-fill-nested.py PLUGIN.so` checks multiple full-size
windows, nearest free grid placement, unchanged existing windows, bar visibility,
and size restoration. Run interactive tests one at a time inside a graphical
session. See `ARM64-INVESTIGATION.md` and `MAC-AUDIT.md` for evidence and remaining
limitations. x86-64 hook behavior has not been revalidated by this fork.
