import modules.gpio
import wiringpi2 as wpi
from threading import Thread
from time import sleep, time

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Switch']

OUTPUT = 1
LOW = 0
HIGH = 1
PIN_OUT = 0

SHORT_DELAY = 100
LONG_DELAY = 400
VERROU1 = 9000
VERROU2 = 2000

REPEAT_COUNT = 5

# Interrupteur RF (Chacom)
class Switch(modules.gpio.Output):
	"""Class 'Switch' interrupteur RF (Chacom)"""

	def __init__(self, conf):
		# print(conf['code'])
		self.sender = conf['code']['sender']
		self.interruptor = conf['code']['interruptor']
		super().__init__(conf)

	def execute(self, cmd):
		result = dict(success=False, name=self.name, state=self.state)
		try:
			if cmd == 'toggle': new_state = not self.state
			elif cmd == 'on': new_state = True
			elif cmd == 'off': new_state = False
			if self.state != new_state:
				t = SenquenceThread(self.pin, self.sender, self.interruptor, new_state)
				t.start()
				self.state = new_state
				result['state'] = new_state
				result['success'] = True
		except:
			pass
		return result

class SenquenceThread(Thread):
	def __init__(self, pin, sender, interruptor, state):
		Thread.__init__(self)
		self.pin = pin
		self.sender = sender
		self.interruptor = interruptor
		self.group = 0
		self.state = 1 if state else 0

	def delayMicroseconds(self, ms):
		s = ms / 1000000
		sleep(s)

	def delayMilliseconds(self, ms):
		s = ms / 1000
		sleep(s)

	def run(self):
		self.sender = '{0:026b}'.format(int(self.sender))
		self.interruptor = '{0:04b}'.format(int(self.interruptor))
		for i in range(0, REPEAT_COUNT):
			# print("pin:", self.pin, "sender:", self.sender, "interruptor:", self.interruptor, "state:", self.state)
			self.transmit(self.sender, self.interruptor, self.group, self.state)
			self.delayMilliseconds(10)

	def transmit(self, sender, interruptor, group, state):
		# Sequence de verrou anoncant le départ du signal au recepeteur
		wpi.digitalWrite(self.pin, HIGH)
		self.delayMicroseconds(SHORT_DELAY)     	# un bit de bruit avant de commencer pour remettre les delais du recepteur a 0
		wpi.digitalWrite(self.pin, LOW)
		self.delayMicroseconds(VERROU1)    			# premier verrou de 9900µs
		wpi.digitalWrite(self.pin, HIGH)    		# high again
		self.delayMicroseconds(SHORT_DELAY)     	# attente de 275µs entre les deux verrous
		wpi.digitalWrite(self.pin, LOW)     		# second verrou de 2675µs
		self.delayMicroseconds(VERROU2)
		wpi.digitalWrite(self.pin, HIGH)    		# On reviens en état haut pour bien couper les verrous des données

		# Envoie du code emetteur (272946 = 1000010101000110010  en binaire)
		for i in sender:
			self.sendPair(int(i))

		# Envoie du bit définissant si c'est une commande de groupe ou non (26em bit)
		self.sendPair(group)
		# Envoie du bit définissant si c'est allumé ou eteint 27em bit)
		self.sendPair(state)

		# Envoie des 4 derniers bits, qui représentent le code interrupteur, ici 0 (encode sur 4 bit donc 0000)
		# nb: sur  les télécommandes officielle chacon, les interrupteurs sont logiquement nommés de 0 à x
		# interrupteur 1 = 0 (donc 0000) , interrupteur 2 = 1 (1000) , interrupteur 3 = 2 (0100) etc...
		for i in interruptor:
			self.sendPair(int(i))

		wpi.digitalWrite(self.pin, HIGH)   			# coupure données, verrou
		self.delayMicroseconds(SHORT_DELAY)    		# attendre 275µs
		wpi.digitalWrite(self.pin, LOW)    			# verrou 2 de 2675µs pour signaler la fermeture du signal
		self.delayMicroseconds(VERROU2)

	def sendPair(self, b):
		# print("sendPair", b)
		if b:
			self.sendBit(1)
			self.sendBit(0)
		else:
			self.sendBit(0)
			self.sendBit(1)

	# Envois d'une pulsation (passage de l'etat haut a l'etat bas)
	# 1 = 310µs haut puis 1340µs bas
	# 0 = 310µs haut puis 310µs bas
	def sendBit(self, b):
		if b:
			wpi.digitalWrite(self.pin, HIGH)
			self.delayMicroseconds(SHORT_DELAY)   # 275 orinally, but tweaked.
			wpi.digitalWrite(self.pin, LOW)
			self.delayMicroseconds(LONG_DELAY)  # 1225 orinally, but tweaked.
		else:
			wpi.digitalWrite(self.pin, HIGH)
			self.delayMicroseconds(SHORT_DELAY)   # 275 orinally, but tweaked.
			wpi.digitalWrite(self.pin, LOW)
			self.delayMicroseconds(SHORT_DELAY)   # 275 orinally, but tweaked.