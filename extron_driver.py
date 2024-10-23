import muse
import threading
import time


class ExtronDriver:

    SOURCE_THREE_COMMAND = "3!\r"
    SOURCE_FOUR_COMMAND = "4!\r"
    SOURCE_SIX_COMMAND = "6!\r"

    VOLUME_DELTA = 10
    MIN_VOLUME = -500
    MAX_VOLUME = 0
    SLEEP_TIME = 0.05

    input_three_is_active = False
    input_four_is_active = False
    input_six_is_active = False
    volume_level = -400

    def __init__(self, device):
        self.is_ramping_up = threading.Event()
        self.is_ramping_dn = threading.Event()
        self.tcp_connection = device
        self.input_three_is_active = False
        self.input_four_is_active = False
        self.input_six_is_active = False
        self.volume_level = -400

    def update_state(self, feedback):
        lines = feedback.split("\r\n")
        for line in lines:
            match line:
                case "In03 All":
                    self.input_one, self.input_four, self.input_six = [
                        True,
                        False,
                        False,
                    ]
                case "In04 All":
                    self.input_one, self.input_four, self.input_six = [
                        False,
                        True,
                        False,
                    ]
                case "In06 All":
                    self.input_one, self.input_four, self.input_six = [
                        False,
                        False,
                        True,
                    ]
        if line.startswith("GrpmD2"):
            self.volume_is_muted = line.split("*")[1]
        elif line.startswith("GrpmD1"):
            self.volume_level = int(line.split("*")[1])

    def ramp_volume_up(self, cls):
        while self.is_ramping_up.is_set():
            target_volume_level = min(
                self.volume_level + cls.VOLUME_DELTA, cls.MAX_VOLUME
            )
            self.device.send(f"\x1BD1*{target_volume_level}GRPM\r\n")
            time.sleep(cls.SLEEP_TIME)

    def ramp_vol_down(self, cls):
        while self.is_ramping_dn.is_set():
            target_volume_level = max(
                self.volume_level - cls.VOLUME_DELTA, cls.MIN_VOLUME
            )
            self.device.send(f"\x1BD1*{target_volume_level}GRPM\r\n")
            time.sleep(cls.SLEEP_TIME)

    def start_volume_ramp_up(self):
        self.is_ramping_up.set()
        thread = threading.Thread(target=self.ramp_volume_up)
        thread.start()

    def stop_volume_ramp_up(self):
        self.is_ramping_up.clear()

    def start_volume_ramp_down(self):
        self.is_ramping_down.set()
        thread = threading.Thread(target=self.ramp_volume_down)

    def stop_volume_ramp_down(self):
        self.is_ramping_dn.clear
