import threading, logging, os, serial, time
from modules import EventManager

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def log(value):
	print(value)
	logging.debug(value)

class ATMega328():
	"""Class 'ATMega328': Serial communication with ATMega328"""

	def __init__(self):
		log("ATMega328::init")
		self.name = "ATMega328"
		self.thread = threading.Thread(target=self.worker)
		self.thread.daemon = True
		self.thread.start()
		EventManager.addEvent(send = [self.send])

	#@property
	def get_running(self):
		return self.__running

	#@running.setter
	def set_running(self, value):
		self.__running = value

	def send(self, cmd, read=False):
		log("ATMega328::send >> " + str(cmd))
		ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
		ser.open()
		ser.write(bytes(str(cmd) + str("\n"), 'UTF-8'))
		result = []
		if read:
			time.sleep(1)
			try:
				line = ser.readline()
				line = line.decode('utf-8').strip()
				if line != "" and '-' in line:
					log("ATMega328::read << " + line)
					result = line.split('-')
			except:
				pass
		ser.close()
		return result


	def worker(self):
		log("ATMega328::startWorker")
		self.set_running(True)
		ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
		ser.open()
		while self.get_running():
			#if self.paused: continue
			try:
				line = ser.readline()
				line = line.decode('utf-8').strip()
				if line != "" and '-' in line:
					log("ATMega328::read << " + line)
					parts = line.split('-')
					cmd = int(parts.pop(0))
					if cmd == 0:
						errorCode = int(parts[1])
						error = parts[2]
						log('Error [' + str(errorCode) + ']: ' + error)
					else:
						if cmd == 1: pass
						elif cmd == 2: EventManager.receive(parts)
						elif cmd == 3: EventManager.sensors(parts)
			except:
				pass
		ser.close()
		log("ATMega328::stopWorker")
