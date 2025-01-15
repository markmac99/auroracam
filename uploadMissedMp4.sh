#!/bin/bash
# Copyright (C) Mark McIntyre
#
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

source ~/vAuroracam/bin/activate

# Takes two arguments:
#   the datetime for which tyou want to upload eg 20250115_162343
#   0 or 1: 0 will upload the mp4 if it exists, while 1 will force recreation of the mp4 and then upload

python $here/redoTimelapse.py $1 $2
