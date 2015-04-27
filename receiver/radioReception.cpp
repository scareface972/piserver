#include <wiringPi.h>
#include <iostream>
#include <stdio.h>
#include <sys/time.h>
#include <time.h>
#include <stdlib.h>
#include <sstream>
#include <string>
#include <curl/curl.h>

using namespace std;
int pin;

struct Interruptor {
	string name;
	long sender;
	long recipient;
};

Interruptor interruptors[2] = {
	//{ "cuisine", 13552350, 0 },
	//{ "plafond", 13552350, 1 },
	{ "plafond", 15530742, 0}, 
	{ "cuisine", 15530742, 1}
};

static string readBuffer;
static size_t writeCallback(char *contents, size_t size, size_t nmemb, void *userp) {
	size_t realsize = size * nmemb;
	readBuffer.append(contents, realsize);
	return realsize;
}

static string getName(long sender, long recipient) {
	int length = (sizeof(interruptors)/sizeof(*interruptors));
	for (int i=0; i<length; i++) {
		if (interruptors[i].sender == sender && interruptors[i].recipient == recipient) {
			return interruptors[i].name;
			break;
		}
	}
}

void send(const char *url) {
	CURL *curl;
	CURLcode res;
	curl = curl_easy_init();
	if(curl) {
		curl_easy_setopt(curl, CURLOPT_URL, url);
		// example.com is redirected, so we tell libcurl to follow redirection
		curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
		readBuffer.clear();
		curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeCallback);
		// Perform the request, res will get the return code 
		res = curl_easy_perform(curl);
		// Check for errors
		if(res != CURLE_OK) fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
		// always cleanup
		curl_easy_cleanup(curl);
		std::cout << readBuffer << std::endl;
	}
}

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

size_t writeToString(void *ptr, size_t size, size_t count, void *stream) {
  ((string*)stream)->append((char*)ptr, 0, size*count);
  return size*count;
}

void sendToAPI() {
	CURL* curl;
    curl_global_init(CURL_GLOBAL_ALL);
    curl = curl_easy_init();
    if (curl) {
	    curl_easy_setopt(curl, CURLOPT_URL, "http://localhost/");
	    string response;
	    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, &writeToString);
	    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
	    CURLcode res = curl_easy_perform(curl);
	    curl_easy_cleanup(curl);
	    curl_global_cleanup();
	}
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
		unsigned long t = 0;
		int prevBit = 0;
		int bit = 0;
		unsigned long sender = 0;
		bool group= false;
		bool on = false;
		unsigned long recipient = 0;
		string command = "", seq = "";
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
			seq.append(intToString(bit));
			prevBit = bit;
			++i;
		}
		if (i>0) {
			log(seq.c_str());
			command.append(longToString(sender));
			if(on) command.append(" on");
			else command.append(" off");
			command.append(" "+longToString(recipient));
			log(command.c_str());
			string name = getName(sender, recipient);
			string url = "http://192.168.0.2/exec/";
			url.append(name);
			url.append("/toggle");
			log(url);
			send(url.c_str());
			delay(10000);
		}
		delay(1);
	}
	scheduler_standard();
}