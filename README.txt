PiServer
========

RaspberryPi Python Server
* Web interface for environment control
* A recognition system of sentences (regular expressions) to execute one (or more) command.
* Independent modules automatically loaded and configured
* Speech recognition & Voice synthesizing

(Recording for the recognition is actualy on local computer to a question of microphone quality)

Requirements
------------

* A RaspberryPi (with Raspbian not tested with other distrib)
* Python3 (with Bottle, http://bottlepy.org)
* WiringPi (http://wiringpi.com)

Installation
------------

* Download distribution PiServer-X.X.tar.gz
* Extract archive and go to directory
	tar xzf PiServer-X.X.tar.gz && cd PiServer-X.X
* And install app
	sudo python3 setup.py install

Configuration
-------------

* Edit /usr/local/piserver/config.json

Running/Stopping service
------------------------

* sudo service piserver start
* sudo service piserver stop
* sudo service piserver restart