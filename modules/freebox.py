import modules
import re, urllib
from threading import Thread
from time import sleep

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Freebox']

START_TV_DELAY = 8

class Freebox(modules.Switch):
	"""Class 'Freebox', télécommande de la Freebox"""

	def __init__(self, conf):
		self.muted = False
		key = "((\w+\s)?"+conf['name']
		if 'alias' in conf: key += "|"+conf['alias']
		key += ")"
		toggle = conf['name']
        # Initialisation des commandes disponibles
		cmds = {
			'toggle' : toggle,
			'power': "(allumer?|etein(dre|s))\s("+key+")+",
			'home': "accueil",
			'ok': "ok|valider" + modules.Module.REPEAT,
			'mute': "silence|mute|coupe le son|remets le son",
			'vol_inc': "(monter?|augmenter?|plus)\s(\w+\s)?(son|volume|fort)" + modules.Module.REPEAT,
			'vol_dec': "(baisser?|diminuer?|redui(s|re)|moins)\s(\w+\s)?(son|volume|fort)" + modules.Module.REPEAT,
			'prgm_inc': "(chaine suivante)" + modules.Module.REPEAT,
			'prgm_dec': "(chaine precedente)" + modules.Module.REPEAT,
			'red': "annuler|retour" + modules.Module.REPEAT,
			'green': "menu\s("+key+")+",
			'yellow': "(info(rmation)?\s("+key+"|programme)+)|page precedente",
			'blue': "page suivante",
			'left': "((vers la\s)?gauche)" + modules.Module.REPEAT,
			'right': "((vers la\s)?droite)" + modules.Module.REPEAT,
			'up': "((vers le\s)?haut|monter)" + modules.Module.REPEAT,
			'down': "((vers le\s)?bas|descendre)" + modules.Module.REPEAT,
			'rec': "enregistrer le programme",
			'rewind': "reculer" + modules.Module.REPEAT,
			'play': "reprendre la lecture",
			'pause': "mettre en pause",
			'forward': "avancer" + modules.Module.REPEAT
		}
		super().__init__(conf, cmds, True)
		self.url = "http://" + conf['box'] + ".freebox.fr/pub/remote_control?code=" + conf['code'];

	def analys(self, qry):
		cmds = super().analys(qry)
		if len(cmds) == 0:
			# TODO: Charger la liste des noms de chaine et canaux sur le site de free
			chaines = ['tf 1', 'france 2', 'france 3', 'canal plus', 'france 5', 'm6', 'arte', 'direct 8', 'w9', 'tmc', 'nt1', 'nrj 12', None, 'france 4']
			# Recherche d'une chaine
			rs = re.match("^(chaine )?(?P<canal>(\d+))", qry)
			if rs: cmds = [self.name + '/' + rs.group('canal')]
			# Ou recherche d'une commande de télécommande
			elif qry in chaines:
				index = chaines.index(qry)
				if index > -1: cmds = [self.name + '/' + str(index+1)]
		return cmds

	def execute(self, key, longPress=False):
		# Execution de la requete sur l'api télécommande de la box
		if '/' in key:
			k = key.split('/')
			key = k[0]
			repeat = int(k[1])
		else: repeat = 1
		longPress = str(1 if longPress else 0)
		if key == 'on' or key == 'off': key = 'power'
		result = dict(success=False, name=self.name, state=self.state)
		if key == 'power' or key == 'toggle' or self.state:
			if key.isdigit():
				for k in key:
					url = self.url + '&key=' + k + '&long=' + longPress
					req = urllib.request.Request(url)
					try: p = urllib.request.urlopen(req)
					except: pass
			else:
				url = self.url + '&key=' + key + '&long=' + longPress
				for r in range(repeat):
					req = urllib.request.Request(url)
					try: p = urllib.request.urlopen(req)
					except: pass
			result['success'] = True
			if key == 'power' or key == 'toggle':
				self.state = not self.state
				if self.state:
					t = StartTV(self)
					t.start()
			elif key == 'mute':
				self.muted = not self.muted
		return result

class StartTV(Thread):
	def __init__(self, callback):
		Thread.__init__(self)
		self.callback = callback

	def run(self):
		# print("StartTV")
		sleep(START_TV_DELAY)
		self.callback.execute('ok')