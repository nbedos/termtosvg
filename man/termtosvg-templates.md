% TERMTOSVG-TEMPLATES(5)
% Nicolas Bedos
% July 2019

## DESCRIPTION
templates are SVG files in which termtosvg embeds animations. Using templates makes it possible to:

* Have user defined terminal color themes and fonts
* Add a terminal UI or window frame to the animation
* Have interactive animations (for example play/pause buttons)

See [here](https://nbedos.github.io/termtosvg/pages/templates.html) for a gallery of the templates
included with termtosvg

## TEMPLATE STRUCTURE

Here is the basic structure of a template:
```SVG
<?xml version="1.0" encoding="utf-8"?>
<svg id="terminal" baseProfile="full" viewBox="0 0 656 325" width="656" version="1.1"
     xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <defs>
        <termtosvg:template_settings xmlns:termtosvg="https://github.com/nbedos/termtosvg">
            <termtosvg:screen_geometry columns="82" rows="19"/>
            <termtosvg:animation type="css"/>
        </termtosvg:template_settings>
        <style type="text/css" id="generated-style">
            <!-- [snip!] -->
        </style>
        <style type="text/css" id="user-style">
            <!-- [snip!] -->
        </style>
    </defs>
    <svg id="screen" width="656" viewBox="0 0 656 323" preserveAspectRatio="xMidYMin meet">
        <!-- [snip!] -->
    </svg>
    <script type="text/javascript" id="generated-js">
        <!-- [snip!] -->
    </script>
</svg>
```

Overall, one can identify:

* An `svg` element with id "terminal"
* A `defs` element which includes:
    * A termtosvg specific `template_settings` element that specifies:
        * the terminal size (number of columns and rows) for which the template is made
        * the animation rendering methods to be used by termtosvg ("css" for CSS or "waapi" for Web Animations API)
    * A `style` element with id "generated-style" that will be overwritten by termtosvg
    * Another `style` element with id "user-style" that should contain at least the terminal color theme. This element is defined by the template creator and won't be overwritten by termtosvg
* An inner `svg` element with id "screen" which will contain the animation produced by termtosvg
* A script element with id "generated-js" that will be overwritten by termtosvg ("waapi" rendering method only)


## TEMPLATE CUSTOMIZATION
The basic idea behind template customization is that termtosvg will preserve elements of the template
that it does not modify. Hence it is possible to

* Customize the style of the animation by modifying the content of the `style` element with id "user-style"
* Add a new `script` element to embed JavaScript code in the animation
* Add other SVG elements, as long as they are not children of the `svg` element with id "screen"

I hope that the information provided here together with the [code for the default templates](../termtosvg/data/templates) is enough to get started
with template customization, but feel free to [open an issue](https://github.com/nbedos/termtosvg/issues/new) if you need some help.

### Custom color theme or font
Terminal color themes must be specified in the `style` element with id "user-style" and must
define all the following classes: `foreground`, `background`, `color0`, `color1`, ..., `color15`.
Font related attributes can also be specified together with the color theme.
See below for an example.

```SVG
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" id="terminal" baseProfile="full" viewBox="0 0 656 325" width="656" version="1.1">
    <defs>
        <termtosvg:template_settings xmlns:termtosvg="https://github.com/nbedos/termtosvg">
            <termtosvg:screen_geometry columns="82" rows="19"/>
        </termtosvg:template_settings>
        <style type="text/css" id="generated-style">
            /* ... Snip! ... */
        </style>
        <style type="text/css" id="user-style">
            .foreground {fill: #c5c5c5;}
            .background {fill: #1c1c1c;}
            .color0 {fill: #1c1c1c;}
            .color1 {fill: #ff005b;}
            /* ... Snip! ... */
            .color15 {fill: #e5e5e5;}

            font-family: Monaco, monospace;
        </style>
    </defs>
    <svg id="screen" width="656" viewBox="0 0 656 323" preserveAspectRatio="xMidYMin meet">
    </svg>
</svg>
```
Complete example here: [gjm8.svg](../termtosvg/data/templates/gjm8.svg)

### Custom terminal UI
Complete example here: [window_frame.svg](../termtosvg/data/templates/window_frame.svg)

### CSS progress bar
Complete example here: [colors_progress_bar.svg](../termtosvg/data/templates/colors_progress_bar.svg)

### Embedding JavaScript
Just add your code in a new `script` element.

Complete example here: [window_frame_js](../termtosvg/data/templates/window_frame_js.svg)

### Restricting the animation to a single loop
For a template using CSS, simply add a custom style element specifying the number of loops like so:
```SVG
<style type="text/css" id="user-style">
    #screen_view {
        animation-iteration-count:1;
    }
</style>
```
Complete example here: [gjm8_single_loop](../termtosvg/data/templates/gjm8_single_loop.svg)

## termtosvg internal template usage
In order to produce the final animation, termtosvg will modify the template in a number of ways.
The knowledge of this internal behavior might turn out useful when writing custom templates.

### Template scaling
The first step is to scale the template to the right size based on the size of the terminal being
recorded and the size of the template specified by the `screen_geometry` element.
For this, termtosvg will update the `viewBox`, `width` and
`height` attributes of the `svg` elements with ids "terminal" and "screen". The `height` and `width`
attributes of these elements must use pixel units.

termtosvg will also update the `columns` and `rows` attributes of the `screen_geometry` to match
the values of the current terminal session and keep things consistent.


### Style update
Next, termtosvg will override the content of the `style` element with id "generated-style" with its own
style sheet. This sheet specifies a few text related attributes. See example below.

```SVG
<style type="text/css" id="generated-style"><![CDATA[
    #screen {
        font-family: 'DejaVu Sans Mono', monospace;
        font-style: normal;
        font-size: 14px;
    }

    text {
        dominant-baseline: text-before-edge;
    }]]>
</style>
```


When set to use CSS animations, termtosvg also defines a single CSS animation for the element
with id `screen_view`. In this case the stylesheet might look like this:

```SVG
<style type="text/css" id="generated-style"><![CDATA[
    #screen {
        font-family: 'DejaVu Sans Mono', monospace;
        font-style: normal;
        font-size: 14px;
    }

    text {
        dominant-baseline: text-before-edge;
    }

    @keyframes roll {
        0.000%{transform:translateY(0px)}
        1.426%{transform:translateY(-323px)}
        1.953%{transform:translateY(-646px)}
        /* Snip! */
        96.344%{transform:translateY(-29393px)}
    }

    #screen_view {
        animation-duration: var(--animation-duration);
        animation-iteration-count:infinite;
        animation-name:roll;
        animation-timing-function: steps(1,end);
    }
]]></style>
```


### Script update
When set to use Web Animations API, termtosvg adds a script element to the SVG that
defines the object `termtosvg_vars`. This object has two attributes
named `transforms` and `timings` as shown below.
```SVG
<script type="text/javascript" id="generated-js"><![CDATA[
var termtosvg_vars = {
    transforms: [
        {transform: 'translate3D(0, 0px, 0)', easing: 'steps(1, end)'},
        {transform: 'translate3D(0, -323px, 0)', easing: 'steps(1, end)', offset: 0.014},
        {transform: 'translate3D(0, -646px, 0)', easing: 'steps(1, end)', offset: 0.020},
        /* Snip! */
        {transform: 'translate3D(0, -29393px, 0)', easing: 'steps(1, end)'}
    ],
    timings: {
        duration: 27349,
        iterations: Infinity
    }
};]]></script>
```
These two attributes should be used in another user-defined script element to create an animation
for the element with id "screen_view". Here is an abridged example taken from the window_frame_js
template:

```SVG
<script type="text/javascript">
var animation = document.getElementById("screen_view").animate(
    termtosvg_vars.transforms,
    termtosvg_vars.timings
)
</script>
```


### Animation update
Finally, termtosvg will overwrite the content of the element `svg` with id "screen" with the code
produced by rendering the terminal session.


In the end, the animation produced by termtosvg has the same structure as the initial template
which makes it possible to use an animation as a template (provided the animation was created with
termtosvg >= 0.5.0).
