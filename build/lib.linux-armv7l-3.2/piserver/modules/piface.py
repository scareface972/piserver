import modules.gpio
import wiringpi2 as wpi

# Les pin sur la piface sont décalé avec wiringPi
PIN_BASE = 200
wpi.piFaceSetup(PIN_BASE)

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['PifaceRelay', 'PifaceLED']

# Relay 220v de la carte
class PifaceRelay(modules.gpio.GPIOOutput):
	"""Class 'PifaceRelay' pour interagir avec les relay PiFace Digital"""

	def __init__(self, conf):
		conf['pin'] += PIN_BASE
		super().__init__(conf)

# LED de contrôle de la carte
class PifaceLED(modules.gpio.GPIOOutput):
	"""Class 'PifaceLED' pour interagir avec les LED PiFace Digital"""

	def __init__(self, conf):
		conf['pin'] += PIN_BASE
		super().__init__(conf)

# TODO: Ajouter une classe pour les boutons