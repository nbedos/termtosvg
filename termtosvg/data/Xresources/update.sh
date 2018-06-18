#!/bin/sh

# Clone base16-xresources repository and run each Xresources file
# through a C preprocessor to interpret #define, #if and other constructs

TERM_TO_SVG_DIR="$HOME/termtosvg"
REPO_DIR="/tmp/base16-xresources"
REPO_URL="https://github.com/chriskempson/base16-xresources.git"
THEMES="circus dracula classic-dark classic-light isotope marrakesh material monokai solarized-dark solarized-light zenburn"

rm -rf "$REPO_DIR" && \
git clone "$REPO_URL" "$REPO_DIR" && \
for theme in $THEMES; do
    # Options:
    #   -E : stop after preprocessing step
    #   -xc : specify C language
    #   -P : omit 'linemarkers' comments
    infile="$REPO_DIR/xresources/base16-$theme.Xresources"
    outfile="$TERM_TO_SVG_DIR/termtosvg/data/Xresources/base16-$theme.Xresources"
    cpp -E -xc -P "$infile" > "$outfile"
done

