import os
import time
from datetime import date 
import pandas as pd
import threading  
# GUI LIB
import PySimpleGUI as sg 
# LSL LIB
from pylsl import StreamInfo, StreamOutlet, IRREGULAR_RATE
import argparse
import signal
# SOUND
import pygame
import random

from p300 import P300Test  # <-- your revised P300Test class (shown below)

# ============ GLOBALS / INITIALIZATION ============

# Event counters 
counter = 0

# Init Pygame
pygame.init()
pygame.mixer.init()

sound1 = pygame.mixer.Sound('audio/440Hz_500ms.mp3')
sound1.set_volume(0.2)
sound2 = pygame.mixer.Sound('audio/440Hzsquare5sec.mp3')
sound2.set_volume(0.2)

is_auto_beep = False
start_stop = True

# Heartbeat timing
heartbeat_update = time.time()

# ============ CSV LOG SETUP ============
today = date.today()
file_path = f'data/{today}.csv'
if os.path.exists(file_path):
    # File exists; append new log row for "APP START"
    df = pd.read_csv(file_path, index_col=False)
else:
    # Create new file
    df = pd.DataFrame(columns=['ux time', 'human time', 'message'])
df.loc[len(df.index)] = [time.time_ns(),
                         time.strftime("%H:%M:%S", time.localtime()),
                         "APP START"]
df.to_csv(file_path, index=False)

# ============ THEME SETUP ============
sg.set_options(font="ModeSeven 12")
sg.LOOK_AND_FEEL_TABLE['my_matrix_theme'] = {
    'BACKGROUND': '#0D0208',
    'TEXT': '#00FF41',
    'INPUT': '#202729',
    'TEXT_INPUT': '#008F11',
    'SCROLL': '#008F11',
    'BUTTON': ('#0D0208', '#00FF41'),
    'PROGRESS': ('#D1826B', '#CC8019'),
    'BORDER': 0,
    'SLIDER_DEPTH': 0,
    'PROGRESS_DEPTH': 0
}
sg.theme('my_matrix_theme')

# ============ LSL OUTLET SETUP ============
parser = argparse.ArgumentParser(description="Stream heartbeat clock and annotation with LSL")
parser.add_argument("--source", default="MirkoTabarnk")
parser.add_argument("--id", default="Mirko_id")
args = parser.parse_args()

info = StreamInfo(args.source, 'Markers', 1, 0, 'string', args.id)
outlet = StreamOutlet(info)

def handler(signum, frame):
    res = input("Ctrl-c was pressed. Do you really want to exit? y/n ")
    if res == 'y':
        exit(1)

signal.signal(signal.SIGINT, handler)

# ============ LSL SEND FUNCTION ============
def send_lsl_timestamp(outlet, msg):
    """
    Directly push an LSL sample with the provided `msg` plus a time-based suffix.
    """
    my_message = f"{msg} t:{time.time_ns()}"
    outlet.push_sample([my_message])

# ============ THREAD FOR LSL (Optional) ============
class thread_send_lsl_timestamp(threading.Thread):
    """
    Sends an LSL message in a separate thread non-blocking. 
    """
    def __init__(self, thread_id, outlet, msg):
        super().__init__()
        self.thread_id = thread_id
        self.outlet = outlet
        self.msg = msg

    def run(self):
        send_lsl_timestamp(self.outlet, self.msg)

# ============ LOGGING UTILITY ============
def log_message_to_csv_and_screen(msg):
    """
    Appends a [timestamp, human-readable-time, message] row to `df`
    and prints to the GUI log box. Also returns the row.
    """
    clicked_time = time.time_ns()
    human_time = time.strftime("%H:%M:%S", time.localtime())
    row = [clicked_time, human_time, msg]
    df.loc[len(df.index)] = row
    window["-LOGBOX-"].print(row)
    return row

def start_timestamp_threads(msg, thread_id=""):
    """
    1) Log the message to CSV + GUI
    2) Start a thread to send LSL so it's non-blocking
    """
    log_message_to_csv_and_screen(msg)
    t = thread_send_lsl_timestamp(thread_id, outlet, msg)
    t.start()

# ============ P300 SETUP ============
# Callback so that whenever P300 plays a tone, we log it / send LSL
def send_p300_message(frequency):
    p300_msg = f"P300 TONE {frequency}Hz"
    start_timestamp_threads(p300_msg, "P300_TONE")

