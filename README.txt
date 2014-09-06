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

* Clone or download and extract the archive to a folder of your choice, eg "/etc/piserver/".
* Edit the configuration file JSON "piserver.json" in there specifying the ip and port for the server (web and api).
* Start the server with superuser privileges "sudo python3 piserver.py"

Run as Service
--------------

* Copy "piserver.init" to /etc/init.d/piserver
* Modify /etc/init.d/piserver with good path to your piserver.py
* Make executable: sudo chmod +x /etc/init.d/piserver

* Starting service: sudo /etc/init.d/piserver start
* Stopping service: sudo /etc/init.d/piserver stop
* Restarting service: sudo /etc/init.d/piserver restart

Voice Recognition
-----------------

* Copy "speech2text.py" on your local computeur
* Edit "speech2text.py" and setup RaspberryPi IP address
* Start speech2text.py and speak
