import modules
import alsaaudio as aa
import audioop, time, wave, os, io, subprocess
from collections import deque
from urllib.request import Request, urlopen
from urllib.error import URLError
import json, unicodedata, logging

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
THRESHOLD = 10000
FLAC_CONV = 'flac -f'

class Recognition(modules.Threadable):
	"""Class Recognition for Voice recognition with Google"""

	def __init__(self, conf):
		super().__init__(conf)
		self.mic_index = conf['mic_index'] if 'mic_index' in conf else -1
		self.threshold = conf['threshold'] if 'threshold' in conf else 10000
		self.lang = conf['lang'] if 'lang' in conf else 'en-US'
		self.api_key = conf['api_key'] if 'api_key' in conf else None

		if self.mic_index < 0:
			print('Error mic_index:', self.mic_index,'undefined')
			return
		if 'enable' not in conf or conf['enable']:
			self.thread.start()

	def worker(self):
		print("-> Recognition worker start...")
		self.set_running(True)
		audio = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NONBLOCK, 'default')
		audio.setchannels(CHANNELS)
		audio.setrate(RATE)
		audio.setformat(FORMAT)
		audio.setperiodsize(CHUNK)

		recording = False
		audio2send = []
		prev_audio = deque(maxlen=int(PREV_AUDIO * (RATE/CHUNK)))

		while self.get_running():
			l,data = audio.read()
			if l:
				try:
					energy = audioop.rms(data, 2)
					if not recording and energy > THRESHOLD:
						#print("* Start recording")
						recording = True
						audio2send.append(data)
						duration = 0
					if recording:
						audio2send.append(data)
						duration += .001
						if energy > THRESHOLD:
							duration = 0
						# record
						#print('duration',duration)
						if duration > SILENCE_LIMIT:
							#print("* Stop recording")
							recording = False
							audio2send = list(prev_audio) + audio2send
							self.recognize(audio2send)
							audio2send = []
							prev_audio.clear()
					else:
						prev_audio.append(data)
				except audioop.error as e:
					if str(e) != "not a whole number of frames":
						raise e
			time.sleep(.001)

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
		flac_data = self.samples_to_flac(audio_data)
		url = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang=%s&key=%s" % (self.lang, self.api_key)
		request = Request(url, data = flac_data, headers = {"Content-Type": "audio/x-flac; rate=%s" % RATE})
		try:
			response = urlopen(request)
		except URLError:
			raise IndexError("No internet connection available to transfer audio data")
		except:
			raise KeyError("Server wouldn't respond (invalid key or quota has been maxed out)")
		response_text = response.read().decode("utf-8")
		#print('recognize', response_text)
		actual_result = []
		for line in response_text.split("\n"):
			if not line: continue
			result = json.loads(line)["result"]
			if len(result) != 0:
				actual_result = result[0]
				break
		if "alternative" in actual_result:
			#result = None
			#for prediction in actual_result["alternative"]:
			#	if "transcript" in prediction:
			#		result = prediction["transcript"].lower()
			#		result = unicodedata.normalize('NFD', result).encode('ascii', 'ignore').decode('utf-8')
			#if result != None:
			#	cmds = self.controller.search(result)
			#	print(cmds)
			spoken_text = []
			for i, prediction in enumerate(actual_result["alternative"]):
				if "transcript" in prediction:
					spoken_text.append(unicodedata.normalize('NFD', prediction["transcript"]).encode('ascii', 'ignore').decode('utf-8').lower())
			executed = False
			for text in spoken_text:
				cmds = self.controller.search(text)
				if cmds['success'] and len(cmds['cmds']) > 0:
					for cmd in cmds['cmds']:
						self.controller.execute(cmd)
					executed = True
					break
			#if not executed:
			#	self.controller.execute("speech/say/Je n'ai pas compris")
		