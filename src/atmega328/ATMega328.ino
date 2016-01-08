#include <Timer.h>
#include <Wire.h>

#include <SensorReceiver.h>
#include <RemoteReceiver.h>
#include <NewRemoteReceiver.h>
#include <InterruptChain.h>
#include <RemoteTransmitter.h>
#include <NewRemoteTransmitter.h>
#include <BH1750.h>
#include <DHT.h>

const unsigned long RED = 0xFF0000;
const unsigned long GREEN = 0x00FF00;
const unsigned long BLUE = 0x0000FF;
const unsigned long ORANGE = 0xFF9F00;
const unsigned long TEAL = 0x008080;
const unsigned long AUBERGINE = 0x614051;

int redLed = 8;
int greenLed = 7;
int blueLed = 6;

int rfIn = 0; // Interrupt 0 on Pin2 
int rfOut = 3;
int tmpPin = 4;

long senderCode = 0;
char separator = '\n';
String rpiCmd = "";

int sensorUid = 0;
DHT htMeter(tmpPin, DHT11);
BH1750 lightMeter;

volatile String msg;

String f2s(float value) {
  char tmp[10];
  String str;
  dtostrf(value,1,2,tmp);
  return String(tmp);
}

void initLed() {
  pinMode(redLed, OUTPUT );
  pinMode(greenLed, OUTPUT );
  pinMode(blueLed, OUTPUT );
}
void setLedColor(unsigned long color) {
  if (color == 0) {
    digitalWrite(redLed, LOW);
    digitalWrite(greenLed, LOW);
    digitalWrite(blueLed, LOW);
    return;
  }
  byte red = (color >> 16) & 0xFF;
  byte green = (color >> 8) & 0xFF;
  byte blue = color & 0xFF;
  digitalWrite(redLed, red);
  digitalWrite(greenLed, green);
  digitalWrite(blueLed, blue);
}

void blinkLedColor(unsigned long color, int repeat) {
  for (int i=0; i<repeat; i++) {
    setLedColor(color);
    delay(250);
    setLedColor(0);
    delay(250);
  }
}

void blinkRGB(){
  setLedColor(RED);
  delay(250);
  setLedColor(GREEN);
  delay(250);
  setLedColor(BLUE);
  delay(250);
  setLedColor(0);
}

void enableReceivers(bool enable) {
  if (enable) {
    //RemoteReceiver::enable();
    //NewRemoteReceiver::enable();
    InterruptChain::enable(0);
    interrupts();
  } else {
    //RemoteReceiver::disable();
    //NewRemoteReceiver::disable();
    InterruptChain::disable(0);
    noInterrupts();
  }
}

void sendV1(long code) {
  setLedColor(TEAL);
  /*Serial.print("Send v1 ");
  Serial.println(code);*/
  enableReceivers(false);
  RemoteTransmitter::sendCode(rfOut, code, 213, 4);
  enableReceivers(true);
  //Serial.println("-> Sent");
  String result = "2-1-";
  result += code;
  result += "-OK";
  Serial.println(result);
  setLedColor(0);
}

void sendV2(int unit, bool isOn, unsigned int repeat) {
  if (senderCode == 0) {
    Serial.println("0-1-No senderCode defined");
    return;
  }
  setLedColor(AUBERGINE);
  /*Serial.print("Send v2 ");
  Serial.print(senderCode);
  Serial.print(", unit: ");
  Serial.print(unit);
  Serial.print(", repeat: ");
  Serial.println(repeat);*/
  enableReceivers(false);
  NewRemoteTransmitter transmitter(senderCode, rfOut, 213, repeat);
  transmitter.sendUnit(unit, isOn);
  enableReceivers(true);
  //Serial.println("-> Sent");
  String result = "2-2-";
  result += unit;
  result += "-";
  result += isOn;
  result += "-OK";
  Serial.println(result);
  setLedColor(0);
}

void readSensors() {
  setLedColor(ORANGE);
  
  uint16_t lux = lightMeter.readLightLevel();
  float tmp = htMeter.readTemperature();
  float hum = htMeter.readHumidity();
  
  String result = "3-";
  result += sensorUid;
  result += "-";
  result += f2s(tmp);
  result += "-";
  result += f2s(hum);
  result += "-";
  result += lux;
  Serial.println(result);
  setLedColor(0);
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
    //Serial.print("Sender code defined: ");
    Serial.println("1-OK");
  } else if (cmd == 2) {
    int i2 = data.indexOf("-", i1+1);
    part = data.substring(i1+1, i2);
    int protocol = part.toInt();
    if (protocol == 1) {
      part = data.substring(i2+1);
      long code = part.toInt();
      //Serial.print("Send v1 code: ");
      //Serial.println(code);
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
      /*Serial.print("Send v2 unit: ");
      Serial.print(unit);
      Serial.print(", state: ");
      Serial.print(state);
      Serial.print(", repeat: ");
      Serial.println(repeat);*/
      sendV2(unit, state, repeat);
    }
  } else if (cmd == 3) {
    int i2 = data.indexOf("-", i1+1);
    part = data.substring(i1+1, i2);
    int uid = part.toInt();
    if (uid == sensorUid)
      readSensors();
  } else if (cmd == 9) {
    int i2 = data.indexOf("-", i1+1);
    part = data.substring(i1+1, i2);
    if (part == "OFF") setLedColor(0);
    else {
      int len = part.length()+1;
      char c[len];
      part.toCharArray(c, len);
      unsigned long color = strtoul(c, NULL, 16);
      part = data.substring(i2+1);
      int repeat = part.toInt();
      if (repeat == 1) setLedColor(color);
      else blinkLedColor(color, repeat);
      //Serial.println("9-OK");
    }
  } else {
    Serial.println("0-Unknown command");
  }
}

void receiveOldCode(unsigned long receivedCode, unsigned int period) {
  String result = "2-1-";
  result += receivedCode;
  Serial.println(result);
  setLedColor(BLUE);
  delay(1000);
  setLedColor(0);
}

void receiveNewCode(NewRemoteCode receivedCode) {
  String result = "2-2-";
  result += receivedCode.address;
  result += "-";
  result += receivedCode.unit;
  result += "-";
  result += receivedCode.switchType == NewRemoteCode::on ? 1 : 0;
  Serial.println(result);
  setLedColor(GREEN);
  delay(1000);
  setLedColor(0);
}

void receiveSensor(byte *data) {
  if ((data[3] & 0x1f) == 0x1e) {
    blinkLedColor(ORANGE, 3);
    byte channel, randomId;
    int temp;
    byte humidity;
    SensorReceiver::decodeThermoHygro(data, channel, randomId, temp, humidity);
    String result = "3-";
    result += randomId;
    result += "-";
    result += f2s(temp);
    result += "-";
    result += f2s(humidity) ;
    Serial.println(result); 
  }
}

void setup(){
  Serial.begin(9600);
  initLed();
  Serial.println(RED);
  
  RemoteReceiver::init(-1, 2, receiveOldCode);
  NewRemoteReceiver::init(-1, 2, receiveNewCode);
  SensorReceiver::init(-1, receiveSensor);
  InterruptChain::setMode(0, CHANGE);
  InterruptChain::addInterruptCallback(0, RemoteReceiver::interruptHandler);
  InterruptChain::addInterruptCallback(0, NewRemoteReceiver::interruptHandler);
  InterruptChain::addInterruptCallback(0, SensorReceiver::interruptHandler);

  htMeter.begin();
  lightMeter.begin();
  
  Serial.println("ATMega328-PU Ready");
  blinkRGB();
}

void loop(){
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
