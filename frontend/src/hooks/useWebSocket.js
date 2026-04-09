import { useState, useEffect, useRef, useCallback } from 'react';

const useWebSocket = (sessionId, token, backendUrl) => {
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState(null);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);

  const connect = useCallback(() => {
    if (!sessionId || !token || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = backendUrl
      .replace('https://', 'wss://')
      .replace('http://', 'ws://');
    
    const fullUrl = `${wsUrl}/api/ws/chat/${sessionId}?token=${token}`;
    
    wsRef.current = new WebSocket(fullUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'progress') {
        setProgress(data);
      } else if (data.type === 'message') {
        setLastMessage(data.data);
        setProgress(null);
      }
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      setTimeout(() => {
        if (sessionId && token) connect();
      }, 3000);
    };
  }, [sessionId, token, backendUrl]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message }));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    if (sessionId && token) connect();
    return () => disconnect();
  }, [sessionId, token, connect, disconnect]);

  return {
    isConnected,
    progress,
    lastMessage,
    sendMessage,
    clearProgress: () => setProgress(null),
    clearLastMessage: () => setLastMessage(null)
  };
};

export default useWebSocket;
