import Chacon
import threading

def worker():
	try :
		print("Start worker...")
		Chacon.receive(2, 0, 8976434)
	except KeyboardInterrupt:
		pass

thread = threading.Thread(target=worker)
thread.daemon = True
thread.start()

while True:
	pass