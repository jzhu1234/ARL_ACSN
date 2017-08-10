#!/usr/bin/env python
# Ryan Sheatsley
# Army Research Laboratory
# Thu Aug 10

# Club lib
import socket
import sys
import speech_recognition as sr
from os import path, remove

# Globals
arduino_addr = '192.168.1.2'
arduino_ping = 1338
arduino_upload = 1337
server_addr = '192.168.1.1'
buffer_size = 4096

# when this script is called, send a UDP packet to the Arduino
usock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
usock.sendto(b'1', (arduino_addr, arduino_ping)) 

# the arduino should be prepping to upload via TCP
tsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tsock.bind((server_addr, arduino_upload))
tsock.listen(1) # only listen for one client

# check if the audio file already exists
if path.isfile('mywav.wav'):
    remove('mywav.wav')

# download the audio file
conn, addr = tsock.accept()
print('Connection accepted')
while True:
    audio_upload = conn.recv(4096)
    if not audio_upload:
        break
    with open('mywav.wav', 'ab') as my_file:
        my_file.write(audio_upload)
conn.close()
print('Connection closed')

# use the audio file as the audio source
r = sr.Recognizer()
AUDIO_FILE = path.join(path.dirname(path.realpath(__file__)), 'mywav.wav')
with sr.AudioFile(AUDIO_FILE) as source:
    audio = r.record(source)  # read the entire audio file

# recognize speech using Sphinx
try:
    transcription = r.recognize_sphinx(audio, language='en-US')
    print("Sphinx thinks you said:\n" + transcription)
except sr.UnknownValueError:
    print("Sphinx could not understand audio")
except sr.RequestError as e:
    print("Sphinx error; {0}".format(e))

if 'military' in transcription:
    sys.exit(1)
else:
    sys.exit(0)
