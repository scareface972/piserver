PiServer
========

RaspberryPi Python Server
* Web interface for environment control
* A recognition system of sentences (regular expressions) to execute one (or more) command.
* Independent modules automatically loaded and configured
* Speech recognition & Voice synthesizing

Requirements
------------

* A RaspberryPi (with Raspbian not tested with other distrib)
* Python3 (with Bottle, http://bottlepy.org)
* WiringPi library (http://wiringpi.com)

Installation
------------

* Download distribution PiServer-X.X.tar.gz
* Extract archive and go to directory
	tar xzf PiServer-X.X.tar.gz && cd PiServer-X.X
* Now, install server (from extract directory)
	1. sudo apt-get install build-essential python3 python3-dev python3-setuptools python3-pip
	2. sudo pip-3 -r requirements.txt
	3. sudo python3 setup.py install
* And for uninstall server (from extract directory)
	sudo pip-3 uninstall piserver -r requirements.txt

Configuration
-------------

* Edit /usr/local/piserver/config.json

Running/Stopping service
------------------------

* sudo service piserver start
* sudo service piserver stop
* sudo service piserver restart

Speech recognition
==================
Speech recognition is actualy on local computer to a question of microphone quality

Modify config in speech2text.py and run program.
You must be register as Google Developper and enable Speech API for use it !

Chacon interruptor
==================

* Requiere RF 433.92MHz transmiter connected to RPi

Define Chacon interruptor to config.json (ex enrty:)
```json
{
	...
	"plafond": {
		"module": "chacon.Interruptor", 	// Module target
		"where": "salon",					// Interruptor physic emplacement
		"group": "lumiere",					// Module group name
		"pin": 0,							// RF Transmiter PIN
		"code": {
			"sender": "8976434",			// Sender code (identify RPi as remote)
			"interruptor": "1"				// Interrupteur number
		}
	}
	...
}
```

Freebox
=======

* Requiere Freebox

Define Freebox interruptor to config.json (ex enrty:)
```json
{
	...
	"freebox": {
		"module": "freebox.Freebox", 		// Module target
		"where": "salon",					// Freebox physic emplacement
		"alias": "tele",					// Module alias name
		"box": "hd1",						// Box url prefix
		"code": "00000000"					// HTTP Remote code
	}
	...
}
```

Temperature & Presure
=====================

* Requiere DHT11 module connected to RPi

Define DHT11 sensor to config.json (ex enrty:)
```json
{
	...
	"temp": {
		"module": "sensor.DHT11",			// Module target
		"pin": 1							// DHT11 Module PIN
	}
	...
}
```

Light capture
=============

* Requiere BH1750FVI module connected to RPi
* Requiere I2C enabled in your RPi (http://skpang.co.uk/blog/archives/575)
* Requiere SMBus for Python 3
	Download and extract : http://ftp.de.debian.org/debian/pool/main/i/i2c-tools/i2c-tools_3.1.0.orig.tar.bz2
	Patch i2c-tools_3.1.0/py-smbus/smbusmodule.c by this : http://permalink.gmane.org/gmane.linux.drivers.i2c/11337
	Install by running : cd i2c-tools_3.1.0/py-smbus && sudo python3 setup.py install

Define BH1750FVI sensor to config.json (ex enrty:)
```json
{
	...
	"light": {
		"module": "sensor.BH1750FVI",			// Module target
		"pin": "i2c"							// BH1750FVI Work with i2c
	}
	...
}
```
