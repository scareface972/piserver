PiServer
========

RaspberryPi Python Server
- Web interface for GPIO control
- A recognition system of sentences (regular expressions) to execute one (or more) command.
- Independent modules automatically loaded and configured

Requirements
------------

* A RaspberryPi (with Raspbian not tested with other distrib)
* Python3 (with Bottle)

First
-----

Setup configuration server file, by default "piserver.json"
Verify by run command:
* sudo python3 /path/to/piserver.py

Run as Service
--------------

Copy "piserver.init" to /etc/init.d/piserver
Modify /etc/init.d/piserver with good path to your piserver.py
Make executable: sudo chmod +x /etc/init.d/piserver

* Starting service: sudo /etc/init.d/piserver start
* Stopping service: sudo /etc/init.d/piserver stop
* Restarting service: sudo /etc/init.d/piserver restart

Voice Recognition
-----------------

Edit "speech2text.py" and setup RaspberryPi IP address
Start speech2text.py and speak
