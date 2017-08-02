/* 
 * //////////////////////////////////////////////////
 * //making sense of the Parallax PIR sensor's output
 * //////////////////////////////////////////////////
 *
 * Switches a LED according to the state of the sensors output pin.
 * Determines the beginning and end of continuous motion sequences.
 *
 * @author: Kristian Gohlke / krigoo (_) gmail (_) com / http://krx.at
 * @date:   3. September 2006 
 *
 * kr1 (cleft) 2006 
 * released under a creative commons "Attribution-NonCommercial-ShareAlike 2.0" license
 * http://creativecommons.org/licenses/by-nc-sa/2.0/de/
 *
 *
 * The Parallax PIR Sensor is an easy to use digital infrared motion sensor module. 
 * (http://www.parallax.com/detail.asp?product_id=555-28027)
 *
 * The sensor's output pin goes to HIGH if motion is present.
 * However, even if motion is present it goes to LOW from time to time, 
 * which might give the impression no motion is present. 
 * This program deals with this issue by ignoring LOW-phases shorter than a given time, 
 * assuming continuous motion is present during these phases.
 *  
 */

/////////////////////////////
//VARS  

//the amount of milliseconds the sensor has to be low 
//before we assume all motion has stopped

int pirPin = 3;    //the digital pin connected to the PIR sensor's output
int ledPin = 11;
#include <avr/sleep.h>
#include <avr/power.h>

#define ledPin (11)

volatile int f_timer=0;

/***************************************************
 *  Name:        ISR(TIMER1_OVF_vect)
 *  Returns:     Nothing.
 *  Parameters:  None.
 *  Description: Timer1 Overflow interrupt.
 ***************************************************/
ISR(TIMER1_OVF_vect)
{
   TCNT1 = 31250;
  /* set the flag. */
   if(f_timer == 0)
   {
     f_timer = 1;
   }
}

/***************************************************
 *  Name:        enterSleep
 *  Returns:     Nothing.
 *  Parameters:  None.
 *  Description: Enters the arduino into sleep mode.
 ***************************************************/
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

/////////////////////////////
//SETUP
void setup(){
  Serial.begin(9600);
  pinMode(pirPin, INPUT);
  pinMode(ledPin, OUTPUT);
  //digitalWrite(pirPin. LOW);

    /*** Configure the timer.***/
  
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

////////////////////////////
//LOOP
void loop() {
  if(f_timer == 1){
    f_timer = 0;
    while (Serial.available >= 3) {
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
        while (Serial.available >= 3) {
          Serial.read();
          Serial.read();
          Serial.read();
        }
      }
    }
    TIMSK1 = 0x01;
    int proximity = digitalRead(pirPin);
    if(proximity == HIGH){
      digitalWrite(ledPin, HIGH);   //the led visualizes the sensors output pin state
      byte id = 4;
      byte data_high = 5;
      byte data_low = 1;
      byte packet[] = {id, data_high, data_low};
      //Serial.println("Sensed Something");
      Serial.write(packet, 3);
    
     }
    else if(proximity == LOW) {
      digitalWrite(ledPin, LOW);  //the led visualizes the sensors output pin state
      }
    enterSleep();
  }
}
