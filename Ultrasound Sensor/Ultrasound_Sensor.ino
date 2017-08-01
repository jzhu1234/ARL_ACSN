int ledPin = 13;

#include <avr/sleep.h>
#include <avr/power.h>

const int trigPin = 9;
const int echoPin = 10;

// defines variables
long duration;
int distance;

volatile int f_timer=0;
volatile int threshold = 0;

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

void setup() {
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);
   
  pinMode(ledPin, OUTPUT);
  pinMode(trigPin, OUTPUT); // Sets the trigPin as an Output
  pinMode(echoPin, INPUT); // Sets the echoPin as an Input
  Serial.begin(9600); //Starts the serial communication

  /* Normal timer operation.*/
  TCCR1A = 0x00; 
  TCNT1=31250; 
  /* Configure the prescaler for 1:1024, giving us a 
   * timeout of 4.09 seconds.
   */
  TCCR1B = 0x05;
  /* Enable the timer overlow interrupt. */
  TIMSK1=0x01;

  // Calibrate distance sensor
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  // Sets the trigPin on HIGH state for 10 microseconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Reads the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(echoPin, HIGH);
  threshold = duration * .9;
}

void loop() {
  if(f_timer==1)
  {
    f_timer = 0;
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    // Sets the trigPin on HIGH state for 10 microseconds
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    // Reads the echoPin, returns the sound wave travel time in micro seconds
    duration = pulseIn(echoPin, HIGH);
    if (duration < threshold){
      digitalWrite(ledPin, HIGH);
      byte msg[] = {5, 6, 1};
      Serial.write(msg,3);
    }
    enterSleep();
  }  
}
