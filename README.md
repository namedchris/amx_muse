# amx_muse
An example of using muse to support multiple support multiple systems using the muse-ipcomm extension.

Usage:
1. Add devices to your muse controller using the folowing namin convention:
    {building}-{room}-{device}-{number} where device may be 'touchpad','switcher', 'display', etc
    e,g,:
    nsb-209-switcher-1
    Use the ipcomm driver appropriate for your applicaton
2. modify the script as nessecary to reflect the your button channels
3. Upload the script to the muse controller

When the script runs it will load all devices by name group them by room number.