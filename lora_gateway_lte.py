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

port = '/dev/ttyUSB0'
baud_rate = 9600

ser = serial.Serial(port, baud_rate, timeout=1)
time.sleep(1.5)  # Wait for the connection to establish

def write_to_serial(data):
    ser.write(data.encode('utf-8'))
    print('msg sent to server: ', data)
    time.sleep(0.1)
    response = ser.readline().decode('utf-8').strip()
    return response


received_msg = ""

def hex2num(hexnum):
    if len(hexnum)==8:
        return struct.unpack('<f', unhexlify(hexnum))[0]
    if len(hexnum)==16:
        return struct.unpack('<d', unhexlify(hexnum))[0]


# This is our callback function that runs when a message is received
def on_recv(payload):
    global received_msg
#    print("From:", payload.header_from)
#    print("Received:", payload.message)
#    print("RSSI: {}; SNR: {}".format(payload.rssi, payload.snr))

    try:
        from_add = struct.pack('<i', payload.header_from).hex()  # integer, 4 byte
        rssi = struct.pack('<i', payload.rssi).hex()  # integer, 4 byte
        snr = struct.pack('<f', payload.snr).hex() # float, 4 byte

        print('rssi:', rssi)
        print('snr:', snr)

        received_msg = payload.message.decode('utf-8') + f'{from_add:<8}{rssi:<8}{snr:<8}' 
    except:
        received_msg = payload.message


# Lora object will use spi port 0 and use chip select 1. GPIO pin 5 will be used for interrupts and set reset pin to 25
# The address of this device will be set to 2
lora = LoRa(spi_channel=1, interrupt_pin=25, my_address=1, spi_port = 0, reset_pin=22, freq=915, tx_power=14,
      modem_config=ModemConfig.Bw125Cr45Sf128, acks=False, crypto=None)
lora.on_recv = on_recv
lora.set_mode_rx()

# Send a message to a recipient device with address 10
# Retry sending the message twice if we don't get an  acknowledgment from the recipient
while True:
    if received_msg != "":
        vals = received_msg
        print(f'raw msg from sensor node: {vals}\n')

        try:
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

            from_add = struct.unpack("<i", unhexlify(vals[104:112]))[0]
            rssi = struct.unpack("<i", unhexlify(vals[112:120]))[0]
            snr = struct.unpack("<f", unhexlify(vals[120:128]))[0]

            print(f'from_add: {from_add}')
            print(f'rssi: {rssi}')
            print(f'snr: {snr}')
            print()

            logging.info(vals)
            response = write_to_serial(vals)
            print(f"msg from server: {response}")
            lora.send(response.encode('utf-8'),255)
 
            if 'OK' in response:
                for i in range(3):
                    GPIO.output(LED_PIN, GPIO.HIGH)
                    time.sleep(0.1)

                    GPIO.output(LED_PIN, GPIO.LOW)
                    time.sleep(0.1)
        except:
            logging.warning(vals)
        received_msg = ""
