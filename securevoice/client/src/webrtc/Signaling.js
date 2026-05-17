import { io } from 'socket.io-client';

const SERVER_URL = window.location.origin;
let socket = null;

export const initSignaling = (roomId, onUserJoined, onOffer, onAnswer, onIceCandidate, onUserLeft) => {
  socket = io(SERVER_URL);

  socket.on('connect', () => {
    console.log('Connected to signaling server');
    socket.emit('join-room', roomId);
  });

  socket.on('user-connected', (userId) => onUserJoined(userId));
  socket.on('offer', (payload) => onOffer(payload));
  socket.on('answer', (payload) => onAnswer(payload));
  socket.on('ice-candidate', (payload) => onIceCandidate(payload));
  socket.on('user-disconnected', (userId) => onUserLeft(userId));
};

export const sendOffer = (target, sdp) => {
  if(socket) socket.emit('offer', { target, caller: socket.id, sdp });
};

export const sendAnswer = (target, sdp) => {
  if(socket) socket.emit('answer', { target, caller: socket.id, sdp });
};

export const sendIceCandidate = (target, candidate) => {
  if(socket) socket.emit('ice-candidate', { target, caller: socket.id, candidate });
};

export const disconnectSignaling = () => {
  if (socket) socket.disconnect();
};
