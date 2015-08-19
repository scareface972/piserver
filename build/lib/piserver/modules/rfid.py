# -*- coding: utf-8 -*-

import os, logging, json
import core.controller, core.handlers
from modules import Module, EventManager

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename='/var/log/piserver/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Reader']

def log(value):
	print(value)
	logging.debug(value)

class Reader(Module):
	"""Class 'Reader' pour capteur RFID"""

	def __init__(self, conf):
		super().__init__(conf)
		self._init_rfid()
		self._load_conf()
		EventManager.addEvent(rfid = [self._event])

	def _init_rfid(self):
		self.rfid = []
		self.passed = {}
		self.conf_file = core.controller.Controller.CONF_PATH + 'rfid.json'
		core.handlers.setObserver(self._load_conf, self.conf_file, core.controller.Controller.CONF_PATH)

	def _load_conf(self):
		self.rfid = json.loads(open(self.conf_file).read())
		log('-> loadRfid, ' + str(len(self.rfid)) + ' entry in ' + self.conf_file)
		#for uid in self.rfid:
		#	log('--> uid: ' + uid['uid'] + ' ' + uid['name'])

	def _check(self, action, uid):
		#log('RFIDReader::check: ' + uid + ", action: " + action)
		for card in self.rfid:
			if card['uid'] == uid:
				#log('--> Card uid: ' + card['uid'] + ' ' + card['name'])
				for action in card['actions_'+action]:
					if 'enabled' in action and action['enabled'] == False: continue
					#log('-> execute: ' + action['module'] + '/' + action['cmd'])
					self.controller.execute(action['module'] + '/' + action['cmd'])

	def _event(self, action, uid):
		#log("-> Event " + action + ": " + uid)
		self._check(action, uid)