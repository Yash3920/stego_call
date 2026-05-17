import React, { useState, useEffect, useRef } from 'react';
import './index.css';
import { initSignaling, disconnectSignaling } from './webrtc/Signaling';
import { CallManager } from './webrtc/CallManager';

function App() {
  const [roomId, setRoomId] = useState('');
  const [inCall, setInCall] = useState(false);
  const [status, setStatus] = useState('Disconnected');
  const [secretMsg, setSecretMsg] = useState('');
  const [decodedMsgs, setDecodedMsgs] = useState([]);
  
  const remoteAudioRef = useRef(null);
  const audioContextRef = useRef(null);
  const stegoNodeRef = useRef(null);
  const callManagerRef = useRef(null);

  useEffect(() => {
    return () => {
      disconnectSignaling();
      if (audioContextRef.current) audioContextRef.current.close();
    };
  }, []);

  const handleDecodedMessage = (msg) => {
    setDecodedMsgs(prev => [...prev, msg]);
  };

  const setupAudioPipeline = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }, video: false });
    
    const audioCtx = new AudioContext({ sampleRate: 48000 });
    audioContextRef.current = audioCtx;
    
    await audioCtx.audioWorklet.addModule('/stego-processor.js');
    
    const sourceNode = audioCtx.createMediaStreamSource(stream);
    const stegoNode = new AudioWorkletNode(audioCtx, 'stego-processor');
    stegoNodeRef.current = stegoNode;
    
    const destNode = audioCtx.createMediaStreamDestination();
    
    sourceNode.connect(stegoNode);
    stegoNode.connect(destNode);
    
    return destNode.stream;
  };
  
  const setupRemotePipeline = async (remoteStream) => {
    if (remoteAudioRef.current) {
        remoteAudioRef.current.srcObject = remoteStream;
    }
    
    if (!audioContextRef.current) return;
    const audioCtx = audioContextRef.current;
    
    const remoteSource = audioCtx.createMediaStreamSource(remoteStream);
    const decoderNode = new AudioWorkletNode(audioCtx, 'stego-processor');
    
    decoderNode.port.onmessage = (e) => {
      if (e.data.type === 'DECODED_TEXT') {
        handleDecodedMessage(e.data.payload);
      }
    };
    
    remoteSource.connect(decoderNode);
    decoderNode.connect(audioCtx.destination);
  };

  const joinRoom = async () => {
    if (!roomId) return;
    setStatus('Connecting...');
    
    const processedStream = await setupAudioPipeline();
    
    callManagerRef.current = new CallManager(processedStream, (remoteStream) => {
      setupRemotePipeline(remoteStream);
    });

    initSignaling(roomId, 
      async (userId) => {
        setStatus('Connected (Caller)');
        await callManagerRef.current.callUser(userId);
      },
      async (payload) => {
        setStatus('Connected (Receiver)');
        await callManagerRef.current.handleOffer(payload);
      },
      async (payload) => {
        await callManagerRef.current.handleAnswer(payload);
      },
      async (payload) => {
        await callManagerRef.current.handleIceCandidate(payload);
      },
      (userId) => {
        setStatus('Disconnected');
        callManagerRef.current.removePeer(userId);
      }
    );
    
    setInCall(true);
  };

  const sendSecret = () => {
    if (stegoNodeRef.current && secretMsg) {
      stegoNodeRef.current.port.postMessage({ type: 'ENCODE_TEXT', payload: secretMsg });
      setSecretMsg('');
    }
  };

  return (
    <div className="app-container">
      <div className="glass-panel">
        <h1>SecureVoice</h1>
        <div className="subtitle">Real-Time Audio Steganography Platform</div>
        
        {!inCall ? (
          <div>
            <div className="input-group">
              <input 
                type="text" 
                placeholder="Enter Room ID" 
                value={roomId} 
                onChange={e => setRoomId(e.target.value)} 
              />
              <button onClick={joinRoom}>Join Call</button>
            </div>
          </div>
        ) : (
          <div>
            <div style={{ marginBottom: '2rem' }}>
              <span className={`status-indicator ${status.includes('Connected') ? 'connected' : ''}`}></span>
              {status}
              <button className="danger" style={{ float: 'right', padding: '0.5rem 1rem' }} onClick={() => window.location.reload()}>End Call</button>
            </div>

            <div className="call-ui">
              <div>
                <div className="panel-title">Steganography Encoder</div>
                <div className="input-group" style={{ flexDirection: 'column' }}>
                  <input 
                    type="text" 
                    placeholder="Secret message..." 
                    value={secretMsg} 
                    onChange={e => setSecretMsg(e.target.value)} 
                  />
                  <button onClick={sendSecret}>Encode & Transmit</button>
                </div>
              </div>

              <div>
                <div className="panel-title">Incoming Secrets</div>
                <div className="message-box">
                  {decodedMsgs.length === 0 ? (
                    <span style={{ color: 'var(--text-muted)' }}>Listening for hidden data...</span>
                  ) : (
                    decodedMsgs.map((msg, idx) => (
                      <div key={idx}>&gt; {msg}</div>
                    ))
                  )}
                </div>
              </div>
            </div>
            
            <audio ref={remoteAudioRef} autoPlay playsInline style={{ display: 'none' }}></audio>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
