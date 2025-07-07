import struct
from binascii import hexlify, unhexlify
from pyLoraRFM9x import LoRa, ModemConfig
import time
from datetime import datetime
import serial
import numpy as np
import json
import RPi.GPIO as GPIO
import logging

# Configure logging to append to a file
logging.basicConfig(
    filename='lora_host.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Pin configuration
LED_PIN = 23  # Replace with the GPIO pin number you're using

# GPIO setup
GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
GPIO.setup(LED_PIN, GPIO.OUT)  # Set the pin as an output

port_lte = '/dev/ttyUSB1'
baud_rate_lte = 9600

ser_lte = serial.Serial(port_lte, baud_rate_lte, timeout=1)
time.sleep(1.5)  # Wait for the connection to establish

def write_to_serial(data):
    ser_lte.write(data.encode('utf-8'))
    print('msg sent to server: ', data)
    time.sleep(0.1)
    response = ser_lte.readline().decode('utf-8').strip()
    return response


received_msg = ""

def hex2num(hexnum):
    if len(hexnum)==8:
        return struct.unpack('<f', unhexlify(hexnum))[0]
    if len(hexnum)==16:
        return struct.unpack('<d', unhexlify(hexnum))[0]


port = '/dev/ttyUSB0'
baud_rate = 9600
wait_response = 1

ser = serial.Serial(port, baud_rate, timeout=3)
time.sleep(1.5)


def write_to_serial_lora(cmd0):
    cmd = cmd0 + '\n'
    ser.write(cmd.encode('utf-8'))
    t1 = datetime.now()
    while True:
        try:
            res = ser.readline().decode('utf-8').strip()
            if res=='OK':
                break
            else:
                response = res

            delta = datetime.now() - t1
            if delta.seconds > wait_response:
                break
        except:
            response = "no data"
    return response


# Send a message to a recipient device with address 10
# Retry sending the message twice if we don't get an  acknowledgment from the recipient
while True:
    if ser.in_waiting > 0:
        try:
            msg0 = ser.readline()
            msg = msg0.decode('utf-8').strip()
            if 'RECV:' in msg:
                vals = msg.split(':')[3]
                print(f'raw msg from sensor node: {vals}\n')

                id = struct.unpack("<L", unhexlify(vals[0:8]))[0]
                count = struct.unpack('<L', unhexlify(vals[8:16]))[0]
                print(f'id:  {id}')
                print(f'counter:  {count}')
                print(f'datetime: {datetime.fromtimestamp(hex2num(vals[16:32]))}')
                print(f'temp    : {hex2num(vals[32:40])}')
                print(f'pressure: {hex2num(vals[40:48])}')
                print(f'Latitude: {hex2num(vals[48:64])}')
                print(f'Longitude: {hex2num(vals[64:80])}')
                print(f'Gx: {hex2num(vals[80:88])}')
                print(f'Gy: {hex2num(vals[88:96])}')
                print(f'Gz: {hex2num(vals[96:104])}')

#            from_add = struct.unpack("<i", unhexlify(vals[104:112]))[0]
#            rssi = struct.unpack("<i", unhexlify(vals[112:120]))[0]
#            snr = struct.unpack("<f", unhexlify(vals[120:128]))[0]

#            print(f'from_add: {from_add}')
#            print(f'rssi: {rssi}')
#            print(f'snr: {snr}')
#            print()

                logging.info(vals)
                response = write_to_serial(vals)
                print(f"msg from server: {response}")
                res = write_to_serial_lora('AT+DATA=ffffff:' + response)
 
                if 'OK' in response:
                    for i in range(3):
                        GPIO.output(LED_PIN, GPIO.HIGH)
                        time.sleep(0.1)

                        GPIO.output(LED_PIN, GPIO.LOW)
                        time.sleep(0.1)
        except:
            logging.warning(msg0)
            pass
