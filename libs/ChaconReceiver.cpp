#include <Python.h>
#include <wiringPi.h>
#include <iostream>
#include <sys/time.h>
#include <time.h>
#include <sched.h>
#include <sstream>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

using namespace std;
int pin;

void scheduler_realtime() {
	struct sched_param p;
	p.__sched_priority = sched_get_priority_max(SCHED_RR);
	if( sched_setscheduler( 0, SCHED_RR, &p ) == -1 ) {
		perror("Failed to switch to realtime scheduler.");
	}
}

void scheduler_standard() {
	struct sched_param p;
	p.__sched_priority = 0;
	if( sched_setscheduler( 0, SCHED_OTHER, &p ) == -1 ) {
		perror("Failed to switch to normal scheduler.");
	}
}

void log(string a) {
	cout << a << endl;
}

string longToString(long mylong) {
	string mystring;
	stringstream mystream;
	mystream << mylong;
	return mystream.str();
}
string intToString(int myint) {
	string mystring;
	stringstream mystream;
	mystream << myint;
	return mystream.str();
}

int pulseIn(int pin, int level, int timeout) {
	struct timeval tn, t0, t1;
	long micros;
	gettimeofday(&t0, NULL);
	micros = 0;
	while (digitalRead(pin) != level) {
		gettimeofday(&tn, NULL);
		if (tn.tv_sec > t0.tv_sec) micros = 1000000L; else micros = 0;
		micros += (tn.tv_usec - t0.tv_usec);
		if (micros > timeout) return 0;
	}
	gettimeofday(&t1, NULL);
	while (digitalRead(pin) == level) {
		gettimeofday(&tn, NULL);
		if (tn.tv_sec > t0.tv_sec) micros = 1000000L; else micros = 0;
		micros = micros + (tn.tv_usec - t0.tv_usec);
		if (micros > timeout) return 0;
	}
	if (tn.tv_sec > t1.tv_sec) micros = 1000000L; else micros = 0;
	micros = micros + (tn.tv_usec - t1.tv_usec);
	return micros;
}

static PyObject *callback = NULL;
static PyObject *ChaconReceiverError;
static PyObject * ChaconReceiver_setCallback(PyObject *self, PyObject *args);
static PyObject * ChaconReceiver_run(PyObject *self, PyObject *args);

static PyMethodDef ChaconReceiverMethods[] = {
	{"setCallback",  ChaconReceiver_setCallback, METH_VARARGS, "Configure callback"},
	{"run",  ChaconReceiver_run, METH_VARARGS, "Start listen 433.92MHz Chacon message."}
};

static struct PyModuleDef ChaconReceiver_module = { PyModuleDef_HEAD_INIT, "ChaconReceiver", NULL, -1, ChaconReceiverMethods };

PyMODINIT_FUNC
PyInit_ChaconReceiver(void) {
	PyObject *m;

	m = PyModule_Create(&ChaconReceiver_module);
	if (m == NULL)
		return NULL;

	ChaconReceiverError = PyErr_NewException("ChaconReceiver.error", NULL, NULL);
	Py_INCREF(ChaconReceiverError);
	PyModule_AddObject(m, "error", ChaconReceiverError);
	return m;
}

static PyObject * ChaconReceiver_run(PyObject *self, PyObject *args) {
	if (setuid(0)) {
		log("Error: setuid");
		return NULL;
	}
	if (!PyArg_ParseTuple(args, "i", &pin)) {
		log("Error:Parsing args");
		return NULL;
	}
	if(wiringPiSetup() == -1) {
        log("Error: Librairie Wiring PI introuvable, veuillez lier cette librairie...");
        return NULL;
    }
    pinMode(pin, INPUT);
	scheduler_realtime();
	for(;;) {
		Py_BEGIN_ALLOW_THREADS
    	int i = 0;
		unsigned long t = 0;
		int prevBit = 0;
		int bit = 0;
		unsigned long sender = 0;
		bool group = false;
		bool on = false;
		unsigned long recipient = 0;
		//string command = "";
		do t = pulseIn(pin, LOW, 1000000);
		while(t < 2400 || t > 2800);
		while(i < 64) {
			t = pulseIn(pin, LOW, 1000000);
			if(t > 300 && t < 360) bit = 0;
			else if(t > 1200 && t < 1500) bit = 1;
			else {
				i = 0;
				break;
			}
			if (i % 2 == 1) {
				if((prevBit ^ bit) == 0) {
					i = 0;
					break;
				}
				if(i < 53) {
					sender <<= 1;
					sender |= prevBit;
				} else if(i == 53) {
					group = prevBit;
				} else if(i == 55) {
					on = prevBit;
				} else {
					recipient <<= 1;
					recipient |= prevBit;
				}
			}
			prevBit = bit;
			++i;
		}
		if (i>0) {
			/*command.append(longToString(sender));
			if(on) command.append(" on");
			else command.append(" off");
			command.append(" "+longToString(recipient));
			log(command.c_str());*/
			PyObject *arglist;
			arglist = Py_BuildValue("(i,i,i,i)", sender, group, on, recipient);
			PyEval_CallObject(callback, arglist);
			Py_DECREF(arglist);
			delay(500);
		}
		delay(1);
    	Py_END_ALLOW_THREADS
    }
	
	scheduler_standard();

	return Py_BuildValue("i", 1);
}

static PyObject * ChaconReceiver_setCallback(PyObject *self, PyObject *args) {
    PyObject *result = NULL;
    PyObject *temp;

    if (PyArg_ParseTuple(args, "O:setCallback", &temp)) {
        if (!PyCallable_Check(temp)) {
            PyErr_SetString(PyExc_TypeError, "parameter must be callable");
            return NULL;
        }
        Py_XINCREF(temp);
        Py_XDECREF(callback);
        callback = temp;
        Py_INCREF(Py_None);
        result = Py_None;
    }
    return result;
}