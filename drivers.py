import mojo


class LGDriver:

    # commands
    POWER_OFF_COMMAND = "ka 00 00\x0D"
    POWER_ON_COMMAND = "ka 00 01\x0D"
    PIC_MUTE_OFF_COMMAND = "kd 0 00\x0D"
    PIC_MUTE_ON_COMMAND = "kd 1 01\x0D"
    # acknowledgements
    POWER_ON_ACK = "a 01 OK01x\x0D"
    POWER_OFF_ACK = "a 01 OK00x\x0D"
    PIC_MUTE_ON_ACK = "d 01 OK01x\x0D"
    PIC_MUTE_OFF_ACK = "d 01 OK00x\x0D"

    def __init__(self, device):
        self.is_powered = False
        self.pic_is_muted = False
        self.device = device

    def update_state(self, cls, feedback):
        lines = feedback.split("\x0D")
        for line in lines:
            match line:
                case cls.POWER_OFF_ACK:
                    self.is_powered = False
                case cls.POWER_ON_ACK:
                    self.is_powered = True
                case cls.PIC_MUTE_OFF_ACK:
                    self.pic_is_muted = False
                case cls.PIC_MUTE_ON_ACK:
                    self.pic_is_muted = True

    def toggle_power(self):
        print("toggle power")
        if self.is_powered:
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
        if self.pic_is_muted:
            return self.PIC_MUTE_OFF_COMMAND
        else:
            return self.PIC_MUTE_ON_COMMAND


import mojo
import threading
import time


class ExtronDriver:

    SOURCE_THREE_COMMAND = "3!\r"
    SOURCE_FOUR_COMMAND = "4!\r"
    SOURCE_SIX_COMMAND = "6!\r"

    VOLUME_DELTA = 10
    MIN_VOLUME = -500
    MAX_VOLUME = 0
    SLEEP_TIME = 0.1

    input_three_is_active = False
    input_four_is_active = False
    input_six_is_active = False
    volume_level = -400

    def __init__(self, device):
        self.is_ramping_up = threading.Event()
        self.is_ramping_down = threading.Event()
        self.device = device
        self.input_three_is_active = False
        self.input_four_is_active = False
        self.input_six_is_active = False
        self.volume_level = -400

    def update_state(self, feedback):
        lines = feedback.split("\r\n")
        for line in lines:
            print(line)
            match line:
                case "In03 All":
                    self.input_three, self.input_four, self.input_six = (
                        True,
                        False,
                        False,
                    )
                case "In04 All":
                    self.input_three, self.input_four, self.input_six = (
                        False,
                        True,
                        False,
                    )
                case "In06 All":
                    self.input_three, self.input_four, self.input_six = (
                        False,
                        False,
                        True,
                    )
        if line.startswith("GrpmD2"):
            self.volume_is_muted = line.split("*")[1]
        elif line.startswith("GrpmD1"):
            self.volume_level = int(line.split("*")[1])

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

    def select_source_three(self):
        print("select_source_three")
        self.device.send(self.SOURCE_THREE_COMMAND)

    def select_source_four(self):
        print("select_source_four")
        self.device.send(self.SOURCE_FOUR_COMMAND)

    def select_source_six(self):
        print("select_source_six")
        self.device.send(self.SOURCE_SIX_COMMAND)
