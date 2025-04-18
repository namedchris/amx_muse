from mojo import context
import drivers


class DeviceRecord:
    def __init__(self,device_id,muse_device):
        self.device_id = device_id
        self.muse_device = muse_device
        self.kind = device_id.split("-")[3]
        match self.kind:
            case "switcher":
                self.driver = drivers.ExtronDriver(device_id, muse_device)
            case "touchpad":
                self.driver = drivers.TouchpadDriver(device_id, muse_device)
            case "keypad":
                self.driver =  drivers.KeyPadDriver(device_id, muse_device)
            case "monitor":
                self.driver = drivers.LGDriver(device_id, muse_device)
            case "projector":
                self.driver = drivers.EpsonDriver(device_id,muse_device)
        split_id = device_id.split("-")
        self.room = "-".join(split_id[:2])


class DeviceRegistry:
    def __init__(self):
        self.devices_records = set()
    
    # update registry with a list of muse devices
    def update(self, devices):
        current_device_ids = set(device.device_id for device in devices)  # Get device_ids from the new list
        
        # Remove devices that are no longer in the framework's list
        for record in list(self.device_records):
            if record.device_id not in current_device_ids:
                self.device_records.remove(record)  # Remove dropped devices

        # Add new devices or update existing ones
        for device in devices:
            new_record = DeviceRecord(device.device_id, device)
            if new_record not in self.device_records:
                self.device_records.add(new_record)  # Add new DeviceRecord

    def get_display_records(self):
        return [record for record in self.device_records if record.kind in ("monitor","projector")]
    
    def get_ui_records(self):
        return [record for record in self.device_records if record.kind in ("keypad","touchpadr")]
    
    def get_switcher_records(self):
        return [record for record in self.device_records if record.kind == "switcher"]

# create a listener for display feedback
def get_display_listener(ui, display):
    def listener(event):
        nonlocal ui, display
        try:
            data = str(event.arguments["data"].decode())
        except UnicodeDecodeError as err:
            context.log.error(f"{err=}")
        # update driver state
        display.recv_buffer += data
        display.update_state()
        if "touchpad" in ui.device_id:
            # update button state
            power_button = ui.device.port[1].channel[9]
            pic_mute_button = ui.device.port[1].channel[210]
            power_button.value = display.power_is_on
            pic_mute_button.value = display.pic_mute_is_on
        elif "keypad" in ui.device_id:
            # TODO implement keypad support
            pass



# create a listener for switchers
def get_switcher_listener(ui, switcher):
    def listener(event):
        nonlocal ui, switcher
        try:
            data = str(event.arguments["data"].decode())
        except UnicodeDecodeError as err:
            context.log.error(f"{err=}")
        switcher.update_state(data)
        if "touchpad" in ui.device_id:
            ui.device.port[1].channel[31] = switcher.input_three_is_active
            ui.device.port[1].channel[32] = switcher.input_four_is_active
            ui.device.port[1].channel[33] = switcher.input_six_is_active
            ui.device.port[1].channel[26] = switcher.volume_is_muted
            ui.device.port[1].level[1] = switcher.get_normalized_volume()*255
        elif "keypad" in ui.device_id:
            # TODO implement keypad support
            pass

    return listener


# remove built-in muse devices and return a set of rooms
def prune_devices(devices, prunings):
    devices = set(devices)
    prunings = set(prunings)
    return devices - prunings



# populate the lists and dictionaries; create and register watchers and listeners
def setup_rooms(event=None):
    # remove built in devices
    device_ids = prune_devices(
        list(context.devices.ids()), ("franky", "led", "idevice")
    )
    muse_devices = [context.devices.get(device_id) for device_id in device_ids if context.devices.get(device_id) is not None]
    device_registry = DeviceRegistry()
    device_registry.update(muse_devices)
    rooms = populate_rooms(device_ids)
    switchers = populate_switchers(device_ids)
    displays = populate_displays(device_ids)
    uis = populate_uis(device_ids)
    for room in rooms:
        print(f"setting up room {room}")
        if room in displays:
            display = displays[room]
        if room in switchers:
            switcher = switchers[room]
        # setup button watchers for room
        if "touchpad" in uis[room].device_id:
            buttons = {
                # muse listeners must accept an event argument. event.value tells you if the you are handling a press or release
                # executes function on push, executes noop on release
                "port/1/button/9": lambda event: (
                    display.toggle_power() if event.value else None
                ),
                "port/1/button/210": lambda event: (
                    display.toggle_pic_mute() if event.value else None
                ),
                "port/1/button/24": lambda event: (
                    switcher.start_volume_ramp_up()
                    if event.value
                    else switcher.stop_volume_ramp_up()
                ),
                "port/1/button/25": lambda event: (
                    switcher.start_volume_ramp_down()
                    if event.value
                    else switcher.stop_volume_ramp_down()
                ),
                "port/1/button/26": lambda event: (
                    switcher.toggle_vol_mute() if event.value else None
                ),
                "port/1/button/31": lambda event: (
                    switcher.select_source_three() if event.value else None
                ),
                "port/1/button/32": lambda event: (
                    switcher.select_source_four() if event.value else None
                ),
                "port/1/button/33": lambda event: (
                    switcher.select_source_six() if event.value else None
                ),
            }
            print(f"Buttons configured for {uis[room].device_id}")
        # register watchers
        for key, action in buttons.items():
            port = int(key.split("/")[1])
            id = int(key.split("/")[3])
            uis[room].device.port[port].button[id].watch(action)
            print(f"Button watchers registered for {uis[room].device_id}")

        # register feedback listeners with muse devicesa
        if room in displays:
            displays[room].device.receive.listen(
                get_display_listener(uis[room], displays[room])
            )
        if room in switchers:    
            switchers[room].device.receive.listen(
                get_switcher_listener(uis[room], switchers[room])
            )
    
async def setup_new_rooms():
    while True:
        setup_rooms()
        await(30)

# get controller context
muse = context.devices.get("idevice")
print("starting script")
# setup rooms when controller comes online
muse.online(setup_rooms)
try:
    device_detection_loop_task = asyncio.create_task(setup_new_rooms)
except asyncio.CancelledError:
    raise
print("script complete")

