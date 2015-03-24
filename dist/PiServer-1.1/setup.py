#!/usr/bin/env python
import os, fileinput, site
from setuptools.command.install import install as installer
from distutils.core import setup, Extension

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
		

dht11 = Extension('libdht11',
					sources = ['libs/libdht11.cpp'],
					libraries = ['wiringPi'])

chacon = Extension('libchacon',
					sources = ['libs/libchacon.cpp'],
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
			'views':['src/views/*']
		},
		ext_modules=[dht11, chacon],
		data_files=[('piserver', ['src/config.json']),
				  ('/etc/init.d', ['src/piserver'])],
		#entry_points={'console_scripts': ['piserver = piserver.piserver:main']},
		cmdclass={'install': install},
	)
