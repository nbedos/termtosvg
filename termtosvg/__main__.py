#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import tempfile

from typing import List, Tuple, Union

import termtosvg.anim as anim
import termtosvg.term as term
import termtosvg.asciicast as asciicast

LOG_FILENAME = os.path.join(tempfile.gettempdir(), 'termtosvg.log')

verbose_parser = argparse.ArgumentParser(add_help=False)
verbose_parser.add_argument(
    '-v',
    '--verbose',
    action='store_true',
    help='increase log messages verbosity'
)

default_themes = sorted(term.default_themes())
theme_parser = argparse.ArgumentParser(add_help=False)
theme_parser.add_argument(
    '--theme',
    help='color theme used to render the terminal session ({})'.format(', '.join(default_themes)),
    choices=default_themes,
    metavar='THEME'
)

USAGE = """termtosvg [output_file] [--theme THEME] [--help] [--verbose]

Record a terminal session and render an SVG animation on the fly
"""

EPILOG = "See also 'termtosvg record --help' and 'termtosvg render --help'"
RECORD_USAGE = """termtosvg record [output_file] [--verbose] [--help]"""
RENDER_USAGE = """termtosvg render input_file [output_file] [--theme THEME] [--verbose] [--help]"""

def parse(args):
    # type: (List) -> Tuple[Union[None, str], argparse.Namespace]
    # Usage: termtosvg [--theme THEME] [--verbose] [output_file]
    parser = argparse.ArgumentParser(
        prog='termtosvg',
        parents=[theme_parser, verbose_parser],
        usage=USAGE,
        epilog=EPILOG
    )
    parser.add_argument(
        'output_file',
        nargs='?',
        help='optional filename of the SVG animation; if missing, a random filename will be '
        'automatically generated',
        metavar='output_file'
    )
    if args:
        if args[0] == 'record':
            # Usage: termtosvg record [--verbose] [output_file]
            parser = argparse.ArgumentParser(
                description='record the session to a file in asciicast v2 format',
                parents=[verbose_parser],
                usage=RECORD_USAGE
            )
            parser.add_argument(
                'output_file',
                nargs='?',
                help='optional filename for the recording; if missing, a random filename will '
                'be automatically generated'
            )
            return 'record', parser.parse_args(args[1:])
        elif args[0] == 'render':
            # Usage: termtosvg render [--theme THEME] [--verbose] input_file [output_file]
            parser = argparse.ArgumentParser(
                description='render an asciicast recording as an SVG animation',
                parents=[theme_parser, verbose_parser],
                usage=RENDER_USAGE
            )
            parser.add_argument(
                'input_file',
                help='recording of the terminal session in asciicast v2 format'
            )
            parser.add_argument(
                'output_file',
                nargs='?',
                help='optional filename for the SVG animation; if missing, a random filename will '
                'be automatically generated',
            )
            return 'render', parser.parse_args(args[1:])

    return None, parser.parse_args(args)


def main(args=None, input_fileno=None, output_fileno=None):
    # type: (List, Union[int, None], Union[int, None]) -> None
    if args is None:
        args = sys.argv
    if input_fileno is None:
        input_fileno = sys.stdin.fileno()
    if output_fileno is None:
        output_fileno = sys.stdout.fileno()

    command, args = parse(args[1:])

    logger = logging.getLogger('termtosvg')
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.handlers = [console_handler]

    if args.verbose:
        file_handler = logging.FileHandler(filename=LOG_FILENAME, mode='w')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.handlers.append(file_handler)
        logger.info('Logging to {}'.format(LOG_FILENAME))

    fallback_theme_name = 'solarized-dark'
    xresources_str = term.default_themes()[fallback_theme_name]
    fallback_theme = asciicast.AsciiCastTheme.from_xresources(xresources_str)

    if command == 'record':
        logger.info('Recording started, enter "exit" command or Control-D to end')
        if args.output_file is None:
            _, cast_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.cast')
        else:
            cast_filename = args.output_file

        columns, lines, theme = term.get_configuration(output_fileno)
        with term.TerminalMode(input_fileno):
            records = term.record(columns, lines, theme, input_fileno, output_fileno)
            with open(cast_filename, 'w') as cast_file:
                for record in records:
                    print(record.to_json_line(), file=cast_file)

        logger.info('Recording ended, cast file is {}'.format(cast_filename))
    elif command == 'render':
        def rec_gen():
            with open(args.input_file, 'r') as cast_file:
                for line in cast_file:
                    yield asciicast.AsciiCastRecord.from_json_line(line)

        logger.info('Rendering started')
        if args.output_file is None:
            _, svg_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
        else:
            svg_filename = args.output_file

        if args.theme is None:
            theme = fallback_theme
        else:
            xresources_str = term.default_themes()[args.theme]
            theme = asciicast.AsciiCastTheme.from_xresources(xresources_str)

        replayed_records = term.replay(rec_gen(), anim.CharacterCell.from_pyte, theme)
        anim.render_animation(replayed_records, svg_filename)

        logger.info('Rendering ended, SVG animation is {}'.format(svg_filename))
    else:
        # No command passed: record and render on the fly
        logger.info('Recording started, enter "exit" command or Control-D to end')
        if args.output_file is None:
            _, svg_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
        else:
            svg_filename = args.output_file

        columns, lines, system_theme = term.get_configuration(output_fileno)

        if args.theme is None:
            if system_theme is None:
                theme = fallback_theme
            else:
                theme = system_theme
        else:
            xresources_str = term.default_themes()[args.theme]
            theme = asciicast.AsciiCastTheme.from_xresources(xresources_str)

        with term.TerminalMode(input_fileno):
            records = term.record(columns, lines, theme, input_fileno, output_fileno)
            replayed_records = term.replay(records, anim.CharacterCell.from_pyte, theme)
            anim.render_animation(replayed_records, svg_filename)

        logger.info('Recording ended, SVG animation is {}'.format(svg_filename))

    for handler in logger.handlers:
        handler.close()


if __name__ == '__main__':
    main()
