import sys
import os
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import main

audio = main.encode_to_audio("Garuda its working")
# Add noise
noise = np.random.normal(0, 0.05, len(audio) + 48000).astype(np.float32)
noise[24000:24000+len(audio)] += audio
audio = noise

print("Simulating Receiver on main.py audio...")
buf = audio.tolist()

state = 0
carrier_count = 0
data_bits = []
pos = 0

SAMPLES_PER_BIT = main.SAMPLES_PER_BIT

while pos + SAMPLES_PER_BIT < len(buf):
    if state == 0:
        step = SAMPLES_PER_BIT // 4
        chunk = np.array(buf[pos:pos+SAMPLES_PER_BIT], dtype=np.float32)
        bit = main.detect_bit(chunk)
        if bit == 1:
            carrier_count += 1
            if carrier_count > 6:
                state = 1
                print("Carrier detected!")
        else:
            carrier_count = 0
        pos += step
        
    elif state == 1:
        step = SAMPLES_PER_BIT // 4
        chunk = np.array(buf[pos:pos+SAMPLES_PER_BIT], dtype=np.float32)
        bit = main.detect_bit(chunk)
        if bit == 0:
            print("Start bit locked!")
            state = 2
            data_bits.clear()
            pos += int(SAMPLES_PER_BIT * 1.5)
        else:
            pos += step
            
    elif state == 2:
        chunk = np.array(buf[pos:pos+SAMPLES_PER_BIT], dtype=np.float32)
        bit = main.detect_bit(chunk)
        print("bit:", bit)
        if bit == -1:
            print("Lost signal.")
            from crypto import from_bits, decrypt
            try:
                payload = from_bits(data_bits)
                res = decrypt(payload)
                if res: print("DECODED:", res)
            except: pass
            break
        data_bits.append(bit)
        pos += SAMPLES_PER_BIT
        
        if len(data_bits) % 80 == 0 and len(data_bits) >= 80:
            try:
                from crypto import from_bits, decrypt
                payload = from_bits(data_bits)
                if len(payload) >= 13:
                    result = decrypt(payload)
                    if result:
                        print("DECODED:", result)
                        break
            except Exception as e:
                print("Error decoding:", e)
