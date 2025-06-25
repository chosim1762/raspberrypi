import struct
from binascii import hexlify, unhexlify
from pyLoraRFM9x import LoRa, ModemConfig
import time
received_msg = ""

def hex2num(hexnum):
    if len(hexnum)==8:
        return struct.unpack('<f', unhexlify(hexnum))[0]
    if len(hexnum)==16:
        return struct.unpack('<d', unhexlify(hexnum))[0]


# This is our callback function that runs when a message is received
def on_recv(payload):
    global received_msg
    received_msg = payload
    #print("From:", payload.header_from)
    #print("Received:", payload.message)
    #print("RSSI: {}; SNR: {}".format(payload.rssi, payload.snr))

# Lora object will use spi port 0 and use chip select 1. GPIO pin 5 will be used for interrupts and set reset pin to 25
# The address of this device will be set to 2
lora = LoRa(spi_channel=1, interrupt_pin=25, my_address=10, spi_port = 0, reset_pin=22, freq=915, tx_power=14,
      modem_config=ModemConfig.Bw125Cr45Sf128, acks=False, crypto=None)
lora.on_recv = on_recv
lora.set_mode_rx()

# Send a message to a recipient device with address 10
# Retry sending the message twice if we don't get an  acknowledgment from the recipient
while True:
    time.sleep(2)
    if received_msg != "":
        vals = received_msg.message.decode('utf-8').split(':')
        print(f'Latitude: {hex2num(vals[0])}')
        print(f'Longitude: {hex2num(vals[1])}')
        print(f'Gx: {hex2num(vals[2])}')
        print(f'Gy: {hex2num(vals[3])}')
        print(f'Gz: {hex2num(vals[4])}')
        print()
        received_msg = ""
