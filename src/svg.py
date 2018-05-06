import os
import pty
import re
import svgwrite
import svgwrite.text
import svgwrite.path
import svgwrite.animate
import time
import datetime

BUFFER_SIZE = 1


def record():
    shell = os.environ.get('SHELL', 'sh')
    records = []
    timings = []

    def read(fd):
        data = os.read(fd, BUFFER_SIZE)
        records.append(data)
        timings.append((data, datetime.datetime.now()))
        return data

    header = 'Script started on {}'.format(time.asctime())
    print(header)
    records.append(header.encode())

    pty.spawn(shell, read)

    footer = 'Script done on {}'.format(time.asctime())
    records.append(footer.encode())
    print(footer)

    return b''.join(records), timings


def convert(timings):
    """
    https://en.wikipedia.org/wiki/ANSI_escape_code
    """
    csi_re = '(?P<CSI_escape_sequence>\x1b\[)' \
             '(?P<CSI_parameter_bytes>[0-9:;<=>?]*)' \
             '(?P<CSI_intermediate_bytes>[!"#$%&\'()*+,-./]*)' \
             '(?P<CSI_final_byte>[@A-Z\[\\\\\]^_`a-z{|}~])'

    apc_re = '(?P<APC_escape_sequence>\x1b_)' \
             '(?P<APC_string>.*?)' \
             '(?P<APC_termination>\x1b\\\\)'

    master_re = '({})'.format('|'.join({csi_re, apc_re}))
    master_pattern = re.compile(master_re.encode('utf-8'))

    bs = b''.join(b for b, _  in timings)
    match_indices = (range(*match.span(0)) for match in master_pattern.finditer(bs))
    blacklist = set.union(*map(set, match_indices))
    new_timings = [timings[i] for i in range(len(timings)) if i not in blacklist]

    return new_timings



# TODO: Might replace this with a read call with a timeout
def group_by_time(timings, threshold=datetime.timedelta(milliseconds=50)):
    grouped_timings = []
    current_string = []
    current_time = None
    for character, t in timings:
        if current_time is not None:
            assert t - current_time >= datetime.timedelta(seconds=0)
            if t - current_time > threshold:
                # Flush current string
                s = b''.join(current_string)
                grouped_timings.append((s, current_time))
                current_string = []

        current_string.append(character)
        current_time = t

    if current_string:
        grouped_timings.append((b''.join(current_string), current_time))

    return grouped_timings


def group_by_line(timings):
    lines = [[]]
    for bstring, time in timings:
        end_of_line, *next_lines = bstring.split(b'\n')
        if end_of_line:
            lines[-1].append((end_of_line, time))

        for line in next_lines:
            lines.append([])
            if line:
                lines[-1].append((line, time))

    return [line for line in lines if line]


# TODO: begin_time = last_round.end_time
def draw(lines, filename: str):
    style = 'font-family: Dejavu Sans Mono; font-style: normal; font-size: 48px;'
    font_size, font_width = 48, 32
    dwg = svgwrite.Drawing(filename, (900, 900), debug=True)
    paragraph = dwg.add(dwg.g(style=style))
    for counter, line in enumerate(lines):
        partial_text = ''
        animation = []
        begin_time = line[0][1]
        end_time = line[-1][1]
        total_time = (end_time - begin_time).total_seconds()
        row = 2 * font_size + counter * (font_size + 2)
        for item, time in line:
            if end_time == begin_time:
                # For discrete animations, the first value in the keyTimes list
                # must be 0 (SVG specification)
                keytime = 0.0
            else:
                elapsed_time = (time - begin_time).total_seconds()
                keytime = elapsed_time / total_time

            assert 0.0 <= keytime <= 1.0

            print(partial_text)
            partial_text = partial_text + item.decode('utf-8')
            end = font_width * len(partial_text)
            d = 'm0,{row} h{end}'.format(row=row, end=end)
            animation.append((d, keytime))

        values, keytimes = zip(*animation)

        # row = base line + counter * (font_size + 2)

        # duration must not be 0
        extra = {
            'begin': 'animation_{}.end'.format(counter-1) if counter > 0 else '0s',
            'dur': '{}s'.format(total_time) if total_time != 0 else '0.01s',
            'fill': 'freeze',
            'id': 'animation_{}'.format(counter),
            'values': ';'.join(values),
            'keyTimes': ';'.join(map(str, keytimes))
        }
        hidden_path = 'm0,{row} h0'.format(row=row)
        path = svgwrite.path.Path(d=hidden_path, id='path_{}'.format(counter))
        path.add(svgwrite.animate.Animate('d', **extra))
        paragraph.add(path)

        text = svgwrite.text.Text('')
        text.add(svgwrite.text.TextPath(path=path, text=partial_text))
        paragraph.add(text)

    dwg.save()


if __name__ == '__main__':
    _, timings = record()
    converted = convert(timings)
    by_time = group_by_time(converted)
    by_line = group_by_line(by_time)
    draw(by_line, '/tmp/live.svg')



