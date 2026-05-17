import sounddevice as sd
import numpy as np

devices = sd.query_devices()
print("WASAPI Devices:")
for i, d in enumerate(devices):
    if d['hostapi'] == 2 and 'CABLE' not in d['name']:
        print(f"[{i}] {d['name']} (In: {d['max_input_channels']})")

print("\nCABLE Devices:")
for i, d in enumerate(devices):
    if d['hostapi'] == 2 and 'CABLE' in d['name']:
        print(f"[{i}] {d['name']} (In: {d['max_input_channels']}, Out: {d['max_output_channels']})")
