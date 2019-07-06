"""Command line interface of termtosvg"""

import argparse
import logging
import os
import shlex
import sys
import tempfile

import termtosvg.config
import termtosvg.anim

logger = logging.getLogger('termtosvg')

DEFAULT_LOOP_DELAY = 1000

USAGE = """termtosvg [output_path] [-c COMMAND] [-D DELAY] [-g GEOMETRY]
                 [-m MIN_DURATION] [-M MAX_DURATION] [-s] [-t TEMPLATE] [-h]

Record a terminal session and render an SVG animation on the fly
"""
EPILOG = "See also 'termtosvg record --help' and 'termtosvg render --help'"
RECORD_USAGE = "termtosvg record [output_path] [-c COMMAND] [-g GEOMETRY] [-h]"
RENDER_USAGE = """termtosvg render input_file [output_path] [-D DELAY]
                 [-m MIN_DURATION] [-M MAX_DURATION] [-s] [-t TEMPLATE] [-h]"""


def integral_duration_validation(duration):
    if duration.lower().endswith('ms'):
        duration = duration[:-len('ms')]

    if duration.isdigit() and int(duration) >= 1:
        return int(duration)
    raise ValueError('duration must be an integer greater than 0')


def parse(args, templates, default_template, default_geometry, default_min_dur,
          default_max_dur, default_cmd, default_loop_delay):
    """Parse command line arguments

    :param args: Arguments to parse
    :param templates: Mapping between template names and templates
    :param default_template: Name of the default template
    :param default_geometry: Default geometry of the screen
    :param default_min_dur: Default minimal duration between frames in
    milliseconds
    :param default_max_dur: Default maximal duration between frames in
    milliseconds
    :param default_max_dur: Default maximal duration between frames in
    milliseconds
    :param default_cmd: Default program (with argument list) recorded
    :param default_loop_delay: Duration of the pause between two consecutive
    loops of the animation in milliseconds
    :return: Tuple made of the subcommand called (None, 'render' or 'record')
    and all parsed
    arguments
    """
    command_parser = argparse.ArgumentParser(add_help=False)
    command_parser.add_argument(
        '-c', '--command',
        help=(('specify the program to record with optional arguments '
               '(default: {})').format(default_cmd)),
        default=default_cmd,
        metavar='COMMAND',
    )

    still_frames_parser = argparse.ArgumentParser(add_help=False)
    still_frames_parser.add_argument(
        '-s', '--still-frames',
        help='output still frames instead of an animation. ',
        action='store_true'
    )

    template_parser = argparse.ArgumentParser(add_help=False)
    template_parser.add_argument(
        '-t', '--template',
        help=('set the SVG template used for rendering the SVG animation. '
              'TEMPLATE may either be one of the default templates ({}) '
              'or a path to a valid template.').format(', '.join(templates)),
        type=lambda name: termtosvg.anim.validate_template(name, templates),
        default=default_template,
        metavar='TEMPLATE'
    )
    geometry_parser = argparse.ArgumentParser(add_help=False)
    geometry_parser.add_argument(
        '-g', '--screen-geometry',
        help='geometry of the terminal screen used for rendering the animation.'
             ' The geometry must be given as the number of columns and the '
             'number of rows on the screen separated by the character "x". '
             'For example "82x19" for an 82 columns by 19 rows screen.',
        metavar='GEOMETRY',
        default=default_geometry,
        type=termtosvg.config.validate_geometry
    )
    min_duration_parser = argparse.ArgumentParser(add_help=False)
    min_duration_parser.add_argument(
        '-m', '--min-frame-duration',
        type=integral_duration_validation,
        metavar='MIN_DURATION',
        default=default_min_dur,
        help=('minimum duration of a frame in milliseconds (default: {}ms)'
              .format(default_min_dur))
    )

    if default_max_dur:
        default_max_dur_label = '{}ms'.format(default_max_dur)
    else:
        default_max_dur_label = 'No maximum value'

    max_duration_parser = argparse.ArgumentParser(add_help=False)
    max_duration_parser.add_argument(
        '-M', '--max-frame-duration',
        type=integral_duration_validation,
        metavar='MAX_DURATION',
        default=default_max_dur,
        help=('maximum duration of a frame in milliseconds (default: {})'
              .format(default_max_dur_label))
    )

    loop_delay_parser = argparse.ArgumentParser(add_help=False)
    loop_delay_parser.add_argument(
        '-D', '--loop-delay',
        type=integral_duration_validation,
        metavar='DELAY',
        default=default_loop_delay,
        help=(('duration in milliseconds of the pause between two consecutive '
               'loops of the animation (default: {}ms)')
              .format(default_loop_delay))
    )

    parser = argparse.ArgumentParser(
        prog='termtosvg',
        parents=[command_parser, loop_delay_parser, geometry_parser, min_duration_parser,
                 max_duration_parser, still_frames_parser, template_parser],
        usage=USAGE,
        epilog=EPILOG
    )
    parser.add_argument(
        'output_path',
        nargs='?',
        help='optional filename of the SVG animation. If --still-frame is '
             'specified, output_path should be the path of the directory where '
             'still frames will be stored. If missing, a random path '
             'will be automatically generated.',
        metavar='output_path'
    )
    if args:
        if args[0] == 'record':
            parser = argparse.ArgumentParser(
                description='record the session to a file in asciicast v2 format',
                parents=[command_parser, geometry_parser],
                usage=RECORD_USAGE
            )
            parser.add_argument(
                'output_path',
                nargs='?',
                help='optional filename of the cast file. If missing, a random '
                     'path will be automatically generated.',
                metavar='output_path'
            )
            return args[0], parser.parse_args(args[1:])

        if args[0] == 'render':
            parser = argparse.ArgumentParser(
                description='render an asciicast recording as an SVG animation',
                parents=[loop_delay_parser,  min_duration_parser,
                         max_duration_parser, still_frames_parser, template_parser],
                usage=RENDER_USAGE
            )
            parser.add_argument(
                'input_file',
                help='recording of a terminal session in asciicast v1 or v2 format'
            )
            parser.add_argument(
                'output_path',
                nargs='?',
                help='optional filename of the SVG animation. If --still-frame '
                     'is specified, output_path should be the path of the '
                     'directory where still frames will be stored. If '
                     'missing, a random path will be automatically generated.',
                metavar='output_path'
            )
            return args[0], parser.parse_args(args[1:])

    return None, parser.parse_args(args)


