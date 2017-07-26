/******************************************************************************
PIR_Motion_Detector_Example.ino
Example sketch for SparkFun's PIR Motion Detector
  (https://www.sparkfun.com/products/13285)
Jim Lindblom @ SparkFun Electronics
May 2, 2016

The PIR motion sensor has a three-pin JST connector terminating it. Connect
the wire colors like this:
- Black: D2 - signal output (pulled up internally)
- White: GND
- Red: 5V

Connect an LED to pin 13 (if your Arduino doesn't already have an LED there).

Whenever the PIR sensor detects movement, it'll write the alarm pin LOW.

Development environment specifics:
Arduino 1.6.7
******************************************************************************/
const int MOTION_PIN = 3; // Pin connected to motion detector
const int LED_PIN = 13; // LED pin - active-high
long unsigned int lowIn;
long unsigned int pause = 1000;
boolean lockLow = true;
boolean takeLowTime;

void setup() 
{
  Serial.begin(9600);
  // The PIR sensor's output signal is an open-collector, 
  // so a pull-up resistor is required:
  pinMode(MOTION_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
}

void loop() 
{
  int proximity = digitalRead(MOTION_PIN);
  if (proximity == LOW) // If the sensor's output goes low, motion is detected
  {
    digitalWrite(LED_PIN, HIGH);
    if (lockLow) {
      lockLow = false;
      Serial.println("Motion detected");
    }
    takeLowTime = true;
  }
  if (digitalRead(MOTION_PIN) == HIGH)
  {
    digitalWrite(LED_PIN, LOW);
    if (takeLowTime) {
      lowIn = millis();
      takeLowTime = false;
    }
    if (!lockLow && millis() - lowIn > pause) {
      lockLow = true;
      Serial.println("Motion End");
    }
  }
}
