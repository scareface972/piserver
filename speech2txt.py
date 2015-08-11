#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request
import pyaudio
import wave
import audioop
from collections import deque
import os
import time
import math
import unicodedata
import json
import requests


#############################################################################
#############################################################################
########## SETUP LANG AND PI HOST ###########################################
PISERVER = "192.168.0.2"
LANG_CODE = 'fr-FR'  # Language to use
API_KEY = "AIzaSyCL1V54VOyfI9RR3vR5Luadc18PcYv9wpg"
#############################################################################
#############################################################################
#############################################################################


GOOGLE_SPEECH_URL = 'https://www.google.com/speech-api/v2/recognize?output=json&app=PiServer&client=PiServer&lang=%s&key=%s' % (LANG_CODE,API_KEY)
FLAC_CONV = 'flac -f'  # We need a WAV to FLAC converter. flac is available
                       # on Linux

# Microphone stream config.
CHUNK = 1024  # CHUNKS of bytes to read each time from mic
FORMAT = pyaudio.paInt16
SAMPLE_WIDTH = pyaudio.get_sample_size(FORMAT)
CHANNELS = 1
INPUT_INDEX = -1
RATE = 16000
THRESHOLD = 2500 # The threshold intensity that defines silence
                  # and noise signal (an int. lower than THRESHOLD is silence).

SILENCE_LIMIT = 1  # Silence limit in seconds. The max ammount of seconds where
                     # only silence is recorded. When this time passes the
                     # recording finishes and the file is delivered.

PREV_AUDIO = 0.5  # Previous audio (in seconds) to prepend. When noise
                  # is detected, how much of previously recorded audio is
                  # prepended. This helps to prevent chopping the beggining
                  # of the phrase.

def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nkfd_form.encode('ASCII', 'ignore')
    return only_ascii

def audio_int(num_samples=50):
    """ Gets average audio intensity of your mic sound. You can use it to get
        average intensities while you're talking and/or silent. The average
        is the avg of the 20% largest intensities recorded.
    """

    print("Getting intensity values from mic.")
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    input_device_index = INPUT_INDEX,
                    input=True,
                    channels=CHANNELS,
                    rate=RATE,
                    frames_per_buffer=CHUNK)

    values = [math.sqrt(abs(audioop.avg(stream.read(CHUNK), 4))) 
              for x in range(num_samples)] 
    values = sorted(values, reverse=True)
    r = sum(values[:int(num_samples * 0.2)]) / int(num_samples * 0.2)
    print(" Finished ")
    print(" Average audio intensity is ", r)
    stream.close()
    p.terminate()
    return r


def listen_for_speech(threshold=THRESHOLD, num_phrases=-1):
    """
    Listens to Microphone, extracts phrases from it and sends it to 
    Google's TTS service and returns response. a "phrase" is sound 
    surrounded by silence (according to threshold). num_phrases controls
    how many phrases to process before finishing the listening process 
    (-1 for infinite). 
    """
    #Open stream
    p = pyaudio.PyAudio()

    stream = p.open(input_device_index = INPUT_INDEX, format=FORMAT, frames_per_buffer=CHUNK, channels=CHANNELS, rate=RATE, input=True)
    # print("")
    # print(" « q » for quit")
    # print(" « p » pause audio listening")
    print("")
    print("* Listening mic. ")

    try:
        audio2send = []
        cur_data = ''  # current chunk  of audio data
        rel = RATE/CHUNK
        slid_win = deque(maxlen=int(SILENCE_LIMIT * rel))
        #Prepend audio from 0.5 seconds before noise was detected
        prev_audio = deque(maxlen=int(PREV_AUDIO * rel))
        started = False
        n = num_phrases
        response = []
        size = 0
        paused = False
        
        while (num_phrases == -1 or n > 0):
            if not paused:
                cur_data = stream.read(CHUNK)
                slid_win.append(math.sqrt(abs(audioop.avg(cur_data, 4))))
                #print('slid',slid_win[-1])
                nbt = sum([x > threshold and x < 9000 for x in slid_win])
                #print('nbt',nbt)
                if(nbt > 0):
                    if(not started):
                        print("Starting record of phrase")
                        started = True
                    audio2send.append(cur_data)
                    size += 1
                elif (started is True):
                    print("Finished", str(size))
                    # The limit was reached, finish capture and deliver.
                    filename = save_speech(list(prev_audio) + audio2send, p)
                    # Send file to Google and get response
                    r = stt_google_flac(filename) 
                    if num_phrases == -1:
                        print("Response", r)
                        if not r == None and len(r) > 0: search_command(r)
                    # else:
                    #     response.append(r)
                    # Remove temp file. Comment line to review.
                    #os.remove(filename)
                    # Reset all
                    started = False
                    slid_win = deque(maxlen=SILENCE_LIMIT * rel)
                    prev_audio = deque(maxlen=0.5 * rel) 
                    audio2send = []
                    size = 0
                    n -= 1
                    print("Listening ...")
                else:
                    prev_audio.append(cur_data)
                    size += 1
    except Exception as e:
        print(e)
        pass
    finally:
        print("* Done recording")
        stream.close()
        p.terminate()
    # return response

