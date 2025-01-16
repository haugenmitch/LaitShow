# LaitShow

Map and control Neopixels in 3D space.

The idea for this project came from Matt Parker's Christmas tree project and a desire to make it more generally applicable. The name is pronounced "Light Show".

## Instructions

Clone this repo on you local machine and on the raspberry pi that will be controlling the Neopixels.

Place `laitshow.service` in `/etc/systemd/system/` on the raspberry pi. Then run:
```
$ sudo systemctl enable laitshow.service
$ sudo systemctl start laitshow.service
```
