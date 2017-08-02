int ledPinYellow = 13;
int ledPinRed = 12;
int ledPinWhite = 11; 

const int trigPin = 9;
const int echoPin = 10;
// defines variables
long duration;
int distance;

#include <SPI.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_LSM9DS0.h>

Adafruit_LSM9DS0 lsm = Adafruit_LSM9DS0(1000);

#define LSM9DS0_XM_CS 10
#define LSM9DS0_GYRO_CS 9

#define LSM9DS0_SCLK 13
#define LSM9DS0_MISO 12
#define LSM9DS0_MOSI 11

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

// Or use this line for a breakout or shield with an I2C connection:
Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);

#if defined(ARDUINO_ARCH_SAMD)
   #define Serial SerialUSB
#endif

#include <avr/sleep.h>
#include <avr/power.h>

volatile int f_timer=0;
volatile int threshold = 0;
const unsigned int twosec = 34286;
const unsigned int foursec = 3036;
volatile unsigned int delay_period=0;

bool magnet_awake = false;
bool RFID_awake = false;

ISR(TIMER1_OVF_vect)
{
  TCNT1 = twosec;
  RFID_awake = false;
  magnet_awake = false;
  digitalWrite(ledPinYellow, LOW);
  digitalWrite(ledPinRed, LOW);
  digitalWrite(ledPinWhite, LOW);
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

void configureSensor(void) {
  lsm.setupMag(lsm.LSM9DS0_MAGGAIN_2GAUSS);
}

void setup() {
  delay_period = twosec;
  Serial.begin(9600);
  
  #ifndef ESP8266
    while (!Serial); // for Leonardo/Micro/Zero
  #endif
  
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
  #ifndef ESP8266
    while (!Serial);     // will pause Zero, Leonardo, etc until serial console opens
  #endif
  /* Initialise the sensor */
  if(!lsm.begin()) {
    /* There was a problem detecting the LSM9DS0 ... check your connections */
    while(1);
  }
  
  /* Setup the sensor gain and integration time */
  configureSensor();
  
  pinMode(trigPin, OUTPUT); // Sets the trigPin as an Output
  pinMode(echoPin, INPUT); // Sets the echoPin as an Input
  Serial.begin(9600); //Starts the serial communication

  pinMode(ledPinYellow, OUTPUT);
  digitalWrite(ledPinYellow, LOW);
  pinMode(ledPinRed, OUTPUT);
  digitalWrite(ledPinRed, LOW);
  pinMode(ledPinWhite, OUTPUT);
  digitalWrite(ledPinWhite, LOW);
  
  // Calibrate distance sensor
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  // Sets the trigPin on HIGH state for 10 microseconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Reads the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(echoPin, HIGH);
  threshold = duration *.9;
  
  //Timer of 2 seconds
  TCCR1A = 0x00; 
  TCNT1=delay_period; 
  TCCR1B = 0x05;
  TIMSK1=0x01;
}
void magnet_sense(){
  if (magnet_awake){
    sensors_event_t accel, mag, gyro, temp;
    lsm.getEvent(&accel, &mag, &gyro, &temp);
  
    // print out magnetometer data
    float sum = abs(mag.magnetic.x) + abs(mag.magnetic.y) + abs(mag.magnetic.z);
  
    if (sum > 2){
      digitalWrite(ledPinRed, HIGH);
      byte msg[] = {1, 2, 1};
      Serial.write(msg,3);
      //Serial.println("Magnet Sense");
      magnet_awake = false;
    }
  }
}

bool ultrasound_sense(){
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  // Sets the trigPin on HIGH state for 10 microseconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Reads the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(echoPin, HIGH);
  if (duration < threshold){
    digitalWrite(ledPinYellow, HIGH);
    byte msg[] = {1, 6, 1};
    //Serial.println("Ultrasound Sense");
    Serial.write(msg,3);
    return true;
  }
  return false;
}

void RFID_sense(){
  if (RFID_awake){
    uint8_t success;
    uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };  // Buffer to store the returned UID
    uint8_t uidLength;                        // Length of the UID (4 or 7 bytes depending on ISO14443A card type)
     
    success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength);
    
    if (success) {
      digitalWrite(ledPinWhite, HIGH);  
      if (uidLength == 4) {
        uint8_t keya[6] = { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF };
        success = nfc.mifareclassic_AuthenticateBlock(uid, uidLength, 4, 0, keya);    
        if (success) {
          uint8_t data[16];
          success = nfc.mifareclassic_ReadDataBlock(4, data);
          if (success) {
            byte bytelow = 1;
            byte bytemid = 1;
            byte bytehigh = 1;
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

void loop() {
  if(f_timer==1){
    f_timer = 0;
    
    bool sensed = ultrasound_sense();
    while (Serial.available() >= 3 || sensed){
      // read the incoming byte:
      byte Bytehigh = Serial.read();
      byte Bytemid = Serial.read();
      byte Bytelow = Serial.read();
      if (Bytehigh == 0) {
        TIMSK1 = 0x00; 
        Serial.print("+++");
        delay(1000);
        Serial.print("ATID");
        Serial.print(Bytemid, HEX);
        Serial.print(Bytelow, HEX);
        Serial.print('/r');
        delay(1000);
        Serial.print("ATWR/r");
        while (Serial.available >= 3) {
          Serial.read();
          Serial.read();
          Serial.read();
        }
        TIMSK1 = 0x01;
      } 
      else if (Bytemid >= 5 || sensed){
        sensed = false;
        // Message is from detector node
        //Turn off interrupt temporarily
        TIMSK1=0x00;
        TCNT1=foursec;
        // Change interrupt
        magnet_awake = true;
        RFID_awake = true;
        TIMSK1=0x01;
        while(magnet_awake||RFID_awake){
          magnet_sense();
          RFID_sense();
        }
      }
    }
    //Serial.println("Sleep");
    enterSleep();
  }
}
