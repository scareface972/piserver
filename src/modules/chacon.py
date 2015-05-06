import core.controller
import modules.gpio
import wiringpi2 as wpi
from time import sleep, time
import re, json, pycurl
from io import BytesIO
import threading, logging
import Chacon as rf

logging.basicConfig(filename='piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Chacon']

class Chacon(modules.Module):
	"""Class Chacon RF 433.92MHz"""

	def __init__(self, conf):
		super().__init__(conf)
		self.pinIn = conf['pinIn']
		self.pinOut = conf['pinOut']
		self.emitter = conf['emitter']
		self.emitters = []
		self.receivers = []
		self.code = self.interruptor = self.state = 0
		self._load_conf()
		self.thread = threading.Thread(target=self.worker)
		self.thread.daemon = True
		self.thread.start()
		
	def _load_conf(self):
		path = 'chacon.json' if core.controller.Controller.DEBUG else '/usr/local/piserver/chacon.json'
		config = json.loads(open(path).read())
		mod_name = self.get_module_name()
		if 'receivers' in config:
			for name in config['receivers']:
				rc = config['receivers'][name]
				cmds = ['on', 'toggle', 'off']
				self.receivers.append({'name': name, 'where': rc['where'], 'group': rc['group'], 'interruptor': rc['interruptor'], 'state': False, 'type': mod_name, 'is_switch': True, 'cmds': cmds})
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

	def get_switcher(self, cmd):
		for receiver in self.receivers:
			if cmd.startWith(receiver['name']):
				return receiver['name']
		return None

	def list_cmds(self):
		return self.cmds

	def execute(self, cmd):
		print("exec", cmd)
		name = cmd.split("/")[0]
		result = dict(success=False, name=name)
		receiver = self._find_interruptor(name)
		if receiver == None:
			result['error'] = 'Unknown target'
		else:
			cmd = cmd.split("/")[1]
			if cmd == 'associate':
				rf.send(self.pinOut, self.emitter, receiver['interruptor'], 1)
				result['state'] = receiver['state']
				result['success'] = True
			else:
				if cmd == 'toggle': new_state = not receiver['state']
				elif cmd == 'on': new_state = True
				elif cmd == 'off': new_state = False
				#if receiver['state'] != new_state:
				rf.send(self.pinOut, self.emitter, receiver['interruptor'], int(new_state))
				result['state'] = receiver['state'] = new_state
				result['success'] = True
		return result
	
	def get_receiver_name(self, code, interruptor, group, state):
		print("emitter callback", code, interruptor, group, state)
		emitter = self._find_emitter(code, interruptor)
		if emitter == None: return
		#print("-> emitter", emitter['name'])
		receiver = self._find_interruptor(emitter['name'])
		if receiver == None: return
		#print("-> receiver", receiver['name'])
		cmd = receiver['name'] + '/toggle' # + ('on' if state == 1 else 'off')
		sleep(2)
		self.execute(cmd)

	def worker(self):
		#print("Start worker...")
		while True:
			rf.setCallback(self.get_receiver_name)
			rf.receive(self.pinIn, self.pinOut, self.emitter)

#class Manager(threading.Thread):
#
#	def __init__(self, parent):
#		threading.Thread.__init__(self)
#		self.cmds = []
#		self.event = threading.Event()
#		self.t1 = Producer(parent, self.cmds, self.event)
#		self.t2 = Consumer(parent, self.cmds, self.event)
#
#	def run(self):
#		self.t1.start()
#		self.t2.start()
#		self.t1.join()
#		self.t2.join()
#
#class Producer(threading.Thread):
#	"""
#	Listen for 433.92MHz message
#	"""
#
#	def __init__(self, parent, cmds, event):
#		"""
#		Constructor.
#
#		@param cmds list of commands
#		@param condition condition synchronization object
#		"""
#		threading.Thread.__init__(self)
#		self.parent = parent
#		self.cmds = cmds
#		#self.condition = condition
#		self.event = event
#
#	def callback(self, code, interruptor, group, state):
#		print("callback", code, interruptor, group, state)
#		emitter = self.parent._find_emitter(code, interruptor)
#		if emitter == None: return
#		print("-> emitter", emitter['name'])
#		receiver = self.parent._find_interruptor(emitter['name'])
#		if receiver == None: return
#		print("-> receiver", receiver['name'])
#		cmd = receiver['name'] + '/' + ('on' if state == 1 else 'off')
#		self.cmds.append(cmd)
#		print('%s appended to list by %s' % (cmd, self.name))
#		self.event.set()
#		self.event.clear()
#
#	def run(self):
#		rf.setCallback(self.callback)
#		rf.receive(self.parent.pinIn, self.parent.pinOut, self.parent.emitter)
#		#print('condition notified by %s' % self.name)
#		#self.condition.notify()
#		#print('condition released by %s' % self.name)
#		#self.condition.release()
#		#sleep(1)
#
#class Consumer(threading.Thread):
#	"""
#	Consumes commands in list
#	"""
#
#	def __init__(self, parent, cmds, event):
#		"""
#		Constructor.
#
#		@param cmds list of commands
#		@param condition condition synchronization object
#		"""
#		threading.Thread.__init__(self)
#		self.parent = parent
#		self.cmds = cmds
#		self.event = event
#
#	def run(self):
#		"""
#		Thread run method. Consumes integers from list
#		"""
#		while True:
#			self.event.wait()
#			sleep(2)
#			try:
#				cmd = self.cmds.pop()
#				print('%s popped from list by %s' % (cmd, self.name))
#				self.parent.execute(cmd)
#			except IndexError:
#				#time.sleep(1)
#				pass
#			#print('condition acquired by %s' % self.name)
#			#while True:
#			#	if self.cmds:
#			#		cmd = self.cmds.pop()
#			#		print('%s popped from list by %s' % (cmd, self.name))
#			#		break
#			#	print('condition wait by %s' % self.name)
#			#	self.condition.wait()
#			#print('condition released by %s' % self.name)
#			#self.condition.release()