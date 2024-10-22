#Todo: put drivers in a driver module where they extend 'Driver'

from mojo import context
import driver



rooms = []

uis = {}
displays = {}
switchers = {}

power_toggle_functions = {}
power_on_functions = {}
power_off_functions = {}
pic_mute_toggle_functions = {}

#if different kinds of displays have different functions, the logic for that goes in this function
#but it seems simplest to abstract drivers behind a Python class
def get_display_functions(display): 
    power_toggle = display[1].toggle_power
    power_on = display[1].power_on
    power_off = display[1].power_off
    toggle_pic_mute = display[1].toggle_pic_mute
    return (power_toggle,power_on,power_off,toggle_pic_mute)


def display_listener(event, room):
    ui = uis[room]
    try:
        data = str(event.arguments['data'].decode())
    except UnicodeDecodeError as err:
        context.log.error(f"{err=}")
        raise
    items = data.split("\x0D")     
    if 'touchpad' in ui[0]:
        #get this rooms display buttons
        power_button = uis[room].port[1].channel[9]
        pic_mute_button = uis[room].port[1].channel[210]
        #update driver state
        for item in items:
            displays[room].update_state(item)
        #update button state    
        power_button.value = displays[room].power_is_on
        pic_mute_button.value = displays[room].pic_mute_is_on
    elif 'keypad' in ui[0]:
        #TODO implement keypad support
        pass

def load_devices():
    device_ids = context.devices.ids()
    print(device_ids)
    for device_id in device_ids:
        muse_device = context.devices.get(device_id)
        #build a set of rooms
        split_id = device_id.split('-')
        room_name = ('-'.join(split_id[:2]))
        rooms.append(room_name)
        #select proper driver based on device_id
        if 'keypad' in device_id:
            uis[room_name] = (device_id, muse_device) #extracting the device name from the device object later is trificult
        elif 'touchpad' in device_id:
            uis[room_name] = (device_id, muse_device) #so I stash it in a tuple here
        elif 'monitor' in device_id:
            displays[room_name] = (device_id, driver.lg_driver(muse_device)) #monitors use a python driver, so I add it to the tuple
        elif 'projector' in device_id:
            displays[room_name] = (device_id, driver.epson_driver(muse_device)) #projectors use a duet driver, so they don't need a python driver
        elif 'switcher' in device_id:
            switchers[room_name] = (device_id, driver.extron_driver(muse_device))

def setup_rooms():
    for room in rooms:
        # get display control funtions
        power_toggle_functions[room],
        power_on_functions[room],
        power_off_functions[room],
        pic_mute_toggle_functions[room] = get_display_functions(displays[room])
        #setup button watchers for room 
        if 'touchpad' in uis[room[0]]:
            buttons = {
                #muse listeners must accept an event argument. event.value tells you if the you are handling a press or release
                #executes function on push, executes noop on release
                "port/1/button/9": lambda event: power_toggle_functions[room] if event.value else None, #a funtion with no return is None, so I think thie works 
                "port/1/button/210": lambda event: pic_mute_toggle_functions[room] if event.value else lambda: None, #if muse needs a callable lambda: None shoule work as a noop
            }
        '''
        elif 'keypad' in uis[room[0]]:
            buttons = {
                "port/1/button/9": lambda event: power_on_functions[room],
                "port/1/button/10": lambda event: power_off_functions[room],
                "port/1/button/6": lambda event: pic_mute_toggle_functions[room],
                "port/1/button/12": lambda event: pass, 
                "port/1/button/13": lambda event: pass,
                "port/1/button/1": lambda event: pass,
                "port/1/button/2": lambda event: pass,
                "port/1/button/5": lambda event: pass,
            }
        '''
        if 'projector' in displays[room[0]]:
            pass
        elif 'monitor' in displays[room[0]]:
            pass
        if 'switcher' in switchers[room[0]]:
            pass    
        #register watchers
        for key, action in buttons.items():
            port = int(key.split('/')[1])
            id = int(key.split('/')[3])
            uis[room].port[port].button[id].watch(action)


    # register feedback listeners with muse devicesa
    displays[room][1].recieve.listen(display_listener)