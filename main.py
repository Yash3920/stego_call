import os
import sys
import time

# Ensure Windows terminal supports UTF-8 for the box drawing characters
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def check_dependencies():
    missing = []
    for pkg in ['numpy', 'sounddevice', 'cryptography']:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"\nMissing libraries: {', '.join(missing)}")
        print(f"Run: pip install {' '.join(missing)}\n")
        sys.exit(1)

check_dependencies()

import numpy as np
import sounddevice as sd
from crypto import encrypt, decrypt, to_bits, from_bits

SAMPLE_RATE = 48000
CHUNK       = 4096
MARKER      = [1,0,1,0,1,1,0,1,1,1,0,0,1,0,1,1,0,1,1,0]
MARKER_LEN  = len(MARKER)
FREQ_ONE    = 1600
FREQ_ZERO   = 1200
TONE_AMP    = 0.1
TONE_DUR    = 0.1

SAMPLES_PER_BIT = int(SAMPLE_RATE * TONE_DUR)

# ── Auto-detect VB-Cable devices ─────────────────────────
def find_cable_input() -> int:
    """Find CABLE Input device ID automatically."""
    for i, d in enumerate(sd.query_devices()):
        name = d['name'].lower()
        if 'cable input' in name and 'vb-audio' in name and d['max_output_channels'] > 0:
            return i
    for i, d in enumerate(sd.query_devices()):
        name = d['name'].lower()
        if 'cable input' in name and d['max_output_channels'] > 0:
            return i
    return None

def find_cable_output() -> int:
    """Find CABLE Output device ID automatically."""
    for i, d in enumerate(sd.query_devices()):
        name = d['name'].lower()
        if 'cable output' in name and 'vb-audio' in name and d['max_input_channels'] > 0:
            return i
    for i, d in enumerate(sd.query_devices()):
        name = d['name'].lower()
        if 'cable output' in name and d['max_input_channels'] > 0:
            return i
    return None

def find_real_mic() -> int:
    """Find real microphone (not VB-Cable)."""
    for i, d in enumerate(sd.query_devices()):
        name = d['name'].lower()
        if d['max_input_channels'] > 0 and 'cable' not in name and 'vb-audio' not in name and 'mapper' not in name and 'primary' not in name:
            return i
    return None


# ── Audio helpers ─────────────────────────────────────────
def generate_tone(freq, duration):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * TONE_AMP).astype(np.float32)

def encode_to_audio(message: str) -> np.ndarray:
    # Payload is: 1 second of CARRIER (FREQ_ONE), followed by a START BIT (FREQ_ZERO), then DATA, then STOP BIT (FREQ_ZERO)
    bits = to_bits(encrypt(message))
    chunks = []
    
    # Carrier wave (1.0 seconds of FREQ_ONE) to lock AGC and allow receiver to sync
    chunks.append(generate_tone(FREQ_ONE, 1.0))
    # Start bit (FREQ_ZERO) indicates data begins NOW
    chunks.append(generate_tone(FREQ_ZERO, TONE_DUR))
    
    for bit in bits:
        chunks.append(generate_tone(FREQ_ONE if bit == 1 else FREQ_ZERO, TONE_DUR))
        
    # Stop bit (FREQ_ZERO)
    chunks.append(generate_tone(FREQ_ZERO, TONE_DUR))
    chunks.append(np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32))
    return np.concatenate(chunks)

def detect_bit(chunk: np.ndarray) -> int:
    """Returns 1, 0, or -1 if noise/silence"""
    fft   = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(len(chunk), 1 / SAMPLE_RATE)
    
    def energy(f):
        mask = (freqs >= f - 150) & (freqs <= f + 150)
        return np.sum(fft[mask])
        
    e1 = energy(FREQ_ONE)
    e0 = energy(FREQ_ZERO)
    
    # Dynamic thresholding based on local energy to reject silence/voice
    total_energy = np.sum(fft)
    if total_energy == 0 or max(e1, e0) < total_energy * 0.15:
        return -1 # Not a valid bit (probably silence or normal voice)
        
    return 1 if e1 > e0 else 0


