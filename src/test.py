import serial, time
import threading

running = True
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
if ser.isOpen(): ser.close()
ser.open()

def send(cmd):
	print("ATMega328 >> " + str(cmd))
	ser.write(bytes(str(cmd) + str("\n"), 'UTF-8'))

def worker():
	while running:
		line = ser.readline()
		line = line.decode('utf-8').strip()
		if line != '':
			print("ATMega328 << " + line)

thread = threading.Thread(target=worker)
thread.daemon = True
thread.start()

while running:
	val = input("Cmd: ")
	if val:
		send(val)
	time.sleep(1)

ser.close()