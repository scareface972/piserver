import modules.gpio
import wiringpi2 as wpi
from time import sleep, time
import re, json
import threading, logging
import ChaconEmitter, ChaconReceiver

logging.basicConfig(filename='piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Emitter', 'Receiver']

# Interrupteur RF (Chacom)
class Emitter(modules.Switch):
	"""Class 'Emitter' interrupteur RF (Chacon)"""

	def __init__(self, conf):
		super().__init__(conf)
		self.sender = conf['sender']
		self.receivers = []
		self._load_conf()

	def _load_conf(self):
		conf_file = 'chacon.json'
		config = json.loads(open(conf_file).read())
		if config['receivers']:
			for name in config['receivers']:
				rc = config['receivers'][name]
				self.receivers.append({'name': name, 'where': rc['where'], 'group': rc['group'], 'interruptor': rc['interruptor']})

	def _find_interruptor(self, name):
		for r in self.receivers:
			if r['name'] == name: return r['interruptor']
		return None

	def _get_receiver(self):
		for module in self.controller.enabled:
			if module.name == 'receiver':
				return module
		return None

	def execute(self, cmd):
		#logging.debug('Emitter::execute: ' + cmd)
		name = cmd.split("/")[0]
		result = dict(success=False, name=name, state=self.state)
		interruptor = self._find_interruptor(name)
		if interruptor == None:
			result['error'] = 'Unknown target'
		receiverInst = self._get_receiver()
		if receiverInst != None: receiverInst.running = False
		cmd = cmd.split("/")[1]
		if cmd == 'associate':
			ChaconEmitter.send(self.pin, self.sender, interruptor, 1)
			result['state'] = self.state
			result['success'] = True
		else:
			current = 1 if self.state else 0
			if cmd == 'toggle': new_state = 0 if current == 1 else 1
			elif cmd == 'on': new_state = 1
			elif cmd == 'off': new_state = 0
			if current != new_state:
				current = ChaconEmitter.send(self.pin, self.sender, interruptor, int(new_state))
				self.state = True if current == 1 else False
				result['state'] = self.state
				result['success'] = True
		if receiverInst != None: receiverInst.running = True
		return result

class Receiver(modules.Module):
	running = True

	def __init__(self, conf):
		self.pin = conf['pin']
		super().__init__(conf)
		self.emitters = []
		self._load_conf()
		self.thread = threading.Thread(target=self.worker)
		self.thread.daemon = True
		self.thread.start()

	def _load_conf(self):
		conf_file = 'chacon.json'
		config = json.loads(open(conf_file).read())
		if config['emitters']:
			for name in config['emitters']:
				em = config['emitters'][name]
				self.emitters.append({'name': name, 'code': em['code'], 'interruptor': em['interruptor']})

	def _get_emitter(self):
		for module in self.controller.enabled:
			if module.name == 'emitter':
				return module
		return None

	def worker(self):
		print("Start worker...")
		ChaconReceiver.setCallback(self.callback)
		ChaconReceiver.run(self.pin)

	def callback(self, sender, on, interruptor):
		print("callback", "sender", sender, "on", on, "interruptor", interruptor)
		print("Receiver.running", Receiver.running)
		if not Receiver.running: return
		for emitter in self.emitters:
			print ("Emitter", emitter)
			if emitter['sender'] == sender and emitter['interruptor'] == recipient:
				if emitter['disabled']: continue
				print("emitter", emitter)
				emitterInst = self._get_emitter()
				if emitterInst == None: return
				emitterInst.execute(emitter['name'] + "/toggle")
		return 1