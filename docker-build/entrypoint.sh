#!/bin/bash

git clone -b $BRANCH https://github.com/nbedos/termtosvg.git term
cd /term && make $1
mv /term/dist/* /builded
rm -rf /term
