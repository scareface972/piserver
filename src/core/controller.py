import bottle
from modules import Switch, speech
import sys, os, importlib, re, json, time
from threading import Thread
import datetime, logging

logging.basicConfig(filename='piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

class Controller():
	"""Class 'Controller', singleton du controleur principal"""

	# Hôte par defaut
	HOST = "*"
	PORT = 80
	
	DEBUG = False

	# chemin relatif du dossier des modules
	MODULES_PATH = "modules"
	# tableau de TOUS les modules dispo
	MODULES = []

	def __init__(self, conf_file):
		self.init_modules()
		self.enabled = []				# tableau des modules ACTIFS
		self.last_cmd = None			# dernière commande executé (pour l'instruction "encore")
		self.load_conf(conf_file)
		self.init_server()
		# self.init_thread()

	def init_modules(self):
		# Recherche des modules dispo
		for name in os.listdir(Controller.MODULES_PATH):
			if name.endswith(".py") and not name.startswith(".") and not name.startswith("__"):
				name = name.replace(".py", "")
				path = Controller.MODULES_PATH + "." + name
				module = importlib.import_module(path)
				if module != None: 
					for m in module.MODULES:
						Controller.MODULES.append(name + "." + m)

	def load_conf(self, conf_file):
		# Chargement de la configuration (fichier JSON)
		# try:
		config = json.loads(open(conf_file).read())
		if 'debug' in config:
			Controller.DEBUG = config['debug']
			del config['debug']
		for name in config:
			if name == 'host':
				Controller.HOST = config[name]
			elif name == 'port':
				Controller.PORT = config[name]
			else:
				conf = config[name]
				mod = conf['module']
				conf['name'] = name
				conf['debug'] = Controller.DEBUG
				# Reconstruction du chemin du module
				path = Controller.MODULES_PATH + "." + mod.split(".")[0]
				# Et de la classe a charger
				clss = mod.split(".")[1]
				# Importation dynamique
				module = importlib.import_module(path)
				# Instanciation
				clzz = getattr(module, clss)
				inst = clzz(conf)
				# Le module Speech a besoin du controller pour répondre (enfin pour couper le son de la freebox lors d'une réponse vocale)
				inst.controller = self
				self.enabled.append(inst)
		# except:
		# 	print("Erreur impossible de charger le ficheir de configuration '" + conf_file + "'")
		# 	sys.exit()

	def get_module(self, name):
		for mod in self.enabled:
			if mod.module_name == name: return mod
		return None

	def init_server(self):
		# Initialisation du serveur web (Bottle)
		# > les route définise la relation entre un chemin d'url et la fonction locale à executer
		self.app = bottle.Bottle()
		self.app.config['autojson'] = True
		self.app.route('/', callback=self.index)
		self.app.route('/static/:path#.+#', callback=self.static)
		self.app.route('/home', callback=self.home)
		self.app.route('/controls', callback=self.controls)
		self.app.route('/modules', callback=self.modules)
		self.app.route('/states', callback=self.states)
		self.app.route('/search/<qry:re:[a-z0-9 _\-]+>', method='GET', callback=self.search)
		self.app.route('/search', method='POST', callback=self.search)
		self.app.route('/exec/<cmd:path>', callback=self.execute)
		self.app.route('/restart', callback=self.restart)
		self.app.route('/reboot', callback=self.reboot)

	def init_thread(self):
		t = CtrlThread(self)
		t.start()

	def run(self):
		self.app.run(host=Controller.HOST, port=Controller.PORT, debug=False, quiet=False)

	def static(self, path):
		return bottle.static_file(path, root='static')

	def index(self):
		return '<h1>Bienvenue</h1>'

	@bottle.view('home')
	def home(self):
		return bottle.template('home', switchers=self.get_switchers())

	@bottle.view('controls')
	def controls(self):
		return bottle.template('controls', switchers=self.get_switchers(), style="black")

	def modules(self):
		mods = []
		for module in self.enabled:
			is_switch = True if isinstance(module, Switch) else False
			mods.append({'name': module.name, 'type': module.get_module_name(), 'group': module.group, 'state': module.state, 'cmds': module.list_cmds(), 'is_switch': is_switch})
		return dict(success=True, modules=mods)

	def states(self):
		bottle.response.content_type = 'text/event-stream'
		bottle.response.set_header('Cache-Control', 'no-cache')
		states = []
		for module in self.get_switchers():
			states.append({'name': module.name, 'state': module.state})
		yield 'data: ' + json.dumps(dict(success=True, states=states)) + '\n\n'

	def search(self, qry=None):
		# Extration de la ou des requête vocale (Google pouvant renvoyé 1 ou plusieurs réponse avec son service speech2text)
		# > Le donnée arrive normalement en post, mais aussi en get pour débug :)
		qrys = []
		if bottle.request.method == 'POST': qrys = json.loads(bottle.request.body.readline().decode("utf-8"))
		elif qry != None: qrys = [qry]
		if len(qrys) > 0: cmds = self.analys(qrys)
		if cmds == None: cmds = []
		success = True if len(cmds) > 0 else False
		return dict(success=success, cmds=cmds)

	def execute(self, cmd):
		self.last_cmd = cmd
		module = self.get_module(cmd)
		if module == None: return
		cmd = cmd.replace(module.name+"/", "")
		# print(module.name, cmd)
		result = module.execute(cmd)
		return result

	def restart(self):
		logging.debug('CONTROLER:: restart')
		result = dict(success=True)
		res = os.system('service piserver restart')
		logging.debug('CONTROLER:: res: ' + str(res))
		if res != 0: result = dict(success=False, result=res)
		return result

	def reboot(self):
		logging.debug('CONTROLER:: reboot')
		result = dict(success=True)
		res = os.system('reboot')
		logging.debug('CONTROLER:: res: ' + str(res))
		if res != 0: result = dict(success=False, result=res)
		return result

	def get_switchers(self):
		switchers = []
		for module in self.enabled:
			if isinstance(module, Switch): switchers.append(module)
		return switchers

	def analys(self, qrys):
		# Recherche de commande correspondant à une phrase
		# > Pour cela on parcours les modules et chaqun va vérifier s'il à une commande correspondante
		# > On renvoi alors la ou le lot de commandes a éxecuter
		print("##########################################")
		print("New request with", len(qrys), "query's")
		for qry in qrys:
			cmds = []
			print('-> Anlysis:', qry)
			# Mot clé exeptionnel pour refaire la dernière commande (pratique pour zappé la télé :))
			rs = re.match('^(encore|recommencer?)$', qry)
			if self.last_cmd != None and rs: return [self.last_cmd]
			for module in self.enabled:
				rs = module.analys(qry)
				for rw in rs: cmds.append(rw)
			if len(cmds) > 0: return cmds

	def get_module(self, cmd):
		for module in self.enabled:
			if cmd.startswith(module.name):
				return module

	def get_module_by_name(self, name):
		for module in self.enabled:
			if name == module.name:
				return module

# class CtrlThread(Thread):
# 	def __init__(self, ctrl):
# 		Thread.__init__(self)
# 		self.ctrl = ctrl
# 		self.lux = 0
# 		self.presence = True

# 	def run(self):
# 		while True:
# 			# print ('runner')
# 			now = datetime.datetime.now()
# 			#if now.hour > 7 and now.hour < 22:
# 			for module in self.ctrl.enabled:
# 				mod = module.__module__.replace('modules.', '') + '.' + module.__class__.__name__
# 				# print('module', mod)
# 				if 'sensor.BH1750FVI' == mod:
# 					self.lux = module.get()
# 					# print('-> lux:', self.lux)
# 				if 'presence.Presence' == mod:
# 					self.presence = module.get()
# 					if not self.presence: module.manual = False
# 					# print('-> presence:', self.presence)
# 			for module in self.ctrl.enabled:
# 				if isinstance(module, Switch):
# 					state = module.state
# 					# print(module.name, 'presence' in module.autoswitch)
# 					if 'presence' in module.autoswitch:
# 						state = self.presence
# 					# print(module.name, 'light' in module.autoswitch)
# 					if 'light' in module.autoswitch:
# 						state = state and self.lux <= 20
# 					if state != module.state and not module.manual:
# 						# print('-->', module.name, state)
# 						module.execute('on' if state else 'off', True)
# 					elif state == module.state and module.manual:
# 						module.manual = False
# 			time.sleep(60 * 10)