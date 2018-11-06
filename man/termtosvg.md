% TERMTOSVG(1)
% Nicolas Bedos
% November 2018

## SYNOPSIS
**termtosvg** [output_file] [-g GEOMETRY] [-t TEMPLATE] [--help]

**termtosvg record** [output_file] [-g GEOMETRY] [-m MIN_DURATION] [-M MAX_DURATION] [-h]

**termtosvg render** *input_file* [output_file] [-m MIN_DURATION] [-M MAX_DURATION] [-t TEMPLATE] [-h]

### DESCRIPTION
termtosvg makes recordings of terminal sessions in animated SVG format. If no output
filename is provided, a random temporary filename will be automatically generated.

#### COMMANDS
The default behavior of termtosvg is to render an SVG animation 

##### termtosvg record
Record a terminal session in asciicast v2 format. The recording is a text file which
contains timing information as well as what was displayed on the screen during the
terminal session. It may be edited to alter the timing of
the recording or the information displayed on the screen of the terminal.

##### termtosvg render
Render an animated SVG from a recording in asciicast v1 or v2 format. This allows
rendering in SVG format of any recording made with asciinema.

## OPTIONS

##### -g, --screen-geometry=GEOMETRY
geometry of the terminal screen used for rendering the animation. The geometry must
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
one of the default templates (gjm8, dracula, solarized_dark, solarized_light,
 progress_bar, window_frame, window_frame_js) or a path to a valid template.



## SVG TEMPLATES
Templates make it possible to customize the SVG animation produced by termtosvg in a number
of ways including, but not limited to:

* Specifying the color theme and font used for rendering the terminal session
* Adding a custom terminal window frame to the animation to make it look like a real terminal
* Adding JavaScript code to pause the animation, seek to a specific frame, etc

See the [dedicated manual page](termtosvg-templates.md) for more details.

## ENVIRONMENT
termtosvg will spawn the shell specified by the SHELL environment variable, or ``/bin/sh`` if the
variable does not exist. Spawning a new shell is necessary so that termtosvg can act
as an intermediary between the shell and the pseudo terminal and capture all the data sent
to the terminal.


## EXAMPLES

Record a terminal session and produce an SVG animation named `animation.svg`:
```
termtosvg animation.svg
```

Record a terminal session and render it using a specific template:
```
termtosvg -t ~/templates/my_template.svg
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