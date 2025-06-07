import serial
import time
import re
import tkinter
import tkinter.ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,NavigationToolbar2Tk)
from matplotlib.figure import Figure

arduino_port = '/dev/ttyACM0'
baud_rate = 115200
pattern = r'[+-]?\b\d+\.\d+\b|\b\d+'   # 문자열에서 실수와 정수를 추출하는 정규표현식

ser = serial.Serial(arduino_port, baud_rate, timeout=1)   # 직렬포트 설정
time.sleep(1.5)  # 직렬포트 연결하는데 충분히 기다리는 시간

def write_to_arduino(data, interval):   # 직렬포트로 문자열을 보내고 결과를 받는 함수
    ser.write(data.encode())  # 아두이노로 데이터 보내기
    time.sleep(interval)  # 아두이노가 데이터를 처리하는 것을 기다리는 시가
    response = ser.readline().decode('utf-8').strip()  # Read the response
    return response

def measure_VI():
    global param

    Rp = float(param['Rp'].get())
    Rm = float(param['Rm'].get())
    points = int(param['Points'].get())
    interval = float(param['Interval'].get())

    Vps = np.linspace(0,5, points + 1)   # 0~5V 사이 전압배열
    Vms = np.linspace(0,5, points + 1)   # 0~5V 사이 전압배열

    param['x'] = []
    param['y'] = []

    for Vp in Vps:
        for Vm in Vms:
            data_to_send = "%.2f %s %.2f %s" % (Vp, Rp, Vm, Rm)
            response = write_to_arduino(data_to_send + "\r\n", interval)
            data_read = re.findall(pattern, response)  # 받은 결과를 정규식 표현에
            print(f"{response}")                       # 따라 숫자만 추출해서 배열로
            print(data_read)
            print()

            param['x'].append(float(data_read[10]))
            param['y'].append(float(data_read[11]))

            param['msg'].config(text="%s %s\n" % (data_read[10],data_read[11]),justify="left")

            param['plot_data'].set_data(np.array(param['x']),np.array(param['y']))
            print(f"{response}")

            param['plot_ax'].relim()
            param['plot_ax'].autoscale_view()

    param['canvas'].draw()


def saveSettingMenu(frame):
    global param

    Set_Label = tkinter.Label(frame, text='Save Environment', fg='red', relief='flat')
    Set_Label.grid(row=0,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    Path_Label = tkinter.Label(frame, text='Path')
    Path_Label.grid(row=1,column=0)
    Path_val = tkinter.StringVar()
    Path_val.set('/data')
    Path = tkinter.Entry(frame, text=Path_val)
    Path.grid(row=1,column=1)


# design the control panel
def controlSettingMenu(window,frame):
    global param

    Set_Label = tkinter.Label(frame, text='Parameters', fg='red', relief='flat')
    Set_Label.grid(row=0,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    Rp_Label = tkinter.Label(frame, text='Rp(ohm)')
    Rp_Label.grid(row=1,column=0)
    Rp_val = tkinter.StringVar()
    Rp_val.set(100)
    Rp = tkinter.Entry(frame, text=Rp_val)
    Rp.grid(row=1,column=1)
    param['Rp'] = Rp_val

    Rm_Label = tkinter.Label(frame, text='Rm(ohm)')
    Rm_Label.grid(row=2,column=0)
    Rm_val = tkinter.StringVar()
    Rm_val.set(100)
    Rm = tkinter.Entry(frame, text=Rm_val)
    Rm.grid(row=2,column=1)
    param['Rm'] = Rm_val

    Points_Label = tkinter.Label(frame, text='Points')
    Points_Label.grid(row=3,column=0)
    Points_val = tkinter.StringVar()
    Points_val.set(10)
    Points = tkinter.Entry(frame, text=Points_val)
    Points.grid(row=3,column=1)
    param['Points'] = Points_val

    Interval_Label = tkinter.Label(frame, text='Interval(s)')
    Interval_Label.grid(row=4,column=0)
    Interval_val = tkinter.StringVar()
    Interval_val.set(0.1)
    Interval = tkinter.Entry(frame, text=Interval_val)
    Interval.grid(row=4,column=1)
    param['Interval'] = Interval_val

    s1 = tkinter.ttk.Separator(frame,orient='horizontal')
    s1.grid(row=5,column=0,columnspan=2,sticky='nsew')

    MeasureIV_Button = tkinter.Button(frame,text='Measure',command=lambda: measure_VI(),width=15,overrelief='solid',repeatdelay=1000,repeatinterval=100)
    MeasureIV_Button.grid(row=6,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    End_Button = tkinter.Button(frame,text='End',command=window.quit,width=15,overrelief='solid',repeatdelay=1000,repeatinterval=100)
    End_Button.grid(row=7,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    Msg = tkinter.Label(frame,text="")
    Msg.grid(row=8,column=0,columnspan=2)

    param['msg'] = Msg


# Design the plotting region
def plotShowGraph(frame):
    global param

    Title_Label = tkinter.Label(frame, text='Measured Data')
    Title_Label.pack()

    fig = Figure(figsize=(5,4), dpi=100)
    ax = fig.add_subplot(111)
    x = np.array([])
    y = np.array([])
    line, = ax.plot(x, y, 'o', markersize=11, markerfacecolor='white', markeredgecolor='blue')

    ax.grid()
    canvas = FigureCanvasTkAgg(fig, master=frame)

    param['plot_data'] = line
    param['plot_ax'] = ax
    param['canvas'] = canvas

    toolbar = NavigationToolbar2Tk(canvas, frame)
    toolbar.update()

    canvas.mpl_connect("key_press_event", lambda event: print(f"you pressed {event.key}"))
    canvas.mpl_connect("key_press_event", key_press_handler)

    canvas.get_tk_widget().pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)



def main():
    global param

    param = {"x":[], "y":[]}

    window = tkinter.Tk()
    window.title("V-I Measurement")
    window.geometry("640x480+250+250")
    window.resizable(False, False)

    # Design a Paned Window

    m1 = tkinter.PanedWindow(window, orient=tkinter.HORIZONTAL)
    m1.pack(fill='both')

    controlFrame = tkinter.Frame(m1)
    controlFrame.pack(side='left',fill='both',expand=True)
    m1.add(controlFrame)

    plotFrame = tkinter.Frame(m1)
    plotFrame.pack(side='right',fill='both',expand=True)
    m1.add(plotFrame, stretch='always')

    # Design the left config window
    notebook = tkinter.ttk.Notebook(controlFrame, width=80, height=100)
    notebook.pack(side='left', fill='both')

    controlTabFrame1 = tkinter.Frame(controlFrame)
    notebook.add(controlTabFrame1, text='Measure')

    controlTabFrame2 = tkinter.Frame(controlFrame)
    notebook.add(controlTabFrame2, text='Setting')


    # Show the left control panel
    controlSettingMenu(window,controlTabFrame1)

    # Show the right plot panel
    plotShowGraph(plotFrame)

    saveSettingMenu(controlTabFrame2)

    window.mainloop()

if __name__ == "__main__":
    main()
