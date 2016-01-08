from modules import Threadable, Switch
import alsaaudio as aa
import audioop, time, wave, os, io, subprocess
from collections import deque
from urllib.request import Request, urlopen
from urllib.error import URLError
import json, unicodedata, logging
import ssl

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Recognition']

CHUNK = 1024
RATE = 16000
CHANNELS = 1
FORMAT = aa.PCM_FORMAT_S16_LE

PREV_AUDIO = 16
SILENCE_LIMIT = 1
THRESHOLD = 14000
FLAC_CONV = 'flac -f'

DEFAULT_NAME = 'jarvis'
HOTKEY_DURATION = 15

def log(value):
	print(value)
	logging.debug(value)

class Recognition(Switch, Threadable):
	"""Class Recognition for Voice recognition with Google"""

	def __init__(self, conf):
		cmds = {
			'on': "active la reconnaissance vocale",
			'off': "desactive la reconnaissance vocale",
		}
		super(Switch, self).__init__(conf, cmds)
		super(Threadable, self).__init__(conf, cmds)
		self.mic_index = conf['mic_index'] if 'mic_index' in conf else -1
		self.threshold = conf['threshold'] if 'threshold' in conf else THRESHOLD
		self.hotkeys = conf['hotkeys'] if 'hotkeys' in conf else [DEFAULT_NAME]
		self.hotkeys.append('freebox')
		self.hotkey_needed = True
		self.last_recognize_time = 0
		self.lang = conf['lang'] if 'lang' in conf else 'en-US'
		self.api_key = conf['api_key'] if 'api_key' in conf else None
		if self.mic_index < 0:
			print('Error mic_index:', self.mic_index,'undefined')
			return
		self.state = conf['autostart'] if 'autostart' in conf else False
		self.thread.start()
		log('-> hotkeys: ' + ', '.join(self.hotkeys))

	def execute(self, cmd):
		log("Recognition::execute: " + cmd)
		if cmd == 'on': self.state = True
		elif cmd == 'off': self.state = False
		return dict(success=True, cmd=cmd)

	def worker(self):
		#log("Recognition::startWorker")
		self.set_running(True)
		try:
			audio = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NONBLOCK, 'default')
			audio.setchannels(CHANNELS)
			audio.setrate(RATE)
			audio.setformat(FORMAT)
			audio.setperiodsize(CHUNK)
			ready = True
		except Exception as e:
			log(str(e))
			self.set_running(False)
			self.state = False
			return

		recording = False
		audio2send = []
		prev_audio = deque(maxlen=int(PREV_AUDIO * (RATE/CHUNK)))

		while self.get_running():
			if self.state:
				l,data = audio.read()
				if l:
					try:
						energy = audioop.rms(data, 2)
						if not recording and energy > self.threshold:
							self.hotkey_needed = time.time() - self.last_recognize_time > HOTKEY_DURATION
							#log("Recognition::startRecording HotKey needed: " + str(self.hotkey_needed))
							self.controller.atmega.set_led('0x0000FF')
							recording = True
							audio2send.append(data)
							duration = 0
						if recording:
							audio2send.append(data)
							duration += .001
							#print('duration',duration)
							if energy > self.threshold:
								duration = 0
							# record
							#print('duration',duration)
							if duration > SILENCE_LIMIT:
								#log("Recognition::stopRecording")
								self.controller.atmega.set_led('OFF')
								recording = False
								audio2send = list(prev_audio) + audio2send
								#print("audio2send")
								#print(" len", len(audio2send))
								#print(" ", audio2send)
								self.recognize(audio2send)
								audio2send = []
								prev_audio.clear()
						else:
							prev_audio.append(data)
					except audioop.error as e:
						if str(e) != "not a whole number of frames":
							raise e
					except Exception as e:
						log(str(e))
			time.sleep(.001)
		self.controller.atmega.set_led('OFF')

	def samples_to_flac(self, frame_data):
		with io.BytesIO() as wav_file:
			wav_writer = wave.open(wav_file, "wb")
			try: # note that we can't use context manager due to Python 2 not supporting it
				wav_writer.setsampwidth(FORMAT)
				wav_writer.setnchannels(CHANNELS)
				wav_writer.setframerate(RATE)
				for data in frame_data:
					wav_writer.writeframes(data)
			finally:  # make sure resources are cleaned up
				wav_writer.close()
			wav_data = wav_file.getvalue()
		
		# determine which converter executable to use
		flac_converter = "flac" #shutil_which("flac") # check for installed version first

		cmd = "\"%s\" --stdout --totally-silent --best -" % flac_converter
		#print('cmd', cmd)
		process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
		flac_data, stderr = process.communicate(wav_data)
		return flac_data

	def recognize(self, audio_data):
		self.controller.atmega.set_led('0x00FF00')
		flac_data = self.samples_to_flac(audio_data)
		#print('flac_data len', len(flac_data))
		url = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang=%s&key=%s" % (self.lang, self.api_key)
		request = Request(url, data = flac_data, headers = {"Content-Type": "audio/x-flac; rate=%s" % RATE})
		try:
			response = urlopen(request)
		except URLError as e:
			log(str(e))
			raise IndexError("No internet connection available to transfer audio data")
		except:
			raise KeyError("Server wouldn't respond (invalid key or quota has been maxed out)")
		finally:
			self.controller.atmega.set_led('OFF')
		response_text = response.read().decode("utf-8")
		actual_result = []
		for line in response_text.split("\n"):
			if not line: continue
			result = json.loads(line)["result"]
			if len(result) != 0:
				actual_result = result[0]
				break
		if "alternative" in actual_result:
			spoken_text = []
			for i, prediction in enumerate(actual_result["alternative"]):
				if "transcript" in prediction:
					spoken_text.append(unicodedata.normalize('NFD', prediction["transcript"]).encode('ascii', 'ignore').decode('utf-8').lower())
			executed = False
			has_hotkey = False
			hot = None
			for text in spoken_text:
				if ' ' in text:
					tmp = text.split(' ')
					found = has_hotkey or tmp[0] in self.hotkeys
					if found: 
						hot = tmp.pop(0)
						has_hotkey = found
					text = ' '.join(tmp)
				if self.hotkey_needed and not has_hotkey: continue
				cmds = self.controller.search(text)
				if cmds['success'] and len(cmds['cmds']) > 0:
					self.last_recognize_time = time.time()
					executed = True
					for cmd in cmds['cmds']:
						self.controller.execute(cmd)
						time.sleep(.1)
					break
			if self.hotkey_needed and not has_hotkey: 
				log('Recognition::HotKey needed but not present !')
				self.controller.atmega.set_led('0x0000FF', 3)
			elif not executed:
				#self.controller.execute("speech/say/Je n'ai pas compris")
				self.controller.atmega.set_led('0xFF0000', 3)
				log("Recognition::notFound")
				for text in spoken_text:
					log("-> " + text)