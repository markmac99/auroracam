#!/bin/bash
# Copyright (C) Mark McIntyre
#
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

hn=$(hostname)
logger -s -t $hn "starting auroracam"
source ~/vAuroracam/bin/activate

pids=$(ps -ef | grep ${here}/grabImage | egrep -v "grep|$$" | awk '{print $2}')
[ "$pids" != "" ] && kill -9 $pids

rm -f ~/.stopac
python $here/auroraCam.py 
