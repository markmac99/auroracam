# A Simple Aurora Camera

The scripts in this folder implement a very simple aurora camera using a barebones IP camera.  As well as the Atom mini-pc mentioned below I have installed it on a Raspberry Pi4 running Bookworm 64-bit, but any small computer would do as long as its running a variant of Linux and has Python 3.7 or later. 

## How it works
A python script captures an image from the camera every few seconds. At the end of the night, the saved images are made into an MP4 and hhe host is rebooted to ensure a clean start for the next day. The software also captures during the day, creating a separate set of data and timelapse. 

### Startup
The software runs as a service and starts automatically. To stop or start it, type the following in a Terminal window:  
``` bash
systemctl --user stop auroracam
systemctl --user start auroracam
``` 

### Configuration File
This holds the IP address, camera location and name, and the location of data and logs as well as the name of any S3 bucket if thats being used. You can also tweak the gain to set the camera to at night though the default should be good.  See the section on Installation for more information. 

### Camera Configuration
The camera is configured by the software (using the python-dvr library) and no manual tweaks should be needed. The exposure and gain are automatically changed at dawn and dusk. 

Note 2024-10-08 i realised i am not setting some parameters correctly (such as disabing the OSD and setting the video mode). Will update this shortly. 

## Hardware
The camera module I'm using is an IMX307 but an IMX291 should also work. When ordering the camera module, specify No Lens and With 48V PoE cable.  I'm using the 4mm F/0.95 lens we use for meteor hunting.  Here's links to the ones i bought, but be warned that links at AliExpress expire and / or get changed so you may need to hunt around:  [Camera](https://www.aliexpress.com/item/1005002676397053.html?spm=a2g0o.order_list.order_list_main.5.638a1802CB1j2M) and [lens](https://www.aliexpress.com/item/1005003145991079.html?spm=a2g0o.order_list.order_list_main.16.638a1802CB1j2M). 

You'll also need a waterproof housing. Suitable CCTV housings can be got from Aliexpress too eg [this one](https://www.aliexpress.com/item/32355130687.html?spm=a2g0o.order_list.order_list_main.25.78581802njHV4Y). Make sure you choose the Plate and Bracket option.

I'm running the software on an Intel ATOM Z8350 miniPC with 4GB memory running Armbian but I also have it running on a Raspberry Pi4b. 

## webserver
A webserver is set up during installation and can be used to view the latest data, historical images and logs.  The webserver can be accessed at http://yourpisname/ where `yourpisname` is the hostname of the raspberry Pi. To make it easier to find, i recommend you give it a unique name such as "auroracam". Note that the site is http not https. 

### Installation
On the target computer, run the following  

``` bash
mkdir -p ~/source/auroracam
cd ~/source/auroracam
wget https://raw.githubusercontent.com/markmac99/auroracam/refs/heads/master/install.sh
bash ./install.sh
```

### Now edit `config.ini` and fill in following
  * IPADDRESS - the IP address of your camera
  * LAT, LON, ALT - your latitude & longitude in degrees (+ for East) and elevation above sealevel in metres. 
  * other values can be left at their defauults. 
  
Now reboot the pi. Shortly after reboot it should start capturing data - you will see the lights on the camera cable flickering every few seconds.  

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
