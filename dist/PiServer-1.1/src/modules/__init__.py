import re

class Module(dict):
	"""Class 'Module': classe de base pour les modules du serveur"""

	# Expression régulière de fin de commande pour multiplié l'action
	# > par exemple "monte le son de 10" essanciellement pour la freebox donc ...
	REPEAT = "(\s(\w+\s)?(?P<repeat>(\d+|un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix))( fois)?)?"
	
	def __init__(self, conf, cmds={}):
		self.controller = None									# le controller
		self.module_name = conf['module'];
		if not hasattr(self, 'state'):
			self.state = None									# état par défaut
		self.name = conf['name']								# nom de référence du module (ex: "salon" pour allume le "salon")
		if 'group' in conf: self.group = conf['group']	# groupe de référence du module (ex: "lumiere" pour allume les "lumières")
		else: self.group = None
		self.cmds = cmds 										# tableau associatif des commandes (commande / regex)
		self.autoswitch = conf['autoswitch'] if 'autoswitch' in conf else ''
		self.setup()

	def get_module_name(self):
		return self.module_name

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
		print('-->', self.name, 'search', "'"+qry+"'")
		results = []
		for (cmd, rex) in self.cmds.items():
			if rex == None: continue
			rs = re.match(rex, qry)
			if rs:
				path = self.name + '/' + cmd
				try:
					v = self.getRepeat(rs.group('repeat'))
					if v > 0: path += '/' + str(v)
				except: pass
				results.append(path)
		if len(results) > 0: print('--->', len(results), 'commands found')
		return results

	def execute(self, cmd, automatic=True):
		return dict(success=False, automatic=automatic)	

	def getRepeat(self, value):
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

class Switch(Module):
	def __init__(self, conf, cmds={}, state=False):
		self.state = state
		super().__init__(conf, cmds)