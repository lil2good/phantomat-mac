#!/usr/bin/env python3
"""Inject real swipe events into a disposable compositor only."""
import importlib.util
import json
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("navigator", root / "tests/navigator-nested.py")
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
n = nav.Nested(sys.argv[1] if len(sys.argv) > 1 else root / "spatialoverview.so",
               root / ".build/swipe-results", extra_lua='''
hl.gesture({fingers=3,direction="horizontal",action="workspace"})
''')
try:
    n.launch()
    print(n.ctl("plugin", "load", str(root / ".build/swipe-probe.so")), flush=True)
    assert "Plugin swipeprobe " in n.ctl("plugin", "list")
    for i, client in enumerate(n.clients()):
        n.dispatch(f'hl.dsp.window.move({{workspace="{i % 3 + 1}",window="address:{client["address"]}",follow=false}})')
    assert n.ctl("swipeprobe", "begin") == "idle"
    assert n.ctl("swipeprobe", "update", "-80") == "active"
    result = n.ctl("dispatch", 'hl.plugin.spatialoverview.overview("open all")', check=False)
    assert "error" in result
    assert not json.loads(n.ctl("spatialoverview"))["screens"], "opening canvas must wait for native swipe"
    assert n.ctl("swipeprobe", "end") == "idle"
    print("PASS canvas cannot open midway through native swipe", flush=True)
    n.dispatch('hl.plugin.spatialoverview.overview("toggle all")')
    time.sleep(1)
    n.keys("-k", "Escape")
    time.sleep(0.5)
    before = json.loads(n.ctl("spatialoverview"))["screens"][0]["view"]
    for delta in [-80, 80, -10, 10] * 3:
        print("swipe", delta, flush=True)
        assert n.ctl("swipeprobe", "begin") == "idle"
        for _ in range(5):
            assert n.ctl("swipeprobe", "update", str(delta)) == "idle", "native workspace swipe ran on canvas"
            time.sleep(0.03)
        assert n.ctl("swipeprobe", "end") == "idle"
        time.sleep(0.3)
        after = json.loads(n.ctl("spatialoverview"))["screens"][0]["view"]
        assert before[:2] != after[:2], "swipe did not pan canvas"
        before = after
    assert n.proc.poll() is None
    print("PASS repeated canvas swipes", flush=True)
    n.ctl("swipeprobe", "begin")
    assert n.ctl("swipeprobe", "update", "40") == "idle"
    n.dispatch('hl.plugin.spatialoverview.overview("close all")')
    time.sleep(1)
    assert n.ctl("swipeprobe", "update", "40") == "idle"
    assert n.ctl("swipeprobe", "end") == "idle"
    assert not json.loads(n.ctl("spatialoverview"))["screens"]
    print("PASS canvas closes during swipe without leaking its end", flush=True)
    n.ctl("swipeprobe", "begin")
    assert n.ctl("swipeprobe", "update", "-80") == "active"
    assert n.ctl("swipeprobe", "end") == "idle"
    print("PASS normal workspace swipe restored", flush=True)
finally:
    n.stop()
