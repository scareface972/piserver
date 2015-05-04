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
#include <ctime>
#include <curl/curl.h>

using namespace std;
int pinIn;
int pinOut;
bool bit2[26] = {};              // 26 bit Identifiant emetteur
bool bit2Interruptor[4] = {};
unsigned int emitter;
unsigned int received[4] = {};
bool scheduler_set = false;

void log(string a) {
	cout << a << endl;
}

void scheduler_realtime() {
	//log("-> pass to realtime");
	struct sched_param p;
	p.__sched_priority = sched_get_priority_max(SCHED_RR);
	if( sched_setscheduler( 0, SCHED_RR, &p ) == -1 ) {
		perror("Failed to switch to realtime scheduler.");
	}
}

void scheduler_standard() {
	//log("-> pass to standard");
	struct sched_param p;
	p.__sched_priority = 0;
	if( sched_setscheduler( 0, SCHED_OTHER, &p ) == -1 ) {
		perror("Failed to switch to normal scheduler.");
	}
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

//Calcul le nombre 2^chiffre indiqué, fonction utilisé par itob pour la conversion decimal/binaire
unsigned long power2(int power) {
	unsigned long integer=1;
	for (int i=0; i<power; i++){
		integer*=2;
	}
	return integer;
} 

//Convertis un nombre en binaire, nécessite le nombre, et le nombre de bits souhaité en sortie (ici 26)
// Stocke le résultat dans le tableau global "bit2"
void itob(unsigned long integer, int length) {
	for (int i=0; i<length; i++){
		if ((integer / power2(length-1-i))==1){
			integer-=power2(length-1-i);
			bit2[i]=1;
		} else bit2[i]=0;
	}
}

void itobInterruptor(unsigned long integer, int length) {
	for (int i=0; i<length; i++){
		if ((integer / power2(length-1-i))==1){
			integer-=power2(length-1-i);
			bit2Interruptor[i]=1;
		} else bit2Interruptor[i]=0;
	}
}

int DELAY_DOWN = 275;
int DELAY_UP   = 1225;
int DELAY_VEROU1 = 9900;
int DELAY_VEROU2 = 2675;

//Envois d'une pulsation (passage de l'etat haut a l'etat bas)
//1 = 310µs haut puis 1340µs bas
//0 = 310µs haut puis 310µs bas
void sendBit(bool b) {
 if (b) {
   digitalWrite(pinOut, HIGH);
   delayMicroseconds(DELAY_DOWN);   //275 orinally, but tweaked.
   digitalWrite(pinOut, LOW);
   delayMicroseconds(DELAY_UP);  //1225 orinally, but tweaked.
 }
 else {
   digitalWrite(pinOut, HIGH);
   delayMicroseconds(DELAY_DOWN);   //275 orinally, but tweaked.
   digitalWrite(pinOut, LOW);
   delayMicroseconds(DELAY_DOWN);   //275 orinally, but tweaked.
 }
}

//Envoie d'une paire de pulsation radio qui definissent 1 bit réel : 0 =01 et 1 =10
//c'est le codage de manchester qui necessite ce petit bouzin, ceci permet entre autres de dissocier les données des parasites
void sendPair(bool b) {
	if(b) {
		sendBit(true);
		sendBit(false);
	} else {
		sendBit(false);
		sendBit(true);
	}
}

//Fonction d'envois du signal
//recoit en parametre un booleen définissant l'arret ou la marche du matos (true = on, false = off)
void transmit(int blnOn) {
	// Sequence de verrou anoncant le départ du signal au recepeteur
	digitalWrite(pinOut, HIGH);
	delayMicroseconds(DELAY_DOWN);     // un bit de bruit avant de commencer pour remettre les delais du recepteur a 0
	digitalWrite(pinOut, LOW);
	delayMicroseconds(DELAY_VEROU1);     // premier verrou de 9900µs
	digitalWrite(pinOut, HIGH);   // high again
	delayMicroseconds(DELAY_DOWN);      // attente de 275µs entre les deux verrous
	digitalWrite(pinOut, LOW);    // second verrou de 2675µs
	delayMicroseconds(DELAY_VEROU2);
	digitalWrite(pinOut, HIGH);  // On reviens en état haut pour bien couper les verrous des données

	int i;
	for(i=0; i<26;i++) sendPair(bit2[i]);
	sendPair(false);
	sendPair(blnOn);
	for(i=0; i<4;i++) sendPair(bit2Interruptor[i]);

	digitalWrite(pinOut, HIGH);   // coupure données, verrou
	delayMicroseconds(DELAY_DOWN);      // attendre 275µs
	digitalWrite(pinOut, LOW);    // verrou 2 de 2675µs pour signaler la fermeture du signal
}

void send(int interruptor, int onoff) {
	//string msg = "-> emitter: ";
	//msg.append(intToString(emitter));
	//msg.append(", interruptor: ");
	//msg.append(intToString(interruptor));
	//msg.append(", onoff: ");
	//msg.append(intToString(onoff));
	//log(msg);
	if (!scheduler_set) scheduler_realtime();
	Py_BEGIN_ALLOW_THREADS
	//struct timeval tv;
	//gettimeofday(&tv,NULL);
	//unsigned long tb = 1000000 * tv.tv_sec + tv.tv_usec;
	itob(emitter,26);
	itobInterruptor(interruptor,4);
	int cnt = 3;
	for(int i=0;i<cnt;i++){
		transmit(onoff == 1);
		delay(10);
	}
	//gettimeofday(&tv,NULL);
	//unsigned long te = 1000000 * tv.tv_sec + tv.tv_usec;
    //cout << cnt << " transmit in " << te-tb << " ms" << endl;
    Py_END_ALLOW_THREADS
	if (!scheduler_set) scheduler_standard();
}

void receive() {
	for(;;) {
		int i = 0;
		unsigned long t = 0;
		int prevBit = 0;
		int bit = 0;
		unsigned int sender = 0;
		unsigned int recipient = 0;
		unsigned int group = 0, on = 0;
		string command = "";
    	do t = pulseIn(pinIn, LOW, 1000000);
		while(t < 2400 || t > 2800);
		while(i < 64) {
			t = pulseIn(pinIn, LOW, 1000000);
			if(t > 270 && t < 360) bit = 0;
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
			if (sender > 0 && sender != emitter && (received[0] != sender || received[1] != recipient || received[2] != group || received[3] != on)) {
				received[0] = sender;
				received[1] = recipient;
			    received[2] = group;
			    received[3] = on;
				break;
			}
		} else {
			delay(1);
		}
    }
}

static PyObject *callback = NULL;
static PyObject *ChaconError;
static PyObject * Chacon_setCallback(PyObject *self, PyObject *args);
static PyObject * Chacon_receive(PyObject *self, PyObject *args);
static PyObject * Chacon_send(PyObject *self, PyObject *args);

static PyMethodDef ChaconMethods[] = {
	{"setCallback",  Chacon_setCallback, METH_VARARGS, "Callback setter"},
	{"receive",  Chacon_receive, METH_VARARGS, "Start listen 433.92MHz Chacon message."},
	{"send",  Chacon_send, METH_VARARGS, "Send 433.92MHz Chacon message."}
};

static struct PyModuleDef Chacon_module = { PyModuleDef_HEAD_INIT, "Chacon", NULL, -1, ChaconMethods };

PyMODINIT_FUNC
PyInit_Chacon(void) {
	PyObject *m;

	m = PyModule_Create(&Chacon_module);
	if (m == NULL)
		return NULL;

	ChaconError = PyErr_NewException("Chacon.error", NULL, NULL);
	Py_INCREF(ChaconError);
	PyModule_AddObject(m, "error", ChaconError);
	return m;
}

static PyObject * Chacon_send(PyObject *self, PyObject *args) {
	if (setuid(0)) {
		log("setuid error\n");
		return NULL;
	}
	int interruptor;
	int onoff;
	if (!PyArg_ParseTuple(args, "iiii", &pinOut, &emitter, &interruptor, &onoff)) {
		log("Parsing args error");
		return NULL;
	}
	if (wiringPiSetup() == -1) {
		log("Error: Librairie Wiring PI introuvable, veuillez lier cette librairie...");
		return NULL;
	}
	pinMode(pinOut, OUTPUT);
	send(interruptor, onoff);
	return Py_BuildValue("i", onoff);
}

static PyObject * Chacon_receive(PyObject *self, PyObject *args) {
	if (setuid(0)) {
		log("Error: setuid");
		return NULL;
	}
	if (!PyArg_ParseTuple(args, "iii", &pinIn, &pinOut, &emitter)) {
		log("Error:Parsing args");
		return NULL;
	}
	if(wiringPiSetup() == -1) {
        log("Error: Librairie Wiring PI introuvable, veuillez lier cette librairie...");
        return NULL;
    }
    pinMode(pinIn, INPUT);
    pinMode(pinOut, OUTPUT);
	scheduler_realtime();
	scheduler_set = true;
	Py_BEGIN_ALLOW_THREADS
	//received[0] = received[1] = received[2] = received[3] = 0;
	for(;;) {
		//log("---> starting receiving <---");
		receive();
		//cout << "received " << received[0] << " " << received[1] << " " << received[2] << endl;
		PyGILState_STATE gstate = PyGILState_Ensure();
		PyObject *arglist = Py_BuildValue("(i,i,i,i)", received[0], received[1], received[2], received[3]);
		PyEval_CallObject(callback, arglist);
		//return arglist;
		Py_DECREF(arglist);
		PyGILState_Release(gstate);
	}
    Py_END_ALLOW_THREADS
    scheduler_standard();
    scheduler_set = false;
	return Py_BuildValue("i", 0);
}

static PyObject * Chacon_setCallback(PyObject *self, PyObject *args) {
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