# ── SENDER ────────────────────────────────────────────────
def run_sender():
    print("\n" + "=" * 50)
    print("   SENDER MODE")
    print("=" * 50)

    mic_id    = find_real_mic()
    cable_in  = find_cable_input()

    if cable_in is None:
        print("\nVB-Cable not found! Make sure it is installed.")
        return

    print(f"\nAuto-detected:")
    print(f"  Mic      : {sd.query_devices(mic_id)['name']}")
    print(f"  VB-Cable : {sd.query_devices(cable_in)['name']}")

    print("\nIn Google Meet / WhatsApp:")
    print("  Set Microphone -> CABLE Output (VB-Audio Virtual Cable)")

    message = input("\nEnter your secret message: ").strip()
    if not message:
        print("Message cannot be empty!")
        return

    print("\nPreparing encrypted audio...")
    audio    = encode_to_audio(message)
    total    = len(audio)
    pos      = [0]
    done     = [False]

    print(f"Prepared {len(to_bits(encrypt(message)))} bits — {total/SAMPLE_RATE:.1f}s of audio")
    input("\nPress Enter when call is active and you are ready to TRANSMIT...")
    print("Sending...\n")

    def callback(indata, outdata, frames, t, status):
        mic = indata[:, 0].copy()
        out = mic.copy()
        if pos[0] < total and not done[0]:
            end   = pos[0] + frames
            chunk = audio[pos[0]:end]
            if len(chunk) < frames:
                chunk    = np.pad(chunk, (0, frames - len(chunk)))
                done[0]  = True
                print("\n\nMessage fully sent!")
            out       = np.clip(mic + chunk, -1.0, 1.0)
            pos[0]   += frames
            pct       = min(int(pos[0] / total * 100), 100)
            bar       = "#" * (pct // 5) + "." * (20 - pct // 5)
            print(f"\r  [{bar}] {pct}%", end="", flush=True)
        outdata[:, 0] = out

    try:
        with sd.Stream(samplerate=SAMPLE_RATE, blocksize=CHUNK, channels=1,
                       dtype='float32', device=(mic_id, cable_in), callback=callback):
            sd.sleep(int((total / SAMPLE_RATE + 2) * 1000))
    except Exception as e:
        print(f"\nError: {e}")

    print("\nSender done.")


# ── RECEIVER ──────────────────────────────────────────────
def run_receiver():
    print("\n" + "=" * 50)
    print("   RECEIVER MODE")
    print("=" * 50)

    cable_out = find_cable_output()

    if cable_out is None:
        print("\nVB-Cable not found! Make sure it is installed.")
        return

    print(f"\nAuto-detected:")
    print(f"  VB-Cable : {sd.query_devices(cable_out)['name']}")

    print("\nIn Google Meet / WhatsApp:")
    print("  Set Speaker -> CABLE Input (VB-Audio Virtual Cable)")
    input("\nPress Enter when call is active and speaker is set...")

    print("\nListening for hidden messages...")
    print("Press Ctrl+C to stop\n")

    buf          = []
    data_bits    = []
    count        = [0]
    last_hb      = [time.time()]
    
    # State Machine
    STATE_WAIT_CARRIER = 0
    STATE_WAIT_START   = 1
    STATE_READ_DATA    = 2
    state = [STATE_WAIT_CARRIER]
    
    carrier_count = [0]
    next_sample_pos = [0] # Exact sample offset to read next bit

    def callback(indata, frames, t, status):
        buf.extend(indata[:, 0].tolist())

        if time.time() - last_hb[0] > 3:
            print("  ... listening ...", flush=True)
            last_hb[0] = time.time()

        # Sliding window processing
        while True:
            if state[0] == STATE_WAIT_CARRIER:
                # Need at least one bit duration to analyze
                if len(buf) < SAMPLES_PER_BIT:
                    break
                
                # Analyze sliding window at 1/4 bit increments for fast lock
                step = SAMPLES_PER_BIT // 4
                chunk = np.array(buf[:SAMPLES_PER_BIT], dtype=np.float32)
                bit = detect_bit(chunk)
                
                if bit == 1:
                    carrier_count[0] += 1
                    if carrier_count[0] > 6: # Saw ~0.6s of solid carrier
                        state[0] = STATE_WAIT_START
                        print("\nCarrier detected! Waiting for start bit...", flush=True)
                else:
                    carrier_count[0] = 0
                    
                del buf[:step]
                
            elif state[0] == STATE_WAIT_START:
                if len(buf) < SAMPLES_PER_BIT:
                    break
                    
                step = SAMPLES_PER_BIT // 4
                chunk = np.array(buf[:SAMPLES_PER_BIT], dtype=np.float32)
                bit = detect_bit(chunk)
                
                if bit == 0:
                    print("Start bit locked! Receiving data...", flush=True)
                    state[0] = STATE_READ_DATA
                    data_bits.clear()
                    # Align EXACTLY to the center of the next bit
                    next_sample_pos[0] = int(SAMPLES_PER_BIT * 1.5)
                    # Don't delete buffer, just shift logically
                    break
                else:
                    del buf[:step]

            elif state[0] == STATE_READ_DATA:
                if len(buf) < next_sample_pos[0] + SAMPLES_PER_BIT:
                    break
                    
                # Read exactly at the synchronized sample position
                chunk = np.array(buf[next_sample_pos[0]:next_sample_pos[0]+SAMPLES_PER_BIT], dtype=np.float32)
                bit = detect_bit(chunk)
                
                if bit == -1:
                    print("\nLost signal. Resetting...")
                    state[0] = STATE_WAIT_CARRIER
                    carrier_count[0] = 0
                    del buf[:next_sample_pos[0]]
                    break
                    
                data_bits.append(bit)
                next_sample_pos[0] += SAMPLES_PER_BIT
                
                # Check for successful decryption every 80 bits (10 bytes)
                if len(data_bits) % 80 == 0 and len(data_bits) >= 80:
                    try:
                        payload = from_bits(data_bits)
                        if len(payload) >= 13:
                            result = decrypt(payload)
                            if result:
                                count[0] += 1
                                print(f"\n{'='*50}")
                                print(f"  SECRET MESSAGE #{count[0]}:")
                                print(f"  {result}")
                                print(f"{'='*50}\n")
                                state[0] = STATE_WAIT_CARRIER
                                carrier_count[0] = 0
                                data_bits.clear()
                                del buf[:next_sample_pos[0]]
                                print("Listening for next message...\n", flush=True)
                                break
                    except Exception:
                        pass
                        
                # Failsafe: if we read 4000 bits without success, we probably desynced
                if len(data_bits) > 4000:
                    print("\nData stream invalid. Resetting...")
                    state[0] = STATE_WAIT_CARRIER
                    carrier_count[0] = 0
                    del buf[:next_sample_pos[0]]
                    break

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=CHUNK, channels=1,
                            dtype='float32', device=cable_out, callback=callback):
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print(f"\nError: {e}")

    print(f"\nSession ended. Messages received: {count[0]}")


