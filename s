#!/bin/bash

if [ -f Sconstruct ]; then
    scons
else
    pdflatex main
fi
