#!/bin/bash

odir=~/Dropbox/wips
mkdir -p $odir

gdir=$1
if [ "$gdir" != "" ] && [ -d $gdir ]; then
    if [ "$gdir" == "." ]; then
        gdir=`basename $PWD`
    else
        cd $gdir
    fi
    echo "using git dir $gdir"
    git diff >$odir/wip-$gdir.patch
    exit 0
fi

cd ~/work/partis
git diff >$odir/wip.patch

cd ~/work/partis/projects/gcdyn
git diff >$odir/wip-gcd.patch

cd ~/work/gcdyn
git diff >$odir/wip-gcd-2.patch

cd ~/work/partis/datascripts
git diff >$odir/wip-ds.patch
