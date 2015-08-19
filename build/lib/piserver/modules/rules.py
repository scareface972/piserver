import threading, logging, os, serial, time, json
import core.controller, core.handlers
from datetime import datetime
from modules import EventManager

log_dir = '/var/log/piserver'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
logging.basicConfig(filename=log_dir+'/piserver.log', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def log(value):
	print(value)
	logging.debug(value)

class Rules():
	"""Class 'Rules': Rules analyser module"""

	def __init__(self):
		self.name = "Rules"
		self._init_rules()
		self._load_rules()
		self.thread = threading.Thread(target=self.worker)
		self.thread.daemon = True
		self.thread.start()

	def _init_rules(self):
		#log("Rules::init")
		self.rules = []
		self.conf_file = core.controller.Controller.CONF_PATH + 'rules.json'
		core.handlers.setObserver(self._load_rules, self.conf_file, core.controller.Controller.CONF_PATH)

	def _load_rules(self):
		self.rules = json.loads(open(self.conf_file).read())
		log('-> loadRules, ' + str(len(self.rules)) + ' entry in ' + self.conf_file)
		#for rule in self.rules: 
		#	log('-> rule: ' + rule['name'])

	#@property
	def get_running(self):
		return self.__running

	#@running.setter
	def set_running(self, value):
		self.__running = value

	def worker(self):
		#log("Rules::startWorker")
		self.set_running(True)
		second = 0
		while self.get_running():
			if second != datetime.now().second:
				second = datetime.now().second
				self.check_rules()
			time.sleep(.5)

	def check_rules(self):
		#log('Rules::checkRules')
		for rule in self.rules:
			if 'enabled' in rule and rule['enabled'] == False: continue
			#log('-> rule: ' + rule['name'])
			actions = []
			for condition in rule['conditions']:
				exe = False
				if 'module' in condition: 
					(exe, acts) = self._check_module(condition)
				if 'hours' in condition or 'minute' in condition or 'second' in condition:
					(exe, acts) = self._check_time(condition)
				if exe:
					if acts != None: 
						for act in acts: 
							actions.append(rule['actions'][act])
					else: 
						actions.extend(rule['actions'])
			execute = len(actions) > 0
			if execute:
				log('Rules::rule "' + rule['name'] + '" > ' + str(execute))
				for action in actions:
					#log('Rules::execute: ' + action['module'] + '/' + action['value'])
					self.controller.execute(action['module'] + '/' + action['value'])

	def _check_module(self, condition):
		if 'action' in condition and condition['action'] == -1: return False, None
		#log('-> checkModule')
		#log('--> condition: ' + str(condition))
		mod = self.controller.get_module(condition['module'])
		value = False
		if mod != None:
			value = mod.eval_rule(condition['prop'], condition['condition'], condition['value'])
			#log('--> result: ' + str(value))
		return value, None if not 'action' in condition else condition['action']

	def _check_time(self, condition):
		if 'action' in condition and condition['action'] == -1: return False, None
		#log('-> checkTime')
		#log('--> condition: ' + str(condition))
		action = None
		now = datetime.now()
		hour = condition['hour'] if 'hour' in condition else now.hour
		minute = condition['minute'] if 'minute' in condition else now.minute
		second = condition['second'] if 'second' in condition else 0
		today = datetime(now.year, now.month, now.day, hour, minute, second)
		value = today.hour == now.hour and today.minute == now.minute and today.second == now.second
		#print(today, value)
		#else:
		#	value = True
		#	if 'hour' in condition and condition['hour'] != datetime.now().hour:
		#		value = False
		#	if value and 'minute' in condition and condition['minute'] != datetime.now().minute:
		#		value = False
		#	if value and 'second' in condition and condition['second'] != datetime.now().second:
		#		value = False
		if 'action' in condition:
			action = condition['action']
		return value, action