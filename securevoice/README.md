# SecureVoice: Real-Time Audio Steganography

SecureVoice is a full-stack, browser-based VoIP application that enables real-time peer-to-peer voice calls using WebRTC, featuring a custom **Steganography Engine** that hides secret messages directly inside the live audio stream.

## Architecture
- **Frontend**: React (Vite), Web Audio API
- **Backend**: Node.js, Express, Socket.io (Signaling Server)
- **Steganography Engine**: Custom `AudioWorkletNode` utilizing Continuous Phase Frequency Shift Keying (CPFSK) via the Goertzel algorithm.

## How it Works
Instead of modifying fragile LSBs (which are destroyed by WebRTC's Opus compression), this application injects inaudible micro-tones (3kHz and 2kHz) into your microphone's PCM audio stream. Because these are actual physical frequencies, they perfectly survive network jitter, resampling, and aggressive VOIP compression.

## Local Development
1. **Install Dependencies**:
   ```bash
   cd securevoice/server
   npm install
   cd ../client
   npm install
   ```

2. **Build the Frontend**:
   ```bash
   cd securevoice/client
   npm run build
   ```

3. **Run the Server**:
   ```bash
   cd securevoice/server
   node index.js
   ```
   *The server runs on port 3000 and automatically serves the built React frontend.*

## Deployment
This app is designed to be hosted as a single monolithic Node.js application. 
Deploy the `securevoice/server` directory to a platform like **Render** or **Railway**. 
Ensure that your host provides **HTTPS**, as modern browsers require a secure context to access the microphone.
