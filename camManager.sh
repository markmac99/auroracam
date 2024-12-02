#!/bin/bash
# Copyright (C) Mark McIntyre
#
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

hn=$(hostname)
logger -s -t $hn "starting auroracam"
source $here/config.ini > /dev/null 2>&1

source ~/vAuroracam/bin/activate
IFACE=wlan0
python $here/CamManager.py -q -i $IFACE
