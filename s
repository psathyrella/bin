#!/bin/bash

if [ -f Sconstruct ] || [ -f SConstruct ]; then
    scons
else
    pdflatex main
fi
