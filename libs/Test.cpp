#include <Python.h>
#include <iostream>
#include <sys/time.h>
#include <time.h>
#include <sched.h>
#include <sstream>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

using namespace std;

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

string intToString(int myint) {
	string mystring;
	stringstream mystream;
	mystream << myint;
	return mystream.str();
}

static PyObject *callback = NULL;
static PyObject *TestError;
static PyObject * Test_setCallback(PyObject *self, PyObject *args);
static PyObject * Test_run(PyObject *self, PyObject *args);

static PyMethodDef TestMethods[] = {
	{"setCallback",  Test_setCallback, METH_VARARGS, "Configure callback"},
	{"run",  Test_run, METH_VARARGS, "Start listen 433.92MHz Chacon message."}
};

static struct PyModuleDef Test_module = { PyModuleDef_HEAD_INIT, "Test", NULL, -1, TestMethods };

PyMODINIT_FUNC
PyInit_Test(void) {
	PyObject *m;

	m = PyModule_Create(&Test_module);
	if (m == NULL)
		return NULL;

	TestError = PyErr_NewException("Test.error", NULL, NULL);
	Py_INCREF(TestError);
	PyModule_AddObject(m, "error", TestError);
	return m;
}

static PyObject * Test_run(PyObject *self, PyObject *args) {
	if (setuid(0)) {
		log("Error: setuid");
		return NULL;
	}
    log("Starting thread...");
	
	PyObject *arglist;
	PyObject *ret;
	PyGILState_STATE gstate;
    
	scheduler_realtime();
	
	Py_BEGIN_ALLOW_THREADS
	int i = 0;
	for(;;i++) {
		string command = "i = ";
		command.append(intToString(i));
		log(command.c_str());
		gstate = PyGILState_Ensure();
		arglist = Py_BuildValue("(k, i)", i, i);
		ret = PyEval_CallObject(callback, arglist);
		if (ret == NULL) log("PyEval_CallObject failed");
        else Py_DECREF(ret);
		Py_DECREF(arglist);
		PyGILState_Release(gstate);
		log("sended");
		sleep(1);
    }
    Py_END_ALLOW_THREADS
	
	scheduler_standard();

	return Py_BuildValue("i", 1);
}

static PyObject * Test_setCallback(PyObject *self, PyObject *args) {
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
        log("Callback defined");
    }
    return result;
}