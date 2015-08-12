#!/usr/bin/env python3
from os import environ, path

from pocketsphinx import Decoder

MODELDIR = "pocketsphinx/model"
DATADIR = "pocketsphinx/test/data"

# Create a decoder with certain model
config = Decoder.default_config()

# US
config.set_string('-hmm', path.join(MODELDIR, 'en-us/en-us'))
config.set_string('-lm', path.join(MODELDIR, 'en-us/en-us.lm.dmp'))
config.set_string('-dict', path.join(MODELDIR, 'en-us/cmudict-en-us.dict'))

# FR
#config.set_string('-hmm', path.join(MODELDIR, 'fr-fr/fr-fr'))
#config.set_string('-lm', path.join(MODELDIR, 'fr-fr/french3g62K.lm.dmp'))
#config.set_string('-dict', path.join(MODELDIR, 'fr-fr/frenchWords62K.dic'))

# Decode streaming data.
decoder = Decoder(config)
decoder.start_utt()
stream = open(path.join(DATADIR, 'goforward.raw'), 'rb')
while True:
  buf = stream.read(1024)
  if buf:
    decoder.process_raw(buf, False, False)
  else:
    break
decoder.end_utt()
print ('Best hypothesis segments: ', [seg.word for seg in decoder.seg()])
