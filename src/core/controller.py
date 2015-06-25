# -*- coding: utf-8 -*-

import bottle
from modules import Threadable, Switch, speech, chacon, freebox
import sys, os, importlib, re, json, time
from threading import Thread
import datetime, logging
import picamera
from multiprocessing import Process

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)

logging.basicConfig(filename='/var/log/piserver/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

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
		self.threads = []				# tableau des modules avec threads
		self.last_cmd = None			# dernière commande executé (pour l'instruction "encore")
		self._load_conf(conf_file)
		self._init_server()

	def _load_conf(self, conf_file):
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
				if isinstance(inst, Threadable):
					self.threads.append(inst)
		# print(" -> host = " + str(Controller.HOST))
		# print(" -> port = " + str(Controller.PORT))

	def _init_server(self):
		# Initialisation du serveur web (Bottle)
		# > les route définise la relation entre un chemin d'url et la fonction locale à executer
		self.app = bottle.Bottle()
		self.app.config['autojson'] = True
		self.app.route('/', callback=self.index)
		self.app.route('/static/:path#.+#', callback=self.static)
		self.app.route('/home', callback=self.home)
		#self.app.route('/cam', callback=self.cam)
		self.app.route('/modules', callback=self.modules)
		self.app.route('/states', callback=self.states)
		self.app.route('/search/<qry:re:[a-z0-9 _\-]+>', method='GET', callback=self.search)
		self.app.route('/search', method='POST', callback=self.search)
		self.app.route('/exec/<cmd:path>', callback=self.execute)

	def _get_switchers(self):
		switchers = []
		for module in self.enabled:
			if isinstance(module, freebox.Freebox): 
				switchers.append({'name':module.name, 'state': module.get_state()})
			elif isinstance(module, chacon.Chacon): 
				switchers.extend(module.get_switchers())
		return switchers

	def get_module(self, cmd):
		for module in self.enabled:
			if cmd.startswith(module.name):
				return module

	def get_module_by_name(self, name):
		for module in self.enabled:
			if name == module.name:
				return module

	def run(self):
		print("Start ",Controller.HOST, Controller.PORT)
		try:
			t = Process(target=self.app.run, kwargs=dict(host=Controller.HOST, port=Controller.PORT, debug=False, quiet=False))
			t.daemon = True
			t.start()
			t.join()
			self.app.run(host=Controller.HOST, port=Controller.PORT, debug=False, quiet=False)
		except KeyboardInterrupt:
			print('')
			for module in self.threads:
				print("kill thread in", module.name, module.get_running())
				if module.get_running():
					module.set_running(False)
					module.thread.join()
					print("-> Thread", module.name, "killed")

	def static(self, path):
		return bottle.static_file(path, root='static')

	def index(self):
		return '<h1>Bienvenue</h1>'

	@bottle.view('home')
	def home(self):
		#print(self._get_switchers())
		return bottle.template('home', switchers=self._get_switchers())

	def cam(self):
		name = 'image.jpg'
		camera = picamera.PiCamera()
		camera.resolution = (1024, 768)
		camera.capture('imgs/' + name, format='jpeg')
		camera.close()
		return bottle.static_file(name, 'imgs');

	def modules(self):
		mods = []
		for module in self.enabled:
			if isinstance(module, freebox.Freebox): 
				mods.append({'name':module.name, 'type': module.get_module_name(), 'state': module.get_state(), 'is_switch': True, 'cmds': module.list_cmds()})
			elif isinstance(module, chacon.Chacon): 
				mods.extend(module.get_switchers())
			else:
				mods.append({'name':module.name, 'type': module.get_module_name(), 'cmds': module.list_cmds()})
		return json.dumps(dict(success=True, modules=mods))

	def states(self):
		bottle.response.content_type = 'text/event-stream'
		bottle.response.set_header('Cache-Control', 'no-cache')
		states = []
		for module in self._get_switchers():
			states.append({'name': module['name'], 'state': module['state']})
		yield 'data: ' + json.dumps(dict(success=True, states=states)) + '\n\n'

	def execute(self, cmd):
		self.last_cmd = cmd
		module = self.get_module(cmd)
		if module == None: return
		cmd = cmd.replace(module.name+"/", "")
		# print(module.name, cmd)
		result = module.execute(cmd)
		return result

	def search(self, qry=None):
		# Extration de la ou des requête vocale (Google pouvant renvoyé 1 ou plusieurs réponse avec son service speech2text)
		# > Le donnée arrive normalement en post, mais aussi en get pour débug :)
		qrys = []
		if qry != None: qrys = [qry]
		elif bottle.request.method == 'POST': qrys = json.loads(bottle.request.body.readline().decode("utf-8"))
		#print(qrys)
		if len(qrys) > 0: cmds = self.analys(qrys)
		if cmds == None: cmds = []
		success = True if len(cmds) > 0 else False
		return dict(success=success, cmds=cmds)

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