def save_speech(data, p):
    """ Saves mic data to temporary WAV file. Returns filename of saved 
        file """
    filename = 'output_'+str(int(time.time()))
    print('save_speech', filename)
    # writes data to WAV file
    #data = ''.join(data)
    d = ""
    for b in data: d += str(b)
    #print('data', d)
    filename += '.wav'
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(SAMPLE_WIDTH)
    wf.setframerate(RATE)  # TODO make this value a function parameter?
    #print('writeframes')
    wf.writeframes(bytes(d, 'utf-8'))
    #print('close')
    wf.close()
    time.sleep(1)
    print("- Converting to flac")
    print("  " + FLAC_CONV + ' ' + filename)
    os.system(FLAC_CONV + ' ' + filename + ' > /dev/null 2>&1')
    #os.remove(filename)
    filename = filename.split('.')[0] + '.flac'
    return filename

def stt_google_flac(audio_fname):
    """ Sends audio file (audio_fname) to Google's text to speech 
        service and returns service's response. We need a FLAC 
        converter if audio is not FLAC (check FLAC_CONV). """

    print("Sending #", audio_fname)
    f = open(audio_fname, 'rb')
    flac_cont = f.read()
    f.close()

    # Headers. A common Chromium (Linux) User-Agent
    #hrs = {"User-Agent": "Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.63 Safari/535.7", 
    #       'Content-type': 'audio/x-flac; rate=16000'}  

    hrs = { 'Content-type': 'audio/x-flac; rate=' + str(RATE) }
    #req = urllib.request.Request(GOOGLE_SPEECH_URL, data=flac_cont, headers=hrs)
    print("Sending request to Google TTS")
    try:
        #p = urllib.request.urlopen(req)
        req = requests.post(GOOGLE_SPEECH_URL, data=flac_cont, headers=hrs)
        print(req)
        print(req.text)
        response = req.text #p.read()
        response = response.replace('{"result":[]}', '').strip()
        res = json.loads(response)['result']
        #print(response)
        if len(res) > 0 and 'alternative' in res[0]:
            res = res[0]['alternative']
        else:
            res = None
        #print(res)
    except Exception as e:
        print(" > Couldn't parse service response", e)
        res = None
    return res

def search_command(rs):
    print(' > Google return', len(rs), 'results...')
    try:
        values = []
        for r in rs:
            cmd = remove_accents(r['transcript']).lower().decode('utf-8')
            if not cmd in values: values.append(cmd)
        print(values)
        url = 'http://' + PISERVER + '/search'
        data = json.dumps(values)
        req = requests.post(url, data=data)
        response = req.text
        #print(response)
        res = json.loads(response)
        print(res)
        if res['success']:
            for cmd in res['cmds']:
                success = exec_command(cmd)
                if success: print(' > Command executed:', cmd)
                else: print(' > Error on exec:', cmd)
    except e:
        print(e)

def exec_command(cmd):
    url = 'http://' + PISERVER + '/exec/' + cmd
    print(" >> Sending request to PiServer" , url)
    req = urllib.request.Request(url)
    try:
        p = urllib.request.urlopen(req)
        response = p.read()
        # print(" > Reponse:", response)
        res = json.loads(response)
        return res['success']
    except:
        # print(" > Couldn't parse pi response")
        return False

def test_pyaudio():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        print (i, d['name'], d['index'], d['maxInputChannels'])

def set_input():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        print(i, d['name'], d['maxInputChannels'])
        if d['maxInputChannels'] > 0: return i#, int(d['defaultSampleRate'])
    return -1

if(__name__ == '__main__'):
    #test_pyaudio()
    INPUT_INDEX = set_input()
    print("Input index:",INPUT_INDEX)
    if INPUT_INDEX > -1: listen_for_speech()  # listen to mic.
    else: print("No input device")
    #r = stt_google_wav('tts.wav') 
    #print("Response", r)
    #if not r == None and len(r) > 0: search_command(r)
    #audio_int()  # To measure your mic levels