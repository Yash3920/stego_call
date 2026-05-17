import sys
import os
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from crypto import encrypt, decrypt, to_bits, from_bits

SAMPLE_RATE = 48000
FREQ_ONE    = 1600
FREQ_ZERO   = 1200
TONE_AMP    = 0.1
TONE_DUR    = 0.1
SAMPLES_PER_BIT = int(SAMPLE_RATE * TONE_DUR)

def generate_tone(freq, duration):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * TONE_AMP).astype(np.float32)

def encode_to_audio(message: str) -> np.ndarray:
    bits = to_bits(encrypt(message))
    chunks = []
    chunks.append(generate_tone(FREQ_ONE, 1.0))
    chunks.append(generate_tone(FREQ_ZERO, TONE_DUR))
    for bit in bits:
        chunks.append(generate_tone(FREQ_ONE if bit == 1 else FREQ_ZERO, TONE_DUR))
    chunks.append(generate_tone(FREQ_ZERO, TONE_DUR))
    chunks.append(np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32))
    return np.concatenate(chunks)

def detect_bit(chunk: np.ndarray) -> int:
    fft   = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(len(chunk), 1 / SAMPLE_RATE)
    
    def energy(f):
        mask = (freqs >= f - 150) & (freqs <= f + 150)
        return np.sum(fft[mask])
        
    e1 = energy(FREQ_ONE)
    e0 = energy(FREQ_ZERO)
    
    print(f"e1: {e1:.2f}, e0: {e0:.2f}")
    if max(e1, e0) < 20.0:
        return -1
        
    return 1 if e1 > e0 else 0

audio = encode_to_audio("Garuda its working")
# Add noise and some random silence at start
noise = np.random.normal(0, 0.01, len(audio) + 20000).astype(np.float32)
noise[10000:10000+len(audio)] += audio
audio = noise

print("Simulating Receiver...")
buf = audio.tolist()

STATE_WAIT_CARRIER = 0
STATE_WAIT_START   = 1
STATE_READ_DATA    = 2
state = STATE_WAIT_CARRIER
carrier_count = 0
data_bits = []
pos = 0

while pos + SAMPLES_PER_BIT < len(buf):
    if state == STATE_WAIT_CARRIER:
        step = SAMPLES_PER_BIT // 4
        chunk = np.array(buf[pos:pos+SAMPLES_PER_BIT], dtype=np.float32)
        bit = detect_bit(chunk)
        if bit == 1:
            carrier_count += 1
            if carrier_count > 6:
                state = STATE_WAIT_START
                print("Carrier detected!")
        else:
            carrier_count = 0
        pos += step
        
    elif state == STATE_WAIT_START:
        step = SAMPLES_PER_BIT // 4
        chunk = np.array(buf[pos:pos+SAMPLES_PER_BIT], dtype=np.float32)
        bit = detect_bit(chunk)
        if bit == 0:
            print("Start bit locked!")
            state = STATE_READ_DATA
            data_bits.clear()
            pos += int(SAMPLES_PER_BIT * 1.5)
        else:
            pos += step
            
    elif state == STATE_READ_DATA:
        chunk = np.array(buf[pos:pos+SAMPLES_PER_BIT], dtype=np.float32)
        bit = detect_bit(chunk)
        if bit == -1:
            print("Lost signal.")
            break
        data_bits.append(bit)
        pos += SAMPLES_PER_BIT
        
        if len(data_bits) % 80 == 0 and len(data_bits) >= 80:
            try:
                payload = from_bits(data_bits)
                if len(payload) >= 13:
                    result = decrypt(payload)
                    if result:
                        print("DECODED:", result)
                        break
            except Exception:
                pass
