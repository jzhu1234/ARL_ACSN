#include <avr/sleep.h>
#include <avr/power.h>
/////////////////////////////
//VARS
//the time we give the sensor to calibrate (10-60 secs according to the datasheet)
int calibrationTime = 10;        

//the time when the sensor outputs a low impulse
long unsigned int lowIn;         

//the amount of milliseconds the sensor has to be low 
//before we assume all motion has stopped
long unsigned int pause = 5000;  

boolean lockLow = true;
boolean takeLowTime;  

const int pirPin = 2;    //the digital pin connected to the PIR sensor's output
int ledPin = 13;
volatile int f_timer=0;

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
/*
void enterSleep(void)
{
  set_sleep_mode(SLEEP_MODE_IDLE);
  
  sleep_enable();
  power_adc_disable();
  power_spi_disable();
  power_timer0_disable();
  power_timer2_disable();
  power_twi_disable();  

  sleep_mode();
  
  sleep_disable(); 
  
  power_all_enable();
}
*/
/////////////////////////////
//SETUP
void setup(){
  Serial.begin(9600);
  pinMode(pirPin, INPUT);
  pinMode(ledPin, OUTPUT);

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
void loop(){
  if(f_timer==1){
    f_timer = 0;
    int proximity = digitalRead(pirPin);
    if (proximity == HIGH){
      digitalWrite(ledPin, HIGH);
      //Serial.println("Motion detected");
      byte msg[] = {2,5,1};
      //Serial.write(msg,3);
    }
    else if (proximity == LOW){
      //Serial.println("No Motion");
      digitalWrite(ledPin, LOW);
    }
    //enterSleep();
  }
}

