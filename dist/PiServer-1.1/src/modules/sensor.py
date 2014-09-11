import modules
import libdht11
import time
import smbus

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['DHT11', 'BH1750FVI']

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
			time.sleep(1)
		result = dict(success=False, name=self.name)
		if cmd == 'temp' or cmd == 'all':
			result['success'] = True
			result['temp_c'] = c
			result['temp_f'] = f
		if cmd == 'humidity' or cmd == 'all':
			result['success'] = True
			result['humidity'] = h
		return result

class BH1750FVI(modules.Module):
	"""Class 'BH1750FVI' pour le catpeur de liminosité BH1750FVI"""

	def __init__(self, conf):
		self.pin = conf['pin']
		cmds = { 'lux': None }
		self.lux = 0
		super().__init__(conf, cmds)

	def get(self):
		self.load()
		return self.lux

	def execute(self, cmd):
		result = dict(success=False, name=self.name)
		if cmd == 'lux':
			self.load()
			result['success'] = True
			result['lux'] = round(self.lux, 2)
		return result

	def load(self):
		bus = smbus.SMBus(1)
		addr = 0x23
		self.lux = 0
		while self.lux == 0:
			data = bus.read_i2c_block_data(addr,0x11)
			self.lux = (data[1] + (256 * data[0])) / 1.2
			time.sleep(1)