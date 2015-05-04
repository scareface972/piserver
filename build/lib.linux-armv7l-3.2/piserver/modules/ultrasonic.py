import modules
import wiringpi2 as wpi
from threading import Thread
from time import sleep

wpi.wiringPiSetup()

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Ultrasonic']

INPUT = 0
OUTPUT = 1
PWM = 2

LOW = 0
HIGH = 1

class Ultrasonic(modules.Switch):
	"""Class 'Ultrasonic' pour interagir HC-SR04 Ultrasonic Sensor"""

	def __init__(self, conf):
		self.thread = None
		self.distance = -1;
		self.pinTrig  = conf['pinTrig']
		self.pinEcho = conf['pinEcho']
		key = "((\w+\s)?(" + conf['name'] + "))"
		cmds = {
			'on': "allumer?\s"+key+"+",
			'off': "(etein(dre|s))\s"+key+"+"
		}
		super().__init__(conf, cmds)
		# TRIG pin must start LOW
		wpi.pinMode(self.pinTrig, OUTPUT)
		wpi.pinMode(self.pinEcho, INPUT)
		wpi.digitalWrite(self.pinTrig, LOW)

	def execute(self, cmd):
		# Exécution de commande avec la librairie wiringPi
		# https://projects.drogon.net/raspberry-pi/wiringpi/
		result = dict(success=False)
		try:
			if cmd == 'distance': 
				result['alive'] = self.thread != None
				result['distance'] = self.distance
			if cmd == 'on' or cmd == 'off':
				if cmd == 'on': 
					new_state = True
				elif cmd == 'off': 
					new_state = False
				if self.state != new_state:
					if new_state and self.thread == None: 
						self.thread = CaptureThread(self, self.pinTrig, self.pinEcho)
						self.thread.start()
					elif not new_state and self.thread != None: 
						self.thread.stop()
						self.thread = None
					self.state = new_state
					result['state'] = new_state
			result['success'] = True
		except Exception as e:
			print(e)
		return result

class CaptureThread(Thread):
	def __init__(self, target, pinTrig, pinEcho):
		Thread.__init__(self)
		self.target = target
		self.pinTrig = pinTrig
		self.pinEcho = pinEcho

	def run(self):
		self.alive = True
		while self.alive:
			try:
				# Send trig pulse
				# print("-> send trig pulse")
				wpi.digitalWrite(self.pinTrig, HIGH)
				wpi.delayMicroseconds(20)
				wpi.digitalWrite(self.pinTrig, LOW)
				# Wait for echo start
				# print("--> wait for echo start")
				while self.alive and wpi.digitalRead(self.pinEcho) == LOW: continue
				# Wait for echo end
				# print("--> wait for echo end")
				startTime = wpi.micros()
				# print("---> startTime: " + str(startTime))
				while self.alive and wpi.digitalRead(self.pinEcho) == HIGH: continue
				travelTime = wpi.micros() - startTime
				# print("---> travelTime: " + str(startTime))
				dist = travelTime / 58
				# print("---> dist: " + str(dist))
				if dist != self.target.distance:
					self.target.distance = dist
					# print("Distance: " + str(self.target.distance))
			except Exception as e:
				print(e)
			finally:
				wpi.digitalWrite(self.pinTrig, LOW)
			sleep(1)

	def stop(self):
		self.target.distance = -1
		self.alive = False
		self.join()