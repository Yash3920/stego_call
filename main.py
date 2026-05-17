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
FREQ_ONE    = 4500
FREQ_ZERO   = 3500
TONE_AMP    = 0.5
TONE_DUR    = 0.1


# ── Auto-detect VB-Cable devices ─────────────────────────
def find_cable_input() -> int:
    """Find CABLE Input device ID automatically."""
    for i, d in enumerate(sd.query_devices()):
        name = d['name'].lower()
        if 'cable input' in name and 'vb-audio' in name and d['max_output_channels'] > 0:
            return i
    # fallback — any cable input
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
    # fallback
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
    bits = MARKER + to_bits(encrypt(message))
    chunks = [np.zeros(int(SAMPLE_RATE * 0.1), dtype=np.float32)]
    for bit in bits:
        chunks.append(generate_tone(FREQ_ONE if bit == 1 else FREQ_ZERO, TONE_DUR))
    chunks.append(np.zeros(int(SAMPLE_RATE * 0.1), dtype=np.float32))
    return np.concatenate(chunks)

def detect_bit(chunk: np.ndarray) -> int:
    fft   = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(len(chunk), 1 / SAMPLE_RATE)
    def energy(f):
        mask = (freqs >= f - 300) & (freqs <= f + 300)
        return np.sum(fft[mask])
    return 1 if energy(FREQ_ONE) > energy(FREQ_ZERO) else 0


# ── SENDER ────────────────────────────────────────────────
def run_sender():
    print("\n" + "=" * 50)
    print("   SENDER MODE")
    print("=" * 50)

    # Auto-detect devices
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

    print(f"Prepared {len(MARKER + to_bits(encrypt(message)))} bits — {total/SAMPLE_RATE:.1f}s of audio")
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
            sd.sleep(int((total / SAMPLE_RATE + 5) * 1000))
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

    samples_per_bit = int(SAMPLE_RATE * TONE_DUR)
    buf          = []
    marker_bits  = []
    data_bits    = []
    found        = [False]
    count        = [0]
    last_hb      = [time.time()]

    def callback(indata, frames, t, status):
        buf.extend(indata[:, 0].tolist())

        if time.time() - last_hb[0] > 3:
            print("  ... listening ...", flush=True)
            last_hb[0] = time.time()

        while len(buf) >= samples_per_bit:
            chunk = np.array(buf[:samples_per_bit], dtype=np.float32)
            del buf[:samples_per_bit]
            bit = detect_bit(chunk)

            if not found[0]:
                marker_bits.append(bit)
                if len(marker_bits) > MARKER_LEN * 2:
                    del marker_bits[0]
                if len(marker_bits) >= MARKER_LEN and marker_bits[-MARKER_LEN:] == MARKER:
                    found[0] = True
                    data_bits.clear()
                    print("\nTransmission detected! Collecting...", flush=True)
            else:
                data_bits.append(bit)
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
                                data_bits.clear()
                                marker_bits.clear()
                                found[0] = False
                                print("Listening for next message...\n", flush=True)
                    except Exception:
                        pass

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