import modules
import libdht11
from time import sleep

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['DHT11']

class DHT11(modules.Module):
	"""Class 'DHT11' pour le catpeur de température et humidité DHT11"""

	def __init__(self, conf):
		self.pin = conf['pin']
		cmds = { 'temp': None, 'humidity': None, 'all': None }
		super().__init__(conf, cmds)

	def execute(self, cmd):
		#print(cmd)
		h = 0
		c = 0
		while h == 0 or c == 0:
			h, c, f = libdht11.get(self.pin)
			sleep(1)
		result = dict(success=False, name=self.name)
		if cmd == 'temp' or cmd == 'all':
			result['success'] = True
			result['temp_c'] = c
			result['temp_f'] = f
		if cmd == 'humidity' or cmd == 'all':
			result['success'] = True
			result['humidity'] = h
		return result