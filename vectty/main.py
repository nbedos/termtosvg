#!/usr/bin/env python3

from vectty.anim import AsciiAnimation
import vectty.term as term


"""
Use case: Record a TERMINAL SESSION and RENDER it as an SVG ANIMATION. The idea
is to produce a short (<2 minutes) animation that can be showcased on a project page to
illustrate a use case.

RECORD a TERMINAL SESSION: CAPTURE input from the terminal session and save it together with both 
TIMINGS (when key are pressed or output is written to screen) and CONFIGURATION (how are 
colors rendered by the terminal, bold... etc). All this data will be used to replay the 
terminal session (since we captured the input of the session, not the output).
Once the terminal session has been replayed, it can be CONVERTED FRAME by frame to an 
SVG ANIMATION that mimicks the terminal session.

The terminal session should be SAVED so that it can be replayed and rendered with different
options at any time.
"""

# TODO: Save session in asciinema v2 format

def main():
    columns, lines, theme = term.get_configuration()
    records = term.record(columns, lines, theme)
    replayed_records = term.replay(records, TODO)

    # TODO: move colors to __init__
    a = AsciiAnimation(t.lines, t.columns)
    a.render_animation(replayed_records, '/tmp/test.svg', t.colors)

if __name__ == '__main__':
    main()
