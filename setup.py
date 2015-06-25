#!/usr/bin/env python3
import os, sys, fileinput, site
from setuptools.command.install import install as installer
from setuptools import setup, Extension
from subprocess import call

os.environ["CC"]  = "g++-4.6"
os.environ["CXX"] = "g++-4.6"

def read(fname):
	return open(os.path.join(os.path.dirname(__file__), fname)).read()

class install(installer):
	def run(self):
		installer.run(self)
		filename = '/etc/init.d/piserver'
		path = site.getsitepackages()[0]
		s = open(filename).read()
		s = s.replace('{user_local_lib_python}', path)
		f=open(filename, 'w')
		f.write(s)
		f.flush()
		f.close()
		filename = path + '/piserver/piserver.py'
		os.chmod(filename, 0o755)
		#call(["update-rc.d", "piserver", "remove"])
		call(["update-rc.d", "piserver", "defaults", "20", "1"])

dht11 = Extension('DHT11Sensor',
					sources = ['libs/DHT11Sensor.cpp'],
					libraries = ['wiringPi'])

chacon = Extension('Chacon',
					sources = ['libs/Chacon.cpp'],
					libraries = ['wiringPi'])

setup(name='PiServer',
		version='1.1',
		description='PiServer is domotic server for Chacon Interruptor, Freebox, Temp Sensor that expose data by web interface and api',
		long_description=read('README.md'),
		author='Benjamin Touchard',
		author_email='benjamin@kolapsis.com',
		url='http://www.kolapsis.com/',
		packages=['piserver', 'piserver.core', 'piserver.modules'],
		package_dir={'piserver': 'src'},
		include_package_data=True,
		package_data={
			'static':['src/static/*'],
			'views':['src/views/*'],
			'imgs':['src/imgs/*']
		},
		ext_modules=[dht11, chacon],
		data_files=[('piserver', ['src/config.json', 'src/rules.json', 'src/chacon.json', 'src/alarms.json']),
					('/etc/init.d', ['src/piserver'])],
		cmdclass={'install': install},
	)
