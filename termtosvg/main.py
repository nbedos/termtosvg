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

USAGE = """termtosvg [output_file] [-c COMMAND] [-g GEOMETRY] [-m MIN_DURATION]
                 [-M MAX_DURATION] [-t TEMPLATE] [-h]

Record a terminal session and render an SVG animation on the fly
"""
EPILOG = "See also 'termtosvg record --help' and 'termtosvg render --help'"
RECORD_USAGE = """termtosvg record [output_file] [-c COMMAND] [-g GEOMETRY]
                 [-m MIN_DURATION] [-M MAX_DURATION] [-h]"""
RENDER_USAGE = """termtosvg render input_file [output_file] [-m MIN_DURATION]
                 [-M MAX_DURATION] [-t TEMPLATE] [-h]"""


def integral_duration(duration):
    if duration.lower().endswith('ms'):
        duration = duration[:-len('ms')]

    if duration.isdigit() and int(duration) >= 1:
        return int(duration)
    raise ValueError('duration must be an integer greater than 0')


def parse(args, templates, default_template, default_geometry, default_min_dur, default_max_dur,
          default_cmd):
    """Parse command line arguments

    :param args: Arguments to parse
    :param templates: Mapping between template names and templates
    :param default_template: Name of the default template
    :param default_geometry: Default geometry of the screen
    :param default_min_dur: Default minimal duration between frames in milliseconds
    :param default_max_dur: Default maximal duration between frames in milliseconds
    :param default_max_dur: Default maximal duration between frames in milliseconds
    :param default_cmd: Default program (with argument list) recorded
    :return: Tuple made of the subcommand called (None, 'render' or 'record') and all parsed
    arguments
    """
    command_parser = argparse.ArgumentParser(add_help=False)
    command_parser.add_argument(
        '-c', '--command',
        help=('specify the program to record with optional arguments (default: {})'
              .format(default_cmd)),
        default=default_cmd,
        metavar='COMMAND',
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
        help='geometry of the terminal screen used for rendering the animation. The geometry must '
        'be given as the number of columns and the number of rows on the screen separated by the '
        'character "x". For example "82x19" for an 82 columns by 19 rows screen.',
        metavar='GEOMETRY',
        default=default_geometry,
        type=termtosvg.config.validate_geometry
    )
    min_duration_parser = argparse.ArgumentParser(add_help=False)
    min_duration_parser.add_argument(
        '-m', '--min-frame-duration',
        type=integral_duration,
        metavar='MIN_DURATION',
        default=default_min_dur,
        help='minimum duration of a frame in milliseconds (default: {}ms)'.format(default_min_dur)
    )

    if default_max_dur:
        default_max_dur_label = '{}ms'.format(default_max_dur)
    else:
        default_max_dur_label = 'No maximum value'

    max_duration_parser = argparse.ArgumentParser(add_help=False)
    max_duration_parser.add_argument(
        '-M', '--max-frame-duration',
        type=integral_duration,
        metavar='MAX_DURATION',
        default=default_max_dur,
        help=('maximum duration of a frame in milliseconds (default: {})'
              .format(default_max_dur_label))
    )
    parser = argparse.ArgumentParser(
        prog='termtosvg',
        parents=[command_parser, geometry_parser, min_duration_parser, max_duration_parser,
                 template_parser],
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
            parser = argparse.ArgumentParser(
                description='record the session to a file in asciicast v2 format',
                parents=[command_parser, geometry_parser, min_duration_parser, max_duration_parser],
                usage=RECORD_USAGE
            )
            parser.add_argument(
                'output_file',
                nargs='?',
                help='optional filename for the recording; if missing, a random filename will '
                'be automatically generated',
                metavar='output_file'
            )
            return 'record', parser.parse_args(args[1:])
        elif args[0] == 'render':
            parser = argparse.ArgumentParser(
                description='render an asciicast recording as an SVG animation',
                parents=[template_parser, min_duration_parser, max_duration_parser],
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
                metavar='output_file'
            )
            return 'render', parser.parse_args(args[1:])

    return None, parser.parse_args(args)


def record_subcommand(process_args, geometry, input_fileno, output_fileno, cast_filename):
    """Save a terminal session as an asciicast recording"""
    import termtosvg.term
    logger.info('Recording started, enter "exit" command or Control-D to end')
    if geometry is None:
        columns, lines = termtosvg.term.get_terminal_size(output_fileno)
    else:
        columns, lines = geometry
    with termtosvg.term.TerminalMode(input_fileno):
        records = termtosvg.term.record(process_args, columns, lines, input_fileno, output_fileno)
        with open(cast_filename, 'w') as cast_file:
            for record in records:
                print(record.to_json_line(), file=cast_file)
    logger.info('Recording ended, cast file is {}'.format(cast_filename))


def render_subcommand(template, cast_filename, svg_filename, min_frame_duration,
                      max_frame_duration):
    """Render the animation from an asciicast recording"""
    import termtosvg.asciicast
    import termtosvg.term

    logger.info('Rendering started')
    asciicast_records = termtosvg.asciicast.read_records(cast_filename)
    replayed_records = termtosvg.term.replay(records=asciicast_records,
                                             from_pyte_char=termtosvg.anim.CharacterCell.from_pyte,
                                             min_frame_duration=min_frame_duration,
                                             max_frame_duration=max_frame_duration)
    termtosvg.anim.render_animation(records=replayed_records,
                                    filename=svg_filename,
                                    template=template)
    logger.info('Rendering ended, SVG animation is {}'.format(svg_filename))


def record_render_subcommand(process_args, template, geometry, input_fileno, output_fileno,
                             svg_filename, min_frame_duration, max_frame_duration):
    """Record and render the animation on the fly"""
    import termtosvg.term

    logger.info('Recording started, enter "exit" command or Control-D to end')
    if geometry is None:
        columns, lines = termtosvg.term.get_terminal_size(output_fileno)
    else:
        columns, lines = geometry
    with termtosvg.term.TerminalMode(input_fileno):
        asciicast_records = termtosvg.term.record(process_args, columns, lines, input_fileno,
                                                  output_fileno)
        replayed_records = termtosvg.term.replay(records=asciicast_records,
                                                 from_pyte_char=termtosvg.anim.CharacterCell.from_pyte,
                                                 min_frame_duration=min_frame_duration,
                                                 max_frame_duration=max_frame_duration)
        termtosvg.anim.render_animation(records=replayed_records,
                                        filename=svg_filename,
                                        template=template)
    logger.info('Recording ended, SVG animation is {}'.format(svg_filename))


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
    command, args = parse(args[1:], templates, default_template, None, 1, None, default_cmd)

    if command == 'record':
        cast_filename = args.output_file
        if cast_filename is None:
            _, cast_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.cast')
        process_args = shlex.split(args.command)
        record_subcommand(process_args, args.screen_geometry, input_fileno, output_fileno,
                          cast_filename)
    elif command == 'render':
        svg_filename = args.output_file
        if svg_filename is None:
            _, svg_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')

        render_subcommand(args.template, args.input_file, svg_filename, args.min_frame_duration,
                          args.max_frame_duration)
    else:
        svg_filename = args.output_file
        if svg_filename is None:
            _, svg_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')

        process_args = shlex.split(args.command)
        record_render_subcommand(process_args, args.template, args.screen_geometry, input_fileno,
                                 output_fileno, svg_filename, args.min_frame_duration,
                                 args.max_frame_duration)

    for handler in logger.handlers:
        handler.close()
