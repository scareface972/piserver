#include <wiringPi.h>
#include <iostream>
#include <stdio.h>
#include <sys/time.h>
#include <time.h>
#include <stdlib.h>
#include <sstream>
#include <string>

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

void logBit(int i, int b, unsigned long t) {
	cout << "i = " << i << ", bit = " << b << ", t = " << t << endl;
}

int main (int argc, char** argv) {
	pin = atoi(argv[1]);
	if(wiringPiSetup() == -1) {
		log("Error: Librairie Wiring PI introuvable, veuillez lier cette librairie...");
		return -1;
	}
	pinMode(pin, INPUT);
	scheduler_realtime();
	for(;;) {
		int i = 0;
		unsigned long t = 0, prevTime = 0;
		int prevBit = 0;
		int bit = 0;
		unsigned long sender = 0;
		bool group= false;
		bool on = false;
		unsigned long recipient = 0;
		string command = "", seq = "";
		//do t = pulseIn(pin, LOW, 1000000);
		//while(t < 2400 || t > 2800);
		//cout << "verou, t = " << t << endl;
		//while(i < 64) {
		bit = -1;
		t = pulseIn(pin, LOW, 1000000);
		//cout << "i = " << i << ", t = " << t << endl;
		if(t > 270 && t < 400) bit = 0;
		else if(t > 1200 && t < 1500) bit = 1;
		if (i > 0) {
			if (i == 1) {
				//logBit(0, prevBit, prevTime);
				seq.append(intToString(prevBit));
			}
			//logBit(i, bit, t);
			seq.append(intToString(bit));
		}
		if (bit != -1) {
			//cout << "t = " << t << endl;
			//if (seq.size() > 0) log(seq.c_str());
			/*i = 0;
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
			}*/
			prevBit = bit;
			prevTime = t;
			++i;
		}
		//}
		if (i>0) {
			log(seq.c_str());
			/*command.append(longToString(sender));
			if(on) command.append(" on");
			else command.append(" off");
			command.append(" "+longToString(recipient));
			log(command.c_str());
			delay(100);*/
		} else {
			//if (seq.size() > 0) log(seq.c_str());
			delay(1);
		}
	}
	scheduler_standard();
}