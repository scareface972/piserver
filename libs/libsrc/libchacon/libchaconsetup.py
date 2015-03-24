from distutils.core import setup, Extension

module1 = Extension('libchacon',
                    sources = ['libchaconmodule.cpp'],
                    libraries = ['wiringPi'])

setup (name = 'Chacon',
       version = '1.0',
       description = 'This is a Lib Chacon package',
       ext_modules = [module1])