from mojo import context
import driver


rooms = []

uis = {}
displays = {}
switchers = {}


# create a listener for display feedback
def get_display_listener(ui, display):
    def listener(event):
        nonlocal ui, display
        power_button = ui.port[1].channel[9]
        pic_mute_button = ui.port[1].channel[210]
        try:
            data = str(event.arguments["data"].decode())
        except UnicodeDecodeError as err:
            context.log.error(f"{err=}")
        # update driver state
        display.update_state(data)
        if "touchpad" in ui[0]:
            # update button state
            power_button.value = display.power_is_on
            pic_mute_button.value = display.pic_mute_is_on
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
        print(data)
        switcher.update_state(data)
        if "touchpad" in ui[0]:
            ui.port[1].channel[31] = switcher.input_three_is_active
            ui.port[1].channel[32] = switcher.input_four_is_active
            ui.port[1].channel[33] = switcher.input_six_is_active
            ui.port[1].channel[26] = switcher.vol_mute_is_active
            ui.port[1].level[1] = switcher.volume_level
        elif "keypad" in ui[0]:
            # TODO implement keypad support
            pass

    return listener


# populate the lists and dictionaries; create and register watchers and listeners
def setup_rooms(event=None):
    print("setting up rooms")
    device_ids = list(context.devices.ids())
    # remove built in devices
    # I need a better method of doing this
    # Sometimes these change, causing exceptions
    try:
        print(device_ids)
        device_ids.remove("franky")
        device_ids.remove("idevice")
        device_ids.remove("led")
        print(device_ids)
    except (ValueError, KeyError) as e:
        print(e)
    print(device_ids)
    for device_id in device_ids:
        muse_device = context.devices.get(device_id)
        # build a set of rooms
        split_id = device_id.split("-")
        room_name = "-".join(split_id[:2])
        if not room_name in rooms:
            print(f"adding {room_name} to room list")
            rooms.append(room_name)
            print(f"{rooms=}")
        # select driver based on device_id
        if "keypad" in device_id:
            uis[room_name] = (
                device_id,
                muse_device,
            )
        elif "touchpad" in device_id:
            uis[room_name] = (
                device_id,
                muse_device,
            )
        # can't find a way to get device_id from muse_device object so it gets stashed in a tuple
        elif "monitor" in device_id:
            displays[room_name] = (device_id, driver.LGDriver(muse_device))
        elif "projector" in device_id:
            # TODO add projector support
            pass
        elif "switcher" in device_id:
            switchers[room_name] = (device_id, driver.ExtronDriver(muse_device))
    for room in rooms:
        display = displays[room][1]
        switcher = switchers[room][1]
        # setup button watchers for room
        if "touchpad" in uis[room][0]:
            buttons = {
                # muse listeners must accept an event argument. event.value tells you if the you are handling a press or release
                # executes function on push, executes noop on release
                # a function with no return is None, so I think this works
                "port/1/button/9": lambda event: (
                    display.toggle_power() if event.value else None
                ),
                "port/1/button/210": lambda event: (
                    display.toggle_pic_mute() if event.value else None
                ),
                "port/1/button/24": lambda event: (
                    switcher.start_volume_ramp_up()
                    if event.value
                    else switcher.stop_volume_ramp_up
                ),
                "port/1/button/25": lambda event: (
                    switcher.start_volume_ramp_down()
                    if event.value
                    else switcher.stop_volume_ramp_down
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
        displays[room][1].device.recieve.listen(
            get_display_listener(uis[room], displays[room])
        )
        switchers[room][1].device.recieve.listen(
            get_switcher_listener(uis[room], switchers[room])
        )


# get controller context
muse = context.devices.get("idevice")
print("starting script")
# setup rooms when controller comes online
setup_rooms()
# muse.online(setup_rooms)
