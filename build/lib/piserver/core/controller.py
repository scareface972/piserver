# -*- coding: utf-8 -*-

import bottle, signal
from multiprocessing import Process
from modules import Threadable, Switch, speech, freebox, homeeasy, recognition, serial, rules
import sys, os, importlib, re, json, time
from threading import Thread
import datetime, logging
import picamera

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def log(value):
	print(value)
	logging.debug(value)

class Controller():
	"""Class 'Controller', singleton du controleur principal"""

	# Hôte par defaut
	HOST = "*"
	PORT = 80
	
	DEBUG = False
	CONF_PATH = '/usr/local/piserver/'
	DB_NAME = CONF_PATH + 'piserver.sq3'

	# chemin relatif du dossier des modules
	MODULES_PATH = "modules"
	# tableau de TOUS les modules dispo
	MODULES = []

	def __init__(self, debug=False):
		Controller.DEBUG = debug
		signal.signal(signal.SIGTERM, self.stop)
		log("####################################################")
		log("####################################################")
		log("########                                     #######")
		log("########            PiServer v1              #######")
		if Controller.DEBUG:
			log("########               DEBUG                 #######")
		log("########                                     #######")
		log("####################################################")
		log("####################################################")
		log("")
		self.enabled = []				# tableau des modules ACTIFS
		self.threads = []				# tableau des modules avec threads
		self.last_cmd = None			# dernière commande executé (pour l'instruction "encore")
		if Controller.DEBUG: Controller.CONF_PATH = 'conf/'
		self.conf_file = Controller.CONF_PATH + 'config.json'
		self._load_conf()
		self._init_server()

	def _load_conf(self):
		# Chargement de la configuration (fichier JSON)
		log('Controller::loadConfig: ' + self.conf_file)
		config = json.loads(open(self.conf_file).read())
		## Ajout manuel de ATMega328 SerialCom
		print ("class", "ATMega328")
		self.atmega = serial.ATMega328()
		self.threads.append(self.atmega)
		## Fin ajout manuel
		for name in config:
			if name == 'host':
				Controller.HOST = config[name]
			elif name == 'port':
				Controller.PORT = config[name]
			else:
				conf = config[name]
				# print(conf)
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
		## Ajout manuel du gestionnaire de règles
		print ("class", "Rules")
		self.rules = rules.Rules()
		self.rules.controller = self
		self.threads.append(self.rules)
		## Fin ajout manuel

	def _init_server(self):
		# Initialisation du serveur web (Bottle)
		# > les route définise la relation entre un chemin d'url et la fonction locale à executer
		path = os.path.dirname(os.path.abspath(__file__)) + '/../views'
		bottle.TEMPLATE_PATH.insert(0,path)
		self.app = bottle.Bottle()
		self.app.config['autojson'] = True
		self.app.route('/', callback=self.index)
		self.app.route('/static/:path#.+#', callback=self.static)
		self.app.route('/home', callback=self.home)
		self.app.route('/modules', callback=self.modules)
		self.app.route('/cam', callback=self.cam)
		self.app.route('/states', callback=self.states)
		self.app.route('/search/<qry:re:[a-z0-9 _\-]+>', method='GET', callback=self.search)
		self.app.route('/search', method='POST', callback=self.search)
		self.app.route('/exec/<cmd:path>', callback=self.execute)

	def _get_switchers(self):
		switchers = []
		for module in self.enabled:
			if isinstance(module, Switch):
				switchers.extend(module.get_module_def())
		return switchers

	def get_module(self, cmd):
		for module in self.enabled:
			if cmd.startswith(module.name):
				return module

	def get_module_by_name(self, name):
		for module in self.enabled:
			# print(module.name)
			if name == module.name:
				return module

	def check_rules(self):
		self.rules.check_rules()

	def run(self):
		try:
			self.app.run(host=Controller.HOST, port=Controller.PORT, debug=False, quiet=True)
			#self.thread = Process(target=self.app.run, kwargs=dict(host=Controller.HOST, port=Controller.PORT, debug=False, quiet=True))
			#self.thread.daemon = True
			#self.thread.start()
			#self.thread.join()
		except KeyboardInterrupt:
			pass
		finally:
			print('Closing all threads...')
			for module in self.threads:
				print("kill thread in", module.name, module.get_running())
				if module.get_running():
					module.set_running(False)
					module.thread.join()
					print("-> Thread", module.name, "killed")

	def stop(self):
		log(">>> Stop App Server <<<")
		self.app.close()

	def static(self, path):
		root = os.path.dirname(os.path.abspath(__file__)) + '/../static'
		return bottle.static_file(path, root=root)

	def index(self):
		return '<h1>Bienvenue</h1>'

	@bottle.view('home')
	def home(self):
		#print(self._get_switchers())
		return bottle.template('home', switchers=self._get_switchers())

	def cam(self):
		path = 'imgs'
		if not os.path.isdir(path): os.mkdir(path)
		name = 'image.jpg'
		camera = picamera.PiCamera()
		camera.resolution = (1024, 768)
		camera.capture(path + '/' + name, format='jpeg')
		camera.close()
		return bottle.static_file(name, 'imgs');

	# A REFAIRE COMME get_switchers
	def modules(self):
		mods = []
		for module in self.enabled:
			mods.extend(module.get_module_def())
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
		#print("##########################################")
		#print("New request with", len(qrys), "query's")
		for qry in qrys:
			cmds = []
			#print('-> Anlysis:', qry)
			# Mot clé exeptionnel pour refaire la dernière commande (pratique pour zappé la télé :))
			rs = re.match('^(encore|recommencer?)$', qry)
			if self.last_cmd != None and rs: return [self.last_cmd]
			for module in self.enabled:
				rs = module.analys(qry)
				for rw in rs: cmds.append(rw)
			if len(cmds) > 0: return cmds
