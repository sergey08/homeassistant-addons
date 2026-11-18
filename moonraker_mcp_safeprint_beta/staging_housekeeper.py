"""Private staging housekeeping; never contacts Moonraker or prints."""
import time
from moonraker_chunk_staging import cleanup_stale_parts, UploadError

INTERVAL_SECONDS = 24 * 60 * 60

def run_forever(sleep=time.sleep, cleanup=cleanup_stale_parts):
    while True:
        try:
            cleanup()
        except (UploadError, OSError) as exc:
            print("Staging housekeeping skipped:", type(exc).__name__, flush=True)
        sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_forever()
