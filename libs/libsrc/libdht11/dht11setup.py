from distutils.core import setup, Extension

module1 = Extension('dht11',
                    sources = ['dht11module.cpp'],
                    libraries = ['wiringPi'])

setup (name = 'DHT11',
       version = '1.0',
       description = 'This is a DHT11 sensor package',
       ext_modules = [module1])