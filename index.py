from mojo import context
import drivers


class DeviceRecord:
    def __init__(self,device_id,muse_device):
        self.device_id = device_id
        self.muse_device = muse_device
        self.kind = device_id.split("-")[2]
        self.driver = None
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
        print(vars(self))#!

class DeviceRegistry:
    def __init__(self):
        self.device_records = set()
    
    # update registry with a list of muse device id
    def update(self, muse_device_ids):

        muse_device_ids = set(muse_device_ids)
        current_device_ids = set(device_record.device_id for device_record in self.device_records)  # Get device_ids from the new list
       
        # Remove devices that are no longer defined in muse
        dropped_devices = set()
        for record in list(self.device_records):
            if record.device_id not in current_device_ids:
                dropped_devices.add(record)
        self.device_records = self.device_records - dropped_devices        
       
        # Add new device records
        new_device_ids = muse_device_ids - current_device_ids
        new_device_records = set()

        for device_id in new_device_ids:
            muse_device = context.devices.get(device_id)
            new_record = DeviceRecord(device_id, muse_device)
            new_device_records.add(new_record)  # Add new DeviceRecord
        self.device_records = self.device_records | new_device_records
        
    def get_display_records(self):
        return [record for record in self.device_records if record.kind in ("monitor","projector")]
    
    def get_ui_records(self):
        return [record for record in self.device_records if record.kind in ("keypad","touchpad")]
    
    def get_switcher_records(self):
        return [record for record in self.device_records if record.kind == "switcher"]
    
    def get_rooms(self):
        return {record.room for record in self.device_records}
    
    #Return the next record of that type for the given room
    def get_display_record_by_room(self,room):
        #displays = self.get_display_records()
        #print(f"{displays=}")
        #for display in displays:
        #    print(f"{display.room} and {room}")
        #    if display.room == room:
        #        return display
        return next(iter(r for r in self.device_records if (r.room == room) and r.kind in ("monitor","projector")), None)
    
    def get_ui_record_by_room(self,room):
        return next(iter(r for r in self.device_records if (r.room == room) and r.kind in ("keypad","touchpad")), None)
    
    def get_switcher_record_by_room(self,room):
        return next(iter(r for r in self.device_records if (r.room == room) and (r.kind == "switcher")), None)
    
# create a listener for display feedback
def get_display_listener(ui, display):
    print("inside display listener")#!
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
    print("inside switcher listener")#!
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

    device_registry = DeviceRegistry()
    device_registry.update(device_ids)
    print(f"{device_registry=}")#!
    switchers = device_registry.get_switcher_records()
    uis = device_registry.get_ui_records()
    displays = device_registry.get_display_records()

    for room in device_registry.get_rooms():
        print(f"setting up room {room}")
        device_records = [device for device in device_registry.device_records if device.room==room]
        print(f"{device_records=}")#!
        for device_record in device_records:
            # setup button watchers for room
            display_record = device_registry.get_display_record_by_room(room)
            switcher_record = device_registry.get_switcher_record_by_room(room)
            ui_record = device_registry.get_ui_record_by_room(room)
            print(f"Line 160: {display_record=} and {switcher_record=}")#!
            if not display_record or not switcher_record:
                continue
            if device_record.kind == "touchpad":
                print("setting up room")#!
                buttons = {
                    # muse listeners must accept an event argument. event.value tells you if the you are handling a press or release
                    # executes function on push, executes noop on release
                    "port/1/button/9": lambda event: (
                        display_record.toggle_power() if event.value else None
                    ),
                    "port/1/button/210": lambda event: (
                        display_record.toggle_pic_mute() if event.value else None
                    ),
                    "port/1/button/24": lambda event: (
                        switcher_record.start_volume_ramp_up()
                        if event.value
                        else switcher_record.stop_volume_ramp_up()
                    ),
                    "port/1/button/25": lambda event: (
                        switcher_record.start_volume_ramp_down()
                        if event.value
                        else switcher_record.stop_volume_ramp_down()
                    ),
                    "port/1/button/26": lambda event: (
                        switcher_record.toggle_vol_mute() if event.value else None
                    ),
                    "port/1/button/31": lambda event: (
                        switcher_record.select_source_three() if event.value else None
                    ),
                    "port/1/button/32": lambda event: (
                        switcher_record.select_source_four() if event.value else None
                    ),
                    "port/1/button/33": lambda event: (
                        switcher_record.select_source_six() if event.value else None
                    ),
                }
                print(f"Buttons configured for {room}")
                # register watchers
                for key, action in buttons.items():
                    port = int(key.split("/")[1])
                    id = int(key.split("/")[3])
                    ui_record.muse_device.device.port[port].button[id].watch(action)
                    print(f"Button watchers registered for {room}")

            # register feedback listeners with muse devices
            display_record.muse_device.device.receive.listen(
                get_display_listener(ui_record.muse_device, display_record.driver)
            )
            switcher_record.muse_device.device.receive.listen(
                get_switcher_listener(ui_record.muse_device, switcher_record.driver)
            )

tick = context.services.get("timeline") 
tick.start([10000],True,-1) 

# get controller context
muse = context.devices.get("idevice")
print("starting script")
# setup rooms when controller comes online
muse.online(setup_rooms)

print("script complete")

