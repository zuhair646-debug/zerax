import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Progress } from '@/components/ui/progress';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';

/**
 * LiveProgress Component
 * يعرض تقدم العمليات في الوقت الحقيقي
 */
export const LiveProgress = ({ progress, isVisible }) => {
  if (!isVisible || !progress) return null;

  const getStatusIcon = () => {
    switch (progress.status) {
      case 'complete':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />;
    }
  };

  const getStatusColor = () => {
    switch (progress.status) {
      case 'complete':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-cyan-500';
    }
  };

  return (
    <div className="bg-slate-800/90 backdrop-blur-sm border border-slate-700 rounded-xl p-4 mb-4 animate-fade-in">
      <div className="flex items-center gap-3 mb-3">
        {getStatusIcon()}
        <span className="text-white font-medium">{progress.message}</span>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-gray-400">
          <span>الخطوة {progress.step} من {progress.total_steps}</span>
          <span>{progress.percent}%</span>
        </div>
        <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
          <div 
            className={`h-full ${getStatusColor()} transition-all duration-500 ease-out`}
            style={{ width: `${progress.percent}%` }}
          />
        </div>
      </div>
    </div>
  );
};

/**
 * useWebSocket Hook
 * للاتصال بالشات الحي
 */
export const useWebSocket = (sessionId, token, onMessage, onProgress) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (!sessionId || !token) return;

    const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
    const wsUrl = backendUrl.replace('https://', 'wss://').replace('http://', 'ws://');
    
    try {
      setConnectionStatus('connecting');
      wsRef.current = new WebSocket(`${wsUrl}/api/ws/chat/${sessionId}?token=${token}`);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setConnectionStatus('connected');
        console.log('WebSocket connected');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'progress') {
            onProgress?.(data);
          } else if (data.type === 'message') {
            onMessage?.(data.data);
          } else if (data.type === 'error') {
            console.error('WebSocket error:', data.message);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        setConnectionStatus('disconnected');
        console.log('WebSocket disconnected');
        
        // Auto-reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          if (sessionId && token) {
            connect();
          }
        }, 3000);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnectionStatus('error');
    }
  }, [sessionId, token, onMessage, onProgress]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message }));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [sessionId, token, connect, disconnect]);

  return {
    isConnected,
    connectionStatus,
    sendMessage,
    connect,
    disconnect
  };
};

/**
 * ConnectionIndicator Component
 * يعرض حالة الاتصال
 */
export const ConnectionIndicator = ({ status }) => {
  const getStatusInfo = () => {
    switch (status) {
      case 'connected':
        return { color: 'bg-green-500', text: 'متصل', pulse: false };
      case 'connecting':
        return { color: 'bg-yellow-500', text: 'جاري الاتصال...', pulse: true };
      case 'error':
        return { color: 'bg-red-500', text: 'خطأ في الاتصال', pulse: false };
      default:
        return { color: 'bg-gray-500', text: 'غير متصل', pulse: false };
    }
  };

  const { color, text, pulse } = getStatusInfo();

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`w-2 h-2 rounded-full ${color} ${pulse ? 'animate-pulse' : ''}`} />
      <span className="text-gray-400">{text}</span>
    </div>
  );
};

export default { LiveProgress, useWebSocket, ConnectionIndicator };
