# A Simple Aurora Camera

The scripts in this folder implement a very simple aurora camera using a barebones IP camera.  As well as the Atom mini-pc mentioned below I have installed it on a Raspberry Pi4 running Bookworm 64-bit, but any small computer would do as long as its running a variant of Linux and has Python 3.7 or later. 

## How it works
A python script captures an image from the camera every few seconds. At the end of the night, the saved images are made into an MP4 and hhe host is rebooted to ensure a clean start for the next day. The software also captures during the day, creating a separate set of data and timelapse. 

### Scheduling the job
Each time the script is run it creates or updates a scheduled job in the Pi's crontab so there's no need to do this manually. 

### Configuration File
This holds the IP address, camera location and name, and the location of data and logs as well as the name of any S3 bucket if thats being used. You can also tweak the gain to set the camera to at night though the default should be good.  See the section on Installation for more information. 

### Camera Configuration
The camera is configured by the software (using the python-dvr library) and no manual tweaks should be needed. The exposure and gain are automatically changed at dawn and dusk. 

Note 2024-10-08 i realised i am not setting some parameters correctly. Will update this shortly. 

## Hardware
The camera module I'm using is an IMX307 but an IMX291 should also work.   
I'm running the software on an Intel ATOM Z8350 miniPC with 4GB memory running Armbian but it should work on pretty much any Linux hardware. 

## webserver
A webserver is set up during installation and can be used to view the latest data, historical images and logs. 

### Installation
On the target computer, run the following  

``` bash
mkdir -p ~/source/auroracam
cd ~/source/auroracam
wget https://raw.githubusercontent.com/markmac99/master/auroracam/install.sh
bash ./install.sh
```

### Now edit `config.ini` and fill in following
  * IPADDRESS - the IP address of your camera
  * CAMID - a camera ID which will be used as part of the filenames. 
  * LAT, LON, ALT - your latitude & longitude in degrees (+ for East) and elevation above sealevel in metres. 
  * other values can be left at their defauults. 
  
Now run *startAuroraCam.sh* and it should complete the installation and start capturing data.

After the first few images have been captured, press Ctrl-C to abort, then reboot the Pi. Log in again and wait one minute, then you should find that the software has automatically started up and is saving images.


## Advanced Configuration 
### uploading to AWS S3 or an FTP server
The images and MP4 can also be uploaded to an AWS S3 bucket or sFTP server by specifying details in the config file. Images are uploaded every 30 seconds.  

  * S3UPLOADLOC - if you want to upload to AWS S3 storage, provide a bucket name eg *s3://mybucket*. 
  * IDKEY - a CSV file containing the AWS key and secret.
 
  * FTPSERVER, FTPUSER, FTPKEY - the server, userid and ssh keyfile to use
  * FTPUPLOADLOC - the folder on the server to upload to
  
## Data Archival
The process generates a lot of data. Automatic housekeeping is performed and will compress, then delete
older data. You can specify how many days to keep via the ini file.

If you have access to an sftp server you can also configure the system to archive zip files of data for safe keeping. You will need to  update the ARCHIVE section of the config file with the server, user, user's ssh key location, and the target folder. 
