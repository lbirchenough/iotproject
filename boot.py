# boot.py - ESP8266 Optimized
import gc
import esp
# Turn off vendor OS debug messages to save a tiny bit of resources
esp.osdebug(None)

# Run a full collection immediately
gc.collect()

# Set a threshold: automatically clean when 4KB is allocated
gc.threshold(4096)