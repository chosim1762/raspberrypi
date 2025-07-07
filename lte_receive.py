from socket import *
from time import ctime
from binascii import hexlify, unhexlify
import json
import datetime
from textwrap import wrap
import struct
import paho.mqtt.client as mqtt
import logging
import requests

token = "7549939433:AAEBjrr5j9CnX9KeqCkeAh9RDxU9GESeKOs"

def push2telegram(mc,msg):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(
        url=url,
        params={'chat_id': mc, 'text': msg, 'parse_mode': 'Markdown'}
    )
    print(url, response.json())

# Configure logging to append to a file
logging.basicConfig(
    filename='lora_server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully!")
        client.subscribe(TOPIC)  # Subscribe to the topic
    else:
        print(f"Connection failed with code {rc}")

# Callback when a message is received
def on_message(client, userdata, msg):
    print(f"Received message: {msg.payload.decode()} on topic: {msg.topic}")

# Callback when the client publishes a message
def on_publish(client, userdata, mid):
    print(f"Message published with ID: {mid}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected MQTT disconnection. Will auto-reconnect")


def convert2mqttform(info,memo=""):
    infos  = []
    infos.append("distance")
    infos.append(int(datetime.datetime.timestamp(info['datetime']) * 10**9))
    orders = ['from_add', 'id', 'counter', 'temperature', 'pressure', 'latitude', 'longitude', 'Gx', 'Gy', 'Gz', 'rssi', 'snr']

    for order in orders:
        infos.append(info[order])

    infos.append(memo)
    return infos

def hex2num(hexnum):
    if len(hexnum)==8:
        return struct.unpack('<f', unhexlify(hexnum))[0]
    if len(hexnum)==16:
        return struct.unpack('<d', unhexlify(hexnum))[0]

def print_data(vals):
    count = struct.unpack('<L', unhexlify(vals[8:16]))[0]
    id =  struct.unpack('<L', unhexlify(vals[0:8]))[0]
    date = datetime.datetime.fromtimestamp(hex2num(vals[16:32]))
    from_add = struct.unpack("<i", unhexlify(vals[104:112]))[0]
    rssi = struct.unpack("<i", unhexlify(vals[112:120]))[0]
    snr = struct.unpack("<f", unhexlify(vals[120:128]))[0]

    info = {
        "id": id,
        "counter": count,
        "datetime": date,
        "temperature": hex2num(vals[32:40]),
        "pressure": hex2num(vals[40:48]),
        "latitude": hex2num(vals[48:64]),
        "longitude": hex2num(vals[64:80]),
        "Gx": hex2num(vals[80:88]),
        "Gy": hex2num(vals[88:96]),
        "Gz": hex2num(vals[96:104]),
        "from_add": from_add,
        "rssi": rssi,
        "snr": snr
    }

    print(f'id: {id}')
    print(f'counter:  {count}')
    print(f'datetime: {date}')
    print(f'temp    : {hex2num(vals[32:40])}')
    print(f'pressure: {hex2num(vals[40:48])}')
    print(f'Latitude: {hex2num(vals[48:64])}')
    print(f'Longitude: {hex2num(vals[64:80])}')
    print(f'Gx: {hex2num(vals[80:88])}')
    print(f'Gy: {hex2num(vals[88:96])}')
    print(f'Gz: {hex2num(vals[96:104])}')
    print(f'Address of sensor node:  {from_add}')
    print(f'rssi of LoRa:  {rssi}')
    print(f'snr of LoRa:  {snr}')
    print()
    return info



def command_meaning(cmd):
    if cmd == b'02':
        mean = 'Response Get Device Status'
    if cmd == b'03':
        mean = 'Response Ack'
    if cmd == b'14':
        mean = 'Request Registration'
    if cmd == b'15':
        mean = 'Response Request Regitration'
    if cmd == b'1b':
        mean = 'Control Order'
    return mean

def status_meaning(status):
    if status == b'00':
        mean = 'CD_SUCCESS'
    if status == b'01':
        mean = 'CD_TOKENMISMATCH'
    if status == b'02':
        mean = 'CD_TID_NOT_MATCH'
    if status == b'03':
        mean = 'CD_DEVICE_NOTREGISTERED'
    return mean

def extract_datum(datum):
    status = wrap(datum[4:], 2)
    status_array = []
    for num in status:
        status_array.append(bytes.fromhex(num).decode('utf-8'))
    if datum[0:4] == '323d':
        code = 'GPIO'
    elif datum[0:4] == '333d':
        code = 'Longitude'
    elif datum[0:4] == '343d':
        code = 'Latitude'
    if datum[0:4] == '353d':
        code = 'DeviceData'
    return code, ''.join(status_array)

def extract_data(data):
    data_decode = {}
    for datum in data:
        code, status = extract_datum(datum)
        data_decode[code] = status
    return data_decode


def extract_header(msg):
    msg_decode = {
        "Version": msg[0:4],
        "Command": msg[4:6],  # 02: Resonse Get Device Status, 03: Response Ack, 14: Request Registration
        "Token": msg[6:46],   # 15: Resonse Request Regitration, 0x1B: Control Order
        'BodyLength': int.from_bytes(unhexlify(msg[46:50]),'little'),
        'TransactionId': msg[50:54],
        'ModelCode': msg[54:62],
        'DeviceId': msg[62:94],
        'DeviceIdLength': int.from_bytes(unhexlify(msg[94:96]),'little'),
        'EncryptionType': msg[96:98],
        'StatusCode': msg[98:100],
        'CommandMeaning': command_meaning(msg[4:6]),
        'StatusMeaning': status_meaning(msg[98:100])
    }
    if msg_decode['BodyLength'] > 0:
        body = msg[100:100 + msg_decode['BodyLength'] * 2]
        if msg_decode['Command'] == b'15':
            msg_decode['Body'] = {
                'AlwaysOn': body[0:2],
                'StartTime': body[2:6],
                'EndTime': body[6:10],
                'HeartBeatInterval': body[10:14],
                'CurrentTime': body[14:22],
                'CurrentTime(UTC)': datetime.datetime.fromtimestamp(int.from_bytes(unhexlify(body[14:22]),'little'))
            }
        if msg_decode['Command'] == b'02':
            msg_decode['Body'] = extract_data(body.decode('utf-8').split('7c'))

        if msg_decode['Command'] == b'1b':
            msg_decode['Body'] = {
                'TransferNumber': body[0:26],
                'CommandType': body[26:28],
                'Payload': ''.join([bytes.fromhex(x).decode('utf-8') for x in wrap(body[28:].decode('utf-8'), 2)])
            }
    return msg_decode

def compose_cmd(msg, cmd, param=''):
    if cmd == 'Response Request Registration':
        msg_encode = msg["Version"] + b'15' + msg['Token'] + b'0b00' + msg['TransactionId'] + msg['ModelCode'] + msg['DeviceId']
        msg_encode += b'08' + msg['EncryptionType'] + b'00' + b'01' + b'1000' + b'1900' + b'0200' + b'97cd5c5d'
    elif cmd == 'Control Order':
        payload_array = [format(ord(char),'x') for char in param]
        body_length = len(payload_array) + 14
        body_length_inhex = body_length.to_bytes(2, byteorder='little').hex().encode('utf-8')
        msg_encode = msg["Version"] + b'1b' + msg['Token'] + body_length_inhex + msg['TransactionId'] + msg['ModelCode'] + msg['DeviceId']
        msg_encode += b'08' + msg['EncryptionType'] + b'00' + b'00000000000000000000000000' + b'06' + ''.join(payload_array).encode('utf-8')
    return msg_encode


HOST = '0.0.0.0'
PORT = 1905
BUFSIZ = 1024
ADDR = (HOST, PORT)

server_socket = socket(AF_INET, SOCK_STREAM)
server_socket.bind(ADDR)
server_socket.listen()

# Define the MQTT broker details
BROKER = "ndlsensor.ddns.net"  # Public broker for testing
PORT = 5653
TOPIC = "db/append/LORACHECK"

# Create an MQTT client instance
client = mqtt.Client()

# Assign callbacks
client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish
client.on_disconnect = on_disconnect

# Connect to the broker
client.connect(BROKER, PORT, 60)
print(client)

counter = 0
while True:
    print('waiting for connection...')
    client_socket, addr = server_socket.accept()
    print('.. connected from: ', addr)

    while True:
        data = client_socket.recv(BUFSIZ)
        if not data:
            break
        msg = extract_header(hexlify(data))
        if msg['Command'] == b'14':
            reply_msg = compose_cmd(msg, 'Response Request Registration')
            print('Get the Request Registration from the device')
            break
    client_socket.send(unhexlify(reply_msg))
    print('Response Request Registration to the device')

    while True:
        counter += 1
        print('Waiting of the Heart Beat: %d' % counter)
        data = client_socket.recv(BUFSIZ)
        if not data:
            break
        print('Got the Device Status from the Device')
        res = extract_header(hexlify(data))
        print(res)
        if "Body" in res:
            if "DeviceData" in res['Body']:
                if not res['Body']['DeviceData'] == 'err':
                    rawdata = res['Body']['DeviceData']
                    print('received raw data: ', rawdata)
                    if len(rawdata)==128:
                        res = print_data(rawdata)
                        memo = "checking the valid distance of LoRa"
                        res_dbtable = convert2mqttform(res,memo) 
                        res_dbform = str(res_dbtable).replace("'",'"')
                        print(res_dbform)
                        logging.info(rawdata)
                        # Publish a message
                        client.publish(TOPIC, res_dbform)

                        mc = "687106415"
#                        push2telegram(mc,res_dbform)
                    else:
                        logging.warning(rawdata)

        message = b'567603'
        client_socket.send(unhexlify(message))
        print('Sent the ACK signal to the Device')
        print()

        return_msg = 'OK'
        message = compose_cmd(extract_header(hexlify(data)),'Control Order',return_msg)
        client_socket.send(unhexlify(message))
        print('Sent the Control Order to the Device')
        print()

# Start the loop to process network traffic and dispatch callbacks
#client.loop_forever()

client_socket.close()
server_socket.close()
