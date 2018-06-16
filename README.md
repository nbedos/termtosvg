[![Build Status](https://travis-ci.org/nbedos/termtosvg.svg?branch=develop)](https://travis-ci.org/nbedos/termtosvg)

# termtosvg
A Linux terminal recorder written in Python which renders your command
line sessions as standalone SVG animations.

<p align="center">
    <img src="https://cdn.rawgit.com/nbedos/termtosvg/develop/examples/htop.svg">
</p>

More examples [here](https://github.com/nbedos/termtosvg/tree/develop/examples)

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

You are now in a subshell where you can type your commands as usual:

```
$ ls
build  examples  LICENSE   README.md  termtosvg           tests
dist   htmlcov   Makefile  setup.py   termtosvg.egg-info
$ wc -l termtosvg/*py
  279 termtosvg/anim.py
    0 termtosvg/__init__.py
   94 termtosvg/__main__.py
  403 termtosvg/term.py
  776 total
```

Once you are done, exit the shell to end the recording:

```
$ exit
Recording ended, file is /tmp/termtosvg_exp5nsr4.svg
```
Finally, use your favorite image viewer to play the animation:
```
$ xdg-open /tmp/termtosvg_exp5nsr4.svg
```

### Color themes
#### Default themes
If you wish to record a terminal session using a specific color theme, say
monokai for example, enter the following command:
```
termtosvg --theme monokai
```

Available themes can be listed by omitting the name of the theme:
```
termtosvg --theme
```

#### Custom themes
If termtosvg is called without the '--theme' option, it will try gathering
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
