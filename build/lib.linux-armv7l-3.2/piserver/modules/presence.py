from core.controller import Controller
import modules
from time import sleep
import json
import logging

logging.basicConfig(filename='piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Presence']

class Presence(modules.Module):
	"""Class 'Presence' pour la présence au domicile (via phone)"""

	def __init__(self, conf):
		super().__init__(conf)
		self.presence = {}
		self.rules = []
		self.has_owner = False
		self.first_time = True
		self.loadRules()
		#print("debug: " + str(Controller.DEBUG))

	def get(self):
		return self.has_owner or self.first_time

	def execute(self, cmd):
		# print('-> execute: ', cmd)
		result = dict(success=False)
		if cmd == 'list':
			result['list'] = self.presence
			result['success'] = True
		else:
			logging.debug('Presence::execute: ' + cmd)
			name, state = cmd.split('/')
			state = True if state == 'true' else False
			current = False if not name in self.presence else self.presence[name]
			# logging.debug("Presence::name: " + name + " > " + str(state))
			# logging.debug('Presence::current: ' + str(current))
			if current != state or self.first_time:
				self.presence[name] = state
				logging.debug('Presence::change: ' + name + ' > ' + str(state))
				# print('-> name: ', name, "state: ", state)
				self.checkChange()
				self.first_time = False
			result['success'] = True
		return result

	def checkChange(self):
		if not len(self.presence) > 0: return
		has_owner = False
		for name in self.presence:
			# print(name, self.presence[name])
			if self.presence[name] == True:
				has_owner = True
				break
		#print("has owner: " + str(has_owner))
		if has_owner != self.has_owner or self.first_time:
			self.has_owner = has_owner
			self.checkRules()
			#switchers = self.controller.get_switchers()
			#if not self.has_owner:
			#	cmd = 'off' # 'on' if self.has_owner else 'off'
			#	for s in switchers:
			#		if not Controller.DEBUG or s.name == 'lampe':
			#			# if s.name == 'freebox' and cmd == 'on': continue
			#			print('-> ' + s.name + ': ' + cmd)
			#			self.controller.execute(s.name + '/' + cmd)

	def loadRules(self):
		path = 'rules.json' if Controller.DEBUG else '/usr/local/piserver/rules.json'
		logging.debug('Presence::load rules: ' + path)
		self.rules = json.loads(open(path).read())

	def checkRules(self):
		for rule in self.rules:
			execute = True
			for condition in rule['conditions']:
				mod = self.controller.get_module(condition['module'])
				if mod != None:
					value = mod.evalRule(condition['prop'], condition['condition'], condition['value'])
					execute = execute and value
					if not execute: break
			# print(rule['name'], execute)
			logging.debug('Presence::checkRules: ' + rule['name'] + ' > ' + str(execute))
			if execute:
				for action in rule['actions']:
					# print(action['module'], action['value'])
					# if Controller.DEBUG and action['module'] != 'lampe': continue
					logging.debug('Presence::exec: ' + action['module'] + '/' + action['value'])
					self.controller.execute(action['module'] + '/' + action['value'])

	def evalRule(self, prop, condition, value):
		# print("evalRule", self.module_name, prop, condition, value)
		if prop == "*" or prop in self.presence:
			v = self.has_owner if prop == "*" else self.presence[prop]
			return eval(str(v) + " " + condition + " " + str(value))
		return False