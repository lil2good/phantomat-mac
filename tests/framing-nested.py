#!/usr/bin/env python3
"""Selected windows fit beneath the visible navigator panel at each output scale."""
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('nav', ROOT / 'tests/navigator-nested.py')
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
n = nav.Nested(sys.argv[1], ROOT / '.build/framing-shots', extra=',initial_zoom=0.72')

def framed(label, listed=False):
    time.sleep(1)
    state = json.loads(n.ctl('spatialoverview'))
    screen = state['screens'][0]
    client = next(c for c in n.clients() if c['title'] == state['selected'])
    zoom = screen['zoom']
    x, y = [(client['at'][i] - screen['view'][i]) * zoom for i in range(2)]
    w, h = [v * zoom for v in client['size']]
    # Default panel: 10px padding on both sides, 60px search, 58px result.
    panel_bottom = height * .075 + 80 + (64 if listed else 0)
    print(label, 'window', [round(v, 1) for v in (x, y, w, h)], 'zoom', zoom, flush=True)
    assert y >= panel_bottom + 15, f'{label}: window overlaps search'
    assert x >= 35 and x + w <= width - 35, f'{label}: horizontal clipping'
    assert y + h <= height - 35, f'{label}: bottom clips'
    expected_center = (panel_bottom + 24 + height - min(48, height * .08)) / 2
    assert abs(y + h / 2 - expected_center) < 12, f'{label}: excess reserved space'
    n.shot(label)
    print('PASS', label, flush=True)
    return zoom

try:
    n.launch()
    monitor = json.loads(n.ctl('monitors', '-j'))[0]
    width, height = monitor['width'] / monitor['scale'], monitor['height'] / monitor['scale']
    n.dispatch('hl.plugin.spatialoverview.overview("toggle all")')
    for app, size in [('spotify', (width * .95, height * 1.2)), ('code', (width * 1.6, height * .65)), ('slack', (width * .4, height * .4))]:
        client = next(c for c in n.clients() if c['class'] == app)
        n.dispatch(f'hl.dsp.window.resize({{x={int(size[0])},y={int(size[1])},window="address:{client["address"]}"}})')
        time.sleep(1)
        n.dispatch(f'hl.plugin.spatialoverview.canvas("search {app}")')
        framed(app + '-search', True)
        n.keys('-k', 'Escape')
        zoom = framed(app + '-clear')
        if app == 'slack':
            assert abs(zoom - .72) < .01, 'small window retains zoom from previous large window'
    assert not n.ctl('configerrors')
finally:
    n.stop()
assert n.proc.returncode == 0, f'abnormal exit: {n.proc.returncode}'
print('ALL PASSED', flush=True)
