import subprocess, sys

p = ["/home/pi/piserver/receiver/receiver", "2"]
process = None

def createProcess():
	try:
		process = subprocess.Popen(p, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	except:
		print ("Echec de la creation du subprocess", sys.exc_info())
		exit()
	return process

def run(process):
	while True:
		try:
			output = process.stdout.readline()
		except:
			# print ("Unexpected error:", sys.exc_info())
			killProcess(process)
		else:
			out = output.decode()
			if out != "": print (out.strip())

def killProcess(proc):
	# print ("terminate process %s" % proc.pid)
	proc.terminate()
	sleep(1)
	if proc.wait() == None:
		while proc.poll() == None:
			proc.kill()
			sleep(1)
	process = createProcess()
	run(process)

process = createProcess()
run(process)

#subprocess.call([cmd, "2"])
#subprocess.call(["ls", "-la"])