#!/usr/bin/env bash
# Session-only test: never writes a startup entry or the user's config.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$project_dir/scripts/common.sh"
plugin="$project_dir/.build/swipe-fixed/spatialoverview.so"
if ! hyprland_session; then
  echo "Run this from a terminal inside your current Hyprland session." >&2
  exit 1
fi
case "${1:-start}" in
  start)
    if spatialoverview_loaded; then
      echo "Phantomat is already loaded. Run this script with stop first."
      exit 1
    fi
    [[ -f "$plugin" ]]
    hyprctl plugin load "$plugin"
    spatialoverview_loaded || exit 1
    hyprctl repl 'dofile(os.getenv("HOME") .. "/.config/hypr/spatialoverview.lua")'
    hyprctl dispatch 'hl.plugin.spatialoverview.overview("open all")'
    echo "Phantomat loaded for this session. Three-finger swipes pan the canvas."
    echo "Stop: $project_dir/scripts/test-session.sh stop"
    ;;
  stop)
    if spatialoverview_loaded; then
      safe_unload
    fi
    hyprctl reload
    errors=$(hyprctl configerrors)
    if [[ -n "$errors" ]]; then
      printf '%s\n' "$errors" >&2
      exit 1
    fi
    echo "Phantomat stopped; normal bindings restored."
    ;;
  *) echo "Usage: $0 [start|stop]" >&2; exit 2 ;;
esac
