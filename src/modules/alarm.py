# -*- coding: utf-8 -*-

import core, modules
import time, threading, sys
from datetime import datetime
import json

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Manager']

class Manager(modules.Module):
	"""Class 'Manager', réveil matin controlant le modules (lumière, box)"""

	def __init__(self, conf):
		super().__init__(conf)
		self.alarms = self._load_conf()
		print(self.alarms)
		self.thread = threading.Thread(target=self.worker)
		self.thread.daemon = True
		self.thread.start()

	def _load_conf(self):
		path = 'alarms.json' if core.controller.Controller.DEBUG else '/usr/local/piserver/alarms.json'
		return json.loads(open(path).read())

	def worker(self):
		while True:
			for alarm in self.alarms:
				if self.check(alarm):
					self.execute(alarm)
			time.sleep(1)

	def check(self, alarm):
		#print("check", alarm['name'])
		now = datetime.now()
		#print("-> now", now)
		if 'date' in alarm:
			#print("-> date", alarm['date'])
			date = datetime.strptime(alarm['date'], "%Y-%m-%d")
			#print("-> date", date)
			delta = date - now
			#print("-> delta days", delta.days)
			if delta.days > 0: return False
		if 'recursive' in alarm:
			#print('-> now', now.weekday(), 'recursive', alarm['recursive'], 'in', now.weekday() in alarm['recursive'])
			if now.weekday() not in alarm['recursive']:
				return False
		#print('-> time', alarm['time']+':00', 'now', now.strftime("%H:%M:%S"), alarm['time'] == now.strftime("%H:%M"))
		return alarm['time']+':00' == now.strftime("%H:%M:%S")

	def execute(self, alarm):
		print("execute alarm", alarm['name'])
		for action in alarm['actions']:
			if action['module'] == None: continue
			module = self.controller.get_module_by_name(action['module'])
			if module != None and 'cmd' in action:
				print("-> execute", action['module'], action['cmd'])
				module.execute(action['cmd'])

class Alarm(threading.Thread):
	def __init__(self, name, timestamp, delay = 60):
		super(Alarm, self).__init__()
		tm = int(timestamp - time.time())
		print ('-> Alarm ' + name + ' in ' + str(tm) + ' seconds (' + str(timestamp) + ')')
		self.name = name
		self.timestamp = timestamp
		self.delay = delay
		self.keep_running = True

	def run(self):
		try:
			self.cntdown = self.delay
			while self.keep_running:
				self.cntdown -= 1
				if self.cntdown == 0:
					if time.time() >= self.timestamp:
						print(">> Alarm '" + self.name + "' <<")
						return
					self.cntdown = self.delay
		except:
			print("Unexpected error:", sys.exc_info()[0])
			return

	def just_die(self):
		self.keep_running = False