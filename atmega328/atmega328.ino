#include <Timer.h>
#include <Wire.h>

#include <RemoteReceiver.h>
#include <RemoteTransmitter.h>
#include <NewRemoteReceiver.h>
#include <NewRemoteTransmitter.h>
#include <InterruptChain.h>
#include <BH1750.h>
#include <DHT.h>

int rfIn = 2;
int rfOut = 3;
int tmpPin = 4;
int ledIn = 7;
int ledOut = 8;

Timer timer;
BH1750 lightMeter;
DHT tempMeter(tmpPin, DHT11);

long senderCode = 0;
char separator = '\n';
String rpiCmd = "";

uint16_t lux;
float tmp = 0, hum = 0;

void setup() {
  blinkLed(ledOut);
  Serial.begin(9600);
  
  lightMeter.begin();
  tempMeter.begin();
  timer.every(600000, readSensors);
  
  RemoteReceiver::init(-1, rfIn, receiveOldCode);
  NewRemoteReceiver::init(-1, rfIn, receiveNewCode);
  InterruptChain::setMode(0, CHANGE);
  InterruptChain::addInterruptCallback(0, RemoteReceiver::interruptHandler);
  InterruptChain::addInterruptCallback(0, NewRemoteReceiver::interruptHandler);
  
  Serial.println("Ready !!");
}

void loop() {
  timer.update();
  char chr;
  while (Serial.available()) {
    chr = (char) Serial.read();
    if (chr != separator) {
      rpiCmd += chr;
    } else {
      parseRPiCommand(rpiCmd);
      rpiCmd = "";
    }
  }
}

void parseRPiCommand(String data) {
  //Serial.print("RPi Command: ");
  //Serial.println(data);
  int i1 = data.indexOf("-");
  String part = data.substring(0, i1);
  int cmd = part.toInt();
  if (cmd == 1) {
    part = data.substring(i1+1);
    senderCode = part.toInt();
    Serial.print("Sender code defined: ");
    Serial.println(senderCode);
  } else if (cmd == 2) {
    int i2 = data.indexOf("-", i1+1);
    part = data.substring(i1+1, i2);
    int protocol = part.toInt();
    if (protocol == 1) {
      part = data.substring(i2+1);
      long code = part.toInt();
      Serial.print("Send v1 code: ");
      Serial.println(code);
      sendV1(code);
    } else if (protocol == 2) {
      int i3 = data.indexOf("-", i2+1);
      part = data.substring(i2+1, i3);
      int unit = part.toInt();
      int i4 = data.indexOf("-", i3+1);
      part = data.substring(i3+1, i4);
      bool state = part.toInt();
      part = data.substring(i4+1);
      unsigned int repeat = part.toInt();
      Serial.print("Send v2 unit: ");
      Serial.print(unit);
      Serial.print(", state: ");
      Serial.print(state);
      Serial.print(", repeat: ");
      Serial.println(repeat);
      sendV2(unit, state, repeat);
    }
  } else if (cmd == 3) {
    readSensors();
  } else {
    Serial.println("0-Unknown command");
  }
}

void receiveOldCode(unsigned long receivedCode, unsigned int period) {
  blinkLed(ledIn);
  String result = "2-1-";
  result += receivedCode;
  Serial.println(result);
}

void receiveNewCode(NewRemoteCode receivedCode) {
  blinkLed(ledIn);
  String result = "2-2-";
  result += receivedCode.address;
  result += "-";
  result += receivedCode.unit;
  result += "-";
  result += receivedCode.switchType == NewRemoteCode::on ? 1 : 0;
  Serial.println(result);
}

void readSensors() {
  lux = lightMeter.readLightLevel();
  tmp = tempMeter.readTemperature();
  hum = tempMeter.readHumidity();
  Serial.print("3-");
  Serial.print(lux);
  Serial.print("-");
  Serial.print(tmp);
  Serial.print("-");
  Serial.println(hum);
}

void sendV1(long code) {
  RemoteReceiver::disable();
  interrupts();
  switchLed(ledOut, HIGH);
  Serial.print("Send: code=");
  Serial.println(code);
  RemoteTransmitter::sendCode(rfOut, code, 213, 4);
  Serial.println("Is Sent !");
  switchLed(ledOut, LOW);
  RemoteReceiver::enable();
}

void sendV2(int unit, bool isOn, unsigned int repeat) {
  if (senderCode == 0) {
    Serial.println("0-1-No senderCode defined");
    return;
  }
  NewRemoteReceiver::disable();
  interrupts();
  switchLed(ledOut, HIGH);
  Serial.print("Send: sender=");
  Serial.print(senderCode);
  Serial.print(", unit=");
  Serial.print(unit);
  Serial.print(", isOn=");
  Serial.println(isOn ? "on" : "off");
  NewRemoteTransmitter transmitter(senderCode, rfOut, 213, repeat);
  transmitter.sendUnit(unit, isOn);
  Serial.println("Is Sent !");
  switchLed(ledOut, LOW);
  NewRemoteReceiver::enable();
}

void blinkLed(int led) {
  pinMode(led, OUTPUT);
  for (int i=0; i<3; i++) {
    digitalWrite(led, HIGH);
    delay(250);
    digitalWrite(led, LOW);
    delay(250);
  }
}
void switchLed(int led, int value) {
  pinMode(led, OUTPUT);
  digitalWrite(led, value);
  delay(100);
}

