#!/usr/bin/env python3
"""Keep bar clicks on the canvas while Phantomat owns the desktop."""
import json
import subprocess
import sys


def hyprctl(*args):
    return subprocess.run(['hyprctl', *args], capture_output=True, text=True, timeout=3, check=True).stdout


def canvas_active():
    try:
        state = json.loads(hyprctl('spatialoverview'))
        return any(not screen.get('closing', False) for screen in state['screens'])
    except (json.JSONDecodeError, KeyError, subprocess.CalledProcessError):
        # An unloaded plugin has no state command. Other query failures must
        # not silently turn a canvas click into a native workspace switch.
        plugins = hyprctl('plugin', 'list')
        if 'Plugin spatialoverview ' in plugins:
            raise RuntimeError('Phantomat is loaded but its canvas state is unavailable')
        return False


def main():
    active = canvas_active()
    if len(sys.argv) == 1:
        print(json.dumps({'active': active}))
        return
    workspace = int(sys.argv[1])
    if not 0 <= workspace <= 10:
        raise ValueError('workspace must be between 0 and 10')
    if active:
        hyprctl('dispatch', 'hl.plugin.spatialoverview.overview("toggle all")')
    elif workspace:
        hyprctl('dispatch', f'hl.dsp.focus({{ workspace = "{workspace}" }})')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
