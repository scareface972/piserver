#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, locale, sys
from core import controller

locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')

debug = False
if len(sys.argv) > 1: debug = sys.argv[1] == '-d'
# Initialisation du controller principale
ctrl = controller.Controller(debug)
# démarrage du serveur
ctrl.run()