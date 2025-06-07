import serial    # 직렬포트를 이용하기 위한 라이브러리
import time
import re        # 출력된 문자열로부터 패턴에 따라 정보 추출
import numpy as np
import os

arduino_port = 'COM17'
baud_rate = 115200
pattern = r'[+-]?\b\d+\.\d+\b|\b\d+'   # 문자열에서 실수와 정수를 추출하는 정규표현식

ser = serial.Serial(arduino_port, baud_rate, timeout=1)   # 직렬포트 설정
time.sleep(1.5)  # 직렬포트 연결하는데 충분히 기다리는 시간

def write_to_arduino(data, interval):   # 직렬포트로 문자열을 보내고 결과를 받는 함수
    ser.write(data.encode())  # 아두이노로 데이터 보내기
    time.sleep(interval)  # 아두이노가 데이터를 처리하는 것을 기다리는 시가
    response = ser.readline().decode('utf-8').strip()  # Read the response
    return response

Rp = 100   # 양의 단자쪽 전류를 측정하기 위한 저항크기
Rm = 100   # 음의 단자쪽 전류를 측정하기 위한 저항크기 
points = 51
interval = 0.1
filepath = "c:/Temp"
filename = "vi3.csv"

fullname = os.path.join(filepath, filename)
Vps = np.linspace(0,5, points + 1)   # 0~5V 사이 전압배열
Vms = np.linspace(0,5, points + 1)   # 0~5V 사이 전압배열

# 결과 저장할 파일을 생성하고 첫번째 줄에 헤더 저장
with open(fullname, "w") as file:
    file.writelines("Vp_set,Vm_set,Rp,Rm,Vp_mea,Vm_mea,Vp_DUT,Vm_DUT,Ip,Im,V_DUT,I_DUT\n")
    file.close()

for Vp in Vps:
    for Vm in Vms:  # 전압을 바꾸어가며 아두이노로 측정조건을 문자열로 송수신
        data_to_send = "%.2f %s %.2f %s" % (Vp, Rp, Vm, Rm)
        response = write_to_arduino(data_to_send + "\r\n", interval)
        data_read = re.findall(pattern, response)  # 받은 결과를 정규식 표현에
        print(f"{response}")                       # 따라 숫자만 추출해서 배열로
        print(data_read)
        print()
        with open(fullname, "a") as file:  # 한줄 측정결과 추가하여 붙임임
            file.writelines(",".join(data_read) + '\n')
            file.close()
ser.close()   # 직렬포트 닫기