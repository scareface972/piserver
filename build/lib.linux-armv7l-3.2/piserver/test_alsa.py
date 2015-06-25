#!/usr/bin/env python3
 
import alsaaudio as aa
import audioop, time, wave, os, io, subprocess
from collections import deque
from urllib.request import Request, urlopen
from urllib.error import URLError
import json, unicodedata

CHUNK = 1024
RATE = 16000
CHANNELS = 1
FORMAT = aa.PCM_FORMAT_S16_LE

PREV_AUDIO = 10
SILENCE_LIMIT = 1
THRESHOLD = 10000
FLAC_CONV = 'flac -f'

data_in = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NONBLOCK, 'default')
data_in.setchannels(CHANNELS)
data_in.setrate(RATE)
data_in.setformat(FORMAT)
data_in.setperiodsize(CHUNK)

recording = False
audio2send = []
rel = RATE/CHUNK
prev_audio = deque(maxlen=int(PREV_AUDIO * rel))

def save_speech(data):
	filename = 'output_'+str(int(time.time()))+'.wav'
	#print('save_speech', filename)
	w = wave.open(filename, 'w')
	w.setnchannels(CHANNELS)
	w.setsampwidth(FORMAT)
	w.setframerate(RATE)
	for d in data:
		w.writeframes(d)
	w.close()
	os.system(FLAC_CONV + ' ' + filename + ' > /dev/null 2>&1')
	os.remove(filename)
	filename = filename.split('.')[0] + '.flac'
	return filename

def samples_to_flac(frame_data):
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

def recognize(audio_data, show_all = False):
	#print('recognize', len(audio_data))

	language = 'fr-Fr'
	key = 'AIzaSyCL1V54VOyfI9RR3vR5Luadc18PcYv9wpg'

	url = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang=%s&key=%s" % (language, key)
	request = Request(url, data = audio_data, headers = {"Content-Type": "audio/x-flac; rate=%s" % RATE})
	
	# check for invalid key response from the server
	try:
		response = urlopen(request)
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
		return None

	# return the best guess unless told to do otherwise
	if not show_all:
		for prediction in actual_result["alternative"]:
			if "transcript" in prediction:
				return prediction["transcript"]
		return None


	# return all the possibilities
	spoken_text = []
	for i, prediction in enumerate(actual_result["alternative"]):
		if "transcript" in prediction:
			spoken_text.append({"text": prediction["transcript"], "confidence": 1 if i == 0 else 0})
	return spoken_text

while True:
	# Read data from device
	l,data = data_in.read()
	if l:
		# Return the maximum of the absolute value of all samples in a fragment.
		try:
			energy = audioop.rms(data, 2)
			if not recording and energy > THRESHOLD:
				#print("* Start recording")
				recording = True
				audio2send = []
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
					#filename = save_speech(audio2send)
					#print('Saved to', filename)
					flac_data = samples_to_flac(audio2send)
					#print(len(flac_data))
					text = recognize(flac_data)
					if text != None:
						text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
						print('You said:', text)
			else:
				prev_audio.append(data)
		except audioop.error as e:
			if str(e) != "not a whole number of frames":
				raise e
	time.sleep(.001)