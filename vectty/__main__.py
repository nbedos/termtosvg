#!/usr/bin/env python3
import argparse
import sys

import vectty.anim as anim
import vectty.term as term


"""
Use case: Record a TERMINAL SESSION and RENDER it as an SVG ANIMATION. The idea
is to produce a short (<2 minutes) animation that can be showcased on a project page to
illustrate a use case.
"""


def main(input_fileno=None, output_fileno=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--theme', help='color theme used for rendering the terminal session')
    args = parser.parse_args()

    if input_fileno is None:
        input_fileno = sys.stdin.fileno()
    if output_fileno is None:
        output_fileno = sys.stdout.fileno()

    columns, lines, theme = term.get_configuration(theme=args.theme)
    records = term.record(columns, lines, theme, input_fileno, output_fileno)
    replayed_records = term.replay(records, anim.CharacterCell.from_pyte)
    anim.render_animation(replayed_records, '/tmp/test.svg')


if __name__ == '__main__':
    main()
