#!/usr/bin/env python3
"""Verify the manual start/stop script without loading the parent compositor."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("navigator", root / "tests/navigator-nested.py")
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
n = nav.Nested(root / ".build/swipe-fixed/spatialoverview.so", root / ".build/session-results")
try:
    n.launch()
    env = n.env()
    env["HYPRLAND_INSTANCE_SIGNATURE"] = n.sig
    env["XDG_STATE_HOME"] = n.state
    script = str(root / "scripts/test-session.sh")
    subprocess.run([script, "stop"], env=env, check=True)
    # The normal fixture loads a plugin on reload; remove that declaration
    # so this child now models the user's startup configuration.
    config = Path(n.tmp.name) / "nested.lua"
    config.write_text(config.read_text().replace('hl.plugin.load(plugin_path)', '-- manual loading only'))
    subprocess.run([script, "stop"], env=env, check=True)
    assert "Plugin spatialoverview " not in n.ctl("plugin", "list")
    subprocess.run([script, "start"], env=env, check=True)
    assert json.loads(n.ctl("spatialoverview"))["screens"]
    assert not n.ctl("configerrors")
    subprocess.run([script, "stop"], env=env, check=True)
    assert "Plugin spatialoverview " not in n.ctl("plugin", "list")
    assert n.proc.poll() is None
    print("PASS session start and stop; no startup load", flush=True)
finally:
    n.stop()
