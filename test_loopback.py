import sys
import os
import threading
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import main

def start_receiver():
    print("Starting receiver thread...")
    try:
        main.run_receiver()
    except Exception as e:
        print("Receiver error:", e)

def start_sender():
    print("Starting sender thread...")
    try:
        # Mock the input
        old_input = __builtins__.input
        def mock_input(prompt):
            if "message:" in prompt:
                return "Garuda loopback"
            if "TRANSMIT" in prompt:
                return ""
            return ""
        __builtins__.input = mock_input
        main.run_sender()
        __builtins__.input = old_input
    except Exception as e:
        print("Sender error:", e)

t1 = threading.Thread(target=start_receiver)
t1.daemon = True
t1.start()

time.sleep(2) # let receiver start

t2 = threading.Thread(target=start_sender)
t2.daemon = True
t2.start()

time.sleep(40) # wait for transmission to finish
print("Test complete.")
