#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, locale, sys
from core import controller

locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')

# Fichier de configuration (JSON) par défaut, ou passé en argument (1er argument)
conf_file = '/usr/local/piserver/config.json' if len(sys.argv) == 1 else sys.argv[1]
# Initialisation du controller principale
ctrl = controller.Controller(conf_file)
# démarrage du serveur
ctrl.run()