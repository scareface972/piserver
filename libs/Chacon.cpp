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
int pinIn;
int pinOut;
int emitter;
bool bit2[26] = {};              // 26 bit Identifiant emetteur
bool bit2Interruptor[4] = {};
int received[3] = {};

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


//Envois d'une pulsation (passage de l'etat haut a l'etat bas)
//1 = 310µs haut puis 1340µs bas
//0 = 310µs haut puis 310µs bas
void sendBit(bool b) {
 if (b) {
   digitalWrite(pinOut, HIGH);
   delayMicroseconds(310);   //275 orinally, but tweaked.
   digitalWrite(pinOut, LOW);
   delayMicroseconds(1340);  //1225 orinally, but tweaked.
 }
 else {
   digitalWrite(pinOut, HIGH);
   delayMicroseconds(310);   //275 orinally, but tweaked.
   digitalWrite(pinOut, LOW);
   delayMicroseconds(310);   //275 orinally, but tweaked.
 }
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
	int i;

	// Sequence de verrou anoncant le départ du signal au recepeteur
	digitalWrite(pinOut, HIGH);
	delayMicroseconds(275);     // un bit de bruit avant de commencer pour remettre les delais du recepteur a 0
	digitalWrite(pinOut, LOW);
	delayMicroseconds(9900);     // premier verrou de 9900µs
	digitalWrite(pinOut, HIGH);   // high again
	delayMicroseconds(275);      // attente de 275µs entre les deux verrous
	digitalWrite(pinOut, LOW);    // second verrou de 2675µs
	delayMicroseconds(2675);
	digitalWrite(pinOut, HIGH);  // On reviens en état haut pour bien couper les verrous des données

	// Envoie du code emetteur (272946 = 1000010101000110010  en binaire)
	for(i=0; i<26;i++) {
		sendPair(bit2[i]);
	}

	// Envoie du bit définissant si c'est une commande de groupe ou non (26em bit)
	sendPair(false);

	// Envoie du bit définissant si c'est allumé ou eteint 27em bit)
	sendPair(blnOn);

	// Envoie des 4 derniers bits, qui représentent le code interrupteur, ici 0 (encode sur 4 bit donc 0000)
	// nb: sur  les télécommandes officielle chacon, les interrupteurs sont logiquement nommés de 0 à x
	// interrupteur 1 = 0 (donc 0000) , interrupteur 2 = 1 (1000) , interrupteur 3 = 2 (0100) etc...
	for(i=0; i<4;i++) {
		if(bit2Interruptor[i]==0) {
			sendPair(false);
		} else {
			sendPair(true);
		}
	}

	digitalWrite(pinOut, HIGH);   // coupure données, verrou
	delayMicroseconds(275);      // attendre 275µs
	digitalWrite(pinOut, LOW);    // verrou 2 de 2675µs pour signaler la fermeture du signal
}

void send(int interruptor, int onoff) {
	if (onoff) printf("envois du signal ON\n");
	else printf("envois du signal OFF\n");
	string msg = "emitter: ";
	msg.append(intToString(emitter));
	msg.append(", interruptor: ");
	msg.append(intToString(interruptor));
	msg.append(", onoff: ");
	msg.append(intToString(onoff));
	log(msg);
	scheduler_realtime();
	itob(emitter,26);
	itobInterruptor(interruptor,4);
	if(onoff == 1){
		for(int i=0;i<3;i++){
			transmit(true);            // envoyer ON
			delay(10);                 // attendre 10 ms (sinon le socket nous ignore)
		}
	} else {
		for(int i=0;i<3;i++){
			transmit(false);           // envoyer OFF
			delay(10);                 // attendre 10 ms (sinon le socket nous ignore)
		}
	}
	scheduler_standard();
}

void receive() {
	Py_BEGIN_ALLOW_THREADS
	for(;;) {
		int i = 0;
		unsigned long t = 0;
		int prevBit = 0;
		int bit = 0;
		unsigned long sender = 0;
		unsigned long recipient = 0;
		int on = 0;
		string command = "";
    	do t = pulseIn(pinIn, LOW, 1000000);
		while(t < 2400 || t > 2800);
		while(i < 64) {
			t = pulseIn(pinIn, LOW, 1000000);
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
				}/*else if(i == 53) {
					group = prevBit;
				}*/ else if(i == 55) {
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
			if (sender > 0) {
				received[0] = sender;
				received[1] = recipient;
			    received[2] = on;
				break;
			}
		} else {
			delay(1);
		}
    }
    Py_END_ALLOW_THREADS
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
		printf("setuid error\n");
		return NULL;
	}

	int interruptor;
	int onoff;

	if (!PyArg_ParseTuple(args, "iiii", &pinOut, &emitter, &interruptor, &onoff)) {
		printf("Parsing args error");
		return NULL;
	}

	printf("args %d, %d, %d, %d\n", pinOut, emitter, interruptor, onoff);

	if (wiringPiSetup() == -1) {
		printf("Librairie Wiring PI introuvable, veuillez lier cette librairie...");
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
    log("Starting thread...");
    
    pinMode(pinIn, INPUT);
    pinMode(pinOut, OUTPUT);
	
	int sended[5] = {};
	sended[0] = sended[1] = sended[2] = sended[3] = sended[4] = 0;
	for(;;) {
		received[0] = received[1] = received[2] = 0;
		receive();
		//cout << "received " << received[0] << " " << received[1] << " " << received[2] << endl;
		//cout << "sended " << sended[0] << " " << sended[1] << " " << sended[2] << endl;
		if (received[0] > 0 && (sended[0] != received[0] || sended[1] != received[1] || sended[2] != received[2])) {
			string name = "";
			//PyGILState_STATE gstate = PyGILState_Ensure();
			PyObject *arglist = Py_BuildValue("(i,i)", received[0], received[1]);
			PyObject *ret = PyEval_CallObject(callback, arglist);
			if (ret == NULL) log("PyEval_CallObject failed");
            else {
            	PyArg_Parse(ret, "(ii)", &sended[3], &sended[4]);
            	Py_DECREF(ret);
            }
            Py_DECREF(arglist);
            //PyGILState_Release(gstate);
            cout << "interruptor " << sended[3] << " " << sended[4] << endl;
            if (sended[3] > 0) {
				sended[0] = received[0];
				sended[1] = received[1];
				sended[2] = received[2];
				send(sended[3], sended[4]);
			}
		}
    }

	return Py_BuildValue("i", 1);
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