# restart_program.py
import os, sys, time, threading
from datetime import datetime, timedelta


# How many seconds until the next target time (h:m)
def _seconds_until(reboot_hour, reboot_minute=0):
    now = datetime.now()
    target = now.replace(hour=reboot_hour, minute=reboot_minute, second=0, microsecond=0)
    if target <= now:  # if today’s time has passed, schedule for tomorrow
        target += timedelta(days=1)
    return int((target - now).total_seconds())


# Start a background thread that restarts this script daily at h:m
def schedule_daily_restart(reboot_hour, reboot_minute=0):
    def loop():
        while True:
            time.sleep(_seconds_until(reboot_hour, reboot_minute))  # wait until the right time
            os.execv(sys.executable, [sys.executable] + sys.argv)
            # replaces the current process with a fresh one

    threading.Thread(target=loop, daemon=True).start()


def restart_now():
    os.execv(sys.executable, [sys.executable] + sys.argv)
