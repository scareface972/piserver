PiServer
========

Un petit serveur domotique
* Contrôler vos lumière, freebox
* Connaître la température, la lumière
* Mise en place de règles automatiques
* Interface de controle web & mobile
* Reconnaissance et synthétisation vocale
* Tous les modules sont indépendants

Il vous faudra
--------------

* Un RaspberryPi (2 conseillé) (avec de préférence Raspbian je n'ai pas tester les autres distrib)
* Python3
* ATMega328 (with Arduino bootloader)
* DHT11, BH1750, RF receiver/transmiter
* Logic Level Converter (rpi <--serial--> atmega328)

Installation
------------

* Installation de l'application:

```
$ cd /tmp
$ git clone https://github.com/btouchard/piserver.git
$ cd piserver
# Ensure dependencies
$ sudo apt-get install libasound2-plugins libasound2-dev libportaudio-dev python3 python3-pip python3-pyaudio flac libcurl4-openssl-dev libssl-dev --yes
$ sudo ./setup.py develop 
# And finally install
$ sudo ./setup.py install
```

* Uploadez .hex sur l'ATMega328 avec avrdude par exemple ou recompilez le sketch avec un Arduino

* Branchements :

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
```

* Vous pouvez désinstaller le serveur avec :

```
$ sudo pip-3 uninstall piserver -r requirements.txt
```

Configuration
-------------

* Editez le fichier de configuration /usr/local/piserver/config.json
Changez au minimum l'IP de votre RPi
Vous pouvez activer/désactiver les modules depuis ce fichier
```json
enable: true/false
```

Lancer le serveur indépendant
-----------------------------

```
$ sudo piserver
```

Ou en tant que service
----------------------

```
$ sudo service piserver start
$ sudo service piserver stop
$ sudo service piserver restart
```

Reconnaissance vocale
=====================

* Enregistrez vous auprès de Google Developper et activez l'api "Speech API" afin d'indiquer la clé d'api dans le fichier config.json
* Connectez un micro USB 
* Petite liste rapide et non exostive de reconnaissance par module
	- chacon: alume/eteint la|les nom|groupe (se base sur les noms dans la config)
	- freebox: allume/eteint la freebox|télé, monte le son, baise le son, chaine [numero_chaine], france 2, canal plus...
	- speech: quelle heure est-il, quel jour sommes-nous, quel temps fait-il, quel temps fait-il aujourd'hui, quel temps fera-il demain, quel temps fera-il dans 2 jours...
	- DHT11: combien fait-il|quelle est la température, quelle est l\'humidité

Fonctionnement 
==============

* Ce sont les modules qui fournissent les phrases clés (anlysés via des expressions régulières)

* Si vous avez par exemple un récepteur Chacon (norme HomeEasy V1/V2) dans la cuisine et que vous avez créer une entrée dans le fichier de configuration /usr/local/piserver/chacon.json comme par exemple 

```json
"cuisine": {
	"protocole": 2,
	"where": "cuisine",
	"group": "lumiere",
	"unit": 3,
	"emitters": [
		{ "protocole": 2, "code": 13552350, "unit": 0, "toggle": true, "repeat": 5 },
		{ "protocole": 2, "code": 17144714, "unit": 0 }
	]
}
```

Alors vos 2 interrupteurs (emetteurs) 13552350 et 17144714 peuvent contrôler la cuisine.
Vous pouvez aussi dire "alume la cuisine" ou "alume la lumière" (allumera le groupe lumière) afin d'allumer la cuisine.
Il en va de même avec "éteint la cuisine" ou "éteint les lumières"
Vous pourrez également allumer ou éteindre votre cuisine depuis l'interface web (http://ip_di_rpi) ou depuis l'app Android.
