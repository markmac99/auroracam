# simple python programme to capture a jpg from an IP camera
# Copyright (C) Mark McIntyre
#
import cv2
import sys
import os
import shutil
import datetime 
import time 
import subprocess
import configparser
from ukmon_meteortools.utils import annotateImageArbitrary, getNextRiseSet
import boto3 
import logging 
import logging.handlers
from setExpo import setCameraExposure
from crontab import CronTab


pausetime = 2 # time to wait between capturing frames 
log = logging.getLogger("logger")


def getStartEndTimes(datadir, thiscfg):
    lat = thiscfg['auroracam']['lat']
    lon = thiscfg['auroracam']['lon']
    ele = thiscfg['auroracam']['alt']

    risetm, settm = getNextRiseSet(lat, lon, ele)
    # capture from an hour before dusk to an hour after dawn - camera autoadjusts now
    risetm = risetm + datetime.timedelta(minutes=60)
    settm = settm - datetime.timedelta(minutes=60)
    if risetm < settm:
        # we are starting after dusk so find out if there's already a folder
        # and use that instead
        log.info('after overnight start time')

        # if starttime=True, then dur is the number of seconds from now to end time.
        starttime = datetime.datetime.utcnow()
        endtime = risetm
        # see if there's an existing folder for the data
        dirs=[]
        flist = os.listdir(datadir)
        for fl in flist:
            if os.path.isdir(os.path.join(datadir, fl)):
                dirs.append(fl)
        dirs.sort()
        laststart = datetime.datetime.strptime(dirs[-1], '%Y%m%d_%H%M%S')
        log.info(f'found folder {dirs[-1]}')

        # if its between noon and midnight on the same day, reuse the folder
        if starttime.hour > 12 and laststart.day == starttime.day:
            log.info(f'using {dirs[-1]}')
            starttime = laststart

        # if its between midnight and noon, and the dates are less than two full 
        # days apart, reuse the  folder. 
        elif starttime.hour <= 12 and (starttime - laststart).days < 2:
            log.info(f'using {dirs[-1]}')
            starttime = laststart
        else:
            pass
    else:
        # next set time is before the next rise time, ie its currently daytime
        starttime = settm
        endtime = risetm
    log.info(f'night starts at {starttime} and ends at {endtime}')
    return starttime, endtime


def adjustColour(fnam, red=1, green=1, blue=1, fnamnew=None):
    img = cv2.imread(fnam, flags=cv2.IMREAD_COLOR)
    img[:,:,2]=img[:,:,2] * red
    img[:,:,1]=img[:,:,1] * green
    img[:,:,0]=img[:,:,0] * blue
    if fnamnew is None:
        fnamnew = fnam
    cv2.imwrite(fnamnew, img)    


def grabImage(ipaddress, fnam, hostname, now, thiscfg):
    capstr = f'rtsp://{ipaddress}:554/user=admin&password=&channel=1&stream=0.sdp'
    # log.info(capstr)
    try:
        cap = cv2.VideoCapture(capstr)
        ret, frame = cap.read()
        cap.release()
    except:
        log.info('unable to grab frame')
        return 
    x = 0
    while x < 5:
        try:
            cv2.imwrite(fnam, frame)
            x = 5
        except:
            x = x + 1
    cap.release()
    cv2.destroyAllWindows()
    title = f'{hostname} {now.strftime("%Y-%m-%d %H:%M:%S")}'
    radj, gadj, badj = (thiscfg['auroracam']['rgbadj']).split(',')
    adjustColour(fnam, red=float(radj), green=float(gadj), blue=float(badj))
    annotateImageArbitrary(fnam, title, color='#FFFFFF')
    return 


