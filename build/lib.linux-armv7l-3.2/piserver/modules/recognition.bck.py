from core.controller import Controller
import modules
import pyaudio
#from ctypes import *
import os, io, subprocess, wave, time
import math, audioop, collections, threading
from urllib.request import Request, urlopen
from urllib.error import URLError
import json, logging
import unicodedata

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Recognition']

#ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

def log(value):
	print(value)
	logging.debug(value)

class Recognition(modules.Threadable):
	"""Class Recognition for Voice recognition with Google"""

	def __init__(self, conf):
		super().__init__(conf)
		self.mic_index = conf['mic_index'] if 'mic_index' in conf else -1
		self.threshold = conf['threshold'] if 'threshold' in conf else 2000
		self.lang = conf['lang'] if 'lang' in conf else 'en-US'
		self.api_key = conf['api_key'] if 'api_key' in conf else None

		#self.c_error_handler = ERROR_HANDLER_FUNC(self.py_error_handler)
		#asound = cdll.LoadLibrary('libasound.so')
		## Set error handler
		#print("Set erro handler")
		#asound.snd_lib_error_set_handler(self.c_error_handler)

		if self.mic_index < 0:
			print('Error mic_index:', self.mic_index,'undefined')
			return
		if 'enable' not in conf or not conf['enable']:
			self.thread.start()

	#def py_error_handler(self, filename, line, function, err, fmt):
	#	print('error', fmt.decode('utf-8'))

	def worker(self):
		print("-> Recognition worker start...")
		self.set_running(True)
		while self.get_running():
			self.r = Recognizer(self.lang, self.api_key)
			self.r.energy_threshold = self.threshold
			self.r.dynamic_energy_threshold = False
			self.m = Microphone(self.mic_index)
			print("Say something!")
			with self.m as source:
				capability = source.audio.get_default_host_api_info()
				#print(capability)
				audio = self.r.listen(source)
			if audio != None:
				print("Got it! Now to recognize it...")
				try:
					text = self.r.recognize(audio)
					self.callback(text)
				except LookupError:
					print("Oops! Didn't catch that")
			time.sleep(1)
		print("-> Recognition stoped")
		
	def callback(self, text):
		log("You said " + text)
		text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
		result = self.controller.search(text)
		log("result " + str(result))
		#result = json.loads(result)
		if 'success' in result and result['success']:
			for cmd in result['cmds']:
				self.controller.execute(cmd)

	def get_running(self):
		return super().get_running()

	def set_running(self, value):
		if hasattr(self, 'r') and not value: self.r.is_listening = value
		super().set_running(value)

class AudioSource(object):
	def __init__(self):
		raise NotImplementedError("this is an abstract class")

	def __enter__(self):
		raise NotImplementedError("this is an abstract class")

	def __exit__(self, exc_type, exc_value, traceback):
		raise NotImplementedError("this is an abstract class")

class AudioData(object):
	def __init__(self, rate, data):
		self.rate = rate
		self.data = data

class Microphone(AudioSource):
	"""
	This is available if PyAudio is available, and is undefined otherwise.
	Creates a new ``Microphone`` instance, which represents a physical microphone on the computer. Subclass of ``AudioSource``.
	If ``device_index`` is unspecified or ``None``, the default microphone is used as the audio source. Otherwise, ``device_index`` should be the index of the device to use for audio input.
	"""
	def __init__(self, device_index = None):
		#assert device_index is None or isinstance(device_index, int), "Device index must be None or an integer"
		#if device_index is not None: # ensure device index is in range
		#	audio = pyaudio.PyAudio(); count = audio.get_device_count(); audio.terminate() # obtain device count
		#	assert 0 <= device_index < count, "Device index out of range"
		self.device_index = device_index
		self.format = pyaudio.paInt16 # 16-bit int sampling
		self.SAMPLE_WIDTH = pyaudio.get_sample_size(self.format)
		self.RATE = 16000 # sampling rate in Hertz
		self.CHANNELS = 1 # mono audio
		self.CHUNK = 1024 # number of frames stored in each buffer

		self.audio = None
		self.stream = None

	def __enter__(self):
		#print('__enter__')
		self.audio = pyaudio.PyAudio()
		self.stream = self.audio.open(
			input_device_index = self.device_index,
			format = self.format, rate = self.RATE, channels = self.CHANNELS, frames_per_buffer = self.CHUNK,
			input = True, # stream is an input stream
		)
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		#print('__exit__')
		self.stream.stop_stream()
		self.stream.close()
		self.stream = None
		self.audio.terminate()

