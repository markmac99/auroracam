#!/bin/bash
# Copyright (C) Mark McIntyre
#
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
source $here/config.ini > /dev/null 2>&1
filetocheck=$DATADIR/../live.jpg
source ~/vAuroracam/bin/activate

while true
do
    if [ ! -f $DATADIR/../.noreboot ] ; then 
        x=$(find ${filetocheck} -mmin +5)
        if [ "$x" !=  "" ] ; then
            logger -s -t checkAuroracam "file late: checking camera address is right"
            ping -c 1  -w 1 $IPADDRESS > /dev/null 2>&1
            if [ $? -eq 1 ] ; then 
                logger -s -t checkAuroracam "no response, trying to reset IP address"
                python $here/CamManager.py "search;config $MACADDRESS $IPADDRESS 255.255.255.0 192.168.1.1;quit"
            else
                logger -s -t checkAuroracam "camera ok, likely software failure, restarting"
                systemctl --user restart auroracam
            fi
        fi
    fi
    sleep 30
done
