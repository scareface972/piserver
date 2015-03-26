import modules.gpio
import wiringpi2 as wpi
from time import sleep, time
import threading, logging
import ChaconEmitter, ChaconReceiver

logging.basicConfig(filename='piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Interruptor']

# Interrupteur RF (Chacom)
class Interruptor(modules.gpio.GPIOOutput):
	"""Class 'Interruptor' interrupteur RF (Chacon)"""

	def __init__(self, conf):
		self.group = 0
		self.sender = int(conf['code']['sender'])
		self.interruptor = int(conf['code']['interruptor'])
		super().__init__(conf)
		self.cmds['associate'] = None

	def execute(self, cmd):
		logging.debug('Interruptor::execute: ' + cmd)
		result = dict(success=False, name=self.name, state=self.state)
		if cmd == 'associate':
			ChaconEmitter.send(self.pin, self.sender, self.interruptor, 1)
			result['state'] = self.state
			result['success'] = True
		else:
			current = 1 if self.state else 0
			if cmd == 'toggle': new_state = current == 1 if 0 else 1
			elif cmd == 'on': new_state = 1
			elif cmd == 'off': new_state = 0
			if current != new_state:
				current = ChaconEmitter.send(self.pin, self.sender, self.interruptor, int(new_state))
				self.state = True if current == 1 else False
				result['state'] = self.state
				result['success'] = True
		return result

class Receiver(modules.Module):
	def __init__(self, conf):
		super().__init__(conf)
		self.pin = conf['pin']
		self.thread = threading.Thread(target=self.worker)
		self.thread.start()

	def worker(self):
		#ChaconReceiver.setCallback(self.callback)
		ChaconReceiver.run(self.pin)

	def callback(self, value):
		print("callback", value)
