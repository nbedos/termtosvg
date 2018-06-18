[![Build Status](https://travis-ci.org/nbedos/termtosvg.svg?branch=master)](https://travis-ci.org/nbedos/termtosvg)

# termtosvg
A Linux terminal recorder written in Python which renders your command
line sessions as standalone SVG animations.

<p align="center">
    <img src="https://cdn.rawgit.com/nbedos/termtosvg/0.2.0/examples/awesome.svg">
</p>

More examples of recordings [here](https://github.com/nbedos/termtosvg/blob/0.2.0/examples/examples.md)

## Motivation
I really like the clean look of SVG animations and I also wanted to see
how this solution would hold out against other attempts at terminal
recording such as [asciinema](https://github.com/asciinema/asciinema).

## Installation
termtosvg is compatible with Python >= 3.5 and can be installed with pip:
```
pip install termtosvg
```

## Usage
### Basic usage
Start recording with:

```
$ termtosvg
Recording started, enter "exit" command or Control-D to end
```

You are now in a subshell where you can type your commands as usual.
Once you are done, exit the shell to end the recording:

```
$ exit
Recording ended, file is /tmp/termtosvg_exp5nsr4.svg
```
Finally, use your favorite image viewer to play the animation:
```
$ xdg-open /tmp/termtosvg_exp5nsr4.svg
```

### Subcommands
Rendering the SVG animation while recording might sometimes slow the
commands being executed a bit because of the CPU usage, so it is
possible to proceed in two steps:
1. Record the terminal session to disk in asciicast v2 format
2. Render the SVG animation using the recording on disk

The usage of these two commands is detailed below.

#### Record
```
$ termtosvg record --help
usage: termtosvg record [output_file] [--verbose] [--help]

record the session to a file in asciicast v2 format

positional arguments:
  output_file    optional filename for the recording; if missing, a random
                 filename will be automatically generated

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  increase log messages verbosity
```
#### Render
```
$ termtosvg render --help
usage: termtosvg render input_file [output_file] [--theme THEME] [--verbose] [--help]

render an asciicast recording as an SVG animation

positional arguments:
  input_file     recording of the terminal session in asciicast v2 format
  output_file    optional filename for the SVG animation; if missing, a random
                 filename will be automatically generated

optional arguments:
  -h, --help     show this help message and exit
  --theme THEME  color theme used to render the terminal session (circus,
                 classic-dark, classic-light, dracula, isotope, marrakesh,
                 material, monokai, solarized-dark, solarized-light, zenburn)
  -v, --verbose  increase log messages verbosity
```
### Color themes
#### Default themes
If you wish to record a terminal session using a specific color theme, say
monokai for example, enter the following command:
```
termtosvg --theme monokai
```

Available themes can be listed with `termtosvg --help`
```
...
  --theme THEME  color theme used to render the terminal session (circus,
                 classic-dark, classic-light, dracula, isotope, marrakesh,
                 material, monokai, solarized-dark, solarized-light, zenburn)
...
```

#### Custom themes
If termtosvg is called without the `--theme` option, it will try gathering
color information from the Xserver running on your machine.

To tell the Xserver about the color theme you wish to use for termtosvg,
you have to declare the foreground, background and default 16 colors in
your ~/.Xresources file. Here is an example based on monokai from the [base16
project](https://github.com/chriskempson/base16-xresources):
```
termtosvg.foreground: #f8f8f2
termtosvg.background: #272822
termtosvg.color0: #272822
termtosvg.color1: #f92672
termtosvg.color2: #a6e22e
termtosvg.color3: #f4bf75
termtosvg.color4: #66d9ef
termtosvg.color5: #ae81ff
termtosvg.color6: #a1efe4
termtosvg.color7: #f8f8f2
termtosvg.color8: #75715e
termtosvg.color9: #fd971f
termtosvg.color10: #383830
termtosvg.color11: #49483e
termtosvg.color12: #a59f85
termtosvg.color13: #f5f4f1
termtosvg.color14: #cc6633
termtosvg.color15: #f9f8f5
```

Once you have added this information to your ~/.Xresources file, load it
with xrdb or restart the Xserver on your machine. You should now be able
to record terminal sessions with those custom colors.

## Dependencies
termtosvg uses:
* [pyte](https://github.com/selectel/pyte) to render the terminal screen
* [svgwrite](https://github.com/mozman/svgwrite) to create SVG animations
* [python-xlib](https://github.com/python-xlib/python-xlib) to query the X server for color configuration and to parse Xresources data
* [base16-xresources](https://github.com/chriskempson/base16-xresources) for default color themes
