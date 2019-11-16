% TERMTOSVG(1)
% Nicolas Bedos
% July 2019

## SYNOPSIS
**termtosvg** [output_path] [-c COMMAND] [-D DELAY] [-g GEOMETRY] [-m MIN_DURATION] [-M MAX_DURATION] [-s] [-t TEMPLATE] [--help]

**termtosvg record** [output_path] [-c COMMAND] [-g GEOMETRY] [-h]

**termtosvg render** *input_file* [output_path] [-D DELAY] [-m MIN_DURATION] [-M MAX_DURATION] [-s] [-t TEMPLATE] [-h]

### DESCRIPTION
termtosvg makes recordings of terminal sessions in animated SVG format.

#### COMMANDS
The default behavior of termtosvg is to render an SVG animation of a shell
session.  If no output filename is provided, a random temporary filename will
be automatically generated.

##### termtosvg record
Record a terminal session in asciicast v2 format. The recording is a text file which
contains timing information as well as what was displayed on the screen during the
terminal session. It may be edited to alter the timing of the recording or the information
displayed on the screen of the terminal.

##### termtosvg render
Render an animated SVG from a recording in asciicast v1 or v2 format. This allows
rendering in SVG format of any recording made with asciinema. Rendering of still frames
is also possible.

## OPTIONS

#### -c, --command=COMMAND
Specify the program to record with optional arguments. COMMAND must be a string listing the
program to execute together will all arguments to be made available to the program. For example
`--command='python -h'` would make termtosvg record the usage of the Python interpreter. If this
option is not set, termtosvg will record the program specified by the $SHELL environment variable
or `/bin/sh`.

#### -D, --loop-delay=DELAY
Duration of the delay between two consecutive loops of the animation in milliseconds.

##### -g, --screen-geometry=GEOMETRY
Geometry of the terminal screen used for rendering the animation. The geometry must
be given as the number of columns and the number of rows on the screen separated by
the character "x". For example "82x19" for an 82 columns by 19 rows screen.

##### -h, --help
Print usage and exit

##### -m, --min-frame-duration=MIN_DURATION
Set the minimum duration of a frame in milliseconds. Frames lasting less than MIN_DURATION
milliseconds will be merged with consecutive frames. The default behavior of termtosvg is to
produce a frame for each update of the terminal screen, but when recording commands that update the
screen very frequently this can cause animations filesize to blow up. Enforcing a minimum frame
duration helps reduces the number of frame of the animations, and thus helps control the size of
animation. MIN_DURATION defaults to 1 millisecond.

##### -M, --max-frame-duration=MAX_DURATION
Set the maximum duration of a frame to MAX_DURATION milliseconds. Frames lasting longer than MAX_DURATION
milliseconds will simply see their duration reduced to MAX_DURATION.

##### -t, --template=TEMPLATE
Set the SVG template used for rendering the SVG animation. TEMPLATE may either be
one of the default templates (base16_default_dark, dracula, gjm8_play,
gjm8_single_loop, gjm8, powershell, progress_bar, putty, solarized_dark,
solarized_light, terminal_app, ubuntu, window_frame_js,
window_frame_powershell, window_frame, xterm) or a path to a valid template.

##### -s, --still-frames
Output still frames in SVG format instead of an animated SVG. If this option is specified,
output_path refers to the destination directory for the frames.


## SVG TEMPLATES
Templates make it possible to customize the SVG animation produced by termtosvg in a number
of ways including, but not limited to:

* Specifying the color theme and font used for rendering the terminal session
* Adding a custom terminal window frame to the animation to make it look like a real terminal
* Adding JavaScript code to pause the animation, seek to a specific frame, etc

See the [dedicated manual page](termtosvg-templates.md) for more details.

## ENVIRONMENT
In case the `--command` option is not specified, termtosvg will spawn the shell specified by
the SHELL environment variable, or `/bin/sh` if the variable is not set.

## EXAMPLES

Record a terminal session and produce an SVG animation named `animation.svg`:
```
termtosvg animation.svg
```

Record a terminal session and render it using a specific template:
```
termtosvg -t ~/templates/my_template.svg
```

Record a specific program such as IPython with the pretty printing option:
```
termtosvg -c 'ipython --pprint'
```

Record a terminal session with a specific screen geometry:
```
termtosvg -g 80x24 animation.svg
```

Record a terminal session in asciicast v2 format:
```
termtosvg record recording.cast
```

Render an SVG animation from a recording in asciicast format
```
termtosvg render recording.cast animation.svg
```

Enforce both minimal and maximal frame durations
```
termtosvg -m 17 -M 2000
```

Specify a 2 seconds delay between animation loops
```
termtosvg -D 2000
```

Render still frames instead of an animated SVG using a specific template
```
termtosvg -s -t gjm8_play
```
