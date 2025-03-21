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
import boto3 
import logging 
import glob
import logging.handlers
import paho.mqtt.client as mqtt
import platform 
import paramiko
import tempfile
from sendToYoutube import sendToYoutube
from PIL import Image, ImageFont, ImageDraw 
import ephem

from makeImageIndex import createLatestIndex
from setExpo import setCameraExposure


pausetime = 2 # time to wait between capturing frames 
log = logging.getLogger("logger")


def getFilesToUpload(thiscfg, s3, bucket, s3prefix):
    """
    Load the current list of folders/files to be archived 

    Parameters
        thiscfg  [object] config 
    """
    datadir = os.path.expanduser(thiscfg['auroracam']['datadir'])
    if s3 is not None:
        log.info('getting list of files to upload from S3')
        try:
            s3.meta.client.download_file(bucket, f'{s3prefix}/FILES_TO_UPLOAD.inf', os.path.join(datadir,'FILES_TO_UPLOAD.inf'))
        except Exception:
            log.info('no files-to-keep list in S3')
    elif thiscfg['archive']['archserver'] != '':
        log.info('getting list of files to upload from archive server')
        archuser = thiscfg['archive']['archuser']
        archfldr = thiscfg['archive']['archfldr']
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = paramiko.RSAKey.from_private_key_file(os.path.expanduser(thiscfg['archive']['archkey']))
        try:
            ssh_client.connect(thiscfg['archive']['archserver'], username=archuser, pkey=pkey, look_for_keys=False)
            ftp_client = ssh_client.open_sftp()
            ftp_client.get(os.path.join(archfldr,'FILES_TO_UPLOAD.inf'), os.path.join(datadir,'FILES_TO_UPLOAD.inf'))
        except Exception:
            log.info('no files-to-keep list on server')

    dirnames = []
    if os.path.isfile(os.path.join(datadir, 'FILES_TO_UPLOAD.inf')):
        dirnames = open(os.path.join(datadir, 'FILES_TO_UPLOAD.inf'), 'r').read().splitlines()
    else:
        log.warning('no FILES_TO_UPLOAD.inf')
    return dirnames


def pushFilesToUpload(thiscfg, s3, bucket, s3prefix):
    """
    Upload current list of folders/files to be archived back to AWS

    Parameters
        thiscfg [object] the config object
    """
    datadir = os.path.expanduser(thiscfg['auroracam']['datadir'])
    locfnam = os.path.join(datadir, 'FILES_TO_UPLOAD.inf')
    open(locfnam, 'w').write('') # empty the file, we've processed it
    if s3 is not None:
        try:
            s3.meta.client.upload_file(locfnam, bucket, f'{s3prefix}/FILES_TO_UPLOAD.inf')
        except Exception:
            log.warning('unable to update files-to-upload')
    elif thiscfg['archive']['archserver'] != '':
        log.info('pushing FILES_TO_UPLOAD back to ftpserver')
        archuser = thiscfg['archive']['archuser']
        archfldr = thiscfg['archive']['archfldr']
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = paramiko.RSAKey.from_private_key_file(os.path.expanduser(thiscfg['archive']['archkey']))
        try:
            ssh_client.connect(thiscfg['archive']['archserver'], username=archuser, pkey=pkey, look_for_keys=False)
            ftp_client = ssh_client.open_sftp()
            ftp_client.put(locfnam, os.path.join(archfldr,'FILES_TO_UPLOAD.inf'))
        except Exception:
            log.warning('unable to update files-to-upload')
    return 


def getFreeSpace():
    free = shutil.disk_usage('/').free
    freekb = free/1024
    return freekb


def getNeededSpace():
    """
    Calculate space required for next 24 hours of operation. 
    each jpg is about 100kB, and we capture about 20,000 per day - about one every 4 seconds 
    plus extra for the timelapses and tarballs, and a bit of overhead 
    """
    jpgspace = 20000 * 100 # 100 kB per file
    mp4space = 100 * 1024  # 100 MB
    tarballspace = 1500 * 1024 # 1.5 GB 
    extraspace = 50 * 1024 # 50 MB extra just in case
    reqspace = jpgspace + extraspace + tarballspace + mp4space
    return reqspace


