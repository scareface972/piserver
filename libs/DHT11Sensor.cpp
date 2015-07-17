#include <Python.h>
#include <wiringPi.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#define MAX_TIME 85

//static int DEFAULT_VALUES[5] = {0,0,0,0,0};
float celcius = 0, humidity = 0, fahrenheit = 0;

static PyObject *DHT11SensorError;
static PyObject * DHT11Sensor_get(PyObject *self, PyObject *args);

static PyMethodDef DHT11SensorMethods[] = {
	{"get",  DHT11Sensor_get, METH_VARARGS, "Retreview DHT11Sensor data."}
};

static struct PyModuleDef DHT11Sensor_module = {
   PyModuleDef_HEAD_INIT,
   "DHT11Sensor",   /* name of module */
   NULL, 	/* module documentation, may be NULL */
   -1,      /* size of per-interpreter state of the module, or -1 if the module keeps state in global variables. */
   DHT11SensorMethods
};

PyMODINIT_FUNC
PyInit_DHT11Sensor(void) {
	PyObject *m;

	m = PyModule_Create(&DHT11Sensor_module);
	if (m == NULL)
		return NULL;

	DHT11SensorError = PyErr_NewException("DHT11Sensor.error", NULL, NULL);
	Py_INCREF(DHT11SensorError);
	PyModule_AddObject(m, "error", DHT11SensorError);
	return m;
}

static PyObject * DHT11Sensor_get(PyObject *self, PyObject *args) {
	int pin;
	uint8_t lststate = HIGH;
	uint8_t counter = 0;
	uint8_t j = 0, i;

	if (!PyArg_ParseTuple(args, "i", &pin))
		return NULL;

	if (wiringPiSetup() == -1) 
		return NULL;

	//do {
		int checksum = -1;
		int dht11_val[5] = {0,0,0,0,0};

		pinMode(pin, OUTPUT);
		digitalWrite(pin, LOW);
		delay(18);

		digitalWrite(pin, HIGH);
		delayMicroseconds(40);
		pinMode(pin, INPUT);

		for(i=0; i<MAX_TIME; i++) {
			counter=0;
			while(digitalRead(pin) == lststate) {
				counter++;
				delayMicroseconds(1);
				if(counter == 255) break;
			}
			lststate = digitalRead(pin);
			if(counter == 255) break;
			// top 3 transistions are ignored
			if(i>=4 && i%2==0){
				dht11_val[j/8] <<= 1;
				if(counter > 16) dht11_val[j/8] |= 1;
				j++;
			}
		}
		// printf("Data (%d): 0x%x 0x%x 0x%x 0x%x 0x%x\n", j, dht11_val[0], dht11_val[1], dht11_val[2], dht11_val[3], dht11_val[4]);
		// verify cheksum and print the verified data
		checksum = (dht11_val[0]+dht11_val[1]+dht11_val[2]+dht11_val[3]) & 0xFF;
		// printf("dht11[4]: %d\n", dht11_val[4]);
		// printf("Checksum: %d\n", checksum);
		if (j >= 40 && dht11_val[4] == checksum && (dht11_val[0] > 0 || dht11_val[1] > 0)) {
			char h[20], c[20], f[20];
			sprintf(h, "%d.%d", dht11_val[0], dht11_val[1]);
			sprintf(c, "%d.%d", dht11_val[2], dht11_val[3]);
			sprintf(f, "%.1f", celcius * 9.0 / 5.0 + 32);
			float hu = atof(h);
			float cl = atof(c);
			float fa = atof(f);
			if (cl > 0 && hu > 0) {
				humidity = hu;
				celcius = cl;
				fahrenheit = fa;
			}
		}
		//delay(500);
		//memcpy(dht11_val, DEFAULT_VALUES, 5*sizeof(int));
	//} while (celcius == 0 || humidity == 0);
	return Py_BuildValue("(f, f, f)", humidity, celcius, fahrenheit);
}