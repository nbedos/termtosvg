#!/bin/sh

# Clone base16-xresources repository and run each Xresources file
# through a C preprocessor to interpret #define, #if and other constructs

TERM_TO_SVG_DIR="$HOME/termtosvg"
REPO_DIR="/tmp/base16-xresources"
REPO_URL="https://github.com/chriskempson/base16-xresources.git"

rm -rf "$REPO_DIR" && \
git clone "$REPO_URL" "$REPO_DIR" && \

xresources_files=$(find "$REPO_DIR/xresources" -name "*.Xresources" | grep -v 256)
for f in $xresources_files; do
    # Options:
    #   -E : stop after preprocessing step
    #   -xc : specify C language
    #   -P : omit 'linemarkers' comments
    cpp -E -xc -P "$f" > "$TERM_TO_SVG_DIR/termtosvg/data/Xresources/$(basename $f)"
done

