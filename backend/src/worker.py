import os
import time
from pathlib import Path
from datetime import datetime, timezone

path = Path("/run/dealer-renewal/worker")
path.parent.mkdir(parents=True, exist_ok=True)
while True:
    path.write_text(datetime.now(timezone.utc).isoformat())
    time.sleep(3)
