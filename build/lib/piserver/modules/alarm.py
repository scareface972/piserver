# -*- coding: utf-8 -*-

import core, modules, json
import time, threading, sys, os, logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename='/var/log/piserver/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.getLogger("watchdog").setLevel(logging.WARNING)

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Alarms']

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

class Alarms(modules.Threadable):
	"""Class 'Alarms', réveil matin controlant le modules (lumière, box)"""

	def __init__(self, conf):
		super().__init__(conf)
		self.alarms = []
		self.passed = {}
		self.alarms_path = 'conf/' if core.controller.Controller.DEBUG else '/usr/local/piserver/'
		self.alarms_file = self.alarms_path + 'alarms.json'
		self._set_observer()
		self.thread.start()

	def _set_observer(self):
		#print('Set observer: ' + self.alarms_path)
		observer = Observer()
		observer.schedule(ConfFileHandler(self._load_conf, self.alarms_file), path=self.alarms_path)
		observer.start()
		self._load_conf()

	def _load_conf(self):
		log('Alarm::load alarms: ' + self.alarms_file)
		self.alarms = json.loads(open(self.alarms_file).read())
		for alarm in self.alarms:
			log('--> alarm: ' + alarm['name'] + ' ' + alarm['time'] + ' ' + (alarm['date'] if 'date' in alarm else 'recursive: ' + str(alarm['recursive'])))

	def worker(self):
		print("-> Alarms::startWorker")
		self.set_running(True)
		while self.get_running():
			for alarm in self.alarms:
				if self._check(alarm):
					self.execute(alarm)
			time.sleep(1)
		#print("-> Alarms worker stopped")

	def _check(self, alarm):
		#log("Alarms:check: " + alarm['name'])
		if 'enable' in alarm and not alarm['enable']:
			return False
		is_time = True
		now = datetime.now()
		if 'date' in alarm and alarm['date'] != 'today':
			date = datetime.strptime(alarm['date'], "%Y-%m-%d")
			delta = date - now
			#log("---> now: " + alarm['date'] + ", delta: " + str(delta.days))
			if delta.days > 0: is_time = False
		elif 'recursive' in alarm:
			#log('---> now: ' + str(now.weekday()) + ', recursive: ' + str(alarm['recursive']) + ', in' + str(now.weekday() in alarm['recursive']))
			if now.weekday() not in alarm['recursive']: is_time = False
		#log('---> time: ' + alarm['time']+', now: ' + now.strftime("%H:%M") + ', ' + str(alarm['time'] == now.strftime("%H:%M")))
		is_time = is_time and alarm['time'] == now.strftime("%H:%M")
		if is_time:
			key = now.strftime("%Y-%m-%d %H:%M")
			if key in self.passed and self.passed[key] == alarm['name']: is_time = False
			else: self.passed[key] = alarm['name']
			#log('--> add to passed: ' + key + " = " + str(self.passed[key]))
		#log("Alarms:check: " + alarm['name'] + ", is_time: " + str(is_time))
		return is_time

	def execute(self, alarm):
		log("Alarm::execute: " + alarm['name'])
		for action in alarm['actions']:
			if action['module'] == None: continue
			if action['module'] == 'sleep': 
				time.sleep(int(action['cmd']))
			else:
				log('-> execute: ' + action['module'] + '/' + action['cmd'])
				self.controller.execute(action['module'] + '/' + action['cmd'])
				time.sleep(1)
			#module = self.controller.get_module_by_name(action['module'])
			#if module != None and 'cmd' in action:
			#	log('-> execute action: ' + action['module'] + ' ' + action['cmd'])
			#	module.execute(action['cmd'])
			#	time.sleep(1)
