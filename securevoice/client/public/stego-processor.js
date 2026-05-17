class StegoProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.encodeBits = null;
    this.encodeIdx = 0;
    this.encodeRepeats = 64; // Redundancy across 64 samples per bit
    this.currentRepeat = 0;

    this.SYNC_PATTERN = [1,0,1,0,1,0,1,0,1,1,1,1,0,0,0,0]; // 16 bits
    this.bitHistory = [];
    this.lastDecodedText = "";
    
    this.port.onmessage = (e) => {
      if (e.data.type === 'ENCODE_TEXT') {
        const text = e.data.payload;
        this.encodeBits = this.textToBits(text);
        this.encodeIdx = 0;
        this.currentRepeat = 0;
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

  process(inputs, outputs) {
    const input = inputs[0];
    const output = outputs[0];

    if (!input || input.length === 0 || !input[0]) return true;

    const channelIn = input[0];
    const channelOut = output[0];

    // Read incoming bits (for decoding)
    // We expect the local mic to have clean audio, but the remote track will have stego.
    // If this processor is attached to the remote track, it decodes.
    // We average the bit over multiple samples (basic low-pass).
    let bitSum = 0;
    for (let i = 0; i < channelIn.length; i++) {
      let sample = channelIn[i];
      let int16 = Math.max(-32768, Math.min(32767, Math.round(sample * 32767)));
      
      // Use 4th bit (index 3) to survive basic compression
      let bit = (Math.abs(int16) >> 3) & 1;
      bitSum += bit;
    }
    
    // Since process() runs on 128 samples, and our redundancy is 64, 
    // we just take the majority bit of the first 64 and second 64 samples.
    for (let chunk = 0; chunk < 2; chunk++) {
      let cSum = 0;
      for (let i = 0; i < 64; i++) {
        let int16 = Math.max(-32768, Math.min(32767, Math.round(channelIn[chunk*64 + i] * 32767)));
        cSum += (Math.abs(int16) >> 3) & 1;
      }
      this.bitHistory.push(cSum > 32 ? 1 : 0);
    }
    
    // Periodically attempt decode and clean history
    if (this.bitHistory.length > 2000) {
      this.attemptDecode();
      // Keep last 1000 bits for overlap
      this.bitHistory = this.bitHistory.slice(-1000);
    }

    // Embed outgoing bits (for encoding)
    for (let i = 0; i < channelIn.length; i++) {
      let sample = channelIn[i];
      
      if (this.encodeBits && this.encodeIdx < this.encodeBits.length) {
        let bit = this.encodeBits[this.encodeIdx];
        let int16 = Math.max(-32768, Math.min(32767, Math.round(sample * 32767)));
        
        let sign = Math.sign(int16) || 1;
        let absVal = Math.abs(int16);
        absVal = absVal & ~(1 << 3);
        if (bit === 1) {
          absVal = absVal | (1 << 3);
        }
        
        channelOut[i] = (absVal * sign) / 32768.0;
        
        this.currentRepeat++;
        if (this.currentRepeat >= this.encodeRepeats) {
          this.currentRepeat = 0;
          this.encodeIdx++;
        }
      } else {
        channelOut[i] = sample;
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
        
        // Safety bounds
        if (len <= 0 || len > 200) {
            continue; 
        }

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
