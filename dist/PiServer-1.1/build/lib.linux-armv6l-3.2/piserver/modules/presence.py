import modules
import logging
from time import sleep

logging.basicConfig(filename='piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Presence']

class Presence(modules.Module):
	"""Class 'Presence' pour la présence au domicile (via phone)"""

	def __init__(self, conf):
		super().__init__(conf)
		self.presence = {}
		self.has_owner = False
		self.first_time = True

	def get(self):
		return self.has_owner or self.first_time

	def execute(self, cmd):
		# print('-> execute: ', cmd)
		logging.debug('PRESENCE:: execute: ' + cmd)
		result = dict(success=False)
		if cmd == 'list':
			result['list'] = self.presence
			result['success'] = True
		else:
			name, state = cmd.split('/')
			state = True if state == 'true' else False
			current = False if not name in self.presence else self.presence[name]
			logging.debug("PRESENCE:: -> name: " + name + " > " + str(state))
			logging.debug('PRESENCE:: -> current: ' + str(current))
			if current != state or self.first_time:
				self.presence[name] = state
				logging.debug('PRESENCE:: --> change: ' + name + ' > ' + str(state))
				# print('-> name: ', name, "state: ", state)
				self.checkChange()
				self.first_time = False
			result['success'] = True
		return result

	def checkChange(self):
		if not len(self.presence) > 0: return
		has_owner = False
		for name in self.presence:
			# print (name, self.presence[name])
			if self.presence[name] == True:
				has_owner = True
				break
		# print("has owner: " + str(has_owner))
		if has_owner != self.has_owner or self.first_time:
			self.has_owner = has_owner
			cmd = 'on' if self.has_owner else 'off'
			switchers = self.controller.get_switchers()
			for s in switchers:
				# print(s.name + '/' + cmd)
				self.controller.execute(s.name + '/' + cmd)