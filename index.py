from mojo import context
import drivers

device_registry = None
class DeviceRecord:
    def __init__(self,device_id,muse_device):
        self.device_id = device_id
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
        
class DeviceRegistry:
    def __init__(self):
        self.device_records = set()
    
    # update registry with a list of muse device id
    def update(self, muse_device_ids):

        muse_device_ids = set(muse_device_ids)
        # get ids for all records
        current_device_ids = set(device_record.device_id for device_record in self.device_records)  # Get device_ids from the new list
       
        # make a set of device id that are no longer in the system
        dropped_device_ids = set()
        for device_id in list(current_device_ids):
            if device_id not in muse_device_ids:
                dropped_device_ids.add(device_id)
        # make a set if record that need removed from the registry
        dropped_device_records = {record for record in self.device_records if record.device_id in dropped_device_ids}
        self.device_records = self.device_records - dropped_device_records   

        # get ids for all records
        current_device_ids = set(device_record.device_id for device_record in self.device_records)  # Get device_ids from the new list
        # get a list of only new device ids so we don't override existing records
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
        rooms = {record.room for record in self.device_records}
        print(f"Current {rooms=}")
        return rooms
    
    #Return the next record of that type for the given room
    def get_display_record_by_room(self,room):
        return next(iter(r for r in self.device_records if (r.room == room) and r.kind in ("monitor","projector")), None)
    
    def get_ui_record_by_room(self,room):
        room_record = next(iter(r for r in self.device_records if (r.room == room) and r.kind in ("keypad","touchpad")), None)
        return room_record
    
    def get_switcher_record_by_room(self,room):
        return next(iter(r for r in self.device_records if (r.room == room) and (r.kind == "switcher")), None)
    
# create a listener for display feedback
def get_display_listener(ui_record, display_driver):
    def listener(event):
        nonlocal ui_record, display_driver
        try:
            print(data)
            data = str(event.arguments["data"].decode())
        except UnicodeDecodeError as err:
            context.log.error(f"{err=}")
        # update driver state
        display_driver.recv_buffer += data
        display_driver.update_state()
        print(F"Event on display: {data}")
        if "touchpad" in ui_record.device_id:
            # update button state
            power_button = ui_record.driver.device.port[1].channel[9]
            pic_mute_button = ui_record.driver.device.port[1].channel[210]
            power_button.value = display_driver.power_is_on
            pic_mute_button.value = display_driver.pic_mute_is_on
        elif "keypad" in ui_record.device_id:
            # TODO implement keypad support
            pass
    return listener

# create a listener for switchers
def get_switcher_listener(ui_record, switcher_driver):
    def listener(event):
        nonlocal ui_record, switcher_driver
        try:
            data = str(event.arguments["data"].decode())
        except UnicodeDecodeError as err:
            context.log.error(f"{err=}")
        print(F"Event on switcher: {data}") 
        switcher_driver.update_state(data)
        if "touchpad" in ui_record.device_id:
            ui_record.driver.device.port[1].channel[31] = switcher_driver.input_three_is_active
            ui_record.driver.device.port[1].channel[32] = switcher_driver.input_four_is_active
            ui_record.driver.device.port[1].channel[33] = switcher_driver.input_six_is_active
            ui_record.driver.device.port[1].channel[26] = switcher_driver.volume_is_muted
            ui_record.driver.device.port[1].level[1] = switcher_driver.get_normalized_volume()*255
        elif "keypad" in ui_record.device_id:
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
    global device_registry
    device_registry = DeviceRegistry()
    device_registry.update(device_ids)
    for room in device_registry.get_rooms():
        print(f"setting up room {room}")
        device_records = [device for device in device_registry.device_records if device.room==room]
        for device_record in device_records:
            # setup button watchers for room
            display_record = device_registry.get_display_record_by_room(room)
            switcher_record = device_registry.get_switcher_record_by_room(room)
            ui_record = device_registry.get_ui_record_by_room(room)
            # skip this room if it is missing a switcher or display
            if not display_record or not switcher_record:
                continue
            if device_record.kind == "touchpad":
                print("Setting up buttons for {ui_record.device_id}")#!
                buttons = {
                    # muse listeners must accept an event argument. event.value tells you if the you are handling a press or release
                    # executes function on push, executes noop on release
                    "port/1/button/9": lambda event: (
                        display_record.driver.toggle_power() if event.value else None
                    ),
                    "port/1/button/210": lambda event: (
                        display_record.driver.toggle_pic_mute() if event.value else None
                    ),
                    "port/1/button/24": lambda event: (
                        switcher_record.driver.start_volume_ramp_up()
                        if event.value
                        else switcher_record.driver.stop_volume_ramp_up()
                    ),
                    "port/1/button/25": lambda event: (
                        switcher_record.driver.start_volume_ramp_down()
                        if event.value
                        else switcher_record.driver.stop_volume_ramp_down()
                    ),
                    "port/1/button/26": lambda event: (
                        switcher_record.driver.toggle_vol_mute() if event.value else None
                    ),
                    "port/1/button/31": lambda event: (
                        switcher_record.driver.select_source_three() if event.value else None
                    ),
                    "port/1/button/32": lambda event: (
                        switcher_record.driver.select_source_four() if event.value else None
                    ),
                    "port/1/button/33": lambda event: (
                        switcher_record.driver.select_source_six() if event.value else None
                    ),
                }
                print(f"Buttons configured for {room}")
                # register watchers
                for key, action in buttons.items():
                    port = int(key.split("/")[1])
                    id = int(key.split("/")[3])
                    ui_record.driver.device.port[port].button[id].watch(action)
                    print(f"Adding button watcher for {port=} and {id=}")
                print(f"Button watchers registered for {room}")

        # register feedback listeners with muse devices
        print(f"adding display listener for {room}")
        display_record.driver.device.receive.listen(
            get_display_listener(ui_record, display_record.driver)
        )
        print(f"adding switcher listener for {room}")
        switcher_record.driver.device.receive.listen(
            get_switcher_listener(ui_record, switcher_record.driver)
        )

            

tick = context.services.get("timeline") 
tick.start([10000],True,-1) 

# get controller context
muse = context.devices.get("idevice")
print("starting script")
# setup rooms when controller comes online
muse.online(setup_rooms)

print("script complete")
