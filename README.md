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
* ATMega328 (with Arduino bootloader)
* DHT11, BH1750, RF receiver/transmiter
* Logic Level Converter (rpi <--serial--> atmega328)

Installation
------------

* PiServer App (Python)
 - cd /tmp
 - git clone https://github.com/btouchard/piserver.git
 - cd piserver
Ensure dependencies
 - sudo ./setup.py develop 
Install
 - sudo ./setup.py install

* Compile and upload atmega328 sketch to ATMega328 using Arduino IDE and board
* Or upload .hex with avrdude

* Wire :
```
	Component			| ATMega328 Pin
	--------------------|---------------------------
	RPi TX 				| Digital Pin 0 (RX)
	RPi RX 				| Digital Pin 1 (TX)
	RF receiver			| Digital Pin 2
	RF transmiter		| Digital Pin 3
	DHT11				| Digital Pin 4
	BH1750 (I²C)		| Analog Input 4 and 5 (I²C)
	--------------------|---------------------------
	Component (Option)	| ATMega328 Pin
	--------------------|---------------------------
	LED (Input RF)		| Digital Pin 7
	LED (Output RF)		| Digital Pin 8
```

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
