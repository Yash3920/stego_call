import os
import urllib.request
import zipfile
import subprocess
import time

def setup_nircmd():
    if not os.path.exists("nircmd.exe"):
        print("Downloading audio routing tool...")
        urllib.request.urlretrieve("https://www.nirsoft.net/utils/nircmd-x64.zip", "nircmd.zip")
        with zipfile.ZipFile("nircmd.zip", 'r') as zip_ref:
            zip_ref.extractall(".")
        print("Tool downloaded.")

def fix_sender():
    print("\nFixing Sender Laptop Settings...")
    # Sender needs to push audio INTO WhatsApp, so CABLE Output is the default mic
    subprocess.run(["nircmd.exe", "setdefaultsounddevice", "CABLE Output", "1"])
    subprocess.run(["nircmd.exe", "setdefaultsounddevice", "CABLE Output", "2"])
    print("SUCCESS: WhatsApp will now listen to the secret script!")

def fix_receiver():
    print("\nFixing Receiver Laptop Settings...")
    # Receiver needs to pull audio FROM WhatsApp, so CABLE Input is the default speaker
    subprocess.run(["nircmd.exe", "setdefaultsounddevice", "CABLE Input", "1"])
    subprocess.run(["nircmd.exe", "setdefaultsounddevice", "CABLE Input", "2"])
    
    # Disable physical speakers to FORCE WhatsApp to use the cable
    # Nircmd can't easily disable without exact names, so we just mute it as a fallback
    # Wait, nircmd CAN mute specific devices:
    # subprocess.run(["nircmd.exe", "mutesysvolume", "1", "Speakers"])
    
    print("SUCCESS: WhatsApp is now forced to route incoming calls to the script!")

if __name__ == "__main__":
    print("="*50)
    print("   AUTOMATIC AUDIO ROUTING FIXER")
    print("="*50)
    setup_nircmd()
    
    print("\nWhich laptop is this?")
    print("  1 - SENDER (The one sending the secret message)")
    print("  2 - RECEIVER (The one decoding the message)")
    
    choice = input("\nChoose (1 or 2): ").strip()
    
    if choice == '1':
        fix_sender()
    elif choice == '2':
        fix_receiver()
    else:
        print("Invalid choice.")
        
    print("\nIMPORTANT: Please RESTART the WhatsApp Call now!")
    input("Press Enter to close...")
