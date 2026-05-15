╔══════════════════════════════════════════════════════════╗
║          VoIP STEGANOGRAPHY TOOL — README                ║
╚══════════════════════════════════════════════════════════╝

WHAT THIS DOES:
───────────────
Hides secret text messages inside live Google Meet or
WhatsApp calls. Audio sounds completely normal to anyone
listening. Only the receiver's laptop extracts the message.


FILES IN THIS PROJECT:
──────────────────────
  main.py         ← Run this on BOTH laptops
  crypto.py       ← Encryption/decryption (don't edit)
  requirements.txt← Library list
  README.txt      ← This file


STEP 1 — INSTALL VB-CABLE (BOTH LAPTOPS):
──────────────────────────────────────────
  1. Download from: vb-audio.com/Cable
  2. Right click VBCABLE_Setup_x64.exe
  3. Click "Run as Administrator"
  4. Click "Install Driver"
  5. RESTART your laptop


STEP 2 — INSTALL PYTHON LIBRARIES (BOTH LAPTOPS):
──────────────────────────────────────────────────
  Open VS Code terminal (Ctrl + `) and run:
  pip install numpy sounddevice cryptography pyaudio

  Or run:
  pip install -r requirements.txt


STEP 3 — SET SAME PASSWORD (BOTH LAPTOPS):
───────────────────────────────────────────
  Open crypto.py
  Change this line on BOTH laptops to same password:
  SHARED_PASSWORD = "your_custom_password_here"


STEP 4 — AUDIO SETUP:
──────────────────────
  SENDER LAPTOP:
    Windows Sound Settings → Input → CABLE Output (VB-Audio)
    Google Meet/WhatsApp → Settings → Mic → CABLE Output

  RECEIVER LAPTOP:
    Windows Sound Settings → Output → CABLE Input (VB-Audio)
    Google Meet/WhatsApp → Settings → Speaker → CABLE Input


STEP 5 — HOW TO USE:
─────────────────────
  Both laptops run the same file:
    python main.py

  Sender   → Choose option 1 → Type secret message
  Receiver → Choose option 2 → Waits automatically

  Order:
    1. Receiver runs main.py → picks option 2 FIRST
    2. Both join Google Meet / WhatsApp call
    3. Sender runs main.py → picks option 1 → types message
    4. Receiver terminal shows the secret message ✅


VERIFY VB-CABLE IS WORKING:
────────────────────────────
  Run main.py → Choose option 3
  You should see "CABLE Output" and "CABLE Input" in the list


TROUBLESHOOTING:
─────────────────
  ❌ VB-Cable not showing?
     → Re-install as Administrator and restart laptop

  ❌ Audio error when running?
     → Run option 3 to check devices
     → Make sure VB-Cable is set as default

  ❌ Message not received?
     → Check both laptops have SAME password in crypto.py
     → Make sure receiver is running BEFORE sender types message

  ❌ pip install fails?
     → Try: pip install numpy sounddevice cryptography --user
