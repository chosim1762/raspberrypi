# https://076923.github.io/posts/Python-tkinter-1/
# https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_tk_sgskip.html

import tkinter
import tkinter.ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,NavigationToolbar2Tk)
from matplotlib.figure import Figure
from scipy.optimize import curve_fit
import time
from random import random
from random import seed
from datetime import datetime
import gpib
import re
import logging
import queue
#import threading

import json
import csv
import pytz
import os

data = [{'V': 1, 'I': 0.5},{'V': 3, 'I': 1.5} ]

def create_csv(data,mode):
    fn = datetime.now().astimezone(pytz.timezone('Asia/Seoul')).strftime("%Y%m%d_%H%M%S.csv")
    current_directory = os.getcwd()
    fn = os.path.join(current_directory, 'data', '%s_%s' % (mode, fn))
    # Open a CSV file for writing
    with open(fn, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # Write the header
        header = data[0].keys()
        writer.writerow(header)

        # Write the data
        for row in data:
            writer.writerow(row.values())
    return data


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.text_widget.after(100, self.poll_queue)  # Start polling message from the queue

    def close(self):
        self.queue.join()

    def emit(self, record):
        self.queue.put(record)

    def poll_queue(self):
        # Check every 100 ms if there is a new message in the queue to display
        while not self.queue.empty():
            msg = self.queue.get(block=False)
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tkinter.END, self.format(msg) + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tkinter.END)  # Autoscroll to the bottom
            self.queue.task_done()
        self.text_widget.after(100, self.poll_queue)