def getDeletableFiles(thiscfg, filestokeep=[]):
    """
    Get a list of files and folders that can be deleted

    Parameters:
        datadir     [string] - the root folder containing the data files eg ~/RMS_data/auroracam
        daystokeep  [int]    - number of recent days to keep and consider not deletable
        filestokeep [string] - a list of files or folders we want to archive before deleting
    """
    datadir = os.path.expanduser(thiscfg['auroracam']['datadir'])
    try:
        daystokeep = int(thiscfg['auroracam']['daystokeep'])
    except Exception:
        daystokeep = 3
    allfiles = os.listdir(datadir)
    allfiles = [x for x in allfiles if 'FILES' not in x]
    origallfiles = allfiles
    for d in range(0,daystokeep):
        yest = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=d)).strftime('%Y%m%d')
        allfiles = [x for x in allfiles if yest not in x]
    for patt in filestokeep:
        toarch = [x for x in origallfiles if patt.strip() in x]
        allfiles += toarch
    allfiles.sort()
    return allfiles


def compressAndDelete(thiscfg, thisfile):
    """
    Compress and delete a data folder.

    Parameters:
        thiscfg     [object] - the configuration
        thisfile    [string] - the name of the file or folder to process
    
    """
    datadir = os.path.expanduser(thiscfg['auroracam']['datadir'])
    if '.zip' in thisfile or '.tgz' in thisfile:
        zfname = os.path.join(datadir, thisfile)
        os.remove(zfname)
        return zfname
    else:
        log.info(f'Archiving {thisfile}')
        zfname = os.path.join(datadir, thisfile)
        archname = shutil.make_archive(zfname, 'zip', zfname)
        if os.path.isfile(archname):
            shutil.rmtree(zfname)
    return archname


def compressAndUpload(thiscfg, thisdir):
    """
    Compress and upload data.

    Parameters:
        thiscfg     [object] - the configuration
        thisdir    [string] - the name of the file or folder to process
    
    """
    datadir = os.path.expanduser(thiscfg['auroracam']['datadir'])
    if '.zip' in thisdir or '.tgz' in thisdir:
        archname = os.path.join(datadir, thisdir)
    else:
        log.info(f'Compressing {thisdir}')
        zfname = os.path.join(datadir, thisdir)
        archname = shutil.make_archive(zfname,'zip',zfname)
        log.info(f'{zfname}')

    archserver = thiscfg['archive']['archserver']
    if archserver == '':
        log.info('not uploading zip file')
        return archname
    
    log.info(f'Uploading {archname}')
    archuser = thiscfg['archive']['archuser']
    archfldr = thiscfg['archive']['archfldr']
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.RSAKey.from_private_key_file(os.path.expanduser(thiscfg['archive']['archkey']))
    try:
        ssh_client.connect(archserver, username=archuser, pkey=pkey, look_for_keys=False)
        ftp_client = ssh_client.open_sftp()
        uploadfile = os.path.join(archfldr, thisdir +'.zip')
        try:
            ftp_client.put(archname, uploadfile)
            try:
                filestat = ftp_client.stat(uploadfile)
                log.info(f'uploaded {filestat.st_size} bytes')
                os.remove(zfname + '.zip')
            except Exception as e:
                log.error(f'unable to upload {thisdir}')
                log.info(e, exc_info=True)
                return None
        except Exception as e:
            log.error(f'unable to upload {thisdir}')
            log.info(e, exc_info=True)
            return None
        ftp_client.close()
        ssh_client.close()
    except Exception as e:
        log.warning(f'connection to {archserver} failed')
        log.info(e, exc_info=True)
        return None
    
    return archname


def purgeLogs(thiscfg):
    logdir = os.path.expanduser(thiscfg['auroracam']['logdir'])
    days_to_keep = 30
    date_to_purge_to = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
    date_to_purge_to = date_to_purge_to.timestamp(date_to_purge_to)
    log.info(f'purging logs older than {days_to_keep}')
    # Only going to purge RMS log files
    flist = glob.glob1(logdir, '*.log*')
    for fl in flist:
        log_file_path = os.path.join(logdir, fl)
        # Check if the file exists and check if it should be purged
        if os.path.isfile(log_file_path):
            # Get the file modification time
            file_mtime = os.stat(log_file_path).st_mtime
            # If the file is older than the date to purge to, delete it
            if file_mtime < date_to_purge_to:
                try:
                    os.remove(log_file_path)
                    log.info("deleted {}".format(fl))
                except Exception as e:
                    log.warning('unable to delete {}: '.format(log_file_path) + repr(e)) 
    return 


