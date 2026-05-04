#!/bin/bash

if [ -f Sconstruct ] || [ -f SConstruct ]; then
    scons
elif [ -f Makefile ]; then
    if grep -qE "^pdf-figures:" Makefile; then
        make pdf-figures
    fi
    make pdf
else
    pdflatex main
fi
