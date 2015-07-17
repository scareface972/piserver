# -*- coding: utf-8 -*-

import core.controller
import modules.gpio
import wiringpi2 as wpi
from time import sleep, time
import re, json, os
import threading, logging
import Chacon as rf

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Chacon']

def log(value):
	print(value)
	logging.debug(value)

class Chacon(modules.Threadable):
	"""Class Chacon RF 433.92MHz"""

	def __init__(self, conf):
		self.cmds = {}
		self.module_name = conf['module']
		self.pinIn = conf['pinIn']
		self.pinOut = conf['pinOut']
		self.emitter = conf['emitter']
		self.emitters = []
		self.receivers = []
		self.code = self.interruptor = self.state = 0
		self._load_conf()
		super().__init__(conf, self.cmds)
		if not 'enabled_receiver' in conf or conf['enabled_receiver']:
			self.thread.start()
		
	def _load_conf(self):
		path = 'chacon.json' if core.controller.Controller.DEBUG else '/usr/local/piserver/chacon.json'
		log('Chacon::load emitters and receivers: ' + path)
		config = json.loads(open(path).read())
		mod_name = self.get_module_name()
		if 'receivers' in config:
			for name in config['receivers']:
				rc = config['receivers'][name]
				key = "((\w+\s)?("+name
				if 'where' in rc: key += "|"+rc['where']
				if 'alias' in rc: key += "|"+rc['alias']
				if 'group' in rc: key += "|"+rc['group']
				key += ")\s?)"
				self.cmds[name+'/toggle'] = name
				self.cmds[name+'/on'] = "allumer?\s"+key+"+"
				self.cmds[name+'/off'] = "(etein(dre|s))\s"+key+"+"
				self.cmds[name+'/associate'] = None
				self.receivers.append({'name': name, 'interruptor': rc['interruptor'], 'state': False, 'type': mod_name, 'is_switch': True, 'cmds': ['on', 'off', 'toggle', 'associate']})
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

	def execute(self, cmd):
		log("Chacon::execute: " + cmd)
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
				rf.send(self.pinOut, self.emitter, receiver['interruptor'], int(new_state))
				result['state'] = receiver['state'] = new_state
				result['success'] = True
		return result
	
	def receive_callback(self, code, interruptor, group, state):
		log("Chacon::callback: " + str(code) + ", " + str(interruptor) + ", " + str(group) + ", " + str(state))
		if self.get_running():
			emitter = self._find_emitter(code, interruptor)
			if emitter == None: return
			#log("-> emitter: " + emitter['name'])
			receiver = self._find_interruptor(emitter['name'])
			if receiver == None: return
			log("-> receiver: " + receiver['name'] + " toggle")
			cmd = receiver['name'] + '/toggle' # + ('on' if state == 1 else 'off')
			self.execute(cmd)

	def worker(self):
		print("-> Chacon worker start...")
		self.set_running(True)
		while self.get_running():
			rf.setCallback(self.receive_callback)
			rf.receive(self.pinIn, self.pinOut, self.emitter)
		print("-> Chacon worker stopped")

	def get_running(self):
		return super().get_running()

	def set_running(self, value):
		#print("set_running", super().get_running(), value)
		if not value: rf.stop()
		super().set_running(value)