def freeSpaceAndArchive(thiscfg, s3, bucket, s3prefix):
    """
    Free up space by compressing and deleting older data. 

    First we obtain the free space and estimate the required space. 
    
    Next we check for data that the user wants specifically to keep. 
    This info is stored in FILES_TO_UPLOAD.inf which may be on S3, the archive server or locally. 
    The user can also specify they want to keep N days uncompressd. 

    We then get a list of all folders, minus the ones we want to keep, and start compressing them 
    from the oldest forward, deleting the folder once compressed. As soon as this frees up enough 
    space, we stop. 

    Finally, we revisit the data we want to preserve, and compress it. If an archive server is
    configured we push the compressed file to the archive.

    If compressing and deleting does not free enough space, we can't proceed so we abort. 

    """    
    log.info('check free space')
    freekb = getFreeSpace()
    reqkb = getNeededSpace()
    log.info(f'Available {freekb} need {reqkb}')

    log.info('checking for data to save')
    dirstoupload = getFilesToUpload(thiscfg, s3, bucket, s3prefix)

    log.info('checking for deletable data')
    deletable = getDeletableFiles(thiscfg, dirstoupload)
    for dir in deletable:
        if freekb > reqkb:
            log.info('sufficient space available')
            break
        compressAndDelete(thiscfg, dir)
        freekb = getFreeSpace()
        log.info(f'free space now {freekb}')

    log.info('space freed up, now archiving if needed')
    for dir in dirstoupload:
        compressAndUpload(thiscfg, dir)
    pushFilesToUpload(thiscfg, s3, bucket, s3prefix)

    log.info('rechecking for deletable data')
    deletable = getDeletableFiles(thiscfg, dirstoupload)
    for dir in deletable:
        if freekb > reqkb:
            log.info('sufficient space available')
            break
        compressAndDelete(thiscfg, dir)
        freekb = getFreeSpace()
        log.info(f'free space now {freekb}')

    try: 
        purgeLogs(thiscfg)
    except Exception as e:
        print(e)
    log.info('finished')
    return True



def annotateImageArbitrary(img_path, message, color='#000'):
    """
    Annotate an image with an arbitrary message in the selected colour at the bottom left  

    Arguments:  
        img_path:   [str] full path and filename of the image to be annotated  
        message:    [str] message to put on the image  
        color:      [str] hex colour string, default '#000' which is black  

    """
    my_image = Image.open(img_path)
    width, height = my_image.size
    image_editable = ImageDraw.Draw(my_image)
    fntheight=20
    try:
        fnt = ImageFont.truetype("arial.ttf", fntheight)
    except Exception:
        fnt = ImageFont.truetype("DejaVuSans.ttf", fntheight)
    #fnt = ImageFont.load_default()
    image_editable.text((15,height-fntheight-15), message, font=fnt, fill=color)
    my_image.save(img_path)


def getNextRiseSet(lati, longi, elev, fordate=None):
    """ Calculate the next rise and set times for a given lat, long, elev  

    Paramters:  
        lati:   [float] latitude in degrees  
        longi:  [float] longitude in degrees (+E)  
        elev:   [float] latitude in metres  
        fordate:[datetime] date to calculate for, today if none

    Returns:  
        rise, set:  [date tuple] next rise and set as datetimes  

    Note that set may be earlier than rise, if you're invoking the function during daytime.  

    """
    obs = ephem.Observer()
    obs.lat = float(lati) / 57.3 # convert to radians, close enough for this
    obs.lon = float(longi) / 57.3
    obs.elev = float(elev)
    obs.horizon = -6.0 / 57.3 # degrees below horizon for darkness
    if fordate is not None:
        obs.date = fordate

    sun = ephem.Sun()
    rise = obs.next_rising(sun).datetime()
    set = obs.next_setting(sun).datetime()
    return rise.replace(tzinfo=datetime.timezone.utc), set.replace(tzinfo=datetime.timezone.utc)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected success")
    else:
        print("Connected fail with code", rc)


def on_publish(client, userdata, result):
    #print('data published - {}'.format(result))
    return


