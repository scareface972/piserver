import bottle
from modules import *
import sys, os, importlib, re, json

class Controller():
	"""Class 'Controller', singleton du controleur principal"""

	# chemin relatif du dossier des modules
	MODULES_PATH = "modules"
	# tableau de TOUS les modules dispo
	MODULES = []

	def __init__(self, conf_file):
		self.init_modules()
		self.enabled = []				# tableau des modules ACTIFS
		self.last_cmd = None			# dernière commande executé (pour l'instruction "encore")
		self.init_server()
		self.load_conf(conf_file)

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

	def init_server(self):
		# Initialisation du serveur web (Bottle)
		# > les route définise la relation entre un chemin d'url et la fonction locale à executer
		self.app = bottle.Bottle()
		self.app.config['autojson'] = True
		self.app.route('/', callback=self.index)
		self.app.route('/static/:path#.+#', callback=self.static)
		self.app.route('/controls', callback=self.controls)
		self.app.route('/manager', callback=self.manager)
		self.app.route('/states', callback=self.states)
		self.app.route('/search/<qry:re:[a-z0-9 _\-]+>', method='GET', callback=self.search)
		self.app.route('/search', method='POST', callback=self.search)
		self.app.route('/exec/<cmd:path>', callback=self.execute)

	def load_conf(self, conf_file):
		# Chargement de la configuration (fichier JSON)
		# try:
			config = json.loads(open(conf_file).read())
			for name in config:
				conf = config[name]
				mod = conf['module']
				del conf['module']
				conf['name'] = name
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

	def index(self):
		return '<h1>Bienvenue</h1>'

	def static(self, path):
		return bottle.static_file(path, root='static')

	@bottle.view('controls')
	def controls(self):
		return bottle.template('controls', switchers=self.get_switchers())

	@bottle.view('manager')
	def manager(seld):
		return bottle.template('manager')

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

	def run(self):
		self.app.run(host='192.168.0.5', port=80, debug=True, quiet=False)

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