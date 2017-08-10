//  Title: Speech Recongition Code
// Author: Ryan Sheatsley
//   Date: Wed Aug 9
// Army Research Laboratory - NSRL

// Club Lib
#include <TMRpcm.h>
#include <SD.h>
#include <SPI.h>
#include <Ethernet.h>

// Globals
TMRpcm audio;                              // Audio controller object
EthernetClient client;                     // Ethernet TCP controller object
EthernetUDP uClient;                       // Ethernet UDP controller object
File rFile;                                // File controller object
char *filename = "myWav.wav";              // Recording filename
IPAddress ip(192, 168, 1, 2);              // IP address of Arduino
IPAddress server(192, 168, 1, 1);          // IP address of Pi
int port = 1337;                           // Port for LEET files
int uPort = 1338;                          // For UDP packets
int ledPin = 9;                            // Pin for LED status
char packetBuffer[UDP_TX_PACKET_MAX_SIZE]; //buffer to hold incoming packet,
byte mac[] = {
  0x90, 0xA2, 0xDA, 0x10, 0x63, 0xBC       // Mac address
};

// Definitions
#define SD_ChipSelectPin 4        // Use digitial pin 4 on Arduino 
#define SampleWindow     4000     // Sample window of 4000ms
#define error(s) error_P(PSTR(s)) // store error strings in flash to save RAM

void setup() {
  // Initialize Serial monitor
  Serial.begin(9600);

  // Initialize LED
  pinMode(ledPin, OUTPUT);

  // Initialize SD card
  if (!SD.begin(SD_ChipSelectPin)) {
    Serial.println("Not able to load SD card!!");
  }
  else {
    Serial.println("SD card loaded...");
  }

  // Initialize Ethernet (give it a second to intialize)
  Ethernet.begin(mac, ip);
  delay(1000);
  uClient.begin(uPort);
  delay(1000);
  Serial.println("Accepting connections...");
}

void record() {

  // Create wav template
  audio.createWavTemplate(filename, 6500);

  // Open the file
  rFile = SD.open(filename, FILE_WRITE);
  if (!rFile) {
    Serial.println("Failed to open for write");
    return;
  }

  // Start writing analog signal to our file
  //Serial.println("Recording...");
  unsigned long start = millis();
  while (millis() - start < SampleWindow) {
    rFile.write(analogRead(0));
  }

  // Close and finalize the recording
  rFile.close();
  delay(500);
  audio.finalizeWavTemplate(filename);
  delay(500);
  //Serial.println("Recording complete");
}

void upload() {

  // Open the file
  rFile = SD.open(filename, FILE_READ);
  if (!rFile) {
    Serial.println("Failed to open for read");
  }

  // Connect to the server
  if (client.connect(server, port)) {
    Serial.println("Connected to server");
  }

  // Send the file to the server
  while (rFile.available()) {
    client.write(rFile.read());
  }

  // Close connection to the server (and file)
  rFile.close();
  client.stop();
  SD.remove(filename);
  Serial.println("Connection closed");
}

void loop() {

  // Process incoming TCP traffic
  int packetSize = uClient.parsePacket();
  if (uClient.available()) {

    // Let people know what's going on
    digitalWrite(ledPin, HIGH);

    // Read the packet
    char c = uClient.read();
    Serial.println(c);

    // Perform our recording
    record();

    // Send to the Pi
    upload();

    // Let people know it's over
    digitalWrite(ledPin, LOW);
  }
}
