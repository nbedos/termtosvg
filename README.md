[![Build Status](https://travis-ci.org/nbedos/termtosvg.svg?branch=master)](https://travis-ci.org/nbedos/termtosvg) [![CircleCI](https://circleci.com/gh/nbedos/termtosvg.svg?style=svg)](https://circleci.com/gh/nbedos/termtosvg)

# termtosvg
termtosvg is a Unix terminal recorder written in Python that renders your command
line sessions as standalone SVG animations.

<p align="center">
    <img src="https://nbedos.github.io/termtosvg/examples/awesome_window_frame.svg">
</p>

* [Gallery of examples](https://nbedos.github.io/termtosvg/pages/examples.html)
* [Gallery of templates](https://nbedos.github.io/termtosvg/pages/templates.html)
* [Manual page](man/termtosvg.md)

## Features
* Produce lightweight and clean looking animations embeddable on a project page
* Custom color themes, terminal UI and animation controls via [SVG templates](man/termtosvg-templates.md)
* Compatible with asciinema recording format
    
## Installation
termtosvg is compatible with Linux, macOS and BSD OSes, requires Python >= 3.5 and can be installed using pip:
```
pip3 install --user termtosvg
```

## Basic usage
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

## Dependencies
termtosvg uses:
* [pyte](https://github.com/selectel/pyte) to render the terminal screen
* [lxml](https://github.com/lxml/lxml) to work with SVG data
