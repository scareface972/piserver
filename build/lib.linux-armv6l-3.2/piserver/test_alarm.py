#!/usr/bin/python
# -*- coding: utf-8 -*-

from modules import alarm
import time

#print(str(time.time()))
now = time.time()
am = alarm.AlarmsManager()
a = alarm.Alarm("réveil", now+10)
am.append(a)