# Changelog

## Version 0.6.0 (2018-11-04)

* Add base16-default-dark color theme ([pull request #57](https://github.com/nbedos/termtosvg/pull/57))
* Add manual pages in groff format ([issue #53](https://github.com/nbedos/termtosvg/issues/53))
* Add support for italic, underscore and strikethrough style attributes (pull requests
[#60](https://github.com/nbedos/termtosvg/pull/60) and [#62](https://github.com/nbedos/termtosvg/pull/62))
* Add --min-frame-duration command line option ([issue #33](https://github.com/nbedos/termtosvg/issues/33))
* Add --max-frame-duration command line option
* Remove unused --verbose command line option
* Reduce file size by optimizing the use of SVG attributes


## Version 0.5.0 (2018-08-05)

* Add support for hidden cursors
* Add support for SVG templates (custom color themes, terminal UI, animation controls...) as
discussed in [issue #53](https://github.com/nbedos/termtosvg/issues/53)
* Remove --font and --theme options, as well as the termtosvg.ini configuration file
* Fix select() deadlock on BSD and macOS ([issue #18](https://github.com/nbedos/termtosvg/issues/18))


## Version 0.4.0 (2018-07-08)

* Add support for rendering recordings in asciicast v1 format ([issue #15](https://github.com/nbedos/termtosvg/issues/15))
* Add support for bold text rendering ([pull request #35](https://github.com/nbedos/termtosvg/pull/35))
* Use temporary file for logging ([issue #12](https://github.com/nbedos/termtosvg/issues/12))


## Version 0.3.0 (2018-07-02)

* Add support for a font option ([pull request #3](https://github.com/nbedos/termtosvg/pull/3))
* Drop support for color information gathering from Xresources (fixes [issues #5](https://github.com/nbedos/termtosvg/issues/5) and [#6](https://github.com/nbedos/termtosvg/issues/6))
* Add configuration file in INI format for defining preferred font and color theme, and for adding or modifying color themes


## Version 0.2.2 (2018-06-25)

* Prevent crash when no Xresources string can be retrieved from the Xserver ([issue #2](https://github.com/nbedos/termtosvg/issues/2))


## Version 0.2.1 (2018-06-25)

* Fallback to non bright colors when using an 8 color palette ([issue #1](https://github.com/nbedos/termtosvg/issues/1))


## Version 0.2.0 (2018-06-24)

* Add support for the asciicast v2 recording format
* Add subcommands for independently recording the terminal session and rendering the SVG animations


## Version 0.1.0 (2018-06-16)
Initial release!