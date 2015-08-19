# -*- coding: utf-8 -*-
import re, threading

class EventManager:
	class Event:
		def __init__(self,functions):
			if type(functions) is not list:
				raise ValueError("functions parameter has to be a list")
			self.functions = functions

		def __iadd__(self,func):
			self.functions.append(func)
			return self

		def __isub__(self,func):
			self.functions.remove(func)
			return self

		def __call__(self,*args,**kvargs):
			for func in self.functions : func(*args,**kvargs)

	@classmethod
	def addEvent(cls,**kvargs):
		for key in kvargs.keys():
			if type(kvargs[key]) is not list:
				raise ValueError("value has to be a list")
			else:
				kvargs[key] = cls.Event(kvargs[key])
				setattr(cls, key, kvargs[key])

		#cls.__dict__.update(kvargs)

class Module(dict):
	"""Class 'Module': classe de base pour les modules du serveur"""

	# Expression régulière de fin de commande pour multiplié l'action
	# > par exemple "monte le son de 10" essanciellement pour la freebox donc ...
	REPEAT = "(\s(\w+\s)?(?P<repeat>(\d+|un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix))( fois)?)?"
	
	def __init__(self, conf, cmds={}):
		#print(conf)
		self.controller = None									# le controller
		self.module_name = conf['module']
		if not hasattr(self, 'state'): self.state = None		# état par défaut
		self.name = conf['name']								# nom de référence du module (ex: "salon" pour allume le "salon")
		if 'group' in conf: self.group = conf['group']			# groupe de référence du module (ex: "lumiere" pour allume les "lumières")
		else: self.group = None
		self.cmds = cmds 										# tableau associatif des commandes (commande / regex)
		self.autoswitch = conf['autoswitch'] if 'autoswitch' in conf else ''
		self.setup()

	def get_module_name(self):
		return self.module_name

	def get_module_def(self):
		return [{'name':self.name, 'type': self.module_name, 'cmds': self.list_cmds()}]

	def get_switchers(self):
		return []

	def list_cmds(self):
		cmds = []
		for (cmd, rex) in self.cmds.items():
			cmds.append(cmd)
		# return "['" + "', '".join(cmds) + "']"
		return cmds

	def setup(self):
		for (cmd, rex) in self.cmds.items():
			if rex == None: continue
			self.cmds[cmd] = '^' + rex + '$'

	def analys(self, qry):
		# Recherche de commande
		# > parcour des commandes et recherche de correspondance avec les expressions régulères
		#print('-->', self.name, 'search', "'"+qry+"'")
		results = []
		for (cmd, rex) in self.cmds.items():
			#print(cmd, rex)
			if rex == None: continue
			rs = re.match(rex, qry)
			if rs:
				path = self.name + '/' + cmd
				try:
					v = self._get_repeat(rs.group('repeat'))
					if v > 0: path += '/' + str(v)
				except: pass
				results.append(path)
		#if len(results) > 0: print('--->', len(results), 'commands found')
		return results

	def execute(self, cmd):
		return dict(success=False, cmd=cmd)	

	def _get_repeat(self, value):
		num = 0
		try:
			num = int(value)
		except:
			if value == 'un': num = 1
			elif value == 'deux': num = 2
			elif value == 'trois': num = 3
			elif value == 'quatre': num = 4
			elif value == 'conq': num = 5
			elif value == 'six': num = 6
			elif value == 'sept': num = 7
			elif value == 'huit': num = 8
			elif value == 'neuf': num = 9
			elif value == 'dix': num = 10
		return num

class Threadable(Module):
	"""Class 'Threadable': classe de base pour les module with async thread"""

	def __init__(self, conf, cmds={}):
		super().__init__(conf, cmds)
		self.set_running(False)
		self.thread = threading.Thread(target=self.worker)
		self.daemon = True

	#@property
	def get_running(self):
		return self.__running

	#@running.setter
	def set_running(self, value):
		self.__running = value

	def worker(self):
		raise Exception('Not implemented')

class Switch(Module):
	"""Class 'Switch': classe de base pour les switch physiques"""

	def __init__(self, conf, cmds={}, state=False):
		self.state = state
		if 'pin' in conf: self.pin = conf['pin']
		if cmds == {}:
			key = "((\w+\s)?(" + conf['name']
			if 'where' in conf: key += "|"+conf['where']
			if 'group' in conf: key += "|"+conf['group']+"s?"
			key += ")\s?)"
			# Initialisation des commandes disponibles
			cmds = {
				'toggle' : key,
				'on': "allumer?\s"+key+"+",
				'off': "(etein(dre|s))\s"+key+"+"
			}
		super().__init__(conf, cmds)

	def get_module_def(self):
		return [{'name':self.name, 'type': self.module_name, 'cmds': self.list_cmds(), 'is_switch': True, 'state': self.state}]