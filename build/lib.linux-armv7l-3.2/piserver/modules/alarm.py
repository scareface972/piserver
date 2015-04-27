# -*- coding: utf-8 -*-

import modules
import time, threading, sys

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Manager']

class Manager(modules.Module):
	"""Class 'Manager', réveil matin controlant le modules (lumière, box)"""

	def __init__(self, conf):
		super().__init__(conf)
		self.alarms = []

	def append(self, alarm):
		if alarm.timestamp < time.time(): return
		alarm.start()
		self.alarms.append(alarm)

	def die(self, name=None):
		for alarm in alarms:
			if alarm.name == name or name == None:
				alarm.just_die()

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