# -*- coding: utf-8 -*-

import core.controller
import modules, sqlite3
from time import sleep
import os, json, logging

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename='/var/log/piserver/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Presence']

def log(value):
	print(value)
	logging.debug(value)

class Presence(modules.Module):
	"""Class 'Presence' pour la présence au domicile (via phone)"""

	def __init__(self, conf):
		self._init_db()
		super().__init__(conf)
		self.presence = {}
		self.has_owner = False
		self.first_time = True

	def _init_db(self):
		conn = sqlite3.connect(core.controller.Controller.DB_NAME)
		cur = conn.cursor()
		if core.controller.Controller.DEBUG:
			cur.execute("DROP TABLE IF EXISTS devices")
		cur.execute("CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, uid INTEGER NUT NULL, ip TEXT NOT NULL, present INTEGER NOT NULL)")
		if core.controller.Controller.DEBUG:
			cur.execute("INSERT INTO devices (name, uid, ip, present) VALUES ('Benjamin', '68627129', '192.168.0.9', 1)")
		conn.commit()

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
			#print('->', uid, self.presence[uid])
			if self.presence[uid]['present'] == True:
				has_owner = True
				break
		log('-> has owner: ' + str(has_owner))
		if has_owner != self.has_owner or self.first_time:
			self.has_owner = has_owner
			self.controller.check_rules()

	def eval_rule(self, prop, condition, value):
		# print("eval_rule", self.module_name, prop, condition, value)
		if prop == "*" or prop in self.presence:
			v = self.has_owner if prop == "*" else self.presence[prop]['present']
			rule = str(v) + " " + condition + " " + str(value)
			#print("Presence::rule", prop, condition, value, rule, eval(rule))
			return eval(rule)
		return False