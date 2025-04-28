# amx_muse
An example of using muse to support multiple support multiple systems using the muse-ipcomm extension.

Installation:
Clone to your local machine, modify as needed, then upload the script to your muse controller and run it using the Muse VScode extension.
Once the script is running it will automatically poll the muse configuration to detect new devices as you add them.

Usage:
1. Using the controllers web-console, add devices to your muse controller using the folowing namin convention:
    {building}-{room}-{device}-{number} where device may be 'touchpad','switcher',
    'display', 'projector' or 'keypad'.
    e,g,:
    nsb-209-switcher-1
2. Configure the drivers as appropriate for your devices
3. modify the script as nessecary to reflect the function of your button channels
4. Upload the script to the muse controller

When the script runs it will load all devices by name and group them by room number.
Currently, this script supports rooms with a single display, a single switcher, and a
touchpad using the button addressing found in index.py. There is also a timeline configured
which will periodically poll muse for new devices and add them to the system without 
needing to restart the script. In this example, basic drivers are provided for an
Extron switcher and an LG display. The ipcomm driver for the extron switcher has been 
tested using the ssh client, and the lg driver has been tested using the tcp driver.