def record_subcommand(process_args, geometry, input_fileno, output_fileno,
                      cast_filename):
    """Save a terminal session as an asciicast recording"""
    from termtosvg.term import get_terminal_size, TerminalMode, record
    logger.info('Recording started, enter "exit" command or Control-D to end')
    if geometry is None:
        columns, lines = get_terminal_size(output_fileno)
    else:
        columns, lines = geometry
    with TerminalMode(input_fileno):
        # Do not write anything to stdout (print, logger...) while in this
        # context manager if the output of the process is set to stdout. We
        # do not want two processes writing to the same terminal.
        records = record(process_args, columns, lines, input_fileno,
                         output_fileno)
        with open(cast_filename, 'w') as cast_file:
            for record_ in records:
                print(record_.to_json_line(), file=cast_file)
    logger.info('Recording ended, cast file is {}'.format(cast_filename))


def render_subcommand(still, template, cast_filename, output_path,
                      min_frame_duration, max_frame_duration, loop_delay):
    """Render the animation from an asciicast recording"""
    from termtosvg.asciicast import read_records
    from termtosvg.term import timed_frames

    logger.info('Rendering started')
    asciicast_records = read_records(cast_filename)
    geometry, frames = timed_frames(asciicast_records, min_frame_duration,
                                    max_frame_duration, loop_delay)
    if still:
        termtosvg.anim.render_still_frames(frames=frames,
                                           geometry=geometry,
                                           directory=output_path,
                                           template=template)
        logger.info('Rendering ended, SVG frames are located at {}'
                    .format(output_path))
    else:
        termtosvg.anim.render_animation(frames=frames,
                                        geometry=geometry,
                                        filename=output_path,
                                        template=template)
        logger.info('Rendering ended, SVG animation is {}'.format(output_path))