def sendToMQTT(broker=None):
    if broker is None:
        srcdir = os.path.split(os.path.abspath(__file__))[0]
        localcfg = configparser.ConfigParser()
        localcfg.read(os.path.join(srcdir, 'mqtt.cfg'))
    broker = localcfg['mqtt']['broker']
    hname = platform.uname().node
    client = mqtt.Client(hname)
    client.on_connect = on_connect
    client.on_publish = on_publish
    if localcfg['mqtt']['username'] != '':
        client.username_pw_set(localcfg['mqtt']['username'], localcfg['mqtt']['password'])
    if localcfg['mqtt']['username'] != '':
        client.username_pw_set(localcfg['mqtt']['username'], localcfg['mqtt']['password'])
    client.connect(broker, 1883, 60)
    usage = shutil.disk_usage('.')
    diskspace = round(usage.used/usage.total*100.0, 2)
    topicroot = localcfg['mqtt']['topic']
    topic = f'{topicroot}/{hname}/diskspace'
    ret = client.publish(topic, payload=diskspace, qos=0, retain=False)
    time.sleep(10)
    cpuf = '/sys/class/thermal/thermal_zone0/temp'
    cputemp = int(open(cpuf).readline().strip())/1000
    topic = f'{topicroot}/{hname}/cputemp'
    ret = client.publish(topic, payload=cputemp, qos=0, retain=False)
    return ret


def roundTime(dt):
    if dt.microsecond > 500000:
        dt = dt + datetime.timedelta(seconds=1, microseconds = -dt.microsecond)
    else:
        dt = dt + datetime.timedelta(microseconds = -dt.microsecond)
    return dt


def getAWSConn(thiscfg, remotekeyname, uid):
    """ 
    This function retreives an AWS key/secret for uploading the live image. 
    """
    servername = thiscfg['uploads']['idserver']
    if servername == '':
        # look for a local key file
        log.info('looking for local AWS key')
        awskeyfile = thiscfg['uploads']['idkey']
        try:
            lis = open(os.path.expanduser(awskeyfile), 'r').readlines()
            keyline = lis[1].split(',')
            key = keyline[-2]
            sec = keyline[-1]
        except Exception:
            key = None
    else:
        # retrieve a keyfile from the server
        log.info('retrieving AWS key')
        sshkeyfile = thiscfg['uploads']['idkey']
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = paramiko.RSAKey.from_private_key_file(os.path.expanduser(sshkeyfile))
        key = ''
        try: 
            ssh_client.connect(servername, username=uid, pkey=pkey, look_for_keys=False)
            ftp_client = ssh_client.open_sftp()
            try:
                handle, tmpfnam = tempfile.mkstemp()
                ftp_client.get(remotekeyname + '.csv', tmpfnam)
            except Exception as e:
                log.error('unable to find AWS key')
                log.info(e, exc_info=True)
            ftp_client.close()
            try:
                lis = open(tmpfnam, 'r').readlines()
                os.close(handle)
                os.remove(tmpfnam)
                key, sec = lis[1].split(',')
            except Exception as e:
                log.error('malformed AWS key')
                log.info(e, exc_info=True)
        except Exception as e:
            log.error('unable to retrieve AWS key')
            log.info(e, exc_info=True)
        ssh_client.close()
    s3 = None
    if key:
        log.info('retrieved key details')
        try:
            conn = boto3.Session(aws_access_key_id=key.strip(), aws_secret_access_key=sec.strip())
            s3 = conn.resource('s3')
            log.info('obtained s3 resource')
        except Exception as e:
            log.info(e, exc_info=True)
            pass
    if s3 is None:
        log.warning('no AWS key retrieved, trying current AWS profile')
        s3 = boto3.resource('s3')
    return s3


def s3details(thiscfg, hostname):
    tmpbucket = thiscfg['uploads']['s3uploadloc']
    if tmpbucket == '':
        return None, None, None
    s3 = getAWSConn(thiscfg, hostname, hostname)
    if tmpbucket[:5]=='s3://':
        tmpbucket =tmpbucket[5:]
    bucket = tmpbucket.replace('/', ' ', 1).split(' ')[0]
    if '/' in tmpbucket:
        s3prefix = tmpbucket.replace('/', ' ', 1).split(' ')[1]
    else:
        if 'camid' in thiscfg['auroracam']:
            s3prefix = thiscfg['auroracam']['camid']
        s3prefix = platform.uname().node
    return s3, bucket, s3prefix


