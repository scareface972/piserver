# -*- coding: utf-8 -*-

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
			'temp': 'combien fait-il|quelle est la température', 
			'humidity': 'quelle est l\'humidité', 
			'weather/now' : "quel temps fait-il",
			'weather/day0' : "quel temps fait-il autjourd'hui",
			'weather/day1' : "quel temps fera-t-il demain",
			'weather/day2' : "quel temps fera-t-il dans deux jours",
			'weather/day3' : "quel temps fera-t-il dans trois jours",
			'weather/day4' : "quel temps fera-t-il dans quatre jours",
			'tv/night/1' : "qu'y a-t-il ce soir sur tf1",
			'tv/night/2' : "qu'y a-t-il ce soir sur france 2",
		}
		super().__init__(conf, cmds)

	def execute(self, cmd):
		result = dict(success=False, name=self.name)
		text = None
		if 'say/' in cmd:
			cmd, text = cmd.split('/')
		elif cmd == 'time' or cmd == 'date':
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
		elif cmd == 'temp' or cmd == 'humidity':
			module = self.controller.get_module('temp/all')
			rs = module.execute('all')
			text = '';
			if cmd == 'temp' and rs['temp_c'] > 0:
				text += 'Il fait ' + str(int(rs['temp_c'])) + ' degrés.'
			if cmd == 'humidity' and rs['humidity'] > 0:
				text += 'Il y a ' + str(int(rs['humidity'])) + '% d\'humidité.'
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
				if day == -1:
					text = "le temps est " + res["weather"][0]["description"]
					text += ", il fait " + str(int(res["main"]["temp"])) + " degrés"
				else:
					res = res["list"][day]
					text = "le temps sera " + res["weather"][0]["description"]
					text += ", il fera " + str(int(res["temp"]["day"])) + " degrés"
		elif cmd.startswith("tv"):
			s = cmd.split('/')
			when = cmd[1]
			canal = cmd[2]
			print("Not implemented yet !")
		result['success'] = text != None
		if text != None: 
			result['weather'] = text
			t = SpeechThread(self.controller, text)
			t.start()
		return result

class SpeechThread(Thread):
	def __init__(self, controller, phrase):
		Thread.__init__(self)
		self.controller = controller
		self.phrase = phrase
		#print ('phrase', self.phrase)

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
		cmd = 'espeak -v fr "%s" --stdout | aplay' % phrase
		print(cmd)
		os.system(cmd)
		#filename = "tts.mp3"
		#googleTranslateURL = "http://translate.google.com/translate_tts?tl=" + Speech.LANG + "&q=" + urllib.parse.quote_plus(phrase) + "&"
		#self.downloadFile(googleTranslateURL, filename)
		#fbx = None
		#if self.controller != None: fbx = self.controller.get_module_by_name('freebox')
		#restore = False
		##if fbx != None and not fbx.muted: 
		##	restore = True
		##	fbx.execute('mute')
		#os.system("mpg123 -a btspeaker -f 10000 -q " + filename) # mplayer tts.mp3 -af extrastereo=0 &
		#if restore: fbx.execute('mute')
		##os.remove(filename)