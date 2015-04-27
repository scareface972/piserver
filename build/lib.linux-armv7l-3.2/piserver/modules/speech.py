import modules
import urllib, os, pycurl, time, json, re
from threading import Thread

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Speech']

class Speech(modules.Module):
	"""Class 'Speech' pour les réponses interactives"""

	LANG 		= "fr"													# A gérer dans la config/manager
	LOCATION 	= "Bordeaux,fr"											# Idem

	def __init__(self, conf):
		# Initialisation des commandes disponibles
		cmds = {
			'time': "quelle heure est-il",
			'date': "quel jour sommes-nous",
			'weather/now' : "quel temps fait-il",
			'weather/day0' : "quel temps fait-il autjourd'hui",
			'weather/day1' : "quel temps fera-t-il demain",
			'weather/day2' : "quel temps fera-t-il dans 2 jours",
			'weather/day3' : "quel temps fera-t-il dans 3 jours",
			'weather/day4' : "quel temps fera-t-il dans 4 jours",
		}
		super().__init__(conf, cmds)

	def execute(self, cmd):
		result = dict(success=False, name=self.name)
		if cmd == 'time' or cmd == 'date':
			# Commande date ou heure, pas bien méchant, on demande au système et un peu de mise en forme :)
			if cmd == 'time':
				text = time.strftime('%H:%M',time.localtime())
				h = int(text.split(':')[0])
				add_dodo = h >= 2 and h < 6
				if h == 0: h = "minuit"
				elif h == 12: h = "midi"
				else: h = str(h) + " heure"
				m = int(text.split(':')[1])
				text = "il est " + h
				if m > 0: text += " " + str(m)
				if add_dodo: text += ", tu devrais aller dormir !"		# Quand il est tôt faut faire dodo :)
			elif cmd == 'date':
				text = time.strftime('nous somme le %A %d %B',time.localtime())
			result['success'] = True
			t = SpeechThread(self.controller, text)
			t.start()
		elif cmd.startswith("weather"):
			# Interrogation du webservice open weather map
			url = "http://api.openweathermap.org/data/2.5/"
			day = -2
			if cmd.endswith("now"): day = -1
			else :
				rs = re.match('weather/day(\d)', cmd)
				if rs: day = int(rs.group(1))
			if day >= -1 and day <= 4:
				if day == -1: url += "weather"
				else: url += "forecast/daily"
				url += "?q=" + Speech.LOCATION + "&lang=" + Speech.LANG + "&units=metric"
				req = urllib.request.Request(url)
				p = urllib.request.urlopen(req)
				rs = p.read().decode('utf-8')
				res = json.loads(rs)
				weather = None
				if day == -1:
					weather = "le temps est " + res["weather"][0]["description"]
					weather += ", il fait " + str(int(res["main"]["temp"])) + " degrés"
				else:
					res = res["list"][day]
					weather = "le temps sera " + res["weather"][0]["description"]
					weather += ", il fera " + str(int(res["temp"]["day"])) + " degrés"
				result['success'] = weather != None
				if weather != None: 
					result['weather'] = weather
					t = SpeechThread(self.controller, weather)
					t.start()
		return result

# Thread de synthétisation vocale, encore merci a Google :)
# > thread séparé pour ne pas bloquer le serveur ...
class SpeechThread(Thread):
	def __init__(self, controller, phrase):
		Thread.__init__(self)
		self.controller = controller
		self.phrase = phrase

	def run(self):
		self.speakSpeechFromText(self.phrase)

	def downloadFile(self, url, filename):
		fp = open(filename, "wb")
		curl = pycurl.Curl()
		curl.setopt(pycurl.HTTPHEADER, [
			"Host: translate.google.com",
			"Referer: http://www.gstatic.com/translate/sound_player2.swf",
			"User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.163 Safari/535.19"
		])
		curl.setopt(pycurl.URL, url)
		curl.setopt(pycurl.WRITEDATA, fp)
		curl.perform()
		curl.close()
		fp.close()

	def speakSpeechFromText(self, phrase):
		filename = "tts.mp3"
		googleTranslateURL = "http://translate.google.com/translate_tts?tl=" + Speech.LANG + "&q=" + urllib.parse.quote_plus(phrase) + "&"
		self.downloadFile(googleTranslateURL, filename)
		fbx = None
		if self.controller != None: fbx = self.controller.get_module_by_name('freebox')
		restore = False
		if fbx != None and not fbx.muted: 
			restore = True
			fbx.execute('mute')
		os.system("mpg123 -q " + filename) # mplayer tts.mp3 -af extrastereo=0 &
		if restore: fbx.execute('mute')
		os.remove(filename)