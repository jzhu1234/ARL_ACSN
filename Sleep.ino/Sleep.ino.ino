#include <avr/sleep.h>
#include <avr/power.h>

#define LED_PIN (13)

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

/***************************************************
 *  Name:        setup
 *  Returns:     Nothing.
 *  Parameters:  None.
 *  Description: Setup for the serial comms and the
 *                timer. 
 ***************************************************/
void setup()
{
  Serial.begin(9600);
  
  /* Don't forget to configure the pin! */
  pinMode(LED_PIN, OUTPUT);

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

/***************************************************
 *  Name:        enterSleep
 *  Returns:     Nothing.
 *  Parameters:  None.
 *  Description: Main application loop.
 ***************************************************/
void loop()
{
  if(f_timer==1)
  {
    f_timer = 0;
    /* Toggle the LED */
    Serial.println("hi");
    
    /* Re-enter sleep mode. */
    enterSleep();
  }
}
