# -*- coding: utf-8 -*-

import core.controller
from modules import Switch, EventManager
from time import sleep, time
import json, os, logging, sqlite3

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.getLogger("sqlite3").setLevel(logging.WARNING)

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['HomeEasy']

def log(value):
	print(value)
	logging.debug(value)

class HomeEasy(Switch):
	"""Class HomeEasy RF 433.92MHz via ATMega368"""

	def __init__(self, conf):
		self._init_db()
		self.cmds = {}
		self.module_name = conf['module']
		self.emitter = conf['emitter']
		self._init_homeeasy()
		self._load_conf()
		super().__init__(conf, self.cmds)
		EventManager.addEvent(ready = [self._ready])
		EventManager.addEvent(receive = [self._parseMessage])
		self.set_sender(self.emitter)

	def _init_db(self):
		try:
			conn = sqlite3.connect(core.controller.Controller.DB_NAME)
			cur = conn.cursor()
			if core.controller.Controller.DEBUG:
				cur.execute("DROP TABLE IF EXISTS receiver")
				cur.execute("DROP TABLE IF EXISTS emitter")
			cur.execute("CREATE TABLE IF NOT EXISTS receiver (`id` INTEGER PRIMARY KEY AUTOINCREMENT, `protocole` INTEGER, `unit` INTEGER UNIQUE, `name` TEXT, `group` TEXT, `state` INTEGER, `on` INTEGER, `off` INTEGER)")
			cur.execute("CREATE TABLE IF NOT EXISTS emitter (`id` INTEGER PRIMARY KEY AUTOINCREMENT, `receiver_id` INTEGER, `protocole` INTEGER, `code` INTEGER, `unit` INTEGER, `toggle` INTEGER, `repeat` INTEGER)")
			conn.commit()
		except sqlite3.Error as e:
			print ("An error occurred:" + str(e.args[0]))

	def _init_homeeasy(self):
		self.conf_file = core.controller.Controller.CONF_PATH + 'homeeasy.json'
		core.handlers.setObserver(self._load_conf, self.conf_file, core.controller.Controller.CONF_PATH)
		
	def _load_conf(self):
		try:
			config = json.loads(open(self.conf_file).read())
			conn = sqlite3.connect(core.controller.Controller.DB_NAME)
			cur = conn.cursor()
			cur.execute("DELETE FROM receiver")
			cur.execute("DELETE FROM emitter")
			log('-> loadUnits, ' + str(len(config)) + ' entry in ' + self.conf_file)
			for rc in config:
				key = "((\w+\s)?("+rc['name']
				if 'where' in rc: key += "|"+rc['where']
				if 'alias' in rc: key += "|"+rc['alias']
				if 'group' in rc: key += "|"+rc['group']
				else: rc['group'] = ''
				key += ")\s?)"
				self.cmds[rc['name']+'/toggle'] = rc['name']
				self.cmds[rc['name']+'/on'] = "allumer?\s"+key+"+"
				self.cmds[rc['name']+'/off'] = "(etein(dre|s))\s"+key+"+"
				self.cmds[rc['name']+'/associate'] = None
				q = str(rc['protocole']) + ', ' + str(rc['unit']) + ', "' + rc['name'] + '", "' + rc['group'] + '", 0'
				q += ', ' + (str(rc['on']) if 'on' in rc else '0')
				q += ', ' + (str(rc['off']) if 'off' in rc else '0')
				cur.execute('INSERT OR IGNORE INTO receiver (`protocole`, `unit`, `name`, `group`, `state`, `on`, `off`) VALUES (' + q + ')')
				last_id = cur.lastrowid
				if 'emitters' in rc:
					for em in rc['emitters']:
						q = str(last_id) + ', ' + str(em['protocole'])
						if 'code' in em and 'unit' in em:
							q +=  ', ' + str(em['code'])
							q +=  ', ' + str(em['unit'])
						if 'on' in em and 'off' in em:
							q +=  ', ' + str(em['on'])
							q +=  ', ' + str(em['off'])
						q +=  ', ' + str(int(em['toggle']) if 'toggle' in em else 0)
						q +=  ', ' + str(int(em['repeat']) if 'repeat' in em else 0)
						cur.execute('INSERT OR IGNORE INTO emitter (`receiver_id`, `protocole`, `code`, `unit`, `toggle`, `repeat`) VALUES (' + q + ')')
			conn.commit()
			cur.close()
			conn.close()
		except sqlite3.Error as e:
			print ("An error occurred:" + str(e.args[0]))

	def _ready(self):
		self.set_sender(self.emitter)

	def _parseMessage(self, result):
		#print("HomeEasy::_parseMessage")
		result = list(map(int, result))
		protocole = result[0]
		code = result[1]
		unit = None
		if len(result) > 2: unit = result[2]
		receiver = self._find_receiver(protocole, code, unit)
		#print("receiver: " + str(receiver))
		if receiver != None:
			repeat = 3
			if 'repeat' in receiver and receiver['repeat'] > 3:
				repeat = receiver['repeat']
			if receiver['toggle']: receiver['new_state'] = not receiver['state']
			elif receiver['e_protocole'] == 1: receiver['new_state'] = int(code == receiver['e_on'])
			else: receiver['new_state'] = result[3]
			#print("-> receiver: " + str(receiver))
			if receiver['protocole'] == 1: self.send_v1(receiver['on'] if receiver['new_state'] == 1 else receiver['off'])
			elif receiver['protocole'] == 2: self.send_v2(receiver['unit'], receiver['new_state'], repeat)
			self.set_switcher(receiver['unit'], receiver['new_state'])

	def _find_receivers(self, field, name):
		receivers = []
		try:
			conn = sqlite3.connect(core.controller.Controller.DB_NAME)
			cur = conn.cursor()
			cur.execute('SELECT * FROM receiver WHERE `' + field + '`="' + str(name) + '"')
			for rc in cur:
				receivers.append(self.to_receiver(rc))
			cur.close()
			conn.close()
		except sqlite3.Error as e:
			print ("An error occurred:" + str(e.args[0]))
		return receivers

	def _find_receiver(self, protocole, code, unit):
		rc = None
		try:
			conn = sqlite3.connect(core.controller.Controller.DB_NAME)
			cur = conn.cursor()
			qry = 'SELECT r.*, e.protocole, e.code, e.toggle, e.repeat'
			qry += ' FROM receiver AS r'
			qry += ' INNER JOIN emitter AS e ON e.`receiver_id` = r.`id`'
			qry += ' WHERE e.`protocole`=' + str(protocole) + ' '
			if protocole == 1:
				qry += 'AND (e.`code`=' + str(code) + ' OR e.`unit`=' + str(code) + ')'
			elif protocole == 2:
				qry += 'AND e.`code`=' + str(code) + ' AND e.`unit`=' + str(unit)
			cur.execute(qry)
			rc = cur.fetchone()
			cur.close()
			conn.close()
		except sqlite3.Error as e:
			print ("An error occurred:" + str(e.args[0]))
		return self.to_receiver(rc)

	def get_module_def(self):
		#log("HomeEasy::get_module_def")
		receivers = []
		try:
			conn = sqlite3.connect(core.controller.Controller.DB_NAME)
			cur = conn.cursor()
			cur.execute("SELECT * FROM receiver")
			for rc in cur:
				receivers.append(self.to_receiver(rc, self.get_module_name()))
			cur.close()
			conn.close()
		except sqlite3.Error as e:
			print ("An error occurred:" + str(e.args[0]))
		return receivers

	def to_receiver(self, rc, nn=None):
		if rc == None: return None
		#print("to_receiver", rc)
		r = {}
		r['id'] = rc[0]
		r['protocole'] = rc[1]
		r['unit'] = rc[2]
		r['name'] = rc[3]
		r['group'] = rc[4]
		r['state'] = rc[5] == 1
		if rc[6] > 0 and rc[7] > 0:
			r['on'] = rc[6]
			r['off'] = rc[7]
		if len(rc) > 8:
			r['e_protocole'] = rc[8]
			r['e_on'] = rc[9]
			r['toggle'] = rc[10] == 1
			r['repeat'] = rc[11]
		if nn != None:
			r['type'] = nn
			r['is_switch'] = True
			r['cmds'] = ['on', 'off', 'toggle', 'associate']
		return r

	def set_switcher(self, unit, state):
		log("HomeEasy::set_switcher unit: " + str(unit) + ", state: " + str(state))
		try:
			conn = sqlite3.connect(core.controller.Controller.DB_NAME)
			cur = conn.cursor()
			cur.execute("UPDATE receiver SET `state` = " + str(int(state)) + " WHERE `unit` = " + str(unit))
			conn.commit()
			cur.close()
			conn.close()
		except sqlite3.Error as e:
			print ("An error occurred:" + str(e.args[0]))
		return state

	def execute(self, cmd):
		log("HomeEasy::execute: " + cmd)
		name = cmd.split("/")[0]
		result = dict(success=False, name=name)
		receivers = self._find_receivers('name', name)
		if len(receivers) == 0:
			receivers = self._find_receivers('group', name)
		if len(receivers) == 0:
			result['error'] = 'Unknown targets'
		else:
			cmd = cmd.split("/")[1]
			if cmd in ['associate', 'state', 'toggle', 'on', 'off']:
				for receiver in receivers:
					if cmd == 'associate':
						if 'on' in receiver or 'off' in receiver:
							result['error'] = 'HomeEasy H200 don\'t requiere association'
						else:
							self.send_v2(receiver['unit'], True)
							result['state'] = self.set_switcher(receiver['unit'], True)
							result['success'] = True
					elif cmd == 'state':
						result['state'] = receiver['state']
						result['success'] = True
					else:
						if cmd == 'toggle': new_state = not receiver['state']
						elif cmd == 'on': new_state = True
						else: new_state = False
						if 'on' in receiver or 'off' in receiver:
							#print("send v1 pinOut: " + str(self.pinOut) + ", code: " + str(receiver["on" if new_state == 1 else "off"]))
							self.send_v1(receiver["on" if new_state == 1 else "off"])
						elif 'unit' in receiver:
							#print("send v2 pinOut: " + str(self.pinOut) + ", emitter: " + str(self.emitter) + ", receiver: " + str(receiver['unit']) + ", new state: " + str(int(new_state)))
							repeat = 2
							#if 'repeat' in receiver and receiver['repeat'] > 2:
							#	repeat = receiver['repeat']
							self.send_v2(receiver['unit'], new_state, repeat)
						result['state'] = self.set_switcher(receiver['unit'], new_state)
				result['success'] = True
			else:
				result['error'] = 'Unknown command'
				result['success'] = True
		return result

	def set_sender(self, code):
		#log("HomeEasy::set_sender: " + str(code))
		#self.serial_write("1-" + str(code))
		EventManager.send("1-" + str(code))

	def send_v1(self, code):
		#log("HomeEasy::send_v1: " + str(code))
		#self.serial_write("2-1-" + str(code))
		EventManager.send("2-1-" + str(code))

	def send_v2(self, unit, state, repeat):
		#log("HomeEasy::send_v2: " + str(unit) + " = " + str(state))
		#self.serial_write("2-2-" + str(unit) + "-" + str(int(state)) + "-" + str(repeat))
		EventManager.send("2-2-" + str(unit) + "-" + str(int(state)) + "-" + str(repeat))