def getStartEndTimes(currdt, thiscfg, origdusk=None):
    lat = thiscfg['auroracam']['lat']
    lon = thiscfg['auroracam']['lon']
    ele = thiscfg['auroracam']['alt']
    risetm, settm = getNextRiseSet(lat, lon, ele, fordate=currdt)
    lastdawn, lastdusk = getNextRiseSet(lat, lon, ele, fordate = currdt - datetime.timedelta(days=1))
    if risetm < settm:
        settm = lastdusk
    # capture from an hour before dusk to an hour after dawn - camera autoadjusts now
    nextrise = roundTime(risetm) + datetime.timedelta(minutes=60)
    nextset = roundTime(settm) - datetime.timedelta(minutes=60)
    lastrise = roundTime(lastdawn) + datetime.timedelta(minutes=60)
    # allow for small variations in dusk timing
    if origdusk:
        if (nextset - origdusk) < datetime.timedelta(seconds=10):
            nextset = origdusk
    log.info(f'night starts at {nextset} and ends at {nextrise}')
    return nextset.replace(tzinfo=datetime.timezone.utc), nextrise.replace(tzinfo=datetime.timezone.utc), lastrise.replace(tzinfo=datetime.timezone.utc)


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
    except Exception as e:
        log.warning('unable to connect to camera')
        log.warning(e, exc_info=True)
        return False
    ret = False
    retries = 0
    while not ret and retries < 10:
        try:
            ret, frame = cap.read()
        except Exception as e:
            log.warning('unable to read frame')
            log.warning(e, exc_info=True)
        retries += 1
    cap.release()
    if not ret:
        log.warning('unable to grab frame')
        return False
    ret = False
    retries = 0
    while not ret and retries < 10:
        try:
            ret = cv2.imwrite(fnam, frame)
        except Exception as e:
            log.info(f'unable to save image {fnam}')
            log.info(e, exc_info=True)
        retries += 1
    cv2.destroyAllWindows()
    if ret:
        title = f'{hostname} {now.strftime("%Y-%m-%d %H:%M:%S")}'
        radj, gadj, badj = (thiscfg['auroracam']['rgbadj']).split(',')
        radj = float(radj)
        gadj = float(gadj)
        badj = float(badj)
        if radj < 0.99 or gadj < 0.99 or badj < 0.99:
            adjustColour(fnam, red=radj, green=gadj, blue=badj)
        annotateImageArbitrary(fnam, title, color='#FFFFFF')
        return True
    else:
        log.warning('no new image so not annotated')
        return False


def makeTimelapse(dirname, s3, bucket, s3prefix, daytimelapse=False, maketimelapse=True, youtube=True):
    hostname = platform.uname().node
    dirname = os.path.normpath(os.path.expanduser(dirname))
    _, mp4shortname = os.path.split(dirname)[:15]
    if daytimelapse:
        mp4name = os.path.join(dirname, mp4shortname + '_day.mp4')
    else:
        mp4name = os.path.join(dirname, mp4shortname + '.mp4')
    log.info(f'creating {mp4name}')
    fps = int(125/pausetime)
    if maketimelapse:
        if os.path.isfile(mp4name):
            os.remove(mp4name)
        cmdline = f'ffmpeg -v quiet -r {fps} -pattern_type glob -i "{dirname}/*.jpg" \
            -vcodec libx264 -pix_fmt yuv420p -crf 25 -movflags faststart -g 15 -vf "hqdn3d=4:3:6:4.5,lutyuv=y=gammaval(0.77)"  \
            {mp4name}'
        log.info(f'making timelapse of {dirname}')
        subprocess.call([cmdline], shell=True)
        log.info('done')
        tlnames = glob.glob(mp4name)
        if len(tlnames) > 0:
            log.info(f'saved to {tlnames[0]}')
        else:
            log.warning(f'problem creating {mp4name}')
    if s3 is not None:
        if daytimelapse:
            targkey = f'{s3prefix}/{mp4shortname[:6]}/{hostname}_{mp4shortname}_day.mp4'
        else:
            targkey = f'{s3prefix}/{mp4shortname[:6]}/{hostname}_{mp4shortname}.mp4'
        try:
            log.info(f'uploading to {bucket}/{targkey}')
            s3.meta.client.upload_file(mp4name, bucket, targkey, ExtraArgs = {'ContentType': 'video/mp4'})
        except Exception as e:
            log.info('unable to upload mp4')
            log.info(e, exc_info=True)
    else:
        #log.info('created but not uploading mp4 to s3')
        pass
    # upload night video to youtube
    if not daytimelapse and youtube is True:
        try:
            log.info('uploading to youtube')
            dtstr = mp4shortname[:4] + '-' + mp4shortname[4:6] + '-' + mp4shortname[6:8]
            title = f'Auroracam timelapse for {dtstr}'
            sendToYoutube(title, mp4name)
        except Exception as e:
            log.info('unable to upload mp4 to youtube')
            log.info(e, exc_info=True)
    return 


