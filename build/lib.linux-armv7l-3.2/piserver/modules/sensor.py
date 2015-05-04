import modules
import DHT11Sensor
import time
import smbus

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['DHT11', 'BH1750FVI']

class DHT11(modules.Module):
	"""Class 'DHT11' pour le catpeur de température et humidité DHT11"""

	def __init__(self, conf):
		cmds = { 'temp': None, 'humidity': None, 'all': None }
		super().__init__(conf, cmds)
		self.pin = conf['pin']
		self.value = dict(success=False, name=self.name)

	def execute(self, cmd):
		#print(cmd)
		h = 0
		c = 0
		h, c, f = DHT11Sensor.get(self.pin)
		self.value['success'] = False
		if cmd == 'temp' or cmd == 'all':
			self.value['success'] = True
			self.value['temp_c'] = c
			self.value['temp_f'] = f
		if cmd == 'humidity' or cmd == 'all':
			self.value['success'] = True
			self.value['humidity'] = h
		return self.value

	def evalRule(self, prop, condition, value):
		# print("evalRule", self.module_name, prop, condition, value)
		if prop in self.value:
			v = self.value[condition]
			return eval(str(v) + " " + condition + " " + str(value))
		return False

class BH1750FVI(modules.Module):
	"""Class 'BH1750FVI' pour le catpeur de luminosité BH1750FVI"""

	def __init__(self, conf):
		self.pin = conf['pin']
		cmds = { 'lux': None }
		self.lux = 0
		super().__init__(conf, cmds)

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
		try:
			data = bus.read_i2c_block_data(addr,0x11)
			self.lux = (data[1] + (256 * data[0])) / 1.2
		except:
			pass

	def evalRule(self, prop, condition, value):
		# print("evalRule", self.module_name, prop, condition, value)
		if prop == 'lux':
			return eval(str(self.lux) + " " + condition + " " + str(value))
		return False