# ── CHECK DEVICES ─────────────────────────────────────────
def run_check_devices():
    print("\n" + "=" * 50)
    print("   CHECK AUDIO DEVICES")
    print("=" * 50)
    print("\nAvailable Devices:")
    print(sd.query_devices())
    
    print("\nAuto-detection results:")
    mic = find_real_mic()
    cab_in = find_cable_input()
    cab_out = find_cable_output()
    
    print(f"  Real Microphone  : {'Found (ID '+str(mic)+')' if mic is not None else 'Not Found'}")
    print(f"  VB-Cable Input   : {'Found (ID '+str(cab_in)+')' if cab_in is not None else 'Not Found'}")
    print(f"  VB-Cable Output  : {'Found (ID '+str(cab_out)+')' if cab_out is not None else 'Not Found'}")
    print("\nPress Enter to return to menu...")
    input()


# ── MAIN MENU ─────────────────────────────────────────────
def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("""
╔══════════════════════════════════════════════════╗
║       VoIP STEGANOGRAPHY TOOL v1.0               ║
║  Hide secret messages inside live calls          ║
╚══════════════════════════════════════════════════╝
    """)
    print("  1  SENDER   - Hide a message in call audio")
    print("  2  RECEIVER - Extract hidden messages")
    print("  3  CHECK    - Verify VB-Cable devices")
    print("  4  EXIT\n")

    choice = input("  Choose (1/2/3/4): ").strip()

    if choice == '1':
        run_sender()
    elif choice == '2':
        run_receiver()
    elif choice == '3':
        run_check_devices()
        main()
    elif choice == '4':
        print("\nGoodbye!\n")
        sys.exit(0)
    else:
        print("\nInvalid choice.")
        input("Press Enter to try again...")
        main()

if __name__ == "__main__":
    main()