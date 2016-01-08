ALSA USB MICROPHONE CONFIGURATION
=================================

Configuration du micro USB
--------------------------

```
$cat /proc/asound/cards 
	0 [ALSA   ]: bcm2835 - bcm2835 ALSA bcm2835 ALSA
	1 [CODEC ]: USB-Audio .....
```

Editer alors alsa-base.conf
```
$sudo nano /etc/modprobe.d/alsa-base.conf
```

Changer la ligne
	options snd-usb-audio index=-2
par
	options snd-usb-audio index=0

Redémarer
```
$sudo reboot
```

Après le reboot, un cat devrait donner:

```
$cat /proc/asound/cards 
	0 [CODEC ]: USB-Audio .....
	1 [ALSA   ]: bcm2835 - bcm2835 ALSA bcm2835 ALSA
```


/etc/asound.conf
----------------

```
$sudo nano etc/asound.conf
```

```
pcm.usb
{
    type hw
    card CODEC
}

pcm.internal
{
    type hw
    card ALSA
}

pcm.!default
{
    type asym
    playback.pcm
    {
        type plug
        slave.pcm "internal"
    }
    capture.pcm
    {
        type plug
        slave.pcm "usb"
    }
}

ctl.!default
{
    type asym
    playback.pcm
    {
        type plug
        slave.pcm "internal"
    }
    capture.pcm
    {
        type plug
        slave.pcm "usb"
    }
}
```


Vérifier que le microphone soit bien reconnu
--------------------------------------------

```
amixer -c 0 sget 'Mic',0
```

SOURCE
------
https://wolfpaulus.com/journal/embedded/raspberrypi2-sr/
