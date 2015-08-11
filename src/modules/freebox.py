# -*- coding: utf-8 -*-

# controle vocale mode zapping
# say zapping > passe sur tf1, et quelques secondes par chaines
# et STOP pour arréter le zapping

import modules
import re, urllib, logging
from threading import Thread
from time import sleep
import hmac, os, json, requests
from hashlib import sha1

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename='/var/log/piserver/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.getLogger("requests").setLevel(logging.WARNING)

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Freebox']

START_TV_DELAY = 6
PISERVER_VERSION = 1

def log(value):
	print(value)
	logging.debug(value)

class Freebox(modules.Module):
	"""Class 'Freebox', télécommande de la Freebox"""

	def __init__(self, conf):
		self.muted = False
		self.state = False
		key = "((\w+\s)?("+conf['name']
		if 'where' in conf: key += "|"+conf['where']
		if 'alias' in conf: key += "|"+conf['alias']
		key += ")\s?)"
		toggle = conf['name']
		# Initialisation des commandes disponibles
		cmds = {
			'toggle' : toggle,
			'on': "allumer?\s"+key+"+",
			'off': "(etein(dre|s))\s"+key+"+",
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
		super().__init__(conf, cmds)
		self.url = "http://" + conf['box'] + ".freebox.fr/pub/remote_control?code=" + str(conf['code'])
		if conf['version'] >= 6:
			self.fbx = FreeboxOSCtrl(False)
			self.verify_fbx()

	def verify_fbx(self):
		self.fbx_ok = False
		th = Thread(target=self._check_fbx)
		th.daemon = True
		th.start()

	def _check_fbx(self):
		self.fbx_status = self.fbx.getRegistrationStatus()
		self.fbx_ok = 'granted' == self.fbx_status
		if not self.fbx_ok :
			log("Freebox::check: WARNING: Veuillez autoriser PiServer à accéder à l'API de votre box.\n         Cliquez sur OUI (flèche vers la droite) sur l'écran LCD de la box serveur, merci.")
			while (not self.fbx.isRegistered()):
				self.fbx_status = self.fbx.registerApp()
				if 'grandted' == self.fbx_status: 
					self.fbx_ok = True
				if 'pending' != self.fbx_status: 
					log("Freebox::check: WARNING: PiServer non authorisé, status:" + self.fbx_status)
					break;
		self.get_state()

	def get_state(self):
		self.fbx_status = self.fbx.getRegistrationStatus()
		self.fbx_ok = 'granted' == self.fbx_status
		if self.fbx_ok:
			self.state = self.fbx.getTvStatus()
			if self.state == None: self.state = False
		return self.state

	def analys(self, qry):
		cmds = super().analys(qry)
		if len(cmds) == 0:
			# Recherche d'une chaine
			rs = re.match("^((chaine|canal) )?(?P<canal>(\d+))", qry)
			if rs: cmds = [self.name + '/' + rs.group('canal')]
			# Ou recherche d'une commande de télécommande
			else:
				for name, canal in CHAINES.items():
					if name == qry:
						cmds = [self.name + '/' + str(canal)]
			#elif qry in CHAINES:
			#	index = CHAINES.index(qry)
			#	if index > -1: cmds = [self.name + '/' + str(index+1)]
		return cmds

	def execute(self, key, longPress=False):
		# Execution de la requete sur l'api télécommande de la box
		log("Freebox::execute: " + key + " (" + str(longPress) + ")")
		is_power_key = key.startswith('on') or key.startswith('off') or key.startswith('toggle')
		result = dict(success=False, name=self.name, state=self.state)
		#if self.fbx_ok and is_power_key:
		#	self.state = self.fbx.getTvStatus()
		#	if self.state == None: 
		#		result['error'] = 'Box inaccessible !'
		#		return result
		#	else:
		#		result['state'] = self.state
		#	log("-> Tv is " + ("ON" if self.state else "OFF"))
		repeat = 1
		canal = None
		if '/' in key:
			k = key.split('/')
			key = k[0]
			if k[1].isdigit():
				repeat = int(k[1])
			elif k[1] == 'canal' and k[2].isdigit():
				canal = k[2]
				log("--> switch to canal after on:" + str(canal))
		if (key.startswith('on') and self.state) or (key.startswith('off') and not self.state):
			result['error'] = 'Freebox is already ' + key
			return result
		if (key == 'vol_inc' or key == 'vol_dec') and repeat == 1:
			repeat = 10
		longPress = str(1 if longPress else 0)
		if key.startswith('on') or key.startswith('off'): 
			key = 'power'
		if key == 'power' or key == 'toggle' or self.state:
			if key.isdigit():
				for k in key:
					url = self.url + '&key=' + k + '&long=' + longPress
					#print(url)
					req = urllib.request.Request(url)
					try: p = urllib.request.urlopen(req)
					except: pass
			else:
				url = self.url + '&key=' + key + '&long=' + longPress
				#print(url)
				for r in range(repeat):
					req = urllib.request.Request(url)
					try: p = urllib.request.urlopen(req)
					except: pass
			result['success'] = True
			if key == 'power' or key == 'toggle':
				self.state = not self.state
				result['state'] = self.state
				if self.state:
					t = StartTV(self, canal)
					t.start()
			elif key == 'mute':
				self.muted = not self.muted
		return result

class StartTV(Thread):
	def __init__(self, callback, canal=None):
		Thread.__init__(self)
		self.callback = callback
		self.canal = canal

	def run(self):
		# print("StartTV")
		sleep(START_TV_DELAY)
		self.callback.execute('ok')
		if self.canal != None:
			sleep(START_TV_DELAY)
			self.callback.execute(self.canal)


class FbxOSException(Exception):

	""" Exception for FreeboxOS domain """

	def __init__(self, reason):
		self.reason = reason

	def __str__(self):
		return self.reason


class FreeboxOSCtrl:

	""" This class handles connection and dialog with FreeboxOS thanks to
	its exposed REST API """

	gAppDesc = {
		"app_id": "fr.freebox.piserver",
		"app_name": "PiServer by Benjamin",
		"app_version": PISERVER_VERSION,
		"device_name": "FbxOS PiServer Client"
	}

	def __init__(self, debug=False):
		""" Constructor """
		self.debug = debug
		self.fbxAddress = "http://mafreebox.freebox.fr"
		self.isLoggedIn = False
		self.registrationSaveFile = "/usr/local/piserver/freebox.json"
		self.registration = {'app_token': '', 'track_id': None}
		self.challenge = None
		self.sessionToken = None
		self.permissions = None
		self._loadRegistrationParams()

	def _log(self, what):
		if self.debug:
			print("Freebox::msg", what)
			logging.debug("Freebox::debug -> " + what)

	def _saveRegistrationParams(self):
		""" Save registration parameters (app_id/token) to a local file """
		self._log(">>> _saveRegistrationParams")
		with open(self.registrationSaveFile, 'w') as outfile:
			json.dump(self.registration, outfile)

	def _loadRegistrationParams(self):
		self._log(">>> _loadRegistrationParams")
		if os.path.exists(self.registrationSaveFile):
			with open(self.registrationSaveFile) as infile:
				data = infile.read()
				if bool(data.strip()): 
					self.registration = json.loads(data)

	def _login(self):
		""" Login to FreeboxOS using API credentials """
		self._log(">>> self._login")
		#if not self.isLoggedIn:
		if not self.isRegistered():
			raise FbxOSException("This app is not registered yet: you have to register it first!")

		# 1st stage: get challenge
		url = self.fbxAddress + "/api/v1/login/"
		# GET
		self._log("GET url: %s" % url)
		r = requests.get(url, timeout=3)
		self._log("GET response: %s" % r.text)
		# ensure status_code is 200, else raise exception
		if requests.codes.ok != r.status_code:
			raise FbxOSException("Get error: %s" % r.text)
		# rc is 200 but did we really succeed?
		resp = json.loads(r.text)
		#self._log("Obj resp: %s" % resp)
		if resp['success']:
			if not resp['result']['logged_in']:
				self.challenge = resp['result']['challenge']
		else:
			raise FbxOSException("Challenge failure: %s" % resp)

		# 2nd stage: open a session
		apptoken = self.registration['app_token']
		key = self.challenge
		self._log("challenge: " + key + ", apptoken: " + apptoken)
		# Hashing token with key
		h = hmac.new(apptoken.encode(), key.encode(), sha1)
		password = h.hexdigest()
		url = self.fbxAddress + "/api/v1/login/session/"
		headers = {'Content-type': 'application/json',
				   'charset': 'utf-8', 'Accept': 'text/plain'}
		payload = {'app_id': FreeboxOSCtrl.gAppDesc['app_id'], 'password': password}
		#self._log("Payload: %s" % payload)
		data = json.dumps(payload)
		self._log("POST url: %s  data: %s" % (url, data))
		# post it
		r = requests.post(url, data, headers=headers, timeout=3)
		# ensure status_code is 200, else raise exception
		self._log("POST response: %s" % r.text)
		if requests.codes.ok != r.status_code:
			raise FbxOSException("Post response error: %s" % r.text)
		# rc is 200 but did we really succeed?
		resp = json.loads(r.text)
		#self._log("Obj resp: %s" % resp)
		if resp['success']:
			self.sessionToken = resp['result']['session_token']
			self.permissions = resp['result']['permissions']
			self._log("Permissions: %s" % self.permissions)
			#if not self.permissions['settings']:
			#	print("Warning: permission 'settings' has not been allowed yet in FreeboxOS server. This script may fail!")
		else:
			raise FbxOSException("Session failure: %s" % resp)
		self.isLoggedIn = True

	def hasRegistrationParams(self):
		""" Indicate whether registration params look initialized """
		self._log(">>> hasRegistrationParams")
		return None != self.registration['track_id'] and '' != self.registration['app_token']

	def getRegistrationStatus(self):
		""" Get the current registration status thanks to the track_id """
		self._log(">>> getRegistrationStatus")
		if self.hasRegistrationParams():
			url = self.fbxAddress + \
				"/api/v1/login/authorize/%s" % self.registration['track_id']
			self._log(url)
			# GET
			self._log("GET url: %s" % url)
			r = requests.get(url, timeout=3)
			self._log("GET response: %s" % r.text)
			# ensure status_code is 200, else raise exception
			if requests.codes.ok != r.status_code:
				raise FbxOSException("Get error: %s" % r.text)
			resp = json.loads(r.text)
			return resp['result']['status']
		else:
			return None

	def isRegistered(self):
		""" Check that the app is currently registered (granted) """
		self._log(">>> isRegistered")
		if self.hasRegistrationParams() and 'granted' == self.getRegistrationStatus():
			return True
		else:
			return False

	def registerApp(self):
		""" Register this app to FreeboxOS to that user grants this apps via Freebox Server
		LCD screen. This command shall be executed only once. """
		self._log(">>> registerApp")
		register = True
		if self.hasRegistrationParams():
			status = self.getRegistrationStatus()
			if 'granted' == status:
				print("This app is already granted on Freebox Server (app_id = %s). You can now dialog with it." % self.registration['track_id'])
				register = False
			elif 'pending' == status:
				print("This app grant is still pending: user should grant it on Freebox Server lcd/touchpad (app_id = %s)." % self.registration['track_id'])
				register = False
			elif 'unknown' == status:
				print("This app_id (%s) is unknown by Freebox Server: you have to register again to Freebox Server to get a new app_id." % self.registration['track_id'])
			elif 'denied' == status:
				print("This app has been denied by user on Freebox Server (app_id = %s)." % self.registration['track_id'])
				register = False
			elif 'timeout' == status:
				print("Timeout occured for this app_id: you have to register again to Freebox Server to get a new app_id (current app_id = %s)." % self.registration['track_id'])
			else:
				print("Unexpected response: %s" % status)

		if register:
			url = self.fbxAddress + "/api/v1/login/authorize/"
			headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
			# post it
			self._log("POST url: %s  data: %s" % (url, FreeboxOSCtrl.gAppDesc))
			r = requests.post(url, data=json.dumps(FreeboxOSCtrl.gAppDesc), headers=headers, timeout=3)
			self._log("POST response: %s" % r.text)
			# ensure status_code is 200, else raise exception
			if requests.codes.ok != r.status_code:
				raise FbxOSException("Post error: %s" % r.text)
			# rc is 200 but did we really succeed?
			resp = json.loads(r.text)
			#self._log("Obj resp: %s" % resp)
			if True == resp['success']:
				self.registration['app_token'] = resp['result']['app_token']
				self.registration['track_id'] = resp['result']['track_id']
				self._saveRegistrationParams()
				sleep(1)
				status = self.getRegistrationStatus()
				#print("Now you have to accept this app on your Freebox server: take a look on its lcd screen.")
			#else:
			#	print("NOK")
		return status

#	def getTvStatus(self):
#		""" Get the current tv status: 1 means ON, 0 means OFF """
#		self._log(">>> getTvStatus")
#		self._login()
#		# GET airplay status
#		headers = {
#			'X-Fbx-App-Auth': self.sessionToken, 'Accept': 'text/plain'}
#		url = self.fbxAddress + "/api/v3/airmedia/receivers/"
#		# GET
#		self._log("GET url: %s" % url)
#		r = requests.get(url, headers=headers, timeout=1)
#		self._log("GET response: %s" % r.text)
#		# ensure status_code is 200, else raise exception
#		if requests.codes.ok != r.status_code:
#			raise FbxOSException("Get error: %s" % r.text)
#		# rc is 200 but did we really succeed?
#		resp = json.loads(r.text)
#		self._log("Obj resp: %s" % resp)
#		isOn = True
#		if True == resp['success']:
#			found = False
#			for receiver in resp['result']:
#				if receiver['name'] == "Freebox Player":
#					found = True
#					isOn = self._stopAirplayReceiver(receiver['name'])
#					self._log("TV is %s" % "ON" if isOn else "OFF")
#			if not found:
#				raise FbxOSException("No Freebox Player Airplay Receiver !")
#		else:
#			raise FbxOSException("Challenge failure: %s" % resp)
#		#self._logout()
#		return isOn

	def getTvStatus(self, name="Freebox%20Player"):
		""" Try to stop airplay receiver """
		self._log(">>> _stopAirplayReceiver")
		self._login()
		# GET airplay status
		headers = {
			'X-Fbx-App-Auth': self.sessionToken, 'Accept': 'text/plain'}
		url = self.fbxAddress + "/api/v3/airmedia/receivers/" + name + "/"
		# GET
		data = {'action': 'stop', 'media_type': 'video'}
		self._log("POST url: %s, data: %s" % (url, json.dumps(data)))
		r = requests.post(url, data=json.dumps(data), headers=headers, timeout=1)
		#self._log("POST response: %s" % r.text)
		# ensure status_code is 200, else raise exception
		if requests.codes.ok != r.status_code:
			#raise FbxOSException("Get error: %s" % r.text)
			return None
		# rc is 200 but did we really succeed?
		resp = json.loads(r.text)
		#self._log("Obj resp: %s" % resp)
		return resp['success']

CHAINES = {
	"tf 1": 1,
	"france 2": 2,
	"france 3": 3,
	"canal plus": 4,
	"france 5": 5,
	"m6": 6,
	"arte": 7,
	"d8": 8,
	"w9": 9,
	"tmc": 10,
	"nt1": 11,
	"nrj 12": 12,
	"lcp": 13,
	"france 4": 14,
	"bfm tv": 15,
	"i tele": 16,
	"d17": 17,
	"gulli": 18,
	"france o": 19,
	"hd1": 20,
	"equipe 21": 21,
	"6ter": 22,
	"numero23": 23,
	"rmc decouverte": 24,
	"cherie 25": 25,
	"rtl9": 28,
	"vivolta": 38,
	"ab 1": 39,
	"disney channel": 48,
	"paramount channel": 56,
	"national geographic channel": 57,
	"nat geo wild": 58,
	"voyage": 59,
	"nrj hits": 65,
	"game one music hd": 66,
	"clubbing tv": 73,
	"o five": 74,
	"just4talent": 76,
	"virgin radio tv": 77,
	"tv5": 79,
	"bfm business": 80,
	"euronews": 82,
	"bloomberg tv": 83,
	"al jazeera int.": 85,
	"sky news int.": 87,
	"i24 news": 88,
	"cnbc": 89,
	"lcp an 24h": 90,
	"public senat 24h": 91,
	"campagnes tv": 92,
	"africa 24": 93,
	"france 24": 95,
	"france 24 anglais": 96,
	"france 24 arabe": 97,
	"gongbase": 116,
	"game one": 118,
	"game one +1": 119,
	"lucky jack hd": 121,
	"men's up": 122,
	"nolife": 123,
	"enorme tv": 125,
	"nrj paris sat": 128,
	"fashion tv": 131,
	"world fashion": 132,
	"equidia live": 137,
	"equidia life": 138,
	"ab moteurs": 143,
	"ginx": 145,
	"ikono": 150,
	"montagne tv": 156,
	"luxe.tv hd": 157,
	"demain !": 163,
	"kto": 164,
	"3flow 3d": 166,
	"souvenirs from earth": 169,
	"penthouse hd": 176,
	"astro center tv": 195,
	"cash tv": 196,
	"m6 boutique": 197,
	"best of shopping": 198,
	"mce": 199,
	"beblack": 212,
	"grandlille tv": 330,
	"tlt toulouse": 331,
	"tv7 bordeaux": 332,
	"8 mont-blanc": 333,
	"telegrenoble": 334,
	"telif": 335,
	"la locale": 336,
	"normandie tv": 337,
	"telenantes nantes 7": 338,
	"la chaine marseille": 339,
	"clermont premiere": 340,
	"tv tours": 341,
	"nrj paris": 342,
	"bfm business paris": 343,
	"idf1": 344,
	"locales idf": 345,
	"alsace 20": 346,
	"telessonne": 347,
	"tvfil78": 348,
	"weo": 349,
	"tlm": 350,
	"valenciennes tv": 351,
	"canal10 guadeloupe": 352,
	"yvelines premiere": 353,
	"calaisis tv": 354,
	"tv sud camargue-cevennes": 355,
	"mirabelle tv": 356,
	"vosges television": 357,
	"tv sud montpellier": 358,
	"maritima tv": 359,
	"tv vendee": 360,
	"opal tv": 361,
	"canal 32": 362,
	"tna": 363,
	"tvr": 364,
	"tebesud": 365,
	"tebeo": 366,
	"d!ci tv": 367,
	"mfm tv": 368,
	"sud1ere": 470,
	"vox africa panafrique": 475,
	"mboa tv": 478,
	"medi1tv": 480,
	"canal algerie": 481,
	"algerie 3": 482,
	"algerie 5": 483,
	"tamazight tv4": 484,
	"beur tv": 486,
	"cctv documentaire": 499,
	"cctv news": 501,
	"cctv-f": 502,
	"arirang": 516,
	"tv romania": 521,
	"god tv": 529,
	"noursat": 530,
	"telesur": 531,
	"tvci": 540,
	"telenova": 541,
	"rai uno": 543,
	"rai due": 544,
	"rai tre": 545,
	"imed tv": 554,
	"ennahar": 555,
	"skyturk": 556,
	"ulusal kanal": 557,
	"arriyadia": 558,
	"2m maroc": 564,
	"tvm europe": 565,
	"hannibal tv": 566,
	"television tunisienne": 567,
	"al masriya": 568,
	"al jazeera": 569,
	"al jazeera children": 570,
	"powertürk tv": 582,
	"trt1": 583,
	"trt coçuk": 586,
	"kanal 24": 589,
	"trt int": 590,
	"kanal 7 int": 591,
	"samanyolu tv": 592,
	"tvt": 593,
	"hilal tv": 594,
	"tv5 turkey": 595,
	"halk tv": 600,
	"vtv4": 606,
	"arte de": 616,
	"dw-tv": 617,
	"rtpi": 626,
	"kuwait tv1": 640,
	"yemen tv": 643,
	"dubai tv": 644,
	"abou dhabi tv": 645,
	"baraem": 646,
	"jordan satellite channel": 648,
	"armenia 1": 650,
	"armenia tv": 651,
	"vesti": 653,
	"nessma": 657,
	"nhk world sd": 680,
	"ntd television": 684,
	"russia today": 694,
	"russia today esp.": 695,
	"record international": 697,
	"russian al yaum": 698,
	"record news": 699,
	"aktu freebox tv": 999,
	"paris premiere": 26,
	"teva": 27,
	"action": 33,
	"cine polar": 34,
	"cine fx": 35,
	"tcm cinema": 36,
	"e!": 37,
	"frissons extremes": 40,
	"canal plus cinema": 41,
	"canal plus sport": 42,
	"canal plus series": 43,
	"canal plus family": 44,
	"canal plus decale": 45,
	"bein sports 1": 46,
	"bein sports 2": 47,
	"disney channel +1": 49,
	"cine+ famiz": 53,
	"m6 music": 60,
	"m6 music club": 61,
	"m6 music black": 62,
	"trace tropical": 63,
	"trace urban": 64,
	"mezzo": 68,
	"mezzo live hd": 69,
	"mcm": 70,
	"mcm top": 71,
	"mcm pop": 72,
	"fox news": 78,
	"cnn": 84,
	"bbc world news": 86,
	"arret sur images.tv": 94,
	"academy video": 103,
	"vod mania": 105,
	"univers cine": 107,
	"coach club": 108,
	"cinema(s) a la demande": 109,
	"boing": 111,
	"boomerang": 112,
	"baby tv": 113,
	"teletoon": 114,
	"piwi": 115,
	"kztv": 117,
	"gong": 124,
	"mangas": 126,
	"fashion tv hd": 127,
	"stylia": 129,
	"eurochannel": 130,
	"sundance channel hd": 133,
	"trace sport stars": 136,
	"fightbox hd": 139,
	"sport365": 140,
	"pfc": 148,
	"golf channel": 149,
	"travel channel": 151,
	"nature hd": 152,
	"nautical channel": 153,
	"escales": 155,
	"histoire": 158,
	"toute  histoire": 159,
	"animaux": 160,
	"chasse et peche": 161,
	"encyclo": 162,
	"myzen hd": 165,
	"3a telesud": 167,
	"the museum channel": 168,
	"pink gay vod": 173,
	"hot video": 174,
	"penthouse hd1": 177,
	"penthouse hd2": 178,
	"brazzers tv": 179,
	"brazzers tv j-1": 180,
	"brazzers tv j-2": 181,
	"brazzers tv j-3": 182,
	"hustler tv": 183,
	"duosexy": 184,
	"xxl": 185,
	"daring!": 186,
	"dorcel tv": 187,
	"pink tv": 188,
	"man-x": 189,
	"my xxl hd": 190,
	"dorcel xxx": 191,
	"hotvideotv": 192,
	"amatix": 193,
	"iconcerts sd": 200,
	"iconcerts hd": 201,
	"c music": 203,
	"vh1": 204,
	"vh1 classic": 205,
	"brava hd": 206,
	"tele melody": 207,
	"rock tv": 208,
	"relax tv": 209,
	"jukebox": 210,
	"deluxe lounge hd": 211,
	"bein sports max 3": 401,
	"bein sports max 4": 402,
	"bein sports max 5": 403,
	"bein sports max 6": 404,
	"bein sports max 7": 405,
	"bein sports max 8": 406,
	"bein sports max 9": 407,
	"bein sports max 10": 408,
	"rtb burkina faso": 450,
	"ortb (benin)": 451,
	"canal 2 cameroun": 453,
	"crtv cameroun": 454,
	"stv2 cameroun": 455,
	"equinoxe": 456,
	"telecongo congo": 458,
	"rtnc": 459,
	"nollywood": 460,
	"rti 1": 461,
	"gabon television": 462,
	"ortc": 464,
	"ortm mali": 465,
	"2stv senegal": 466,
	"rts senegal": 467,
	"la chaine du futur": 468,
	"africable panafrique": 469,
	"africabox": 476,
	"om5 tv": 477,
	"berbere tv": 487,
	"berbere jeunesse": 488,
	"berbere music": 489,
	"cctv4": 500,
	"cctv divertissement": 503,
	"la chaine du cinema chinois": 504,
	"beijing tv": 505,
	"shangai dragon tv": 506,
	"la chaine de jiangsu": 507,
	"hunan satellite tv": 508,
	"xiamen star tv": 509,
	"zhejiang star tv": 510,
	"tvs2": 511,
	"phoenix infonews": 512,
	"phoenix chinese": 513,
	"zee tv": 514,
	"zee cinema": 515,
	"b4u music (inde)": 518,
	"protv": 522,
	"bbc entertainment": 526,
	"ritmoson latino": 532,
	"de pelicula": 533,
	"tl novelas": 534,
	"canal de las est.": 535,
	"telehit": 536,
	"tve int.": 537,
	"canal 24 horas": 538,
	"antenna 1 (grece)": 542,
	"mediaset italia": 546,
	"rtr planeta": 547,
	"tvn 24": 551,
	"tvp polonia": 560,
	"tvp kultura": 561,
	"tvp info": 562,
	"itvn": 563,
	"art cinema": 572,
	"art movies": 573,
	"al hekayat": 574,
	"iqraa": 575,
	"art aflam 2": 576,
	"cima": 577,
	"mbc": 578,
	"lbc europe": 579,
	"hekayat 2": 580,
	"tv": 581,
	"kanal d": 584,
	"star tv": 585,
	"atv avrupa": 588,
	"tgrt eu": 596,
	"show turk": 599,
	"geo tv": 601,
	"geo news": 602,
	"b4u movies": 603,
	"ctn": 607,
	"tvk": 608,
	"kbs world": 609,
	"613 tv": 613,
	"the israeli network": 614,
	"rtl": 618,
	"rtl2": 619,
	"super rtl": 620,
	"rtl nitro": 621,
	"rtl vox": 622,
	"prosieben": 623,
	"sat1": 624,
	"ntv": 625,
	"sic internacional": 627,
	"deepam tv": 639,
	"shant": 652,
	"murr tv": 654,
	"nbn": 655,
	"future tv": 656,
	"al jadeed": 658,
	"almajd holy quran": 661,
	"almajd al hadeeth": 662,
	"almajd space channel": 663,
	"azhari tv": 665,
	"m hits": 666,
	"m aflam": 667,
	"m drama": 668,
	"moga comedy": 669,
	"mbc masr": 670,
	"mbc 3": 672,
	"rtv pink plus": 673,
	"rtv pink extra": 674,
	"pink film": 675,
	"pink music": 676,
	"jstv1": 681,
	"jstv2": 682,
	"vijay": 685,
	"star life ok": 686,
	"star jalsha": 687,
	"star plus": 688,
	"star gold": 689,
	"channel one russia": 690,
	"dom kino": 691,
	"muzika pervoyo": 692,
	"vremya": 693,
	"tv globo": 696,
	"karusel": 700,
}