class LogWidget(tkinter.Frame):
    def __init__(self, logfile=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tkinter.Button(self, text='Clear', command=self.clear).grid(row=0, column=0)

        self.text = tkinter.Text(self, wrap='none', borderwidth=0)
        text_vsb = tkinter.Scrollbar(self, orient='vertical', command=self.text.yview)
        text_hsb = tkinter.Scrollbar(self, orient='horizontal', command=self.text.xview)
        self.text.configure(yscrollcommand=text_vsb.set, xscrollcommand=text_hsb.set, font='TkFixedFont')

        self.text.grid(row=1, column=0, sticky='nsew')
        text_vsb.grid(row=1, column=1, sticky='ns')
        text_hsb.grid(row=2, column=0, sticky='ew')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.pack(side='top', fill='both', expand=True)

        self.text_handler = TextHandler(self.text)
#        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        self.text_handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.addHandler(self.text_handler)
        logger.setLevel(logging.INFO)

    def destroy(self):
        logging.getLogger().removeHandler(self.text_handler)

    def clear(self):
        self.text.configure(state='normal')
        self.text.delete('1.0', tkinter.END)
        self.text.configure(state='disabled')

def main():
    param = {}
    data = {}
    status = ''

    window = tkinter.Tk()
    window.title("Device Characteristiscis Measurement")
    window.geometry("640x480+250+250")
    window.resizable(False, False)

    menubar = tkinter.Menu(window)
    menu_1 = tkinter.Menu(menubar, tearoff=0)
    menu_1.add_command(label="Manual")
    menubar.add_cascade(label="About", menu=menu_1)

    menu_2 = tkinter.Menu(menubar, tearoff=0)
    menu_2.add_command(label="HP4140B")
    menu_2.add_command(label="SI1260")
    menu_2.add_command(label="Exit", command=window.quit)
    menubar.add_cascade(label="Setting", menu=menu_2)

    m1 = tkinter.PanedWindow(window, orient=tkinter.HORIZONTAL)
    m1.pack(fill='both',expand=True)

    controlFrame = tkinter.Frame(m1)
    controlFrame.pack(side='left',fill='both',expand=False)
    m1.add(controlFrame)
    m2 = tkinter.PanedWindow(m1, orient=tkinter.VERTICAL)
    m2.pack(fill='both', expand=True)
    m1.add(m2)

    plotFrame = tkinter.Frame(m2)
    plotFrame.pack(side='right', fill='both', expand=True)
    m2.add(plotFrame, stretch='always')

    logger = LogWidget(master=m2)
    logger.pack(fill='both', expand=True)
    m2.add(logger, height=200)

    notebook = tkinter.ttk.Notebook(controlFrame, width=80, height=100)
    notebook.pack(side="left", fill="both")

    frame1 = tkinter.Frame(controlFrame)
    notebook.add(frame1, text="4140")

    frame2 = tkinter.Frame(controlFrame)
    notebook.add(frame2, text="1260")

    frame3 = tkinter.Frame(controlFrame)
    notebook.add(frame3, text="Memo")

    frame4 = tkinter.Frame(plotFrame, relief="solid")
    frame4.pack(side="right", fill="both", expand=False)

    # Design of the Setting Window at Frame1 for Gate Voltage
    Vds_Label = tkinter.Label(frame1, text="Setting Vds", fg="red", relief="flat")
    Vds_Label.grid(row=0,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    StartVd_Label = tkinter.Label(frame1, text="Start Va(V)")
    StartVd_Label.grid(row=1,column=0)
    startvd_val = tkinter.StringVar()
    startvd_val.set(0)
    StartVd = tkinter.Entry(frame1, text=startvd_val)
    StartVd.grid(row=1,column=1)

    StopVd_Label = tkinter.Label(frame1, text="Stop Va(V)")
    StopVd_Label.grid(row=2,column=0)
    stopvd_val = tkinter.StringVar()
    stopvd_val.set(1)
    StopVd = tkinter.Entry(frame1, text=stopvd_val)
    StopVd.grid(row=2,column=1)

    StepDNum_Label = tkinter.Label(frame1, text="Step Va(V)")
    StepDNum_Label.grid(row=3,column=0)
    stepdnum_val = tkinter.StringVar()
    stepdnum_val.set(0.1)
    StepDNum = tkinter.Entry(frame1, text=stepdnum_val)
    StepDNum.grid(row=3,column=1)

    HoldD_Label = tkinter.Label(frame1, text="Hold(s)")
    HoldD_Label.grid(row=4,column=0)
    holdd_val = tkinter.StringVar()
    holdd_val.set(2)
    HoldD = tkinter.Entry(frame1, text=holdd_val)
    HoldD.grid(row=4,column=1)

    DelayD_Label = tkinter.Label(frame1, text="Delay(s)")
    DelayD_Label.grid(row=5,column=0)
    delayd_val = tkinter.StringVar()
    delayd_val.set(0.5)
    DelayD = tkinter.Entry(frame1, text=delayd_val)
    DelayD.grid(row=5,column=1)

    s1 = tkinter.ttk.Separator(frame1,orient="horizontal")
    s1.grid(row=6,column=0,columnspan=2,sticky='nsew')

    # Design of the Setting Window at Frame2 for Drain-Source Voltage
    Vgs_Label = tkinter.Label(frame1, text="Setting Vgs", fg="red", relief="flat")
    Vgs_Label.grid(row=7,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    StartVg_Label = tkinter.Label(frame1, text="Start Vb(V)")
    StartVg_Label.grid(row=8,column=0)
    startvg_val = tkinter.StringVar()
    startvg_val.set(0)
    StartVg = tkinter.Entry(frame1, text=startvg_val)
    StartVg.grid(row=8,column=1)

    StopVg_Label = tkinter.Label(frame1, text="Stop Vb(V)")
    StopVg_Label.grid(row=9,column=0)
    stopvg_val = tkinter.StringVar()
    stopvg_val.set(1)
    StopVg = tkinter.Entry(frame1, text=stopvg_val)
    StopVg.grid(row=9,column=1)

    StepGNum_Label = tkinter.Label(frame1, text="Step Vb(V)")
    StepGNum_Label.grid(row=10,column=0)
    stepgnum_val = tkinter.StringVar()
    stepgnum_val.set(1)
    StepGNum = tkinter.Entry(frame1, text=stepgnum_val)
    StepGNum.grid(row=10,column=1)

    HoldG_Label = tkinter.Label(frame1, text="Hold (s)")
    HoldG_Label.grid(row=11,column=0)
    holdg_val = tkinter.StringVar()
    holdg_val.set(2)
    HoldG = tkinter.Entry(frame1, text=holdg_val)
    HoldG.grid(row=11,column=1)

    DelayG_Label = tkinter.Label(frame1, text="Delay (s)")
    DelayG_Label.grid(row=12,column=0)
    delayg_val = tkinter.StringVar()
    delayg_val.set(2)
    DelayG = tkinter.Entry(frame1, text=delayg_val)
    DelayG.grid(row=12,column=1)

    checkgoption = tkinter.IntVar()
    checkG_Scale = tkinter.Checkbutton(frame1, text="Sweep?",variable=checkgoption)
    checkG_Scale.grid(row=13,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    s2 = tkinter.ttk.Separator(frame1,orient="horizontal")
    s2.grid(row=14,column=0,columnspan=2,sticky='nsew')

    # Design of the Setting Window at Frame2 for Impedance meter
    Bias_Label = tkinter.Label(frame2, text="Setting Bias", fg="red", relief="flat")
    Bias_Label.grid(row=0,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    BiasAC_Label = tkinter.Label(frame2, text="ac amp(V)")
    BiasAC_Label.grid(row=1,column=0)
    biasac_val = tkinter.StringVar()
    biasac_val.set(0.1)
    BiasAC = tkinter.Entry(frame2, text=biasac_val)
    BiasAC.grid(row=1,column=1)

    BiasDC_Label = tkinter.Label(frame2, text="dc Off(V)")
    BiasDC_Label.grid(row=2,column=0)
    biasdc_val = tkinter.StringVar()
    biasdc_val.set(0)
    BiasDC = tkinter.Entry(frame2, text=biasdc_val)
    BiasDC.grid(row=2,column=1)

    s3 = tkinter.ttk.Separator(frame2,orient="horizontal")
    s3.grid(row=3,column=0,columnspan=2,sticky='nsew')

    # Design of the Setting Window at Frame2 for Drain-Source Voltage
    Freq_Label = tkinter.Label(frame2, text="Setting Frequency", fg="red", relief="flat")
    Freq_Label.grid(row=4,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    StartF_Label = tkinter.Label(frame2, text="Start(Hz)")
    StartF_Label.grid(row=5,column=0)
    startf_val = tkinter.StringVar()
    startf_val.set(10)
    StartF = tkinter.Entry(frame2, text=startf_val)
    StartF.grid(row=5,column=1)

    StopF_Label = tkinter.Label(frame2, text="Stop(Hz)")
    StopF_Label.grid(row=6,column=0)
    stopf_val = tkinter.StringVar()
    stopf_val.set(1000000)
    StopF = tkinter.Entry(frame2, text=stopf_val)
    StopF.grid(row=6,column=1)

    StepF_Label = tkinter.Label(frame2, text="Step #")
    StepF_Label.grid(row=7,column=0)
    stepfnum_val = tkinter.IntVar()
    stepfnum_val.set(20)
    StepFNum = tkinter.Entry(frame2, text=stepfnum_val)
    StepFNum.grid(row=7,column=1)

    checkfoption = tkinter.IntVar(value=1)
    checkF_Scale = tkinter.Checkbutton(frame2, text="Log Scale?",variable=checkfoption)
    checkF_Scale.grid(row=8,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    s4 = tkinter.ttk.Separator(frame2,orient="horizontal")
    s4.grid(row=9,column=0,columnspan=2,sticky='nsew')


    # Show the result of the measurement
    label4 = tkinter.Label(frame4, text="Measured Data")
    label4.pack()

    fig = Figure(figsize=(5,4),dpi=100)
    ax = fig.add_subplot(111)
    x = np.array([])
    y = np.array([])
    line, = ax.plot(x, y, "o", markersize=11, markerfacecolor='white',markeredgecolor='blue') # linestyle=":", marker="*", color="#524FA1")
    ax.grid()
#    ax.legend()

    canvas = FigureCanvasTkAgg(fig, master=frame4)
    #canvas.draw()

    # pack_toolbar=False will make it easier to use a layout manager later on.
    toolbar = NavigationToolbar2Tk(canvas, frame4)
    toolbar.update()

    canvas.mpl_connect("key_press_event", lambda event: print(f"you pressed {event.key}"))
    canvas.mpl_connect("key_press_event", key_press_handler)

    canvas.get_tk_widget().pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)



    def generate_source(option):
        if option['LinearSweep']:
            UnitVs = np.linspace(option['Start'], option['Stop'], option['Step'], endpoint=True)
        else:
            UnitVs0 = np.linspace(np.log10(option['Start']), np.log10(option['Stop']), option['Step'], endpoint=True)
            UnitVs = np.power(10, UnitVs0)
        return UnitVs

    def update_data(mode):
        global param
        check_variable()
        if mode == "VI":
            option = {'Start': param['StartVd'],'Stop': param['StopVd'],'Step': param['StepDNum'], \
                      'Hold': param['HoldD'], 'Delay': param['DelayD'],'DualSweep':True,'LinearSweep':True}

            optionG = {'Start': param['StartVg'],'Stop': param['StopVg'],'Step': param['StepGNum'], \
                      'Hold': param['HoldG'], 'Delay': param['DelayG'],'DualSweep':True,'LinearSweep': True, \
                      'Sweep': bool(param['G_logscale'])}

            Vgs = np.arange(optionG['Start'], optionG['Stop'], optionG['Step'])
            if not optionG['Stop'] in Vgs:
                Vgs = np.concatenate((Vgs, np.array([optionG['Stop']])))

            con = gpib.dev(0,4)
            Vs = []
            Is = []
            Vgsweep = []

            for vg in Vgs:
                pb_volt = vg
                print('Vg: %.2f' % vg)
                comm_sweep = 'PS%.2f;PT%.2f,PE%.2f;NPH%.1f;PD%.1f,PB%.2f\n' % (option['Start'], option['Stop'], \
                          option['Step'], option['Hold'], option['Delay'], pb_volt)

                gpib.write(con, 'F2A4B1RA1I1L2M3\n')
                gpib.write(con, comm_sweep)
                gpib.write(con, 'W1\n')

                while True:
                    val = gpib.read(con,23 * 1).decode('ascii')
                    V = float(re.findall("A[+-].{5}", val)[0].replace('A',''))
                    Vs.append(V)
                    Vgsweep.append(vg)
                    if val[1:2] == 'N':
                        print('%s' % val)
                        I = float(re.findall("NI[+-].{9}", val)[0].replace('NI',''))
                        Is.append(I)
                    if val[1:2] == 'L':
                        I = float(re.findall("LI[+-].{9}", val)[0].replace('LI',''))
                        Is.append(I)
                        print('%s' % val)
                        break

                data['VI'] = {'V': Vs, 'I': Is, 'Vg': Vgsweep}

                if optionG['Sweep'] == False:
                    break
                else:
                    time.sleep(optionG['Hold'])
                    continue

            data_json = []
            for i in range(len(Vs)):
                data_json.append({'V': Vs[i], 'I': Is[i], 'Vg': Vgsweep[i]})
            csv = create_csv(data_json, 'VI')

            logging.info('VI measurements done')
            line.set_data(np.array(Vs), np.array(Is))
            ax.set_xlabel("V (V)")
            ax.set_ylabel("I (A)")

        if mode == "Z":
            option = {'Start': param['StartF'],'Stop': param['StopF'],'Step': int(param['StepFNum']), \
               'BiasAC': param['BiasAC'], 'BiasDC' : param['BiasDC'], 'LinearSweep': not bool(param['F_logscale'])}
            freqs = generate_source(option)

            con = gpib.dev(0,6)

            # reset device and use default configuration
            gpib.write(con, '*RST\n')  # Reset
            time.sleep(1)
            gpib.write(con, '*SRE16\n') # Sets the service request enble register to the 16 bit
            time.sleep(1)
            gpib.write(con, 'OS 0\n') # Set the separator as comma  (if 1, terminator)
            time.sleep(1)
            gpib.write(con, 'RH 1\n')  # Set the heading as 'on'  (if 0, off)

            # configure data output
            gpib.write(con, 'OP 1,0\n')  # Set the RS423 off
            gpib.write(con, 'OP 2,1\n')  # Set the GPIB, all
            gpib.write(con, 'OP 3,0\n')  # Set File, off
            gpib.write(con, 'RH 0\n')   # Set Heading off (if 1, on)

            print('F (Hz), Z (Ohm), Phase (deg)')
            vac, vdc = option['BiasAC'], option['BiasDC']

            fs = []
            Zrs = []
            Zis = []
            amps = []
            phas = []

            gpib.write(con, 'GT0\n')  # Generator Type: 0 (Volage), 1 (Current)
            gpib.write(con, 'VA ' + str(vac) + '\n')
            gpib.write(con, 'VB ' + str(vdc) + '\n')
            gpib.write(con, 'SW 0\n')

            for freq in freqs:
                # configure generator output
#                gpib.write(con, 'GT0\n')  # Generator Type: 0 (Volage), 1 (Current)
                gpib.write(con, 'FR ' + str(freq) + '\n')
#                gpib.write(con, 'VA ' + str(vac) + '\n')
#                gpib.write(con, 'VB ' + str(vdc) + '\n')

                # turn off sweep
#                gpib.write(con, 'SW 0\n')

                # acquire single measurement
                time.sleep(1)
                gpib.write(con, 'SI\n')
#                time.sleep(2)

                output = gpib.read(con,50).decode('ascii')
                print(output)
                output = output.split(',')
                frequency = float(output[0])
                Z_real = float(output[1])
                Z_imag = float(output[2])
                amps.append(np.sqrt(Z_real**2 + Z_imag**2))
                phas.append(np.arctan2(Z_imag, Z_real) * 180 / np.pi)

                print([frequency, Z_real, Z_imag])
                fs.append(frequency)
                Zrs.append(Z_real)
                Zis.append(Z_imag)

            data['Z'] = {'f': fs, 'Zr': Zrs, 'Zi': Zis}

            data_json = []
            for i in range(len(fs)):
               data_json.append({'f': fs[i], 'Zr': Zrs[i], 'Zi': Zis[i], 'amplitude': amps[i], 'phase': phas[i]})

            print(create_csv(data_json,'Z'))

            logging.info('impedance spectroscopy done')
            line.set_data(np.array(Zrs), -np.array(Zis))
            ax.set_xlabel("Z'(Ohm)")
            ax.set_ylabel('-Z"(Ohm)')

        ax.relim()
        ax.autoscale_view()
        canvas.draw()

    def save_data(mode):
        print(mode)
        print(data)

    def check_variable():
        global param
        param = { 'StartVg': float(startvg_val.get()), 'StopVg': float(stopvg_val.get()), \
             'StepGNum': float(stepgnum_val.get()), 'HoldG': float(holdg_val.get()), \
             'G_logscale': int(checkgoption.get()), 'DelayD': float(delayd_val.get()), 'DelayG': float(delayg_val.get()), \
             'StartVd': float(startvd_val.get()), 'StopVd': float(stopvd_val.get()),  \
             'StepDNum': float(stepdnum_val.get()), 'HoldD': float(holdd_val.get()), \
             'StartF': float(startf_val.get()), 'StopF': float(stopf_val.get()), \
             'StepFNum': float(stepfnum_val.get()), 'F_logscale': int(checkfoption.get()),\
             'BiasAC': float(biasac_val.get()), 'BiasDC': float(biasdc_val.get()) }

    # action tab
    # https://coderslegacy.com/python/tkinter-lambda/

    MeasureIV_Button = tkinter.Button(frame1,text="Measure",command=lambda: update_data("VI"),width=15,overrelief="solid",repeatdelay=1000,repeatinterval=100)
    MeasureIV_Button.grid(row=15,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)
    SaveIV_Button = tkinter.Button(frame1,text="Save",command=lambda: save_data("VI"),width=15,overrelief="solid",repeatdelay=1000,repeatinterval=100)
    SaveIV_Button.grid(row=16,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    MeasureZ_Button = tkinter.Button(frame2,text="Measure",command=lambda: update_data("Z"),width=15,overrelief="solid",repeatdelay=1000,repeatinterval=100)
    MeasureZ_Button.grid(row=10,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)
    SaveZ_Button = tkinter.Button(frame2,text="Save",command=lambda: save_data("Z"),width=15,overrelief="solid",repeatdelay=1000,repeatinterval=100)
    SaveZ_Button.grid(row=11,column=0,columnspan=2,sticky=tkinter.N+tkinter.W)

    Check_Button = tkinter.Button(frame3,text="Check",command=check_variable,overrelief="solid",repeatdelay=1000,repeatinterval=100)
    Check_Button.pack()

    logging.info('Ready for measurement')

    window.config(menu=menubar)
    window.mainloop()


if __name__ == "__main__":
    main()