def makeTimelapse(dirname, s3, camname, bucket, daytimelapse=False):
    dirname = os.path.normpath(os.path.expanduser(dirname))
    _, mp4shortname = os.path.split(dirname)
    if daytimelapse:
        mp4name = os.path.join(dirname, mp4shortname + '_day.mp4')
    else:
        mp4name = os.path.join(dirname, mp4shortname + '.mp4')
    log.info(f'creating {mp4name}')
    fps = int(125/pausetime)
    if os.path.isfile(mp4name):
        os.remove(mp4name)
    cmdline = f'ffmpeg -v quiet -r {fps} -pattern_type glob -i "{dirname}/*.jpg" \
        -vcodec libx264 -pix_fmt yuv420p -crf 25 -movflags faststart -g 15 -vf "hqdn3d=4:3:6:4.5,lutyuv=y=gammaval(0.77)"  \
        {mp4name}'
    log.info(f'making timelapse of {dirname}')
    subprocess.call([cmdline], shell=True)
    log.info('done')
    if s3 is not None:
        targkey = f'{camname}/{mp4shortname[:6]}/{camname}_{mp4shortname}.mp4'
        try:
            log.info(f'uploading to {bucket}/{targkey}')
            s3.meta.client.upload_file(mp4name, bucket, targkey, ExtraArgs = {'ContentType': 'video/mp4'})
        except:
            log.info('unable to upload mp4')
    else:
        print('created but not uploading mp4')
    return 


def setupLogging(thiscfg):
    print('about to initialise logger')
    logdir = os.path.expanduser(thiscfg['auroracam']['logdir'])
    os.makedirs(logdir, exist_ok=True)

    logfilename = os.path.join(logdir, 'auroracam_' + datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S.%f') + '.log')
    handler = logging.handlers.TimedRotatingFileHandler(logfilename, when='D', interval=1) 
    handler.setLevel(logging.INFO)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt='%(asctime)s-%(levelname)s-%(module)s-line:%(lineno)d - %(message)s', 
        datefmt='%Y/%m/%d %H:%M:%S')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt='%(asctime)s-%(levelname)s-%(module)s-line:%(lineno)d - %(message)s', 
        datefmt='%Y/%m/%d %H:%M:%S')
    ch.setFormatter(formatter)
    log.addHandler(ch)
    log.setLevel(logging.INFO)
    log.setLevel(logging.DEBUG)
    log.info('logging initialised')
    return 



def addCrontabEntry(local_path):
    cron = CronTab(user=True)
    #found = False
    iter=cron.find_command('uploadLiveJpg.sh')
    for i in iter:
        if i.is_enabled():
            #found = True
            cron.remove(i)
    #dtstr = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    job = cron.new(f'sleep 60 && {local_path}/uploadLiveJpg.sh') # > {logdir}/uploadLiveJpg-{dtstr}.log 2>&1')
    job.every_reboot()
    cron.write()


