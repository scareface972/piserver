import modules
import wiringpi2 as wpi

wpi.wiringPiSetup()

# Tableau des modules (classe) dispo (pour eviter le parsage du document lors du chargement dynamique des modules)
MODULES = ['Output']

class Output(modules.Switch):
    """Class 'Item' pour interagir les sorties GPIO"""

    def __init__(self, conf):
        self.pin = conf['pin']
        key = conf['name']
        if 'group' in conf: key += "|"+conf['group']+"s?"
        # Initialisation des commandes disponibles
        cmds = {
            'toggle' : key,
            'on': "allumer?\s(\w+\s)?("+key+")+",
            'off': "(etein(dre|s))\s(\w+\s)?("+key+")+"
        }
        super().__init__(conf, cmds)

    def execute(self, cmd):
        # Exécution de commande avec la librairie wiringPi
        # https://projects.drogon.net/raspberry-pi/wiringpi/
        result = dict(success=False, name=self.name, state=self.state)
        try:
            if cmd == 'toggle': new_state = not self.state
            elif cmd == 'on': new_state = True
            elif cmd == 'off': new_state = False
            if self.state != new_state:
                wpi.digitalWrite(self.pin, 1 if new_state else 0)
                self.state = new_state
                result['state'] = new_state
            result['success'] = True
        except:
            pass
        return result

# TODO: Il faudrait également gérer les entrées...