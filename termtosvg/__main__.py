#!/usr/bin/env python3
import argparse
import logging
import sys
import tempfile
from typing import List, Tuple, Union

import termtosvg.anim as anim
import termtosvg.config as config
import termtosvg.asciicast as asciicast
import termtosvg.term as term

logger = logging.getLogger('termtosvg')

USAGE = """termtosvg [output_file] [--font FONT] [--theme THEME] [--help] [--verbose]
Record a terminal session and render an SVG animation on the fly
"""
EPILOG = "See also 'termtosvg record --help' and 'termtosvg render --help'"
RECORD_USAGE = """termtosvg record [output_file] [--verbose] [--help]"""
RENDER_USAGE = """termtosvg render input_file [output_file] [--font FONT] [--theme THEME] """ \
               """[--verbose] [--help]"""


def parse(args, themes):
    # type: (List) -> Tuple[Union[None, str], argparse.Namespace]
    # Usage: termtosvg  [output_file] [--font FONT] [--theme THEME] [--verbose]
    font_parser = argparse.ArgumentParser(add_help=False)
    font_parser.add_argument(
        '--font',
        help="font to specify in the CSS portion of the SVG animation (DejaVu Sans Mono, " \
             "Monaco...). If the font is not installed on the viewer's machine, the browser will" \
             " display a default monospaced font instead.",
        metavar='FONT'
    )
    theme_parser = argparse.ArgumentParser(add_help=False)
    theme_parser.add_argument(
        '--theme',
        help='color theme used to render the terminal session ({})'.format(
            ', '.join(themes)),
        choices=themes,
        metavar='THEME'
    )
    verbose_parser = argparse.ArgumentParser(add_help=False)
    verbose_parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='increase log messages verbosity'
    )
    parser = argparse.ArgumentParser(
        prog='termtosvg',
        parents=[font_parser, theme_parser, verbose_parser],
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
            # Usage: termtosvg render [--font FONT] [--theme THEME] [--verbose] input_file [output_file]
            parser = argparse.ArgumentParser(
                description='render an asciicast recording as an SVG animation',
                parents=[font_parser, theme_parser, verbose_parser],
                usage=RENDER_USAGE
            )
            parser.add_argument(
                'input_file',
                help='recording of a terminal session in asciicast v1 or v2 format'
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

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.handlers = [console_handler]
    logger.setLevel(logging.INFO)

    configuration = config.init_read_conf()
    available_themes = config.CaseInsensitiveDict(**configuration)
    del available_themes['global']

    command, args = parse(args[1:], available_themes)

    if args.verbose:
        _, log_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.log')
        file_handler = logging.FileHandler(filename=log_filename, mode='w')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.handlers.append(file_handler)
        logger.info('Logging to {}'.format(log_filename))

    if command == 'record':
        logger.info('Recording started, enter "exit" command or Control-D to end')
        if args.output_file is None:
            _, cast_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.cast')
        else:
            cast_filename = args.output_file

        columns, lines = term.get_terminal_size(output_fileno)
        with term.TerminalMode(input_fileno):
            records = term.record(columns, lines, input_fileno, output_fileno)
            with open(cast_filename, 'w') as cast_file:
                for record in records:
                    print(record.to_json_line(), file=cast_file)

        logger.info('Recording ended, cast file is {}'.format(cast_filename))
    elif command == 'render':
        logger.info('Rendering started')
        if args.output_file is None:
            _, svg_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
        else:
            svg_filename = args.output_file

        if args.font is None:
            font = configuration['GLOBAL']['font']
        else:
            font = args.font

        fallback_theme_name = configuration['GLOBAL']['theme']
        fallback_theme = configuration[fallback_theme_name]
        cli_theme = configuration.get(args.theme)

        records = asciicast.read_records(args.input_file)
        replayed_records = term.replay(records=records,
                                       from_pyte_char=anim.CharacterCell.from_pyte,
                                       override_theme=cli_theme,
                                       fallback_theme=fallback_theme)
        anim.render_animation(replayed_records, svg_filename, font)

        logger.info('Rendering ended, SVG animation is {}'.format(svg_filename))
    else:
        # No command passed: record and render on the fly
        logger.info('Recording started, enter "exit" command or Control-D to end')
        if args.output_file is None:
            _, svg_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
        else:
            svg_filename = args.output_file

        columns, lines = term.get_terminal_size(output_fileno)

        if args.font is None:
            font = configuration['GLOBAL']['font']
        else:
            font = args.font

        fallback_theme_name = configuration['GLOBAL']['theme']
        fallback_theme = configuration[fallback_theme_name]
        cli_theme = configuration.get(args.theme)
        with term.TerminalMode(input_fileno):
            records = term.record(columns, lines, input_fileno, output_fileno)
            replayed_records = term.replay(records=records,
                                           from_pyte_char=anim.CharacterCell.from_pyte,
                                           override_theme=cli_theme,
                                           fallback_theme=fallback_theme)
            anim.render_animation(replayed_records, svg_filename, font)

        logger.info('Recording ended, SVG animation is {}'.format(svg_filename))

    for handler in logger.handlers:
        handler.close()


if __name__ == '__main__':
    main()