p300_test = P300Test(tone_callback=send_p300_message)

# ============ RANDOM SOUND THREAD ============
def call_random_function():
    while is_auto_beep:
        time.sleep(random.randint(4, 8))
        if not is_auto_beep:
            break
        sound1.play()
        start_timestamp_threads("AUTO_BEEP")

# ============ GUI SETUP ============
layout = [
    [sg.Button("TRIGGER", key="-TRIGGER-"),
     sg.Button("BEEP", key="-BEEP-"), 
     sg.Button("AUTO BEEP ON", key="-AUTO_BEEP-"), 
     sg.Button("START", key="-RECORDING-"),
     sg.Button("START P300", key="-P300-")],
    [sg.HSeparator()],
    [sg.Button("DRIBBLE", key="-DRIBBLE-"),
     sg.Button("SHOT", key="-SHOT-"),
     sg.Button("RELEASE", key="-RELEASE-"),
     sg.Text("COUNT: ", key="-COUNTER-", size=(15, 1))],
    [sg.HSeparator()],
    [sg.Button("SEND", key="-SEND-", bind_return_key=True), sg.Input("", key="-MESSAGE-")],
    [sg.HSeparator()],
    [sg.Multiline(size=(66, 10), key='-LOGBOX-')]
]

window = sg.Window("TEST V10", layout, keep_on_top=True, location=(500, 125))

# ============ MAIN LOOP ============
while True:
    event, values = window.read(timeout=1000)

    # -- Window closed --
    if event == sg.WIN_CLOSED:
        df.to_csv(file_path, index=False)
        is_auto_beep = False
        # If we had a random beep thread, shutting it down
        start_timestamp_threads("APP END", "END")
        print("---------DATA SAVED------------")
        break

    # -- P300 Start/Stop --
    if event == "-P300-":
        if p300_test.running:
            # STOP
            p300_test.stop()
            window["-P300-"].update("START P300")
            start_timestamp_threads("P300 STOPPED", "P300")
        else:
            # START
            threading.Thread(target=p300_test.start, daemon=True).start()
            window["-P300-"].update("STOP P300")
            start_timestamp_threads("P300 STARTED", "P300")

    # -- TRIGGER --
    if event == "-TRIGGER-":
        start_timestamp_threads("TRIGGER", "TRIGGER")

    # -- BEEP --
    if event == "-BEEP-":
        sound1.play()
        start_timestamp_threads("BEEP", "BEEP")

    # -- RANDOM BEEP ON/OFF --
    if event == "-AUTO_BEEP-":
        is_auto_beep = not is_auto_beep
        if is_auto_beep:
            window['-AUTO_BEEP-'].update('AUTO BEEP OFF')
            start_timestamp_threads("AUTO BEEP START", "AUTO_BEEP")
            threading.Thread(target=call_random_function, daemon=True).start()
        else:
            window['-AUTO_BEEP-'].update('AUTO BEEP ON')
            start_timestamp_threads("AUTO BEEP ENDS", "AUTO_BEEP")

    # -- RECORDING START/STOP --
    if event == "-RECORDING-":
        start_stop = not start_stop
        if start_stop:
            window['-RECORDING-'].update('START')
            start_timestamp_threads("STOP", "RECORDING")
        else:
            window['-RECORDING-'].update('STOP')
            start_timestamp_threads("START", "RECORDING")
        sound2.play()

    # -- SEND CUSTOM MSG --
    if event == "-SEND-":
        custom_msg = values["-MESSAGE-"]
        start_timestamp_threads(custom_msg, "MESSAGE")
        window["-MESSAGE-"].update("")

    # -- BALL / DRIBBLE / SHOT / RELEASE --
    if event == "-DRIBBLE-":
        start_timestamp_threads("DRIBBLE", "MESSAGE")

    if event == "-SHOT-":
        counter += 1
        window['-COUNTER-'].update(f'COUNT: {counter}')
        start_timestamp_threads(f"SHOT COUNT: {counter}", "MESSAGE")

    if event == "-RELEASE-":
        start_timestamp_threads("RELEASE", "MESSAGE")

    # -- HEARTBEAT every 5s --
    if time.time() - heartbeat_update > 5:
        start_timestamp_threads("H", "HEARTBEAT")
        heartbeat_update = time.time()

window.close()
