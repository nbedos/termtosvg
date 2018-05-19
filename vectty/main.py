#!/usr/bin/env python3

from vectty.anim import AsciiAnimation
from vectty.term import TerminalSession


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

# TODO: Factorize x attribute of texts elements (note: it seems it can't be done with CSS)
# TODO: Since we're not using textLength after all, go back to one line = one <text> (+ <tspan>s)
# TODO: Group lines with the same timings in a single group with a unique animation
# TODO: Remove frame rendering code
# TODO: AsciiBuffer type (based on mappings)
# TODO: Use viewbox to render a portion of the history
# TODO: Save session in asciinema v2 format
# TODO: Use screen buffer difference for cell targeted updating, or just use screen.dirty from pyte


def main():
    t = TerminalSession()
    t.get_configuration()
    timings = t.record()
    squashed_timings = t.replay(timings)

    a = AsciiAnimation()
    line_timings = a._line_timings(squashed_timings)
    a.render_animation(line_timings, '/tmp/test.svg', t.colors)


if __name__ == '__main__':
    main()
