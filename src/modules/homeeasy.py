# -*- coding: utf-8 -*-

import core.controller
from time import sleep, time
import smbus, os, re, json, subprocess
import modules, threading, logging
import wiringpi2 as wpi

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['HomeEasy']

def log(value):
	print(value)
	logging.debug(value)

class HomeEasy(modules.Threadable):
	"""Class HomeEasy RF 433.92MHz"""

	def __init__(self, conf):
		wpi.wiringPiSetup()
		self.speed = .2;
		self.cmds = {}
		self.reset_pin = 7
		self.module_name = conf['module']
		self.emitter_code = conf['emitter']
		self.receivers = []
		self.bus = smbus.SMBus(1)
		self.address = 0x12
		self._load_conf()
		super().__init__(conf, self.cmds)
		
	def _load_conf(self):
		path = 'homeeasy.json' if core.controller.Controller.DEBUG else '/usr/local/piserver/homeeasy.json'
		log('HomeEasy::load emitters and receivers: ' + path)
		config = json.loads(open(path).read())
		mod_name = self.get_module_name()
		if 'reset' in config:
			self.reset_pin = config['reset']
			print("reset pin set to " + str(self.reset_pin))
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
				receiver = {'name': name, 'protocole': rc['protocole'], 'unit':rc['unit'], 'state': False, 'type': mod_name, 'is_switch': True, 'cmds': ['on', 'off']}
				if receiver['protocole'] == 1:
					receiver['on'] = rc['on']
					receiver['off'] = rc['off']
				elif receiver['protocole'] == 2:
					receiver['cmds'].append('associate')
				if 'emitters' in rc:
					receiver['emitters'] = []
					for em in rc['emitters']:
						emitter = { 'name': name, 'protocole': em['protocole'] }
						if emitter['protocole'] == 1:
							emitter['on'] = em['on']
							emitter['off'] = em['off']
						elif emitter['protocole'] == 2:
							emitter['code'] = em['code']
							emitter['unit'] = em['unit']
							emitter['toggle'] = em['toggle'] if 'toggle' in em else False
						if 'delay' in em:
							emitter['delay'] = em['delay']
						receiver['emitters'].append(emitter)
				self.receivers.append(receiver)
		#self._setup()

	def _find_receiver(self, name):
		for r in self.receivers:
			if r['name'] == name: return r
		return None

	def _write_data(self, value, data):
		try :
			self.bus.write_block_data(self.address, value, list(bytearray(data.encode('utf-8'))))
		except IOError:
			print("IOError in writeData")
			subprocess.call(['i2cdetect', '-y', '1'])
			print("error wait a second...")
			sleep(1)
			self.bus.write_block_data(self.address, value, list(bytearray(data.encode('utf-8'))))
		except:
			print("error wait a second...")
			sleep(1)
		sleep(self.speed)

	def _read_data(self):
		return self.bus.read_byte_data(self.address, 0x00)

	def _set_emitter_code(self, code):
		self._write_data(1, str(code))

	def _add_receiver(self, protocole, unit, on=0, off=0):
		#print("add receiver:", "'" + str(protocole) + '-' + str(unit) + '-' + str(on) + '-' + str(off) + "'")
		self._write_data(2, str(protocole) + '-' + str(unit) + '-' + str(on) + '-' + str(off))

	def _add_emitter(self, protocole, receiver, code, unit, toggle=False, delay=0):
		#print("add emitter:", "'" + str(protocole) + '-' + str(receiver) + '-' + str(code) + '-' + str(unit) + '-' + str(1 if toggle else 0) + "'")
		self._write_data(3, str(protocole) + '-' + str(receiver) + '-' + str(code) + '-' + str(unit) + '-' + str(1 if toggle else 0) + '-' + str(delay))

	def _get_receiver_unit(self, name):
		for r in self.receivers:
			if r['name'] == name:
				return r['unit']
		return -1

	def _get_state(self, name):
		unit = self._get_receiver_unit(name)
		if unit != -1:
			self._write_data(4, str(unit))
			data = self._read_data()
			return True if data == 1 else False
		return False

	def _set_state(self, name, state):
		unit = self._get_receiver_unit(name)
		if unit != -1:
			self._write_data(5, str(unit) + '-' + state)

	def _setup(self):
		log("-> setup atmega using i2c")
		self.speed = .5;
		self._set_emitter_code(self.emitter_code)
		for r in self.receivers:
			if r['protocole'] == 1:
				self._add_receiver(r['protocole'], r['unit'], r['on'], r['off'])
			elif r['protocole'] == 2:
				self._add_receiver(r['protocole'], r['unit'])
			for e in r['emitters']:
				if e['protocole'] == 1:
					self._add_emitter(e['protocole'], r['unit'], e['on'], e['off'])
				elif e['protocole'] == 2:
					self._add_emitter(e['protocole'], r['unit'], e['code'], e['unit'], e['toggle'] if 'toggle' in e else False, e['delay'] if 'delay' in e else 0)
		self.speed = .2;
		log("-> success")

	def _reset(self):
		log("-> reset atmega on pin " + str(self.reset_pin))
		wpi.pinMode(self.reset_pin, 1)
		wpi.digitalWrite(self.reset_pin, 0)
		sleep(0.12)
		wpi.digitalWrite(self.reset_pin, 1)
		sleep(2)
		log("-> success")

	def get_switchers(self):
		rvs = []
		for receiver in self.receivers:
			rvs.append({'name': receiver['name'], 'state': self._get_state(receiver['name']), 'type': receiver['type'], 'is_switch': receiver['is_switch'], 'cmds': receiver['cmds']})
		return rvs

	def get_switcher(self, cmd):
		for receiver in self.receivers:
			if cmd.startWith(receiver['name']):
				return receiver['name']
		return None

	def execute(self, cmd):
		log("HomeEasy::execute: " + cmd)
		if cmd == 'reset':
			self._reset()
			result = dict(success=True, cmd=cmd)
		elif cmd == 'setup':
			self._setup()
			result = dict(success=True, cmd=cmd)
		else:
			name = cmd.split("/")[0]
			result = dict(success=False, name=name)
			receiver = self._find_receiver(name)
			if receiver == None:
				result['error'] = 'Unknown target'
			else:
				cmd = cmd.split("/")[1]
				if cmd == 'associate':
					self._set_state(receiver['name'], 'on')
					result['state'] = receiver['state'] = True
					result['success'] = True
				else:
					if cmd == 'toggle': 
						cmd = 'off' if receiver['state'] else 'on'
					self._set_state(receiver['name'], cmd)
					result['state'] = receiver['state'] = True if cmd == 'on' else False
					result['success'] = True
		return result
