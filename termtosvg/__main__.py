#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import tempfile

from typing import Any, List, Union

import termtosvg.anim as anim
import termtosvg.term as term
import termtosvg.asciicast as asciicast

LOG_FILENAME = os.path.join(tempfile.gettempdir(), 'termtosvg.log')


def main(input_fileno=None, output_fileno=None, args=None):
    # type: (Union[int, None], Union[int, None], Union[List[Any], None]) -> None
    if input_fileno is None:
        input_fileno = sys.stdin.fileno()
    if output_fileno is None:
        output_fileno = sys.stdout.fileno()
    if args is None:
        args = sys.argv

    default_themes = sorted(term.default_themes())
    parser = argparse.ArgumentParser(prog='termtosvg')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='increase log messages verbosity')
    subparsers = parser.add_subparsers(help='command', dest='command')

    # Subcommand RECORD: termtosvg record [output_filename] [--verbose]
    parser_record = subparsers.add_parser('record', help='record the session to a file in asciicast'
                                                         ' v2 format')
    parser_record.add_argument('filename', nargs='?', help='optional output file; if missing, a '
                               'random temporary filename will be automatically generated')

    # Subcommand RENDER: termtosvg render input_filename  [--verbose]
    parser_render = subparsers.add_parser('render', help='render an asciicast recording as an SVG '
                                          'animation')
    parser_render.add_argument('filename', help='recording of the terminal session in asciicast v2 format')

    args = parser.parse_args(args[1:])


    logger = logging.getLogger(parser.prog)
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

    use_system_theme = True
    theme = 'solarized-light'

    # TODO: Gestion des thèmes: quand obligatoire ??
    if args.command == 'record':
        logger.info('Recording started, enter "exit" command or Control-D to end')
        if args.filename is not None:
            cast_filename = args.filename
        else:
            _, cast_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.cast')

        columns, lines, theme = term.get_configuration(use_system_theme, theme, output_fileno)
        with term.TerminalMode(input_fileno):
            records = term.record(columns, lines, theme, input_fileno, output_fileno)
            with open(cast_filename, 'w') as cast_file:
                for record in records:
                    print(record.to_json_line(), file=cast_file)

        logger.info('Recording ended, cast file is {}'.format(cast_filename))
    elif args.command == 'render':
        def rec_gen():
            with open(args.filename, 'r') as cast_file:
                for line in cast_file:
                    yield asciicast.AsciiCastRecord.from_json_line(line)

        logger.info('Rendering started')
        _, svg_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
        replayed_records = term.replay(rec_gen(), anim.CharacterCell.from_pyte)
        anim.render_animation(replayed_records, svg_filename)

        logger.info('Rendering ended, SVG animation is {}'.format(svg_filename))
    else:
        # No command passed: record and render on the fly
        logger.info('Recording started, enter "exit" command or Control-D to end')
        _, svg_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')

        columns, lines, theme = term.get_configuration(use_system_theme, theme, output_fileno)
        with term.TerminalMode(input_fileno):
            records = term.record(columns, lines, theme, input_fileno, output_fileno)
            replayed_records = term.replay(records, anim.CharacterCell.from_pyte)
            anim.render_animation(replayed_records, svg_filename)

        logger.info('Recording ended, SVG animation is {}'.format(svg_filename))

    for handler in logger.handlers:
        handler.close()


if __name__ == '__main__':
    main()
