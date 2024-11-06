from mojo import context
import drivers

# create a listener for display feedback
def get_display_listener(ui, display):
    def listener(event):
        nonlocal ui, display
        power_button = ui[1].port[1].channel[9]
        pic_mute_button = ui[1].port[1].channel[210]
        try:
            data = str(event.arguments["data"].decode())
        except UnicodeDecodeError as err:
            context.log.error(f"{err=}")
        # update driver state
        display[1].recv_buffer += data
        display[1].update_state()
        if "touchpad" in ui[0]:
            # update button state
            power_button.value = display[1].power_is_on
            pic_mute_button.value = display[1].pic_mute_is_on
        elif "keypad" in ui[0]:
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
        switcher[1].update_state(data)
        if "touchpad" in ui[0]:
            ui[1].port[1].channel[31] = switcher[1].input_three_is_active
            ui[1].port[1].channel[32] = switcher[1].input_four_is_active
            ui[1].port[1].channel[33] = switcher[1].input_six_is_active
            ui[1].port[1].channel[26] = switcher[1].volume_is_muted
            ui[1].port[1].level[1] = switcher[1].get_normalized_volume()*255
        elif "keypad" in ui[0]:
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
        if "switcher" in device_id:
            switchers[room_name] = (device_id, drivers.ExtronDriver(muse_device))
    return switchers


def populate_displays(device_ids):
    displays = {}
    for device_id in device_ids:
        muse_device = context.devices.get(device_id)
        room_name = parse_device_id(device_id)
        if "monitor" in device_id:
            displays[room_name] = (device_id, drivers.LGDriver(muse_device))
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
            uis[room_name] = (device_id, muse_device)
        elif "touchpad" in device_id:
            uis[room_name] = (
                device_id,
                muse_device,
            )
        # TODO implement touchpad support
    return uis


# populate the lists and dictionaries; create and register watchers and listeners
def setup_rooms(event=None):
    # remove built in devices
    device_ids = prune_devices(
        list(context.devices.ids()), ("franky", "led", "idevice")
    )
    rooms = populate_rooms(device_ids)
    switchers = populate_switchers(device_ids)
    displays = populate_displays(device_ids)
    uis = populate_uis(device_ids)
    for room in rooms:
        print(f"setting up room {room}")
        display = displays[room][1]
        switcher = switchers[room][1]
        # setup button watchers for room
        if "touchpad" in uis[room][0]:
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
        # register watchers
        for key, action in buttons.items():
            port = int(key.split("/")[1])
            id = int(key.split("/")[3])
            uis[room][1].port[port].button[id].watch(action)

        # register feedback listeners with muse devicesa
        displays[room][1].device.receive.listen(
            get_display_listener(uis[room], displays[room])
        )
        switchers[room][1].device.receive.listen(
            get_switcher_listener(uis[room], switchers[room])
        )
    


# get controller context
muse = context.devices.get("idevice")
print("starting script")
# setup rooms when controller comes online
muse.online(setup_rooms)

print("script complete")