class Recognizer(AudioSource):
	def __init__(self, language = "fr-FR", key = "AIzaSyCL1V54VOyfI9RR3vR5Luadc18PcYv9wpg"):
		"""
		Creates a new ``Recognizer`` instance, which represents a collection of speech recognition functionality.
		The language is determined by ``language``, a standard language code like `"en-US"` or `"en-GB"`, and defaults to US English. A list of supported language codes can be found `here <http://stackoverflow.com/questions/14257598/>`__. Basically, language codes can be just the language (``en``), or a language with a dialect (``en-US``).
		The Google Speech Recognition API key is specified by ``key``. If not specified, it uses a generic key that works out of the box.
		"""
		assert isinstance(language, str), "Language code must be a string"
		assert isinstance(key, str), "Key must be a string"
		self.key = key
		self.language = language
		self.is_listening = False
		self.energy_threshold = 300 # minimum audio energy to consider for recording
		self.dynamic_energy_threshold = True
		self.dynamic_energy_adjustment_damping = 0.15
		self.dynamic_energy_ratio = 1.5
		self.pause_threshold = 1.2 # seconds of quiet time before a phrase is considered complete
		self.quiet_duration = 0.5 # amount of quiet time to keep on both sides of the recording

	def samples_to_flac(self, source, frame_data):
		assert isinstance(source, AudioSource), "Source must be an audio source"
		import platform, os, stat
		with io.BytesIO() as wav_file:
			wav_writer = wave.open(wav_file, "wb")
			try: # note that we can't use context manager due to Python 2 not supporting it
				wav_writer.setsampwidth(source.SAMPLE_WIDTH)
				wav_writer.setnchannels(source.CHANNELS)
				wav_writer.setframerate(source.RATE)
				wav_writer.writeframes(frame_data)
			finally:  # make sure resources are cleaned up
				wav_writer.close()
			wav_data = wav_file.getvalue()
		
		# determine which converter executable to use
		system = platform.system()
		path = os.path.dirname(os.path.abspath(__file__)) # directory of the current module file, where all the FLAC bundled binaries are stored
		flac_converter = "flac" #shutil_which("flac") # check for installed version first

		cmd = "\"%s\" --stdout --totally-silent --best -" % flac_converter
		print('cmd', cmd)
		process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
		flac_data, stderr = process.communicate(wav_data)
		return flac_data

	def record(self, source, duration = None):
		"""
		Records up to ``duration`` seconds of audio from ``source`` (an ``AudioSource`` instance) into an ``AudioData`` instance, which it returns.
		If ``duration`` is not specified, then it will record until there is no more audio input.
		"""
		assert isinstance(source, AudioSource), "Source must be an audio source"

		frames = io.BytesIO()
		seconds_per_buffer = (source.CHUNK + 0.0) / source.RATE
		elapsed_time = 0
		while True: # loop for the total number of chunks needed
			elapsed_time += seconds_per_buffer
			if duration and elapsed_time > duration: break

			buffer = source.stream.read(source.CHUNK)
			if len(buffer) == 0: break
			frames.write(buffer)

		frame_data = frames.getvalue()
		frames.close()
		return AudioData(source.RATE, self.samples_to_flac(source, frame_data))

	def adjust_for_ambient_noise(self, source, duration = 1):
		"""
		Adjusts the energy threshold dynamically using audio from ``source`` (an ``AudioSource`` instance) to account for ambient noise.
		Intended to calibrate the energy threshold with the ambient energy level. Should be used on periods of audio without speech - will stop early if any speech is detected.
		The ``duration`` parameter is the maximum number of seconds that it will dynamically adjust the threshold for before returning. This value should be at least 0.5 in order to get a representative sample of the ambient noise.
		"""
		assert isinstance(source, AudioSource), "Source must be an audio source"

		seconds_per_buffer = (source.CHUNK + 0.0) / source.RATE
		elapsed_time = 0

		# adjust energy threshold until a phrase starts
		while True:
			elapsed_time += seconds_per_buffer
			if elapsed_time > duration: break
			buffer = source.stream.read(source.CHUNK)

			# check if the audio input has stopped being quiet
			energy = audioop.rms(buffer, source.SAMPLE_WIDTH) # energy of the audio signal
			if energy > self.energy_threshold: break

			# dynamically adjust the energy threshold using assymmetric weighted average
			damping = self.dynamic_energy_adjustment_damping ** seconds_per_buffer # account for different chunk sizes and rates
			target_energy = energy * self.dynamic_energy_ratio
			self.energy_threshold = self.energy_threshold * damping + target_energy * (1 - damping)

	def listen(self, source, timeout = None):
		"""
		Records a single phrase from ``source`` (an ``AudioSource`` instance) into an ``AudioData`` instance, which it returns.
		This is done by waiting until the audio has an energy above ``recognizer_instance.energy_threshold`` (the user has started speaking), and then recording until it encounters ``recognizer_instance.pause_threshold`` seconds of silence or there is no more audio input. The ending silence is not included.
		The ``timeout`` parameter is the maximum number of seconds that it will wait for a phrase to start before giving up and throwing a ``TimeoutException`` exception. If ``None``, it will wait indefinitely.
		"""
		assert isinstance(source, AudioSource), "Source must be an audio source"

		# record audio data as raw samples
		frames = collections.deque()
		assert self.pause_threshold >= self.quiet_duration >= 0
		seconds_per_buffer = (source.CHUNK + 0.0) / source.RATE
		pause_buffer_count = int(math.ceil(self.pause_threshold / seconds_per_buffer)) # number of buffers of quiet audio before the phrase is complete
		quiet_buffer_count = int(math.ceil(self.quiet_duration / seconds_per_buffer)) # maximum number of buffers of quiet audio to retain before and after
		elapsed_time = 0

		# store audio input until the phrase starts
		self.is_listening = True
		while self.is_listening:
			elapsed_time += seconds_per_buffer
			if timeout and elapsed_time > timeout: # handle timeout if specified
				raise TimeoutError("listening timed out")

			buffer = source.stream.read(source.CHUNK)
			if len(buffer) == 0: break # reached end of the stream
			frames.append(buffer)

			# check if the audio input has stopped being quiet
			energy = audioop.rms(buffer, source.SAMPLE_WIDTH) # energy of the audio signal
			if energy > self.energy_threshold: break

			# dynamically adjust the energy threshold using assymmetric weighted average
			if self.dynamic_energy_threshold:
				damping = self.dynamic_energy_adjustment_damping ** seconds_per_buffer # account for different chunk sizes and rates
				target_energy = energy * self.dynamic_energy_ratio
				self.energy_threshold = self.energy_threshold * damping + target_energy * (1 - damping)

			if len(frames) > quiet_buffer_count: # ensure we only keep the needed amount of quiet buffers
				frames.popleft()
		if not self.is_listening:
			return None
		
		# read audio input until the phrase ends
		pause_count = 0
		while self.is_listening:
			buffer = source.stream.read(source.CHUNK)
			if len(buffer) == 0: break # reached end of the stream
			frames.append(buffer)

			# check if the audio input has gone quiet for longer than the pause threshold
			energy = audioop.rms(buffer, source.SAMPLE_WIDTH) # energy of the audio signal
			if energy > self.energy_threshold:
				pause_count = 0
			else:
				pause_count += 1
			if pause_count > pause_buffer_count: # end of the phrase
				break
		if not self.is_listening:
			return None

		 # obtain frame data
		for i in range(quiet_buffer_count, pause_count): frames.pop() # remove extra quiet frames at the end
		frame_data = b"".join(list(frames))
		
		return AudioData(source.RATE, self.samples_to_flac(source, frame_data))

	def recognize(self, audio_data, show_all = False):
		"""
		Performs speech recognition, using the Google Speech Recognition API, on ``audio_data`` (an ``AudioData`` instance).
		Returns the most likely transcription if ``show_all`` is ``False``, otherwise it returns a ``dict`` of all possible transcriptions and their confidence levels.
		Note: confidence is set to 0 if it isn't given by Google
		Also raises a ``LookupError`` exception if the speech is unintelligible, a ``KeyError`` if the key isn't valid or the quota for the key has been maxed out, and ``IndexError`` if there is no internet connection.
		"""
		assert isinstance(audio_data, AudioData), "Data must be audio data"

		url = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang=%s&key=%s" % (self.language, self.key)
		self.request = Request(url, data = audio_data.data, headers = {"Content-Type": "audio/x-flac; rate=%s" % audio_data.rate})
		
		# check for invalid key response from the server
		try:
			response = urlopen(self.request)
		except URLError:
			raise IndexError("No internet connection available to transfer audio data")
		except:
			raise KeyError("Server wouldn't respond (invalid key or quota has been maxed out)")
		response_text = response.read().decode("utf-8")

		# ignore any blank blocks
		actual_result = []
		for line in response_text.split("\n"):
			if not line: continue
			result = json.loads(line)["result"]
			if len(result) != 0:
				actual_result = result[0]
				break

		# make sure we have a list of transcriptions
		if "alternative" not in actual_result:
			raise LookupError("Speech is unintelligible")

		# return the best guess unless told to do otherwise
		if not show_all:
			for prediction in actual_result["alternative"]:
				if "transcript" in prediction:
					return prediction["transcript"]
			raise LookupError("Speech is unintelligible")


		# return all the possibilities
		spoken_text = []
		for i, prediction in enumerate(actual_result["alternative"]):
			if "transcript" in prediction:
				spoken_text.append({"text": prediction["transcript"], "confidence": 1 if i == 0 else 0})
		return spoken_text
	
	def listen_in_background(self, source, callback):
		"""
		Spawns a thread to repeatedly record phrases from ``source`` (an ``AudioSource`` instance) into an ``AudioData`` instance and call ``callback`` with that ``AudioData`` instance as soon as each phrase are detected.
		Returns the thread (a ``threading.Thread`` instance) immediately, while the background thread continues to run in parallel.
		Phrase recognition uses the exact same mechanism as ``recognizer_instance.listen(source)``.
		The ``callback`` parameter is a function that should accept two parameters - the ``recognizer_instance``, and an ``AudioData`` instance representing the captured audio. Note that this function will be called from a non-main thread.
		"""
		assert isinstance(source, AudioSource), "Source must be an audio source"
		import threading
		def threaded_listen():
			while True:
				with source as s: audio = self.listen(s)
				callback(self, audio)
		listener_thread = threading.Thread(target=threaded_listen)
		listener_thread.start()
		return listener_thread

def shutil_which(file, mode=os.F_OK | os.X_OK, path=None):
	"""Locate a file in the user's path, or a supplied path. The function
	yields full paths in which the given file matches a file in a directory on
	the path.
	"""
	if not path:
		path = os.environ.get("PATH", os.defpath)

	for dir in path.split(os.pathsep):
		full_path = os.path.join(dir, file)
		if os.path.exists(full_path) and os.access(full_path, mode):
			yield full_path