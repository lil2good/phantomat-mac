#!/usr/bin/env python3
"""Check software cursor visibility above the final shader's fixed controls."""
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("nav", ROOT / "tests/navigator-nested.py")
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
def capture(name):
    raw = subprocess.check_output(["grim", *([] if "background" in name else ["-c"]), "-t", "ppm", "-"], env=n.env())
    _, size, _, pixels = raw.split(b"\n", 3)
    width, height = map(int, size.split())
    n.shots.mkdir(parents=True, exist_ok=True)
    (n.shots / (name + ".ppm")).write_bytes(raw)
    return width, height, pixels

def bright(frame, x, y):
    width, height, pixels = frame
    if not (0 <= x < width and 0 <= y < height):
        return False
    return min(pixels[(y * width + x) * 3:(y * width + x) * 3 + 3]) > 200

def pointer(x, y, click=False):
    args = [str(ROOT / ".build/vpointer"), str(width), str(height), "abs", str(x), str(y), "sleep", "200"]
    if click:
        args += ["down", "sleep", "100", "up"]
    subprocess.run(args, env=n.env(), check=True)
    time.sleep(0.3)

plugin = sys.argv[1] if len(sys.argv) > 1 else ROOT / ".build/cursor-fixed/spatialoverview.so"
references = {}
# Cursor backend selection is configured before startup. A runtime config
# toggle can leave the previous backend active and falsely pass this test.
for software in (0, 1):
    n = nav.Nested(plugin, ROOT / f".build/cursor-results/{software}", extra=",initial_zoom=0.15",
                   extra_lua=f"hl.config({{cursor={{no_hardware_cursors={software}}}}})")
    try:
        n.launch()
        n.dispatch('hl.plugin.spatialoverview.overview("toggle all")')
        time.sleep(1)
        monitor = json.loads(n.ctl("monitors", "-j"))[0]
        scale = monitor["scale"]
        width, height = round(monitor["width"] / scale), round(monitor["height"] / scale)
        positions = {"arrange": (width - 297, height - 47), "minimap": (width - 150, height - 95),
                     "search": (width // 2, round(height * 0.075 + 25))}
        for name, (x, y) in positions.items():
            pointer(20, height // 2)
            background = capture(name + "-background")
            pointer(x, y)
            frame = capture(name + "-cursor")
            if not software:
                # Subtract the background to avoid counting labels as cursor pixels.
                mask = [(px, py) for py in range(round(y * scale), round((y + 36) * scale))
                        for px in range(round(x * scale), round((x + 36) * scale))
                        if bright(frame, px, py) and not bright(background, px, py)]
                assert len(mask) > 20, f"{name}: missing hardware cursor reference"
                references[name] = mask
                continue
            mask = references[name]
            coverage = sum(bright(frame, px, py) for px, py in mask) / len(mask)
            assert coverage > 0.85, f"{name}: software cursor obscured or displaced ({coverage:.0%} visible)"
            print(f"PASS cursor above {name}: {coverage:.0%} of reference pixels", flush=True)
            pointer(20, height // 2)
            after = capture(name + "-background-after")
            stale = sum(bright(after, px, py) for px, py in mask) / len(mask)
            assert stale < 0.15, f"{name}: stale cursor remains after moving away ({stale:.0%})"
            print(f"PASS old cursor clears above {name}", flush=True)

        if software:
            client = n.clients()[0]
            n.dispatch(f'hl.dsp.window.move({{x=-1800,y=-1000,window="address:{client["address"]}"}})')
            time.sleep(0.5)
            before = {c["address"]: c["at"] for c in n.clients()}
            pointer(*positions["arrange"], click=True)
            time.sleep(1)
            assert before != {c["address"]: c["at"] for c in n.clients()}, "Tidy click did not arrange windows"
            print("PASS clicking visible Tidy button arranges windows", flush=True)
        assert not n.ctl("configerrors")
    finally:
        n.stop()
    assert n.proc.returncode == 0, f"nested compositor exited with {n.proc.returncode}"
print("ALL PASSED", flush=True)
