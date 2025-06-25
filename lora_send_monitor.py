from pyLoraRFM9x import LoRa, ModemConfig
from binascii import hexlify, unhexlify
import SHTC3 as sh
import LPS22HB as lp
import ICM20948 as ic
import time
import math
import serial
from datetime import datetime
import struct

# Convert to decimal degrees
def convert_to_decimal(degrees, direction):
    if direction in ['N','S']:
        decimal = float(degrees[:2]) + float(degrees[2:]) / 60
    if direction in ['E','W']:
        decimal = float(degrees[:3]) + float(degrees[3:]) / 60
    return decimal

def extract_gps(nmea):
    # Split the sentence into parts
    parts = nmea.split(',')

    # Extract latitude and longitude
    timestr = parts[1]
    latitude = parts[2]
    latitude_direction = parts[3]
    longitude = parts[4]
    longitude_direction = parts[5]
    altitude = parts[9]

    latitude_decimal = convert_to_decimal(latitude, latitude_direction)
    longitude_decimal = convert_to_decimal(longitude, longitude_direction)
    altitude_meters = float(altitude)

    gps = {"latitude": latitude_decimal, "longitude": longitude_decimal, "altitude": altitude_meters, "time": timestr}
    gps["latitude_hex"] = struct.pack('<d', gps["latitude"]).hex()  # struct.unpack('<d', unhexlify(str_double2hex))[0]
    gps["longitude_hex"] = struct.pack('<d', gps["longitude"]).hex()

    return gps


PRESS_DATA = 0.0
TEMP_DATA = 0.0
u8Buf=[0,0,0]

lora = LoRa(spi_channel=1, interrupt_pin=25, my_address=10, spi_port = 0, reset_pin=22, freq=915, tx_power=14,
      modem_config=ModemConfig.Bw125Cr45Sf128, acks=False, crypto=None)


GPS_BAUD = 9600
GPS = serial.Serial('/dev/serial0', GPS_BAUD, timeout=1)

shtc3 = sh.SHTC3(sh.sbc, 1, sh.SHTC3_I2C_ADDRESS)

lps22hb = lp.LPS22HB()

icm20948 = ic.ICM20948()
icm20948.icm20948_Gyro_Accel_Read()
icm20948.icm20948MagRead()
icm20948.icm20948CalAvgValue()

time.sleep(0.1)

if GPS.in_waiting > 0:
   gps_data = GPS.readline().decode('utf-8').strip()
   if gps_data.startswith('$GPGGA'):
      print(gps_data)
      monitor = extract_gps(gps_data)


      lps22hb.LPS22HB_START_ONESHOT()
      if (lps22hb._read_byte(lp.LPS_STATUS)&0x01)==0x01:  # a new pressure data is generated
         u8Buf[0]=lps22hb._read_byte(lp.LPS_PRESS_OUT_XL)
         u8Buf[1]=lps22hb._read_byte(lp.LPS_PRESS_OUT_L)
         u8Buf[2]=lps22hb._read_byte(lp.LPS_PRESS_OUT_H)
         PRESS_DATA=((u8Buf[2]<<16)+(u8Buf[1]<<8)+u8Buf[0])/4096.0

      if (lps22hb._read_byte(lp.LPS_STATUS)&0x02)==0x02:   # a new pressure data is generated
         u8Buf[0]=lps22hb._read_byte(lp.LPS_TEMP_OUT_L)
         u8Buf[1]=lps22hb._read_byte(lp.LPS_TEMP_OUT_H)
         TEMP_DATA=((u8Buf[1]<<8)+u8Buf[0])/100.0

      icm20948.imuAHRSupdate(ic.MotionVal[0] * 0.0175, ic.MotionVal[1] * 0.0175, ic.MotionVal[2] * 0.0175,
            ic.MotionVal[3],ic.MotionVal[4],ic.MotionVal[5],
            ic.MotionVal[6],ic.MotionVal[7],ic.MotionVal[8])
      pitch = math.asin(-2 * ic.q1 * ic.q3 + 2 * ic.q0* ic.q2)* 57.3
      roll  = math.atan2(2 * ic.q2 * ic.q3 + 2 * ic.q0 * ic.q1, -2 * ic.q1 * ic.q1 - 2 * ic.q2* ic.q2 + 1)* 57.3
      yaw   = math.atan2(-2 * ic.q1 * ic.q2 - 2 * ic.q0 * ic.q3, 2 * ic.q2 * ic.q2 + 2 * ic.q3 * ic.q3 - 1) * 57.3

      monitor["TempTH"] = shtc3.SHTC3_Read_TH()
      monitor["Humidity"] = shtc3.SHTC3_Read_RH()
      monitor["TempPR"] = TEMP_DATA
      monitor["Pressure"] = PRESS_DATA
      monitor["Roll"] = roll
      monitor["Pitch"] = pitch
      monitor["Yaw"] = yaw
      monitor["ax"] = ic.Accel[0]
      monitor["ay"] = ic.Accel[1]
      monitor["az"] = ic.Accel[2]
      monitor["Gx"] = ic.Gyro[0]
      monitor["Gy"] = ic.Gyro[1]
      monitor["Gz"] = ic.Gyro[2]
      monitor["Bx"] = ic.Mag[0]
      monitor["By"] = ic.Mag[1]
      monitor["Bz"] = ic.Mag[2]

      print(monitor)

      gx = struct.pack('<f', monitor["Gx"]).hex()
      gy = struct.pack('<f', monitor["Gy"]).hex()
      gz = struct.pack('<f', monitor["Gz"]).hex()

      message = f'{monitor["latitude_hex"]:<16}:{monitor["longitude_hex"]:<16}:{gx:<8}:{gy:<8}:{gz:<8}'
      lora.send(message.encode('utf-8'),255)
