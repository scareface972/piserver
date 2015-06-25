# -*- coding: utf-8 -*-

from core.controller import Controller
import modules
from time import sleep
import os, json, logging
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename='/var/log/piserver/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Presence']

def log(value):
	print(value)
	logging.debug(value)

class ConfFileHandler(PatternMatchingEventHandler):
	def __init__(self, callback, file):
		super(ConfFileHandler, self).__init__(None, None, True, False)
		self.callback = callback
		self.file = file

	def dispatch(self, event):
		#print(event.event_type, event.is_directory, event.src_path)
		if event.src_path == self.file and event.event_type == 'modified':
			self.callback()

class Presence(modules.Module):
	"""Class 'Presence' pour la présence au domicile (via phone)"""

	def __init__(self, conf):
		super().__init__(conf)
		self.presence = {}
		self.rules = []
		self.has_owner = False
		self.first_time = True
		self.rules_path = './' if Controller.DEBUG else '/usr/local/piserver/'
		self.rules_file = self.rules_path + 'rules.json'
		self._set_observer()

	def _set_observer(self):
		#print('Set observer: ' + self.rules_path)
		observer = Observer()
		observer.schedule(ConfFileHandler(self._load_rules, self.rules_file), path=self.rules_path)
		observer.start()
		self._load_rules()

	def get(self):
		return self.has_owner or self.first_time

	def execute(self, cmd):
		log('Presence::execute: ' + cmd)
		result = dict(success=False)
		if cmd == 'list':
			presence = []
			for uid in self.presence:
				#log('--> uid: ' + uid + ', present: ' + str(self.presence[uid]['present']))
				if self.presence[uid]['present']:
					presence.append({'uid':uid, 'name':self.presence[uid]['name'], 'present':self.presence[uid]['present']})
			result['results'] = presence
			result['success'] = True
		else:
			uid, state, name = cmd.split('/')
			state = True if state == 'true' else False
			current = None if not uid in self.presence else self.presence[uid]['present']
			#log("-> uid: " + uid + ", name: " + name + " > " + str(state))
			#log('-> current: ' + str(current))
			if current != state or self.first_time:
				if not uid in self.presence: self.presence[uid] = {}
				self.presence[uid]['name'] = name
				self.presence[uid]['present'] = state
				log('-> change: ' + uid + ", name: " + name + ' > ' + str(state))
				self._check_change()
				self.first_time = False
			result['success'] = True
		return result

	def _check_change(self):
		#log('Presence::_check_change')
		if not len(self.presence) > 0: return
		has_owner = False
		for uid in self.presence:
			# print(uid, self.presence[uid])
			if self.presence[uid]['present'] == True:
				has_owner = True
				break
		#log('-> has owner: ' + str(has_owner))
		if has_owner != self.has_owner or self.first_time:
			self.has_owner = has_owner
			self._check_rules()

	def _load_rules(self):
		log('Presence::load rules: ' + self.rules_file)
		self.rules = json.loads(open(self.rules_file).read())
		for rule in self.rules: 
			log('-> rule: ' + rule['name'])

	def _check_rules(self):
		#log('Presence::_check_rules')
		for rule in self.rules:
			#log('-> rule: ' + rule['name'])
			execute = True
			for condition in rule['conditions']:
				#log('--> condition: ' + str(condition))
				mod = self.controller.get_module(condition['module'])
				if mod != None:
					value = mod.eval_rule(condition['prop'], condition['condition'], condition['value'])
					#log('--> result: ' + str(value))
					execute = execute and value
					if not execute: break
			#log('-> rule: ' + rule['name'] + ' > ' + str(execute))
			if execute:
				for action in rule['actions']:
					log('Presence::execute: ' + action['module'] + '/' + action['value'])
					self.controller.execute(action['module'] + '/' + action['value'])

	def eval_rule(self, prop, condition, value):
		# print("eval_rule", self.module_name, prop, condition, value)
		if prop == "*" or prop in self.presence:
			v = self.has_owner if prop == "*" else self.presence[prop]['present']
			return eval(str(v) + " " + condition + " " + str(value))
		return False