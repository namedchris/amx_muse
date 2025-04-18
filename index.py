from mojo import context
import drivers
import asyncio

rooms = {}
uis = {}
displays = {}
switchers = {}

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

    return listener


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


# parse a device ID to get room name
def parse_device_id(device_id):
    split_id = device_id.split("-")
    room_name = "-".join(split_id[:2])
    return room_name


# remove built-in muse devices and return a set of rooms
def prune_devices(devices, prunings):
    devices = set(devices)
    prunings = set(prunings)
    return devices - prunings


# parse device IDs to make a set of rooms
def populate_rooms(devices):
    rooms = []
    for device_id in devices:
        rooms.append(parse_device_id(device_id))
    return set(rooms)


def populate_switchers(device_ids):
    switchers = {}
    for device_id in device_ids:
        muse_device = context.devices.get(device_id)
        room_name = parse_device_id(device_id)
        if "switcher" not in device_id:
            return switchers
        if device_id not in switchers.values():
            switchers[room_name] = drivers.ExtronDriver(device_id,muse_device)
    return switchers


def populate_displays(device_ids):
    displays = {}
    for device_id in device_ids:
        muse_device = context.devices.get(device_id)
        room_name = parse_device_id(device_id)
        if "monitor" in device_id:
            displays[room_name] = drivers.LGDriver(device_id, muse_device)
        elif "projector" in device_id:
            # TODO add projector support
            pass
    return displays


def populate_uis(device_ids):
    uis = {}
    for device_id in device_ids:
        muse_device = context.devices.get(device_id)
        room_name = parse_device_id(device_id)
        if "keypad" in device_id:
            uis[room_name] = drivers.KeypadDriver(device_id, muse_device)
        elif "touchpad" in device_id:
            uis[room_name] = drivers.TouchpadDriver(device_id,muse_device)
    return uis


# populate the lists and dictionaries; create and register watchers and listeners
def setup_rooms(event=None):
    # remove built in devices
    device_ids = prune_devices(
        list(context.devices.ids()), ("franky", "led", "idevice")
    )
    global devices
    devices = populate_rooms(device_ids)
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

def device_listener(tlEvent):
    setup_rooms()

tick = context.services.get("timeline") 
tick.start([10000],True,-1) 

# get controller context
muse = context.devices.get("idevice")
print("starting script")
# setup rooms when controller comes online
tick.expired.listen(device_listener)
muse.online(setup_rooms)
print("script complete")

