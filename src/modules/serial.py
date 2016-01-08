import threading, logging, os, serial, time
from modules import EventManager
import wiringpi2 as wpi

wpi.wiringPiSetup()

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def log(value):
	print(value)
	logging.debug(value)

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"" COMMANDS LIST """"""""""""""""""""""""""""""""""""""""""""""""
0 = ERROR
1 = DEFINE HOMEEASY SENDER CODE
2 = SEND/RECEIVE HOMEEASY ORDERS
3 = REQUEST/RECEIVE SENSORS VALUES
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

class ATMega328():
	"""Class 'ATMega328': Serial communication with ATMega328"""

	def __init__(self):
		#log("ATMega328::init")
		self.name = "ATMega328"
		self.cmds = []
		self.set_running(True)
		self.reading_response = False
		self.thread = threading.Thread(target=self.worker)
		self.thread.daemon = True
		self.thread.start()
		EventManager.addEvent(send = [self.send])

	#def openSerial(self):
	#	log("ATMega328 >> open ttyAMA0")
	#	self.ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
	#	self.ser.open()

	#@property
	def get_running(self):
		return self.__running

	#@running.setter
	def set_running(self, value):
		self.__running = value

	def set_led(self, value, repeat=1):
		self.send("9-"+value+"-"+str(repeat))

	def send(self, cmd):
		self.cmds.append(cmd)
		#log("ATMega328 >> " + str(cmd)) #+ (" (wait response)" if read else "")
		#ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
		#ser.open()
		#ser.write(bytes(str(cmd) + str("\n"), 'UTF-8'))
		#ser.close()
		#result = []
		#if read:
		#	self.reading_response = True
		#	ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
		#	ser.open()
		#	time.sleep(.1)
		#	response = None
		#	#log("ATMega328 >> waiting response")
		#	while response == None and self.get_running():
		#		line = ser.readline()
		#		line = line.decode('utf-8').strip()
		#		if line != '' and line.endswith('-OK'):
		#			#log('-> Direct response')
		#			result = line.split('-')
		#	ser.close()
		#return result


	def worker(self):
		#log("ATMega328::startWorker")
		ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
		if not ser.isOpen(): ser.open()
		while self.get_running():
			if len(self.cmds) > 0:
				cmd = self.cmds.pop(0)
				if cmd:
					#log("ATMega328 >> " + str(cmd))
					ser.write(bytes(str(cmd) + str("\n"), 'UTF-8'))
					time.sleep(.1)
			line = ser.readline()
			line = line.decode('utf-8').strip()
			if line != '':
				log("ATMega328 << " + line)
				if 'Ready' in line:
					EventManager.ready()
				#if line.endswith('-OK'):
				#	log("ATMega328 << response: " + line)
				#	#self.response = line
				elif '-' in line and not line.endswith('-OK'):
					#log("ATMega328 << " + line)
					parts = line.split('-')
					cmd = int(parts.pop(0))
					#log("ATMega328::read << " + line)
					if cmd == 0:
						if len(parts) > 1:
							errorCode = int(parts[1])
							error = parts[2]
						else:
							errorCode = 0
							error = "Unknown error"
						log('ATMega328 Error [' + str(errorCode) + ']: ' + error)
					else:
						if cmd == 1: pass
						elif cmd == 2: EventManager.receive(parts)
						elif cmd == 3: EventManager.sensors(parts)
						elif cmd == 4: EventManager.sensors(parts)
		ser.close()
		#log("ATMega328::stopWorker")