if __name__ == '__main__':
    ipaddress = sys.argv[1]
    hostname = sys.argv[2]
    if len(sys.argv)> 4:
        force_day = True
    else:
        force_day = False

    thiscfg = configparser.ConfigParser()
    local_path =os.path.dirname(os.path.abspath(__file__))
    thiscfg.read(os.path.join(local_path, 'config.ini'))
    setupLogging(thiscfg)

    ulloc = thiscfg['auroracam']['uploadloc']
    if ulloc[:5] == 's3://':
        s3 = boto3.resource('s3')
        bucket = ulloc[5:]
    else:
        print('not uploading to AWS S3')
        s3 = None
        bucket = None
    addCrontabEntry(local_path)

    nightgain = int(thiscfg['auroracam']['nightgain'])
    camid = thiscfg['auroracam']['camid']
    datadir = os.path.expanduser(thiscfg['auroracam']['datadir'])
    os.makedirs(datadir, exist_ok=True)
    norebootflag = os.path.join(datadir, '..', '.noreboot')
    if os.path.isfile(norebootflag):
        os.remove(norebootflag)
    
    # get todays dusk and tomorrows dawn times
    dusk, dawn = getStartEndTimes(datadir, thiscfg)
    dirnam = os.path.join(datadir, dusk.strftime('%Y%m%d_%H%M%S'))
    os.makedirs(dirnam, exist_ok=True)
    daytimelapse = int(thiscfg['auroracam']['daytimelapse'])
    if daytimelapse:
        daydirnam = os.path.join(datadir, dawn.strftime('%Y%m%d_%H%M%S'))
        log.info(f'daytimelapse is on, creating {daydirnam}')
        os.makedirs(daydirnam, exist_ok=True)

    now = datetime.datetime.utcnow()
    if now > dawn or now < dusk:
        isnight = False
        setCameraExposure(ipaddress, 'DAY', nightgain, True, True)
    else:
        isnight = True
        setCameraExposure(ipaddress, 'NIGHT', nightgain, True, True)

    log.info(f'now {now}, night start {dusk}, end {dawn}')
    uploadcounter = 0
    while True:
        now = datetime.datetime.utcnow()
        if now < dawn and now > dusk and isnight is False:
            if daytimelapse:
                # make the daytime mp4
                norebootflag = os.path.join(datadir, '..', '.noreboot')
                open(norebootflag, 'w')
                makeTimelapse(daydirnam, s3, camid, bucket, daytimelapse)
                os.remove(norebootflag)
            isnight = True
            setCameraExposure(ipaddress, 'NIGHT', nightgain, True, True)
        # if force_day then save a dated file for the daytime 
        if force_day is True:
            fnam = os.path.join(dirnam, now.strftime('%Y%m%d_%H%M%S') + '.jpg')
            os.makedirs(dirnam, exist_ok=True)
            grabImage(ipaddress, fnam, hostname, now, thiscfg)
            log.info(f'grabbed {fnam}')

        # if we are in the daytime period, just grab an image
        elif now > dawn or now < dusk:
            # grab the image
            fnam = os.path.expanduser(os.path.join(datadir, '..', 'live.jpg'))
            grabImage(ipaddress, fnam, hostname, now, thiscfg)
            log.info(f'grabbed {fnam}')
            if daytimelapse:
                fnam2 = os.path.join(daydirnam, now.strftime('%Y%m%d_%H%M%S') + '.jpg')
                log.info(f'copying to {fnam2}')
                shutil.copyfile(fnam, fnam2)
            if isnight is True:
                # make the mp4
                norebootflag = os.path.join(datadir, '..', '.noreboot')
                open(norebootflag, 'w')
                makeTimelapse(dirnam, s3, camid, bucket)
                # refresh the dusk/dawn times for tomorrow
                dusk, dawn = getStartEndTimes(datadir, thiscfg)
                dirnam = os.path.join(datadir, dusk.strftime('%Y%m%d_%H%M%S'))
                os.makedirs(dirnam, exist_ok=True)
                setCameraExposure(ipaddress, 'DAY', nightgain, True, True)
                log.info('switched to daytime mode, now rebooting')
                isnight = False
                os.remove(norebootflag)
                os.system('/usr/bin/sudo /usr/sbin/shutdown -r now')

        # otherwise its night time so save a dated file
        else:
            isnight = True
            dirnam = os.path.join(datadir, dusk.strftime('%Y%m%d_%H%M%S'))
            os.makedirs(dirnam, exist_ok=True)
            fnam = os.path.join(dirnam, now.strftime('%Y%m%d_%H%M%S') + '.jpg')
            grabImage(ipaddress, fnam, hostname, now, thiscfg)
            log.info(f'grabbed {fnam}')
            fnam2 = os.path.expanduser(os.path.join(datadir, '..', 'live.jpg'))
            if os.path.isfile(fnam):
                shutil.copy(fnam, fnam2)
                log.info('updated live copy')
            else:
                log.info(f'{fnam} missing')

        uploadcounter += pausetime
        testmode = int(os.getenv('TESTMODE', default=0))
        if uploadcounter > 9 and testmode == 0 and s3 is not None:
            log.info('uploading live image')
            if os.path.isfile(fnam):
                try:
                    s3.meta.client.upload_file(fnam, bucket, f'{hostname}/live.jpg', ExtraArgs = {'ContentType': 'image/jpeg'})
                except:
                    log.info('unable to upload live image')
                    pass
                uploadcounter = 0
            else:
                uploadcounter -= pausetime
        if testmode == 1:
            log.info(f'would have uploaded {fnam}')
        log.info(f'sleeping for {pausetime} seconds')
        time.sleep(pausetime)
