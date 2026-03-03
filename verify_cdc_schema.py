from call_data_capture import CallDataCaptureEngine
import time
print("Initializing CDC Engine to trigger schema migration...")
engine = CallDataCaptureEngine() # Uses default path
time.sleep(2) # Give background thread time to run
print("Done.")
