/******************************************************************************
Piezo_Vibration_Sensor.ino
Example sketch for SparkFun's Piezo Vibration Sensor
  (https://www.sparkfun.com/products/9197)
Jim Lindblom @ SparkFun Electronics
April 29, 2016

- Connect a 1Mohm resistor across the Piezo sensor's pins.
- Connect one leg of the Piezo to GND
- Connect the other leg of the piezo to A0

Vibrations on the Piezo sensor create voltags, which are sensed by the Arduino's
A0 pin. Check the serial monitor to view the voltage generated.

Development environment specifics:
Arduino 1.6.7
******************************************************************************/
int ledPin = 13;

#include <avr/sleep.h>
#include <avr/power.h>

volatile int f_timer=0;
const int PIEZO_PIN = A0; // Piezo output

ISR(TIMER1_OVF_vect)
{
   TCNT1 = 31250;
  /* set the flag. */
  digitalWrite(ledPin, LOW);
   if(f_timer == 0)
   {
     f_timer = 1;
   }
}

void enterSleep(void)
{
  set_sleep_mode(SLEEP_MODE_IDLE);
  
  sleep_enable();
  /* Disable all of the unused peripherals. This will reduce power
   * consumption further and, more importantly, some of these
   * peripherals may generate interrupts that will wake our Arduino from
   * sleep!
   */
  power_adc_disable();
  power_spi_disable();
  power_timer0_disable();
  power_timer2_disable();
  power_twi_disable();  

  /* Now enter sleep mode. */
  sleep_mode();
  
  /* The program will continue from here after the timer timeout*/
  sleep_disable(); /* First thing to do is disable sleep. */
  
  /* Re-enable the peripherals. */
  power_all_enable();
}

void setup()
{
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);
  
  Serial.begin(9600);
  /* Normal timer operation.*/
  TCCR1A = 0x00; 
  TCNT1=31250; 
  
  /* Configure the prescaler for 1:1024, giving us a 
   * timeout of 4.09 seconds.
   */
  TCCR1B = 0x05;
  /* Enable the timer overlow interrupt. */
  TIMSK1=0x01;
}

void loop() 
{
  if(f_timer==1){
    f_timer = 0;
    /*
    while (Serial.available() >= 3) {
      byte h = Serial.read();
      byte m = Serial.read();
      byte l = Serial.read();
      if (h == 0) {
        TIMSK1 = 0x00;
        Serial.print("+++");
        delay(1000);
        Serial.print("ATID");
        Serial.print(m, HEX);
        Serial.print(l, HEX);
        Serial.print('\r');
        delay(1000);
        Serial.print("ATWR\r");
        while (Serial.available() >= 3) {
          Serial.read();
          Serial.read();
          Serial.read();
        }
      }
    }
    TIMSK1 = 0x01;
    */
    // Read Piezo ADC value in, and convert it to a voltage
    int piezoADC = analogRead(PIEZO_PIN);
    if (piezoADC != 0){
      digitalWrite(ledPin, HIGH);
      byte bytelow = 1;
      byte bytemid = 7;
      byte bytehigh = 3;
      byte msg[] = {bytehigh, bytemid, bytelow}; 
      Serial.write(msg, 3);
    }
    enterSleep();
  }
}
