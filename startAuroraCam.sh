#!/bin/bash
# Copyright (C) Mark McIntyre
#
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"


hn=$(hostname)
logger -s -t $hn "starting auroracam"
filetocheck=$DATADIR/../live.jpg

source $here/config.ini > /dev/null 2>&1
source ~/vAuroracam/bin/activate

pids=$(ps -ef | grep ${here}/grabImage | egrep -v "grep|$$" | awk '{print $2}')
[ "$pids" != "" ] && kill -9 $pids

rm -f ~/.stopac

# ensure camera is on correct address
x=$(find ${filetocheck} -mmin +5)
if [ "$x" !=  "" ] ; then
    logger -s -t startAuroraCam": checking camera address is right"
    ping -c 1  -w 1 $IPADDRESS > /dev/null 2>&1
    if [ $? -eq 1 ] ; then 
        logger -s -t startAuroraCam "no response from $IPADDRESS, trying to reset"
        python $here/CamManager.py "search;config $MACADDRESS $IPADDRESS 255.255.255.0 $ROUTERADDRESS;quit"
    fi
    ping -c 1  -w 1 $IPADDRESS > /dev/null 2>&1
    if [ $? -eq 1 ] ; then 
        logger -s -t startAuroraCam": unable to reset camera, exiting"
        exit
    fi
fi

python $here/auroraCam.py 
