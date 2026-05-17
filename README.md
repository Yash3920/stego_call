# SecureVoice: VoIP Steganography Pipeline

This repository contains the full source code for a real-time VoIP audio steganography system. It enables users to hide secret, encrypted text messages within live voice calls. 

This project was built to bypass modern VoIP noise-cancellation algorithms (like WhatsApp Desktop and Google Meet) which actively destroy traditional Least Significant Bit (LSB) steganography over the network.

## Project Architecture

There are two main implementations in this repository:

### 1. `securevoice/` (Web App - Recommended)
A full-stack, browser-based WebRTC application that bypasses external VoIP apps entirely. 
* **Frontend**: React (Vite) with a premium glassmorphism UI and mobile-responsive layout.
* **Backend**: Node.js, Express, and Socket.io for peer-to-peer WebRTC signaling.
* **Steganography Engine**: A highly robust Continuous Phase Frequency Shift Keying (CPFSK) modem running directly inside the browser's `AudioWorkletNode`. It encodes binary data as 3,000 Hz and 2,000 Hz micro-tones, surviving any internet jitter or Opus compression.

### 2. `stego_call/` (Python CLI - Classic)
A terminal-based Python application that routes audio through Virtual Audio Cables (VB-Cable) into third-party VoIP apps like Google Meet or WhatsApp.
* Features an AES-GCM encrypted payload system.
* Implements a state-machine CPFSK receiver.
* **Note**: Requires manual Windows audio routing configuration.

---

## Quick Start (Web App)

1. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/Yash3920/stego_call.git
   cd stego_call/securevoice/server
   npm install
   cd ../client
   npm install
   ```

2. Build the frontend and run the monolithic server:
   ```bash
   cd ../client
   npm run build
   cd ../server
   node index.js
   ```

3. Open `http://localhost:3000` in your browser. (Note: WebRTC requires HTTPS or localhost to access the microphone).

---

## Deployment
The `securevoice` application is designed to be hosted as a single monolithic Node.js application. Simply deploy the `securevoice/server` directory to a platform like **Render.com** (with the build command `cd ../client && npm install && npm run build && cd ../server && npm install`) to get an instant public HTTPS URL for live testing between any devices.

## Disclaimer
This project is an academic proof-of-concept for real-time digital signal processing, WebRTC manipulation, and audio steganography.
