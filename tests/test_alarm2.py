import time, threading, sys, signal

class Alarm(threading.Thread):
	def __init__(self, name, tm, delay = 60):
		super(Alarm, self).__init__()
		print("Alarm: " + str(tm))
		self.name = name
		self.tm = tm
		self.delay = delay
		self.keep_running = True

	def run(self):
		try:
			# print("running")
			self.cntdown = self.delay
			while self.keep_running:
				self.cntdown -= 1
				if self.cntdown == 0:
					if time.time() >= self.tm:
						print(">> ALARM NOW <<")
						return
					self.cntdown = self.delay
		except:
			# print("Unexpected error:", sys.exc_info()[0])
			return

	def just_die(self):
		self.keep_running = False

now = time.time()
print("Now: " + str(now))

alarm = Alarm("a", now+10, 10)
alarm.start()

running = True
def end_read(signal,frame):
    global running
    running = False

signal.signal(signal.SIGINT, end_read)

try:
	while running:
		if not running: 
			alarm.just_die()
except:
	print("Yikes lets get out of here")
finally:
	alarm.just_die()