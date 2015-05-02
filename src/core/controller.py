import bottle
from modules import Switch, speech, chacon, freebox
import sys, os, importlib, re, json, time
from threading import Thread
import datetime, logging
import picamera

logging.basicConfig(filename='piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

class Controller():
	"""Class 'Controller', singleton du controleur principal"""

	# Hôte par defaut
	HOST = "*"
	PORT = 80
	
	DEBUG = True

	# chemin relatif du dossier des modules
	MODULES_PATH = "modules"
	# tableau de TOUS les modules dispo
	MODULES = []

	def __init__(self, conf_file):
		#self.init_modules()
		self.enabled = []				# tableau des modules ACTIFS
		self.last_cmd = None			# dernière commande executé (pour l'instruction "encore")
		self._load_config(conf_file)

	def _load_config(self, conf_file):
		# Chargement de la configuration (fichier JSON)
		config = json.loads(open(conf_file).read())
		if 'debug' in config:
			Controller.DEBUG = config['debug']
			del config['debug']
		# print(" -> load config: debug = " + str(Controller.DEBUG))
		for name in config:
			if name == 'host':
				Controller.HOST = config[name]
			elif name == 'port':
				Controller.PORT = config[name]
			else:
				conf = config[name]
				#print(conf)
				if 'enabled' in conf and conf['enabled'] == False: continue
				mod = conf['module']
				conf['name'] = name
				conf['debug'] = Controller.DEBUG
				# Reconstruction du chemin du module
				path = Controller.MODULES_PATH + "." + mod.split(".")[0]
				# Et de la classe a charger
				clss = mod.split(".")[1]
				# Importation dynamique
				# print (" --> import module: " + path)
				module = importlib.import_module(path)
				# print (" --> module: " + str(module))
				# Instanciation
				print ("class", clss)
				clzz = getattr(module, clss)
				inst = clzz(conf)
				# Le module Speech a besoin du controller pour répondre (enfin pour couper le son de la freebox lors d'une réponse vocale)
				inst.controller = self
				self.enabled.append(inst)
		# print(" -> host = " + str(Controller.HOST))
		# print(" -> port = " + str(Controller.PORT))
		self.init_server()

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
		#self.app.route('/controls', callback=self.controls)
		#self.app.route('/cam', callback=self.cam)
		#self.app.route('/modules', callback=self.modules)
		self.app.route('/states', callback=self.states)
		self.app.route('/search/<qry:re:[a-z0-9 _\-]+>', method='GET', callback=self.search)
		self.app.route('/search', method='POST', callback=self.search)
		self.app.route('/exec/<cmd:path>', callback=self.execute)

	def run(self):
		#print("Start ",Controller.HOST, Controller.PORT)
		self.app.run(host=Controller.HOST, port=Controller.PORT, debug=False, quiet=False)

	def static(self, path):
		return bottle.static_file(path, root='static')

	def index(self):
		return '<h1>Bienvenue</h1>'

	@bottle.view('home')
	def home(self):
		print(self.get_switchers())
		return bottle.template('home', switchers=self.get_switchers())

	#@bottle.view('controls')
	#def controls(self):
	#	return bottle.template('controls', switchers=self.get_switchers(), style="black")

	def cam(self):
		name = 'image.jpg'
		camera = picamera.PiCamera()
		camera.resolution = (1024, 768)
		camera.capture('imgs/' + name, format='jpeg')
		camera.close()
		return bottle.static_file(name, 'imgs');	

	#def modules(self):
	#	mods = []
	#	for module in self.enabled:
	#		is_switch = True if isinstance(module, freebox.Freebox) or isinstance(module, chacon.Chacon) else False
	#		mods.append({'name': module.name, 'type': module.get_module_name(), 'group': module.group, 'state': module.state, 'cmds': module.list_cmds(), 'is_switch': is_switch})
	#	print(mods)
	#	return dict(success=True, modules=mods)

	def states(self):
		bottle.response.content_type = 'text/event-stream'
		bottle.response.set_header('Cache-Control', 'no-cache')
		states = []
		for module in self.get_switchers():
			states.append({'name': module['name'], 'state': module['state']})
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

	def get_switchers(self):
		switchers = []
		for module in self.enabled:
			if isinstance(module, freebox.Freebox): 
				switchers.append({'name':module.name, 'state': module.state})
			elif isinstance(module, chacon.Chacon): 
				switchers.extend(module.get_switchers())
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
