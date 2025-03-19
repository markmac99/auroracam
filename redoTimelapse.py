from auroraCam import makeTimelapse, setupLogging, s3details
import platform
import os
import sys
import configparser
import logging

log = logging.getLogger("logger")

if len(sys.argv) < 2:
    print('usage: python ./redoTimelapse.py yyyymmdd_hhmmss ')
    exit(0)

dirpath = sys.argv[1]
force = False
if len(sys.argv) > 2:
    if int(sys.argv[2])==1:
        force = True

thiscfg = configparser.ConfigParser()
local_path =os.path.dirname(os.path.abspath(__file__))
thiscfg.read(os.path.join(local_path, 'config.ini'))
setupLogging(thiscfg)

datadir = os.path.expanduser(thiscfg['auroracam']['datadir'])
hostname = platform.uname().node

yt = thiscfg['youtube']['doupload']
if yt=='1' or yt.lower()=='true':
    yt=True
else:
    yt=False

s3, bucket, s3prefix = s3details(thiscfg, hostname)
if s3 is None:
    print('NOT uploading to AWS S3')
else:
    print('uploading to AWS S3')

dirname = os.path.join(datadir, dirpath)
                          
makeTimelapse(dirname, s3, bucket, s3prefix, daytimelapse=False, maketimelapse=force, youtube=yt)
