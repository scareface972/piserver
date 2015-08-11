# -*- coding: utf-8 -*-

import core.controller
from modules import Module, EventManager
from time import sleep, time
import json, os, logging, sqlite3

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.getLogger("sqlite3").setLevel(logging.WARNING)

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Chacon']

db_name = 'piserver.sq3'
conn = sqlite3.connect(db_name)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS receiver")
cur.execute("DROP TABLE IF EXISTS emitter")
cur.execute("CREATE TABLE IF NOT EXISTS receiver (id INTEGER PRIMARY KEY AUTOINCREMENT, protocole INTEGER, unit INTEGER UNIQUE, name TEXT, state INTEGER, `on` INTEGER, off INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS emitter (id INTEGER PRIMARY KEY AUTOINCREMENT, receiver_id INTEGER, protocole INTEGER, code INTEGER, unit INTEGER, toggle INTEGER, repeat INTEGER)")
conn.commit()

def log(value):
	print(value)
	logging.debug(value)

class Chacon(Module):
	"""Class HomeEasy RF 433.92MHz via ATMega368"""

	def __init__(self, conf):
		self.cmds = {}
		self.module_name = conf['module']
		self.emitter = conf['emitter']
		self.set_sender(self.emitter)
		self._load_conf()
		super().__init__(conf, self.cmds)
		EventManager.addEvent(receive = [self._parseMessage])

	def _parseMessage(self, result):
		#print("Chacon::_parseMessage")
		result = list(map(int, result))
		#print(result)
		protocole = result[0]
		code = result[1]
		unit = None
		if len(result) > 2: unit = result[2]
		print(protocole, code, unit)
		receiver = self._find_receiver(protocole, code, unit)
		#print("receiver: " + str(receiver))
		if receiver != None:
			repeat = 3
			if 'repeat' in receiver and receiver['repeat'] > 3:
				repeat = receiver['repeat']
			if receiver['toggle']: receiver['new_state'] = not receiver['state']
			elif receiver['e_protocole'] == 1: receiver['new_state'] = int(code == receiver['e_on'])
			else: receiver['new_state'] = result[3]
			#print(receiver)
			if receiver['protocole'] == 1: self.send_v1(receiver['on'] if receiver['new_state'] == 1 else receiver['off'])
			elif receiver['protocole'] == 2: self.send_v2(receiver['unit'], receiver['new_state'], repeat)
			self.set_switcher(receiver['unit'], receiver['new_state'])
		
	def _load_conf(self):
		global db_name
		path = 'chacon.json' if core.controller.Controller.DEBUG else '/usr/local/piserver/chacon.json'
		log('Chacon::load receivers: ' + path)
		config = json.loads(open(path).read())
		conn = sqlite3.connect(db_name)
		cur = conn.cursor()
		if 'receivers' in config:
			values = []
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
				q = str(rc['protocole']) + ', ' + str(rc['unit']) + ', "' + name + '", 0'
				q += ', ' + (str(rc['on']) if 'on' in rc else '0')
				q += ', ' + (str(rc['off']) if 'off' in rc else '0')
				cur.execute('INSERT OR IGNORE INTO receiver (protocole, unit, name, state, `on`, off) VALUES (' + q + ')')
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
						cur.execute('INSERT OR IGNORE INTO emitter (receiver_id, protocole, code, unit, toggle, repeat) VALUES (' + q + ')')
		conn.commit()
		#print("receivers:")
		#cur.execute("SELECT * FROM receiver")
		#print("emitters:")
		#for r in cur: print(r)
		#cur.execute("SELECT * FROM emitter")
		#for e in cur: print(e)
		cur.close()
		conn.close()
		log('-> receivers loaded')

	def _find_by_name(self, name):
		global db_name
		conn = sqlite3.connect(db_name)
		cur = conn.cursor()
		cur.execute('SELECT * FROM receiver WHERE name="'+name+'"')
		rc = cur.fetchone()
		cur.close()
		conn.close()
		return self.to_receiver(rc)

	def _find_by_unit(self, unit):
		global db_name
		conn = sqlite3.connect(db_name)
		cur = conn.cursor()
		cur.execute('SELECT * FROM receiver WHERE unit='+str(unit))
		rc = cur.fetchone()
		cur.close()
		conn.close()
		return self.to_receiver(rc)

	def _find_receiver(self, protocole, code, unit):
		global db_name
		conn = sqlite3.connect(db_name)
		cur = conn.cursor()
		qry = 'SELECT r.*, e.protocole, e.code, e.toggle, e.repeat'
		qry += ' FROM receiver AS r'
		qry += ' INNER JOIN emitter AS e ON e.receiver_id = r.id'
		qry += ' WHERE e.protocole=' + str(protocole) + ' '
		if protocole == 1:
			qry += 'AND (e.code=' + str(code) + ' OR e.unit=' + str(code) + ')'
		elif protocole == 2:
			qry += 'AND e.code=' + str(code) + ' AND e.unit=' + str(unit)
		#print(qry)
		cur.execute(qry)
		rc = cur.fetchone()
		cur.close()
		conn.close()
		return self.to_receiver(rc)

	def get_switchers(self):
		#log("Chacon::get_switchers")
		receivers = []
		global db_name
		conn = sqlite3.connect(db_name)
		cur = conn.cursor()
		cur.execute("SELECT * FROM receiver")
		for rc in cur:
			receivers.append(self.to_receiver(rc, self.get_module_name()))
		cur.close()
		conn.close()
		return receivers

	def to_receiver(self, rc, nn=None):
		if rc == None: return None
		#print("to_receiver", rc)
		r = {}
		r['id'] = rc[0]
		r['protocole'] = rc[1]
		r['unit'] = rc[2]
		r['name'] = rc[3]
		r['state'] = rc[4] == 1
		if rc[5] > 0 and rc[6] > 0:
			r['on'] = rc[5]
			r['off'] = rc[6]
		if len(rc) > 7:
			r['e_protocole'] = rc[7]
			r['e_on'] = rc[8]
			r['toggle'] = rc[9] == 1
			r['repeat'] = rc[10]
		if nn != None:
			r['type'] = nn
			r['is_switch'] = True
			r['cmds'] = ['on', 'off', 'toggle', 'associate']
		return r

	def set_switcher(self, unit, state):
		log("Chacon::set_switcher unit: " + str(unit) + ", state: " + str(state))
		global db_name
		conn = sqlite3.connect(db_name)
		cur = conn.cursor()
		cur.execute("UPDATE receiver SET state = " + str(int(state)) + " WHERE unit = " + str(unit))
		conn.commit()
		cur.close()
		conn.close()
		return state

	def execute(self, cmd):
		log("Chacon::execute: " + cmd)
		name = cmd.split("/")[0]
		result = dict(success=False, name=name)
		receiver = self._find_by_name(name)
		if receiver == None:
			result['error'] = 'Unknown target'
		else:
			cmd = cmd.split("/")[1]
			if cmd == 'associate':
				if 'on' in receiver or 'off' in receiver:
					result['error'] = 'HomeEasy H200 no requiere association'
				else:
					self.send_v2(receiver['unit'], True)
					result['state'] = self.set_switcher(receiver['unit'], True)
					result['success'] = True
			elif cmd == 'state':
				result['state'] = receiver['state']
				result['success'] = True
			elif cmd in ['toogle', 'on', 'off']:
				if cmd == 'toggle': new_state = not receiver['state']
				elif cmd == 'on': new_state = True
				else: new_state = False
				if 'on' in receiver or 'off' in receiver:
					#print("send v1 pinOut: " + str(self.pinOut) + ", code: " + str(receiver["on" if new_state == 1 else "off"]))
					self.send_v1(receiver["on" if new_state == 1 else "off"])
				elif 'unit' in receiver:
					#print("send v2 pinOut: " + str(self.pinOut) + ", emitter: " + str(self.emitter) + ", receiver: " + str(receiver['unit']) + ", new state: " + str(int(new_state)))
					repeat = 2
					if 'repeat' in receiver and receiver['repeat'] > 2:
						repeat = receiver['repeat']
					self.send_v2(receiver['unit'], new_state, repeat)
				result['state'] = self.set_switcher(receiver['unit'], new_state)
				result['success'] = True
			else:
				result['error'] = 'Unknown command'
				result['success'] = True
		return result

	def set_sender(self, code):
		#log("Chacon::set_sender: " + str(code))
		#self.serial_write("1-" + str(code))
		EventManager.send("1-" + str(code))

	def send_v1(self, code):
		#log("Chacon::send_v1: " + str(code))
		#self.serial_write("2-1-" + str(code))
		EventManager.send("2-1-" + str(code))

	def send_v2(self, unit, state, repeat):
		#log("Chacon::send_v2: " + str(unit) + " = " + str(state))
		#self.serial_write("2-2-" + str(unit) + "-" + str(int(state)) + "-" + str(repeat))
		EventManager.send("2-2-" + str(unit) + "-" + str(int(state)) + "-" + str(repeat))

	#def serial_write(self, cmd):
	#	ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
	#	ser.open()
	#	log("Chacon >> " + str(cmd))
	#	ser.write(bytes(str(cmd) + str("\n"), 'UTF-8'))
	#	ser.close()
	#
	#def worker(self):
	#	log("Chacon::startWorker")
	#	self.set_running(True)
	#	ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
	#	ser.open()
	#	while self.get_running():
	#		#if self.paused: continue
	#		try:
	#			line = ser.readline()
	#			line = line.decode('utf-8').strip()
	#			if line != "":
	#				log("Chacon << " + line)
	#				if '-' in line:
	#					parts = line.split('-')
	#					cmd = int(parts[0])
	#					#log("<< cmd = " + str(cmd) + " " + str(cmd == 0))
	#					if cmd == 0:
	#						errorCode = int(parts[1])
	#						error = parts[2]
	#						log('Error [' + str(errorCode) + ']: ' + error)
	#						if errorCode == 1:
	#							self.set_sender(self.emitter)
	#					elif cmd == 1:
	#						pass
	#					elif cmd == 2:
	#						protocole = int(parts[1])
	#						code = int(parts[2])
	#						unit = int(parts[3]) if protocole == 2 else None
	#						receiver = self._find_receiver(protocole, code, unit)
	#						#print("receiver: " + str(receiver))
	#						if receiver != None:
	#							repeat = 2
	#							if 'repeat' in receiver and receiver['repeat'] > 2:
	#								repeat = receiver['repeat']
	#							if receiver['protocole'] == 1: receiver['new_state'] = code == receiver['on']
	#							else: receiver['new_state'] = int(parts[4])
	#							print(receiver)
	#							if receiver['protocole'] == 1: self.send_v1(receiver['on'] if receiver['new_state'] == 1 else receiver['off'])
	#							elif receiver['protocole'] == 2: self.send_v2(receiver['unit'], receiver['new_state'], repeat)
	#		except:
	#			pass
	#	ser.close()
	#	#log("-> Chacon worker stopped")