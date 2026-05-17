class StegoProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.encodeBits = null;
    this.encodeIdx = 0;
    
    // FSK Settings
    this.SAMPLE_RATE = 48000;
    this.SAMPLES_PER_BIT = 1024; // ~46 baud (Slower but much more accurate)
    this.FREQ_1 = 3000; // 3kHz for 1
    this.FREQ_0 = 2000; // 2kHz for 0
    this.currentEncodeSample = 0;
    this.phase = 0;

    this.SYNC_PATTERN = [1,0,1,0,1,0,1,0,1,1,1,1,0,0,0,0]; 
    
    this.decodeBuffer = new Float32Array(this.SAMPLES_PER_BIT);
    this.decodeIdx = 0;
    this.bitHistory = [];
    this.lastDecodedText = "";
    
    this.port.onmessage = (e) => {
      if (e.data.type === 'ENCODE_TEXT') {
        const text = e.data.payload;
        this.encodeBits = this.textToBits(text);
        this.encodeIdx = 0;
        this.currentEncodeSample = 0;
        this.phase = 0;
      }
    };
  }

  textToBits(text) {
    const bits = [...this.SYNC_PATTERN];
    const len = text.length;
    for (let i = 15; i >= 0; i--) bits.push((len >> i) & 1);
    for (let i = 0; i < text.length; i++) {
      const code = text.charCodeAt(i);
      for (let j = 7; j >= 0; j--) {
        bits.push((code >> j) & 1);
      }
    }
    return bits;
  }

  goertzel(samples, targetFreq) {
    const k = Math.round(targetFreq * samples.length / this.SAMPLE_RATE);
    const omega = (2 * Math.PI * k) / samples.length;
    const cosine = Math.cos(omega);
    const coeff = 2 * cosine;

    let q0 = 0, q1 = 0, q2 = 0;
    for (let i = 0; i < samples.length; i++) {
      q0 = coeff * q1 - q2 + samples[i];
      q2 = q1;
      q1 = q0;
    }
    const real = q1 - q2 * cosine;
    const imag = q2 * Math.sin(omega);
    return Math.sqrt(real * real + imag * imag);
  }

  process(inputs, outputs) {
    const input = inputs[0];
    const output = outputs[0];

    if (!input || input.length === 0 || !input[0]) return true;

    const channelIn = input[0];
    const channelOut = output[0];
    const VOL_BOOST = 1.0; // Removed boost to prevent clipping which ruins the FSK signal

    // --- DECODER ---
    for (let i = 0; i < channelIn.length; i++) {
      this.decodeBuffer[this.decodeIdx++] = channelIn[i];
      if (this.decodeIdx >= this.SAMPLES_PER_BIT) {
        // We have a full block, detect frequency
        const energy1 = this.goertzel(this.decodeBuffer, this.FREQ_1);
        const energy0 = this.goertzel(this.decodeBuffer, this.FREQ_0);
        
        // Threshold to ignore silence
        if (energy1 > 2.0 || energy0 > 2.0) {
            this.bitHistory.push(energy1 > energy0 ? 1 : 0);
        } else {
            // Push something arbitrary or just 0 so history slides, 
            // but we don't want to overflow.
            this.bitHistory.push(0);
        }
        
        if (this.bitHistory.length > 2000) {
          this.attemptDecode();
          this.bitHistory = this.bitHistory.slice(-1000);
        }
        
        this.decodeIdx = 0; // Reset buffer
      }
    }

    // --- ENCODER ---
    for (let i = 0; i < channelIn.length; i++) {
      let sample = channelIn[i] * VOL_BOOST; 
      
      if (this.encodeBits && this.encodeIdx < this.encodeBits.length) {
        let bit = this.encodeBits[this.encodeIdx];
        let freq = bit === 1 ? this.FREQ_1 : this.FREQ_0;
        
        this.phase += (2 * Math.PI * freq) / this.SAMPLE_RATE;
        if (this.phase > 2 * Math.PI) this.phase -= 2 * Math.PI;
        
        // Add a 5% amplitude sine wave (much quieter, less weird noise)
        let tone = Math.sin(this.phase) * 0.05; 
        
        channelOut[i] = Math.max(-1.0, Math.min(1.0, sample + tone));
        
        this.currentEncodeSample++;
        if (this.currentEncodeSample >= this.SAMPLES_PER_BIT) {
          this.currentEncodeSample = 0;
          this.encodeIdx++;
          // Optional: Phase reset for cleaner FSK? 
          // CPFSK (Continuous Phase) is better, so we don't reset phase.
        }
      } else {
        channelOut[i] = Math.max(-1.0, Math.min(1.0, sample));
      }
    }

    return true;
  }

  attemptDecode() {
    for(let i=0; i < this.bitHistory.length - 16; i++) {
      let match = true;
      for(let j=0; j<16; j++) {
        if(this.bitHistory[i+j] !== this.SYNC_PATTERN[j]) {
          match = false; break;
        }
      }
      
      if(match) {
        let lenIdx = i + 16;
        if (lenIdx + 16 > this.bitHistory.length) break;
        let len = 0;
        for(let j=0; j<16; j++) len = (len << 1) | this.bitHistory[lenIdx+j];
        
        if (len <= 0 || len > 200) continue; 

        let textIdx = lenIdx + 16;
        if (textIdx + len*8 > this.bitHistory.length) break;
        
        let text = "";
        for(let c=0; c<len; c++) {
          let charCode = 0;
          for(let b=0; b<8; b++) {
            charCode = (charCode << 1) | this.bitHistory[textIdx + c*8 + b];
          }
          text += String.fromCharCode(charCode);
        }
        
        if (text && text !== this.lastDecodedText) {
          this.port.postMessage({ type: 'DECODED_TEXT', payload: text });
          this.lastDecodedText = text;
        }
        i = textIdx + len*8; 
      }
    }
  }
}

registerProcessor('stego-processor', StegoProcessor);