def record_render_subcommand(process_args, still, template, geometry,
                             input_fileno, output_fileno, output_path,
                             min_frame_duration, max_frame_duration,
                             loop_delay):
    """Record and render the animation on the fly"""
    from termtosvg.term import get_terminal_size, TerminalMode, record, timed_frames

    logger.info('Recording started, enter "exit" command or Control-D to end')
    if geometry is None:
        columns, lines = get_terminal_size(output_fileno)
    else:
        columns, lines = geometry
    with TerminalMode(input_fileno):
        # Do not write anything to stdout (print, logger...) while in this
        # context manager if the output of the process is set to stdout. We
        # do not want two processes writing to the same terminal.
        asciicast_records = record(process_args, columns, lines, input_fileno,
                                   output_fileno)
        geometry, frames = timed_frames(asciicast_records, min_frame_duration,
                                        max_frame_duration, loop_delay)

        if still:
            termtosvg.anim.render_still_frames(frames, geometry, output_path,
                                               template)
            end_msg = 'Rendering ended, SVG frames are located at {}'
        else:
            termtosvg.anim.render_animation(frames, geometry, output_path,
                                            template)
            end_msg = 'Rendering ended, SVG animation is {}'

    logger.info(end_msg.format(output_path))


def main(args=None, input_fileno=None, output_fileno=None):
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

    templates = termtosvg.config.default_templates()
    default_template = 'gjm8' if 'gjm8' in templates else sorted(templates)[0]
    default_cmd = os.environ.get('SHELL', 'sh')
    command, args = parse(args[1:], templates, default_template, None, 1,
                          None, default_cmd, DEFAULT_LOOP_DELAY)

    if command == 'record':
        if args.output_path is None:
            _, cast_filename = tempfile.mkstemp(prefix='termtosvg_',
                                                suffix='.cast')
        else:
            cast_filename = args.output_path
        process_args = shlex.split(args.command)
        record_subcommand(process_args, args.screen_geometry, input_fileno,
                          output_fileno, cast_filename)
    elif command == 'render':
        if args.output_path is None:
            if args.still_frames:
                output_path = tempfile.mkdtemp(prefix='termtosvg_')
            else:
                _, output_path = tempfile.mkstemp(prefix='termtosvg_',
                                                  suffix='.svg')
        else:
            output_path = args.output_path
            if args.still_frames:
                try:
                    os.mkdir(output_path)
                except FileExistsError:
                    if not os.path.isdir(output_path):
                        raise

        render_subcommand(args.still_frames, args.template, args.input_file,
                          output_path, args.min_frame_duration,
                          args.max_frame_duration, args.loop_delay)
    else:
        if args.output_path is None:
            if args.still_frames:
                output_path = tempfile.mkdtemp(prefix='termtosvg_')
            else:
                _, output_path = tempfile.mkstemp(prefix='termtosvg_',
                                                  suffix='.svg')
        else:
            output_path = args.output_path
            if args.still_frames:
                try:
                    os.mkdir(output_path)
                except FileExistsError:
                    if not os.path.isdir(output_path):
                        raise

        process_args = shlex.split(args.command)
        record_render_subcommand(process_args, args.still_frames, args.template,
                                 args.screen_geometry, input_fileno,
                                 output_fileno, output_path,
                                 args.min_frame_duration,
                                 args.max_frame_duration,
                                 args.loop_delay)

    for handler in logger.handlers:
        handler.close()
