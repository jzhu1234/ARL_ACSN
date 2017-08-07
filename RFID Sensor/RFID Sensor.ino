#include <Wire.h>
#include <SPI.h>
#include <Adafruit_PN532.h>

// If using the breakout with SPI, define the pins for SPI communication.
#define PN532_SCK  (2)
#define PN532_MOSI (3)
#define PN532_SS   (4)
#define PN532_MISO (5)

// If using the breakout or shield with I2C, define just the pins connected
// to the IRQ and reset lines.  Use the values below (2, 3) for the shield!
#define PN532_IRQ   (2)
#define PN532_RESET (3)  // Not connected by default on the NFC Shield

Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);

#if defined(ARDUINO_ARCH_SAMD)
// for Zero, output on USB Serial console, remove line below if using programming port to program the Zero!
// also change #define in Adafruit_PN532.cpp library file
   #define Serial SerialUSB
#endif

#include <avr/sleep.h>
#include <avr/power.h>


volatile int f_timer=0;
volatile int threshold = 0;
const unsigned int twosec = 34286;
const unsigned int foursec = 3036;
volatile unsigned int delay_period=0;

bool RFID_awake = false;

ISR(TIMER1_OVF_vect)
{
  TCNT1 = twosec;
  RFID_awake = false;
  /* set the flag. */
  if(f_timer == 0)
  {
    f_timer = 1;
  }
}

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
  sleep_disable(); /* First thing to do is disable sleep. */
  power_all_enable();
}

void setup() {
  
  //Serial.begin(9600);
  /*
  #ifndef ESP8266
    while (!Serial); // for Leonardo/Micro/Zero
  #endif
  */
  Serial.begin(115200);
  
  nfc.begin();

  uint32_t versiondata = nfc.getFirmwareVersion();
  if (! versiondata) {
    //Serial.print("Didn't find PN53x board");
    while (1); // halt
  }
  
  nfc.setPassiveActivationRetries(0xFE);
  
  // configure board to read RFID tags
  nfc.SAMConfig();
  Serial.begin(9600);
  
  //Timer of 2 seconds
  TCCR1A = 0x00; 
  TCNT1=twosec; 
  TCCR1B = 0x05;
  TIMSK1=0x01;
}

void RFID_sense(){
  if (RFID_awake){
    uint8_t success;
    uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };  // Buffer to store the returned UID
    uint8_t uidLength;                        // Length of the UID (4 or 7 bytes depending on ISO14443A card type)
     
    success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength);
    
    if (success) {  
      if (uidLength == 4) {
        uint8_t keya[6] = { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF };
        success = nfc.mifareclassic_AuthenticateBlock(uid, uidLength, 4, 0, keya);    
        if (success) {
          uint8_t data[16];
          success = nfc.mifareclassic_ReadDataBlock(4, data);
          if (success) {
            byte bytelow = 1;
            byte bytemid = 1;
            byte bytehigh = 6;
            byte msg[] = {bytehigh, bytemid, bytelow};
            RFID_awake = false;
            //Serial.println("RFID Sense");
            Serial.write(msg, 3);
          }
        }
      }
    }
  }
}


void loop(void) {
  if(f_timer==1){
    f_timer = 0;
    
    while (Serial.available() >= 3){
      // read the incoming byte:
      byte Bytehigh = Serial.read();
      byte Bytemid = Serial.read();
      byte Bytelow = Serial.read();

      if (Bytemid >= 5 && Bytehigh != 0){
        // Message is from detector node
        //Turn off interrupt temporarily
        TIMSK1=0x00;
        TCNT1=foursec;
        // Change interrupt
        RFID_awake = true;
        TIMSK1=0x01;
        while(RFID_awake){
          RFID_sense();
        }
      }
    }
    //Serial.println("Sleep");
    enterSleep();
  }  
} 
