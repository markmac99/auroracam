#!/bin/bash
# Copyright (C) Mark McIntyre
#

FPS=60
source ~/vAuroracam/bin/activate

if [ $# -lt 1 ] ; then
    echo usage: ./makeMP4 yyyymmdd_hhmmss 
else
    here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
    source $here/config.ini > /dev/null 2>&1

    fldr=$1

    touch $DATADIR/../.noreboot
    echo making an mp4 of $DATADIR/$fldr

    python redoTimelapse.py $fldr 1

    rm -f ${DATADIR}/../.noreboot
fi