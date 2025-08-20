import os, sys, time, threading
from datetime import datetime, timedelta


# Find the seconds until a given hour and minute of the day
def _seconds_until(reboot_hour, reboot_minute=0):
    now = datetime.now()
    reboot_time = now.replace(hour=reboot_hour, minute=reboot_minute, second=0, microsecond=0)
    if reboot_time <= now:
        reboot_time += timedelta(days=1)
    return int((reboot_time - now).total_seconds())


# Start a background thread that restarts this script daily at reboot_hour:reboot_minute
def schedule_daily_restart(reboot_hour, reboot_minute=0):
    def loop():
        while True:
            delay = _seconds_until(reboot_hour, reboot_minute)
            time.sleep(delay)
            print(
                f"[{datetime.now()}] Restarting program (scheduled {reboot_hour:02d}:{reboot_minute:02d})...",
                flush=True,
            )
            # Replace the current process with a fresh instance
            os.execv(sys.executable, [sys.executable] + sys.argv)

    threading.Thread(target=loop, daemon=True).start()


def restart_now():
    print(
        f"[{datetime.now()}] Restarting program now...",
        flush=True,
    )
    # Replace the current process with a fresh instance
    os.execv(sys.executable, [sys.executable] + sys.argv)
