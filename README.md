[![Build Status](https://travis-ci.org/nbedos/termtosvg.svg?branch=master)](https://travis-ci.org/nbedos/termtosvg)

# termtosvg
A Linux terminal recorder written in Python that renders your command
line sessions as standalone SVG animations.

<p align="center">
    <img src="https://cdn.rawgit.com/nbedos/termtosvg/0.4.0/examples/awesome.svg">
</p>

More examples of recordings can be found [here](https://github.com/nbedos/termtosvg/blob/0.4.0/examples/examples.md)

## Motivation
I really like the clean look of SVG animations. I wanted to see
how this solution would hold out against other terminal
recorders such as [asciinema](https://github.com/asciinema/asciinema).

## Installation
termtosvg is compatible with Python >= 3.5 and can be installed with pip:
```
pip3 install --user termtosvg
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
Finally, use your favorite web browser to play the animation:
```
$ firefox /tmp/termtosvg_exp5nsr4.svg
```

### Detailed usage
```
$ termtosvg --help
usage: termtosvg [output_file] [--font FONT] [--theme THEME] [--help] [--verbose]
Record a terminal session and render an SVG animation on the fly

positional arguments:
  output_file    optional filename of the SVG animation; if missing, a random
                 filename will be automatically generated

optional arguments:
  -h, --help     show this help message and exit
  --font FONT    font to specify in the CSS portion of the SVG animation
                 (DejaVu Sans Mono, Monaco...). If the font is not installed
                 on the viewer's machine, the browser will display a default
                 monospaced font instead.
  --theme THEME  color theme used to render the terminal session (circus,
                 classic-dark, classic-light, dracula, isotope, marrakesh,
                 material, monokai, solarized-dark, solarized-light, zenburn)
  -v, --verbose  increase log messages verbosity

See also 'termtosvg record --help' and 'termtosvg render --help'
```

### Subcommands
Rendering the SVG animation while recording sometimes slows down
the commands being executed due to the CPU usage. It is possible
to proceed in two ways:
1. Record the terminal session to disk in asciicast v2 format
2. Render the SVG animation using the recording on disk

The detailed usage of these two commands is available with
`termtosvg record --help` and `termtosvg render --help`

### Configuration
termtosvg configuration file is located at `~/.config/termtosvg/termtosvg.ini`
and will be created by termtosvg if it does not exist. The configuration
file is self-documenting but here are the basics.

#### Global section
The 'global' section of the file specifies the font and color theme used.

```
[global]
font = DejaVu Sans Mono
theme = solarized-dark
```
These options can be overridden at the command line with the `--font` and
`--theme` flags.

#### Color themes
All other sections of the file define color themes. For example here's
the definition of the theme 'circus':
```
[circus]
foreground = #a7a7a7
background = #191919
color0 = #191919
color1 = #dc657d
color2 = #84b97c
color3 = #c3ba63
color4 = #639ee4
color5 = #b888e2
color6 = #4bb1a7
color7 = #a7a7a7
color8 = #5f5a60
color9 = #4bb1a7
color10 = #202020
color11 = #303030
color12 = #505050
color13 = #808080
color14 = #b888e2
color15 = #ffffff
```

Color themes can freely be added, removed or modified. Once a color theme
has been added to the configuration it can be referred to in the global
section of the configuration file, or be used at the command line as a
parameter to the `--theme` flag.

Definitions for the foreground and background colors and for color0 to
color7 are mandatory. If color8 through color15 (bright ANSI colors) are
defined, they are used by termtosvg to display bold characters as a
replacement for color0 through color7. 

## Dependencies
termtosvg uses:
* [pyte](https://github.com/selectel/pyte) to render the terminal screen
* [svgwrite](https://github.com/mozman/svgwrite) to create SVG animations
* [base16-xresources](https://github.com/chriskempson/base16-xresources) for default color themes
* [rawgit](https://rawgit.com/) for hosting SVG animations displayed here on GitHub [rawgit on GitHub](https://github.com/rgrove/rawgit))
