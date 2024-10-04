#!/bin/bash

odir=~/Dropbox/wips
mkdir -p $odir

cd ~/work/partis
git diff >$odir/wip.patch

cd ~/work/partis/projects/gcdyn
git diff >$odir/wip-gcd.patch

cd ~/work/gcdyn
git diff >$odir/wip-gcd-2.patch

cd ~/work/partis/datascripts
git diff >$odir/wip-ds.patch
