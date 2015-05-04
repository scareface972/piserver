#include <iostream>
#include <stdio.h>
#include <stdlib.h>
#include <sstream>
#include <string>
#include <curl/curl.h>

struct Interruptor {
	std::string name;
	long sender;
	long recipient;
};

Interruptor interruptors[2] = {
	{ "cuisine", 13552350, 0 },
	{ "plafond", 13552350, 1 }
};

static std::string readBuffer;
static size_t writeCallback(char *contents, size_t size, size_t nmemb, void *userp) {
	size_t realsize = size * nmemb;
	readBuffer.append(contents, realsize);
	return realsize;
}

static std::string getName(long sender, long recipient) {
	for (int i=0; i<2; i++) {
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
		if(res != CURLE_OK)
			fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
		// always cleanup
		curl_easy_cleanup(curl);
		std::cout << readBuffer << std::endl;
	}
}

int main(void) {
	long cs = 13552350, cr = 0;
	std::string name = getName(cs, cr);
	std::cout << name << std::endl;
	std::string url = "http://192.168.0.2/exec/chacon/";
	url.append(name);
	url.append("/toggle");
	std::cout << url << std::endl;
	send(url.c_str());
	return 0;
}