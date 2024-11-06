import mojo
import threading
import time
import io
from collections import deque


class LGDriver:

    # commands
    POWER_OFF_COMMAND = "ka 00 00\x0D"
    POWER_ON_COMMAND = "ka 00 01\x0D"
    PIC_MUTE_OFF_COMMAND = "kd 0 00\x0D"
    PIC_MUTE_ON_COMMAND = "kd 1 01\x0D"
    # acknowledgements
    POWER_ON_ACK = "a 01 OK01x"
    POWER_OFF_ACK = "a 01 OK00x"
    PIC_MUTE_ON_ACK = "d 01 OK01x"
    PIC_MUTE_OFF_ACK = "d 01 OK00x"
    # errors
    POWER_ON_ERROR = "a 01 NG01x" #returned when powered on monitor is asked to power on

    def __init__(self, device_id, device):
        self.device_id = device_id
        self.device = device
        self.power_is_on = False
        self.pic_mute_is_on = False
        self.recv_buffer = ''
        

    def update_state(self):
        lines = []
        # consume buffer, appending lines to lines, leaving unterminated lines in the buffer
        while 'x' in self.recv_buffer:
            items = self.recv_buffer.partition('x')
            line = items[0]+items[1]
            self.recv_buffer = items[2]
            print(f"{line=}\n{self.recv_buffer=}")
            lines.append(line)
        for line in lines:
            print(f"{line=}")
            match line:
                case self.POWER_OFF_ACK:
                    self.power_is_on = False
                case self.POWER_ON_ACK | self.POWER_ON_ERROR:
                    self.power_is_on = True
                case self.PIC_MUTE_OFF_ACK:
                    self.pic_mute_is_on = False
                case self.PIC_MUTE_ON_ACK:
                    self.pic_mute_is_on = True

    def toggle_power(self):
        print("toggle power")
        if self.power_is_on:
            self.device.send(self.POWER_OFF_COMMAND)
        else:
            self.device.send(self.POWER_ON_COMMAND)

    def power_off(self):
        print("power off")
        self.device.send(self.POWER_OFF_COMMAND)

    def power_on(self):
        print("power on")
        self.device.send(self.POWER_ON_COMMAND)

    def toggle_pic_mute(self):
        print("toggle pic mute")
        if self.pic_mute_is_on:
            self.device.send(self.PIC_MUTE_OFF_COMMAND)
        else:
            self.device.send(self.PIC_MUTE_ON_COMMAND)


class ExtronDriver:

    SWITCHER_PASSWORD = "changeme"

    SOURCE_THREE_COMMAND = "3!\r"
    SOURCE_FOUR_COMMAND = "4!\r"
    SOURCE_SIX_COMMAND = "6!\r"
    VOL_MUTE_OFF_COMMAND = '\x1BD2*0GRPM\r\n'
    VOL_MUTE_ON_COMMAND = '\x1BD2*1GRPM\r\n'

    VOLUME_DELTA = 10
    MIN_VOLUME = -500
    MAX_VOLUME = 0
    SLEEP_TIME = 0.1

    input_three_is_active = False
    input_four_is_active = False
    input_six_is_active = False
    volume_level = -400

    def __init__(self, device_id, device):
        self.is_ramping_up = threading.Event()
        self.is_ramping_down = threading.Event()
        self.device_id = device_id
        self.device = device
        self.input_three_is_active = False
        self.input_four_is_active = False
        self.input_six_is_active = False
        self.volume_level = -400
        self.volume_is_muted = False
    
    #returns volume as a percentage of the MIN_VOLUME - MAX_VOLUME  range
    def get_normalized_volume(self):
        range = self.MAX_VOLUME - self.MIN_VOLUME
        offset = 0-self.MIN_VOLUME
        normalized_volume = (self.volume_level + offset)/range
        return normalized_volume    

    def update_state(self, feedback):
        lines = feedback.split("\r\n")
        for line in lines:
            print(line)
            if line.startswith("In03 All"):
                    self.input_three_is_active, self.input_four_is_active, self.input_six_is_active = (
                        True,
                        False,
                        False,
                    )
            elif line.startswith("In04 All"):
                    self.input_three_is_active, self.input_four_is_active, self.input_six_is_active = (
                        False,
                        True,
                        False,
                    )
            elif line.startswith("In06 All"):
                    self.input_three_is_active, self.input_four_is_active, self.input_six_is_active = (
                        False,
                        False,
                        True,
                    )
            if line.startswith("GrpmD2"):
                self.volume_is_muted = False if (line.split("*")[1]) == '0' else True
            elif line.startswith("GrpmD1"):
                self.volume_level = int(line.split("*")[1])
                print(f"{self.volume_level=}")
            elif line.startswith("Password:"):
                self.device.send(f"{self.SWITCHER_PASSWORD}\r")
           

    def ramp_volume_up(self):
        while self.is_ramping_up.is_set():
            target_volume_level = min(
                self.volume_level + self.VOLUME_DELTA, self.MAX_VOLUME
            )
            self.device.send(f"\x1BD1*{target_volume_level}GRPM\r\n")
            print("vol up")
            time.sleep(self.SLEEP_TIME)

    def ramp_volume_down(self):
        while self.is_ramping_down.is_set():
            target_volume_level = max(
                self.volume_level - self.VOLUME_DELTA, self.MIN_VOLUME
            )
            self.device.send(f"\x1BD1*{target_volume_level}GRPM\r\n")
            time.sleep(self.SLEEP_TIME)
            print("vol down")

    def start_volume_ramp_up(self):
        self.is_ramping_up.set()
        thread = threading.Thread(target=self.ramp_volume_up)
        thread.start()

    def stop_volume_ramp_up(self):
        self.is_ramping_up.clear()

    def start_volume_ramp_down(self):
        self.is_ramping_down.set()
        thread = threading.Thread(target=self.ramp_volume_down)
        thread.start()

    def stop_volume_ramp_down(self):
        self.is_ramping_down.clear()

    def toggle_vol_mute(self):
        print("toggle vol mute")
        # TODO send toggle vol mute command
        print(f"{self.volume_is_muted=}")
        if self.volume_is_muted:
            print("sending mute off")
            self.device.send(self.VOL_MUTE_OFF_COMMAND)
        else:
            print("sending mute on")
            self.device.send(self.VOL_MUTE_ON_COMMAND)

    def select_source_three(self):
        print("select_source_three")
        print(self.device)
        self.device.send(self.SOURCE_THREE_COMMAND)

    def select_source_four(self):
        print("select_source_four")
        self.device.send(self.SOURCE_FOUR_COMMAND)

    def select_source_six(self):
        print("select_source_six")
        self.device.send(self.SOURCE_SIX_COMMAND)
