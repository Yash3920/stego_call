import { sendOffer, sendAnswer, sendIceCandidate } from './Signaling';

function forcePCMU(sdp) {
  let lines = sdp.split('\r\n');
  let mLineIndex = lines.findIndex(line => line.startsWith('m=audio'));
  if (mLineIndex !== -1) {
    let mLine = lines[mLineIndex];
    let parts = mLine.split(' ');
    let codecs = parts.slice(3);
    codecs = codecs.filter(c => c !== '0');
    codecs.unshift('0');
    lines[mLineIndex] = parts.slice(0, 3).join(' ') + ' ' + codecs.join(' ');
  }
  return lines.join('\r\n');
}

export class CallManager {
  constructor(localStream, onRemoteStream) {
    this.localStream = localStream;
    this.onRemoteStream = onRemoteStream;
    this.peers = {}; 
  }

  createPeerConnection(targetId) {
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    });

    this.localStream.getTracks().forEach(track => {
      pc.addTrack(track, this.localStream);
    });

    pc.ontrack = (event) => {
      if (event.streams && event.streams[0]) {
        this.onRemoteStream(event.streams[0]);
      }
    };

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        sendIceCandidate(targetId, event.candidate);
      }
    };

    this.peers[targetId] = pc;
    return pc;
  }

  async callUser(targetId) {
    const pc = this.createPeerConnection(targetId);
    const offer = await pc.createOffer();
    offer.sdp = forcePCMU(offer.sdp);
    await pc.setLocalDescription(offer);
    sendOffer(targetId, pc.localDescription);
  }

  async handleOffer(payload) {
    const pc = this.createPeerConnection(payload.caller);
    await pc.setRemoteDescription(new RTCSessionDescription(payload.sdp));
    const answer = await pc.createAnswer();
    answer.sdp = forcePCMU(answer.sdp);
    await pc.setLocalDescription(answer);
    sendAnswer(payload.caller, pc.localDescription);
  }

  async handleAnswer(payload) {
    const pc = this.peers[payload.caller];
    if (pc) {
      await pc.setRemoteDescription(new RTCSessionDescription(payload.sdp));
    }
  }

  async handleIceCandidate(payload) {
    const pc = this.peers[payload.caller];
    if (pc && payload.candidate) {
      await pc.addIceCandidate(new RTCIceCandidate(payload.candidate));
    }
  }

  removePeer(targetId) {
    if (this.peers[targetId]) {
      this.peers[targetId].close();
      delete this.peers[targetId];
    }
  }
}
