# -*- coding: utf-8 -*-

import core.controller
from modules import Threadable, EventManager
import json, time, os, logging, sqlite3
from watchdog.observers import Observer
import math

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.getLogger("sqlite3").setLevel(logging.WARNING)

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Sensors']

LOCAL_UID = 0

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def log(value):
	print(value)
	logging.debug(value)

class Sensors(Threadable):
	"""Class 'Sensors' (DHT11, BH1750, BMP085) via ATMega368"""

	def __init__(self, conf):
		self._init_db()
		self.cmds = {}
		self._init_conf()
		self._load_conf()
		super().__init__(conf, self.cmds)
		EventManager.addEvent(ready = [self._ready])
		EventManager.addEvent(sensors = [self._parse_message])
		self.request_values(LOCAL_UID)
		self.thread.start()

	def _init_db(self):
		conn = sqlite3.connect(core.controller.Controller.DB_NAME)
		cur = conn.cursor()
		if core.controller.Controller.DEBUG:
			cur.execute("DROP TABLE IF EXISTS sensors")
		cur.execute("CREATE TABLE IF NOT EXISTS sensors (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER NOT NULL, `where` TEXT NOT NULL, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, temp REAL, hum REAL, lux REAL)")
		conn.commit()

	def _init_conf(self):
		self.conf_file = core.controller.Controller.CONF_PATH + 'sensors.json'
		#print('-> Init observer: ' + self.conf_file)
		core.handlers.setObserver(self._load_conf, self.conf_file, core.controller.Controller.CONF_PATH)

	def _load_conf(self):
		self.sensors = json.loads(open(self.conf_file).read())
		log('-> loadSensors, ' + str(len(self.sensors)) + ' entry in ' + self.conf_file)
		for sensor in self.sensors:
			#log('-> sensor: %s %s %s' % (sensor['uid'], sensor['where'], sensor['caps']))
			parts = sensor['caps'].split(',')
			for part in parts:
				self.cmds[sensor['where'].lower()+'/' + part.lower()] = None

	def _get_sensor_uid(self, where):
		for sensor in self.sensors:
			if sensor['where'].lower() == where.lower():
				return sensor['uid']
		return -1

	def _get_sensor_where(self, uid):
		for sensor in self.sensors:
			if sensor['uid'] == uid:
				return sensor['where']
		return "Unknown"

	def _ready(self):
		self.request_values(LOCAL_UID)

	def _parse_message(self, result):
		result = list(map(float, result))
		#if math.isnan(result[1]): return
		uid = int(result[0])
		where = self._get_sensor_where(uid)
		temp = result[1] if len(result) > 1 and not math.isnan(result[1]) else 'NULL'
		hum  = result[2] if len(result) > 2 and not math.isnan(result[2]) else 'NULL'
		lux  = result[3] if len(result) > 3 and not math.isnan(result[3]) else 'NULL'
		try:
			conn = sqlite3.connect(core.controller.Controller.DB_NAME)
			cur = conn.cursor()
			qry = 'INSERT INTO sensors (uid, `where`, temp, hum, lux) VALUES (%d, "%s", %s, %s, %s)' % (uid, where, temp, hum, lux)
			#print(qry)
			cur.execute(qry)
			conn.commit()
			cur.close()
			conn.close()
		except sqlite3.Error as e:
			print ("An error occurred: %s" % e.args[0])

	def _read(self, uid=None):
		result = []
		try:
			conn = sqlite3.connect(core.controller.Controller.DB_NAME)
			conn.row_factory = dict_factory
			cur = conn.cursor()
			qry = 'SELECT uid, `where`, temp, hum, lux, time FROM sensors WHERE id IN (SELECT MAX(id) FROM sensors '
			qry += 'GROUP BY uid) ' if uid == None else 'WHERE uid=%d) ' % uid
			qry += 'ORDER BY uid'
			#print(qry)
			cur.execute(qry)
			result = cur.fetchall()
			conn.commit()
			cur.close()
			conn.close()
		except sqlite3.Error as e:
			print ("An error occurred: %s" % e.args[0])
		return result

	def worker(self):
		#print("-> Sensors::startWorker")
		self.set_running(True)
		delay = 300 if core.controller.Controller.DEBUG else 1800
		cnt = 0
		while self.get_running():
			time.sleep(1)
			cnt += 1
			if cnt == delay:
				self.request_values(LOCAL_UID)
				cnt = 0

	def execute(self, cmd):
		log("Sensors::execute: " + cmd)
		result = dict(success=True)
		if cmd == "all":
			result['sensors'] = self._read()
		else:
			uid = self._get_sensor_uid(cmd)
			rs  = self._read(uid)
			result['sensor'] = rs[0] if len(rs) > 0 else {}
		return result

	def eval_rule(self, prop, condition, value):
		tmp = prop.split("/")
		if len(tmp) >= 2:
			where = tmp[0]
			prop = tmp[1]
			uid = self._get_sensor_uid(lower(where))
		else:
			uid = LOCAL_UID
			where = self._get_sensor_where(LOCAL_UID)
		#print("Sensors::rule", uid, where, prop, condition, value)
		rs = self._read(uid)
		if len(rs) == 0: return False
		rs = rs[0]
		#print (rs)
		if prop in rs: #, 'pressure'
			rule = str(rs[prop]) + " " + condition + " " + str(value)
			#print(rule, eval(rule))
			return eval(rule)
		return False

	def request_values(self, uid):
		EventManager.send("3-" + str(uid))
