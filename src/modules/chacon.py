import modules.gpio
import wiringpi2 as wpi
from time import sleep, time
import re, json
import threading, logging
import Chacon as rf

logging.basicConfig(filename='piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Chacon']

class Chacon(modules.Module):
	"""Class Chacon RF 433.92MHz"""

	def __init__(self, conf):
		self.pinIn = conf['pinIn']
		self.pinOut = conf['pinOut']
		self.emitter = conf['emitter']
		super().__init__(conf)
		self.emitters = []
		self.receivers = []
		self.code = self.interruptor = self.state = 0
		self._load_conf()
		self.thread = threading.Thread(target=self.worker)
		self.thread.daemon = True
		self.thread.start()

	def _load_conf(self):
		conf_file = 'chacon.json'
		config = json.loads(open(conf_file).read())
		if 'receivers' in config:
			for name in config['receivers']:
				rc = config['receivers'][name]
				self.receivers.append({'name': name, 'where': rc['where'], 'group': rc['group'], 'interruptor': rc['interruptor'], 'state': False})
		if 'emitters' in config:
			for name in config['emitters']:
				em = config['emitters'][name]
				self.emitters.append({'name': name, 'code': em['code'], 'interruptor': em['interruptor']})

	def _find_interruptor(self, name):
		for r in self.receivers:
			if r['name'] == name: return r
		return None

	def _find_emitter(self, code, interruptor):
		for e in self.emitters:
			if e['code'] == code and e['interruptor'] == interruptor: return e
		return None

	def get_switchers(self):
		return self.receivers

	def list_cmds(self):
		return self.cmds
	
	def callback(self, code, interruptor, state):
		if self.emitter != code: #and (self.code != code or self.interruptor != interruptor or self.state != state):
			self.code = code
			self.interruptor = interruptor
			self.state = state
			print("callback", code, interruptor, state)
			emitter = self._find_emitter(code, interruptor)
			if emitter == None: return
			print("->", emitter['name'])
			receiver = self._find_interruptor(emitter['name'])
			if receiver == None: return
			receiver['state'] = True if state == 1 else False
			cmd = emitter['name']+'/'+('on' if receiver['state'] else 'off')
			print("->", cmd)
			th = threading.Thread(target=self.execute, args=(cmd,))
			th.daemon = True
			th.start()

	def worker(self):
		print("Start worker...")
		rf.setCallback(self.callback)
		rf.receive(self.pinIn, self.pinOut, self.emitter)

	def execute(self, cmd):
		print("exec", cmd)	
		name = cmd.split("/")[0]
		print("-> name", name)
		result = dict(success=False, name=name)
		receiver = self._find_interruptor(name)
		if receiver == None:
			result['error'] = 'Unknown target'
		else:
			result['state'] = receiver['state']
			cmd = cmd.split("/")[1]
			if cmd == 'associate':
				rf.send(self.pinOut, self.emitter, receiver['interruptor'], 1)
				result['success'] = True
			else:
				current = 1 if receiver['state'] else 0
				if cmd == 'toggle': new_state = 0 if current == 1 else 1
				elif cmd == 'on': new_state = 1
				elif cmd == 'off': new_state = 0
				if current != new_state:
					current = rf.send(self.pinOut, self.emitter, receiver['interruptor'], int(new_state))
					self.state = True if current == 1 else False
					result['state'] = receiver['state'] = True if new_state == 1 else False
					result['success'] = True
		return result