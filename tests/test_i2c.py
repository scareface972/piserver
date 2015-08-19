import smbus
import time
import wiringpi2 as wpi

bus = smbus.SMBus(1)
wpi.wiringPiSetup()
address = 0x12

def writeData(value, data):
	bus.write_block_data(address, value, list(bytearray(data.encode('utf-8'))))
	time.sleep(.2)

def readData():
	return bus.read_byte_data(address,0x00)

def setEmitterCode(code):
	writeData(1, str(code))

def addReceiver(name, unit):
	writeData(2, str(unit) + '-' + name)

def addEmitter(receiver, code, unit):
	writeData(3, str(receiver) + '-' + str(code) + '-' + str(unit))

def getState(name):
	writeData(4, name)
	data = readData()
	return 'on' if data == 1 else 'off'

def setState(name, state):
	writeData(5, name + '-' + state)

def setup():
	setEmitterCode(8976434)
	addReceiver('plafond', 1)
	addEmitter(1, 13552350, 1)
	addEmitter(1, 17144714, 1)
	addReceiver('cuisine', 3)
	addEmitter(3, 13552350, 0)
	addEmitter(3, 17144714, 0)

def reset():
  pin = 7
  wpi.pinMode(pin, 1)
  wpi.digitalWrite(pin, 0)
  time.sleep(0.12)
  wpi.digitalWrite(pin, 1)

while True:
	var = int(input("1 - Etat\n2 - Changer\n3 - Setup\n4 - Reset\n>> "))
	if not var: continue

	if var == 1:
		name = int(input("1 - Cuisine\n2 - Plafond\n>> "))
		if name == 1: name = 'cuisine'
		elif name == 2: name = 'plafond'
		state = getState(name)
		print (name, 'is', state)
		print ('---------------------------')

	elif var == 2:
		name = int(input("1 - Cuisine\n2 - Plafond\n>> "))
		if name == 1: name = 'cuisine'
		elif name == 2: name = 'plafond'
		state = int(input("1 - On\n2 - Off\n>> "))
		if state == 1: state = 'on'
		elif state == 2: state = 'off'
		setState(name, state)
		print (name, 'change to', state)
		print ('---------------------------')

	elif var == 3:
		setup()
	elif var == 4:
		reset()