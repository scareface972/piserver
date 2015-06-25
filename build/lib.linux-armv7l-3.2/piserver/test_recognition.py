#!/usr/bin/env python3
import pyaudio

index = -1
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
	d = p.get_device_info_by_index(i)
	print (i, d['name'], d['index'], d['maxInputChannels'])
	if d['maxInputChannels'] > 0: 
		index = i
		break
#print(index)
#exit()

#import speech_recognition as sr
#r = sr.Recognizer()
#with sr.Microphone() as source:                # use the default microphone as the audio source
#    audio = r.listen(source)                   # listen for the first phrase and extract it into audio data
#
#try:
#    print("You said " + r.recognize(audio))    # recognize speech using Google Speech Recognition
#except LookupError:                            # speech is unintelligible
#    print("Could not understand audio")	



import speech_recognition as sr

def callback(recognizer, audio):                          # this is called from the background thread
    try:
        print("You said " + recognizer.recognize(audio))  # received audio data, now need to recognize it
    except LookupError:
        print("Oops! Didn't catch that")
        pass

if index > -1:
	r = sr.Recognizer("fr-FR", "AIzaSyCL1V54VOyfI9RR3vR5Luadc18PcYv9wpg")
	print ('r.energy_threshold =', r.energy_threshold)
	r.energy_threshold = 2000
	print ('r.energy_threshold =', r.energy_threshold)
	r.listen_in_background(sr.Microphone(index), callback)

import time

while True: time.sleep(0.1)                         # we're still listening even though the main thread is blocked