def setupLogging(thiscfg, prefix='auroracam_'):
    print('about to initialise logger')
    logdir = os.path.expanduser(thiscfg['auroracam']['logdir'])
    os.makedirs(logdir, exist_ok=True)

    logfilename = os.path.join(logdir, prefix + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S.%f') + '.log')
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


def uploadOneFile(fnam, ulloc, ftpserver, userid, sshkey):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.RSAKey.from_private_key_file(os.path.expanduser(sshkey))
    try: 
        targloc = os.path.join(ulloc, os.path.basename(fnam))
        ssh_client.connect(ftpserver, userid, pkey=pkey, look_for_keys=False)
        ftp_client = ssh_client.open_sftp()
        ftp_client.put(fnam, targloc)
        ftp_client.close()
        ssh_client.close()
    except Exception as e:
        log.warn(f'unable to upload to {ftpserver}:{targloc}')
        log.info(e, exc_info=True)
    return 


if __name__ == '__main__':
    hostname = platform.uname().node

    thiscfg = configparser.ConfigParser()
    local_path =os.path.dirname(os.path.abspath(__file__))
    thiscfg.read(os.path.join(local_path, 'config.ini'))
    setupLogging(thiscfg)

    datadir = os.path.expanduser(thiscfg['auroracam']['datadir'])
    os.makedirs(datadir, exist_ok=True)
    norebootflag = os.path.join(datadir, '..', '.noreboot')
    open(norebootflag, 'w')
    s3, bucket, s3prefix = s3details(thiscfg, hostname)
    if s3 is not None:
        log.info(f'S3 upload target {bucket}/{s3prefix}')

    freeSpaceAndArchive(thiscfg, s3, bucket, s3prefix)

    ftpserver = thiscfg['uploads']['ftpserver']
    if ftpserver != '':
        log.info(f'SFTP upload target {ftpserver}')
        userid = thiscfg['uploads']['ftpuser']
        sshkey = thiscfg['uploads']['ftpkey']
        ftploc = thiscfg['uploads']['ftpuploadloc']
    else:
        log.info('not uploading to ftpserver')
        ftpserver = None
        userid = None
        sshkey = None
        ftploc = None

    yt = thiscfg['youtube']['doupload']
    if yt=='1' or yt.lower()=='true':
        yt=True
    else:
        yt=False

    ipaddress = thiscfg['auroracam']['ipaddress']
    macaddress = thiscfg['auroracam']['macaddress']
    nightgain = int(thiscfg['auroracam']['nightgain'])
    if os.path.isfile(norebootflag):
        os.remove(norebootflag)
    
    # get todays dusk and tomorrows dawn times
    now = datetime.datetime.now(datetime.timezone.utc)
    dusk, dawn, lastdawn = getStartEndTimes(now, thiscfg)
    daytimelapse = int(thiscfg['auroracam']['daytimelapse'])
    if now > dawn or now < dusk:
        isnight = False
        setCameraExposure(ipaddress, 'DAY', nightgain, True, True)
    else:
        isnight = True
        setCameraExposure(ipaddress, 'NIGHT', nightgain, True, True)

    log.info(f'now {now}, dusk {dusk}, dawn {dawn} last dawn {lastdawn}')
    uploadcounter = 0
    currtime = datetime.datetime.now()
    while True:
        lastdusk = dusk
        dusk, dawn, lastdawn = getStartEndTimes(now, thiscfg, lastdusk)
        if isnight:
            capdirname = os.path.join(datadir, dusk.strftime('%Y%m%d_%H%M%S'))
        else:
            capdirname = os.path.join(datadir, lastdawn.strftime('%Y%m%d_%H%M%S'))
        
        if dusk != lastdusk and isnight:
            # its dawn
            capdirname = os.path.join(datadir, lastdusk.strftime('%Y%m%d_%H%M%S'))

        #log.info(f'capturing to {capdirname}')
        now = datetime.datetime.now(datetime.timezone.utc)
        fnam = os.path.expanduser(os.path.join(datadir, '..', 'live.jpg'))
        thiscfg.read(os.path.join(local_path, 'config.ini'))
        gotaframe = grabImage(ipaddress, fnam, hostname, now, thiscfg)
        if not gotaframe:
            log.warning('failed to grab frame')
        else:
            newtime = datetime.datetime.now()
            framegap = (newtime - currtime).seconds
            currtime = newtime
            os.makedirs(capdirname, exist_ok=True)
            open(os.path.join(capdirname,'frameintervals.txt'),'a+').write(f"{currtime.strftime('%Y%m%d-%H%M%S')},{framegap}\n")
            log.info(f'grabbed {fnam}')

        # due to slight variations in the results from ephem, the time of dawn and dusk may drift by a second or two
        # this caters for it be reusing any existing folder thats timestamped within 10s
        capdirbase = os.path.split(capdirname)[1]
        # FIXME
        existingfolder = glob.glob(os.path.join('/home/mark/data/auroracam', capdirbase[:-2]+'*'))
        if len(existingfolder) > 0:
            capdirname = existingfolder[0]

        if gotaframe and (daytimelapse or isnight): 
            os.makedirs(capdirname, exist_ok=True)
            fnam2 = os.path.join(capdirname, now.strftime('%Y%m%d_%H%M%S') + '.jpg')
            shutil.copyfile(fnam, fnam2)
            createLatestIndex(capdirname)
            uploadcounter += pausetime
            log.info(f'and copied to {capdirname}')
        # when we move from day to night, make the day timelapse then switch exposure and flag
        if now < dawn and now > dusk and isnight is False:
            if daytimelapse:
                # make the daytime mp4
                norebootflag = os.path.join(datadir, '..', '.noreboot')
                open(norebootflag, 'w')
                makeTimelapse(capdirname, s3, bucket, s3prefix, daytimelapse=True, youtube=yt)
                createLatestIndex(capdirname)
                os.remove(norebootflag)
            isnight = True
            setCameraExposure(ipaddress, 'NIGHT', nightgain, True, True)
            capdirname = os.path.join(datadir, dusk.strftime('%Y%m%d_%H%M%S'))
            os.makedirs(capdirname, exist_ok=True)

        # when we move from night to day, make the night timelapse then switch exposure and flag and reboot
        if dusk != lastdusk and isnight:
            norebootflag = os.path.join(datadir, '..', '.noreboot')
            open(norebootflag, 'w')
            makeTimelapse(capdirname, s3, bucket, s3prefix, youtube=yt)
            createLatestIndex(capdirname)
            log.info('switched to daytime mode, now rebooting')
            setCameraExposure(ipaddress, 'DAY', nightgain, True, True)
            os.remove(norebootflag)
            try:
                os.system('/usr/bin/sudo /usr/sbin/shutdown -r now')
            except Exception as e:
                log.info('unable to reboot')
                log.info(e, exc_info=True)

        testmode = int(os.getenv('TESTMODE', default=0))
        log.info(f'fnam is {fnam}, uploadcounter {uploadcounter}')
        if uploadcounter > 9 and testmode == 0 and os.path.isfile(fnam):
            #log.info('uploading image')
            if s3 is not None:
                try:
                    s3, bucket, s3prefix = s3details(thiscfg, hostname)
                    s3.meta.client.upload_file(fnam, bucket, f'{s3prefix}/live.jpg', ExtraArgs = {'ContentType': 'image/jpeg'})
                    log.info(f'uploaded live image to {bucket}/{s3prefix}')
                    uploadcounter = 0
                except Exception as e:
                    log.warning(f'upload to {bucket}/{s3prefix} failed')
                    log.info(e, exc_info=True)
            else:
                #log.info('s3 not configured')
                pass
            if ftpserver is not None:
                try:
                    uploadOneFile(fnam, ftploc, ftpserver, userid, sshkey)
                    log.info(f'uploaded live image to {ftpserver}')
                    uploadcounter = 0
                except Exception as e:
                    log.warning(f'upload to {ftpserver} failed')
                    log.info(e, exc_info=True)
            else:
                #log.info('ftpserver not configured')
                pass
        if testmode == 1:
            log.info(f'would have uploaded {fnam}')
        log.info(f'sleeping for {pausetime} seconds')
        if os.path.isfile(os.path.expanduser('~/.stopac')):
            os.remove(os.path.expanduser('~/.stopac'))
            log.info('Shutting down at user request')
            exit(0)
        time.sleep(pausetime)
