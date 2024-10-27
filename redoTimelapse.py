from auroraCam import makeTimelapse, getAWSConn, setupLogging
import platform
import os
import sys
import configparser
import logging

log = logging.getLogger("logger")


dirpath = sys.argv[1]
force = False
if len(sys.argv) > 2:
    if int(sys.argv[2])==1:
        force = True

thiscfg = configparser.ConfigParser()
local_path =os.path.dirname(os.path.abspath(__file__))
thiscfg.read(os.path.join(local_path, 'config.ini'))
ulloc = thiscfg['auroracam']['uploadloc']
camid = thiscfg['auroracam']['camid']
datadir = os.path.expanduser(thiscfg['auroracam']['datadir'])
hostname = platform.uname().node

setupLogging(thiscfg)
if ulloc[:5] == 's3://':
    idserver = thiscfg['uploads']['idserver']
    sshkey = thiscfg['uploads']['idkey']
    uid = platform.uname()[1]
    s3 = getAWSConn(thiscfg, uid, uid)
    bucket = ulloc[5:]
else:
    print('not uploading to AWS S3')
    s3 = None
    bucket = None
dirname = os.path.join(datadir, dirpath)
                          
makeTimelapse(dirname, s3, camid, bucket, daytimelapse=False, maketimelapse=force)
