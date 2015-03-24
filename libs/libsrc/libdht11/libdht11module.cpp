#include <Python.h>
#include <wiringPi.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#define MAX_TIME 85

static int DEFAULT_VALUES[5] = {0,0,0,0,0};

static PyObject *DHT11Error;
static PyObject * dht11_get(PyObject *self, PyObject *args);

static PyMethodDef DHT11Methods[] = {
	{"get",  dht11_get, METH_VARARGS, "Retreview DHT11 data."}
};

static struct PyModuleDef dht11module = {
   PyModuleDef_HEAD_INIT,
   "dht11",   /* name of module */
   NULL, 	/* module documentation, may be NULL */
   -1,      /* size of per-interpreter state of the module,
				or -1 if the module keeps state in global variables. */
   DHT11Methods
};

PyMODINIT_FUNC
PyInit_dht11(void) {
	PyObject *m;

	m = PyModule_Create(&dht11module);
	if (m == NULL)
		return NULL;

	DHT11Error = PyErr_NewException("dht11.error", NULL, NULL);
	Py_INCREF(DHT11Error);
	PyModule_AddObject(m, "error", DHT11Error);
	return m;
}

static PyObject * dht11_get(PyObject *self, PyObject *args) {
	int pin;
	uint8_t lststate = HIGH;
	uint8_t counter = 0;
	uint8_t j = 0, i;
	float farenheit;
	int checksum = -1;
	int dht11_val[5] = {0,0,0,0,0};

	if (!PyArg_ParseTuple(args, "i", &pin))
		return NULL;

	if (wiringPiSetup() == -1) 
		return NULL;

	while (checksum != dht11_val[4]) {
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
		if(j>=40 && (dht11_val[4] == checksum)) {
			farenheit = dht11_val[2] * 9.0 / 5.0 + 32;
			// printf("Humidity = %d.%d %% Temperature = %d.%d *C (%.1f *F)\n",dht11_val[0],dht11_val[1],dht11_val[2],dht11_val[3],farenheit);
			char h[20], c[20], f[20];
			sprintf(h, "%d.%d", dht11_val[0], dht11_val[1]);
			sprintf(c, "%d.%d", dht11_val[2], dht11_val[3]);
			sprintf(f, "%.1f", farenheit);
			return Py_BuildValue("(f, f, f)", atof(h), atof(c), atof(f));
		}
		delay(100);
		memcpy(dht11_val, DEFAULT_VALUES, 5*sizeof(int));
	}
	return Py_BuildValue("(f, f, f)", 0, 0, 0);
}