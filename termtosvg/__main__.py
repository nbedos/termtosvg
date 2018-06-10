#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import tempfile

from typing import Any, List, Union

import termtosvg.anim as anim
import termtosvg.term as term

LOG_FILENAME = os.path.join(tempfile.gettempdir(), 'termtosvg.log')


def main(input_fileno=None, output_fileno=None, args=None):
    # type: (Union[int, None], Union[int, None], Union[List[Any], None]) -> None
    if input_fileno is None:
        input_fileno = sys.stdin.fileno()
    if output_fileno is None:
        output_fileno = sys.stdout.fileno()
    if args is None:
        args = sys.argv

    parser = argparse.ArgumentParser(prog=args[0])
    parser.add_argument('--theme', help='color theme used for rendering the terminal session')
    parser.add_argument('--verbose', '-v', action='store_true', help='increase log messages verbosity')
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

    logger.info('Recording started, enter "exit" command or Control-D to end')

    if args.theme is None:
        use_system_theme = True
        theme = 'solarized-light'
    else:
        use_system_theme = False
        theme = args.theme

    columns, lines, theme = term.get_configuration(use_system_theme, theme, output_fileno)
    with term.TerminalMode(input_fileno):
        records = term.record(columns, lines, theme, input_fileno, output_fileno)
        replayed_records = term.replay(records, anim.CharacterCell.from_pyte)
        _, svg_file = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
        anim.render_animation(replayed_records, svg_file)

    logger.info('Recording ended, file is {}'.format(svg_file))

    for handler in logger.handlers:
        handler.close()


if __name__ == '__main__':
    main()
