#!/bin/bash
# copyright mark mcintyre, 2024-

sudo apt-get install -y python3-opencv lighttpd virtualenv vim
virtualenv ~/vAuroracam  
source ~/vAuroracam/bin/activate  
pip install --upgrade pip
mkdir -p ~/source/auroracam
mkdir -p ~/data/{auroracam,logs}
chmod 755 ~
cd ~/source/auroracam
[ -f config.ini ] && mv config.ini config.bkp
flist=(startAuroraCam.sh auroraCam.py config.ini setExpo.py sendToYoutube.py makeImageIndex.py imgindex.html.template index.html redoTimelapse.py mqtt.cfg requirements.txt auroracam.service) 
for f in ${flist[@]} ; do
[ -f ${f} ] && rm ${f}
wget https://raw.githubusercontent.com/markmac99/auroracam/refs/heads/master/${f}  
done 
chmod +x *.sh
pip install -r requirements.txt
sudo cp index.html /var/www/html
sudo ln -s $HOME/data /var/www/html
grep dir-listing /etc/lighttpd/lighttpd.conf
if [ $? -eq 1 ] ; then 
sudo chmod 666 /etc/lighttpd/lighttpd.conf 
echo server.dir-listing = \"enable\" >> /etc/lighttpd/lighttpd.conf 
sudo chmod 644 /etc/lighttpd/lighttpd.conf
sudo systemctl restart lighttpd
fi 
sudo cp auroracam.service /etc/systemd/user
systemctl --user daemon-reload
systemctl --user enable auroracam
systemctl --user start auroracam
loginctl enable-linger

