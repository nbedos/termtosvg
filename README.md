[![Build Status](https://travis-ci.org/nbedos/termtosvg.svg?branch=develop)](https://travis-ci.org/nbedos/termtosvg) [![Coverage](https://codecov.io/gh/nbedos/termtosvg/branch/develop/graph/badge.svg)](https://codecov.io/gh/nbedos/termtosvg)


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
* Produce lightweight and clean looking animations or still frames embeddable on a project page
* Custom color themes, terminal UI and animation controls via [SVG templates](man/termtosvg-templates.md)
* Compatible with asciinema recording format
    
## Installation
termtosvg is compatible with Linux, macOS and BSD OSes, requires Python >= 3.5 and can be installed using pip:
```
pip3 install --user termtosvg
```

Various independently maintained, OS specific packages have been made available by the community:

    
| OS       | Repository  | Installation command  |
|----------|-------------|---|
| Archlinux  | [Arch](https://www.archlinux.org/packages/community/any/termtosvg/)  |`pacman -S termtosvg`   |
| FreeBSD | [ports](https://www.freshports.org/graphics/py-termtosvg) | |
| Gentoo | [media-gfx/termtosvg](https://packages.gentoo.org/packages/media-gfx/termtosvg) | `emerge media-gfx/termtosvg`|
| macOS  | [Homebrew](https://formulae.brew.sh/formula/termtosvg)  |`brew install termtosvg`   |
| OpenBSD  | [ports](https://github.com/openbsd/ports/tree/master/graphics/termtosvg)  |   |
| NixOS | [nixpkgs](https://github.com/NixOS/nixpkgs/blob/master/pkgs/tools/misc/termtosvg/) | |


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
