import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './Agent.css';

function Agent() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const [conversationId, setConversationId] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [streamingMessage, setStreamingMessage] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('session_token');
    if (!token) {
      navigate('/');
      return;
    }
    setSessionToken(token);
    loadConversationHistory(token);
  }, [navigate]);

  const loadConversationHistory = async (token) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/agent/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages);
          setConversationId(data.conversation_id);
        }
      }
    } catch (error) {
      console.error('Error loading history:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setStreamingMessage('');

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: conversationId
        })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;
          
          try {
            const jsonStr = line.slice(6);
            if (jsonStr === '[DONE]') continue;
            
            const data = JSON.parse(jsonStr);
            
            if (data.type === 'content') {
              fullResponse += data.content;
              setStreamingMessage(fullResponse);
            } else if (data.type === 'done') {
              if (data.conversation_id && !conversationId) {
                setConversationId(data.conversation_id);
              }
            } else if (data.type === 'error') {
              throw new Error(data.error);
            }
          } catch (e) {
            console.error('Parse error:', e);
          }
        }
      }

      if (fullResponse) {
        const assistantMessage = {
          role: 'assistant',
          content: fullResponse,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
      setStreamingMessage('');
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'عذراً، حدث خطأ في الاتصال. يرجى المحاولة مرة أخرى.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
      setStreamingMessage('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = async () => {
    if (!window.confirm('هل تريد بدء محادثة جديدة؟ سيتم حفظ المحادثة الحالية.')) {
      return;
    }
    setMessages([]);
    setConversationId(null);
    setStreamingMessage('');
  };

  const handleLogout = () => {
    localStorage.removeItem('session_token');
    navigate('/');
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="agent-container">
      <div className="agent-header">
        <div className="header-left">
          <button onClick={() => navigate('/dashboard')} className="back-btn">
            ← الرجوع
          </button>
          <h1>🤖 الوكيل الذكي</h1>
        </div>
        <div className="header-right">
          <button onClick={handleNewChat} className="new-chat-btn">
            💬 محادثة جديدة
          </button>
          <button onClick={handleLogout} className="logout-btn">
            تسجيل الخروج
          </button>
        </div>
      </div>

      <div className="chat-container">
        <div className="messages-container">
          {messages.length === 0 && !streamingMessage ? (
            <div className="welcome-message">
              <div className="welcome-icon">🤖</div>
              <h2>مرحباً بك في الوكيل الذكي!</h2>
              <p>أنا هنا لمساعدتك في أي شيء تحتاجه.</p>
              <div className="suggestions">
                <div className="suggestion-card" onClick={() => setInputValue('ما هي خدماتك؟')}>
                  <span className="suggestion-icon">💼</span>
                  <span>ما هي خدماتك؟</span>
                </div>
                <div className="suggestion-card" onClick={() => setInputValue('كيف يمكنني استخدام المنصة؟')}>
                  <span className="suggestion-icon">📚</span>
                  <span>كيف أستخدم المنصة؟</span>
                </div>
                <div className="suggestion-card" onClick={() => setInputValue('أخبرني عن إمكانياتك')}>
                  <span className="suggestion-icon">⚡</span>
                  <span>أخبرني عن إمكانياتك</span>
                </div>
                <div className="suggestion-card" onClick={() => setInputValue('ساعدني في بناء موقع')}>
                  <span className="suggestion-icon">🚀</span>
                  <span>ساعدني في بناء موقع</span>
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === 'user' ? '👤' : '🤖'}
                  </div>
                  <div className="message-content">
                    <div className="message-header">
                      <span className="message-role">
                        {msg.role === 'user' ? 'أنت' : 'الوكيل الذكي'}
                      </span>
                      <span className="message-time">{formatTime(msg.timestamp)}</span>
                    </div>
                    <div className="message-text">
                      <ReactMarkdown
                        components={{
                          code({ node, inline, className, children, ...props }) {
                            const match = /language-(\w+)/.exec(className || '');
                            return !inline && match ? (
                              <SyntaxHighlighter
                                style={vscDarkPlus}
                                language={match[1]}
                                PreTag="div"
                                {...props}
                              >
                                {String(children).replace(/\n$/, '')}
                              </SyntaxHighlighter>
                            ) : (
                              <code className={className} {...props}>
                                {children}
                              </code>
                            );
                          }
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              ))}
              
              {streamingMessage && (
                <div className="message assistant streaming">
                  <div className="message-avatar">🤖</div>
                  <div className="message-content">
                    <div className="message-header">
                      <span className="message-role">الوكيل الذكي</span>
                      <span className="message-time typing-indicator">● ● ●</span>
                    </div>
                    <div className="message-text">
                      <ReactMarkdown
                        components={{
                          code({ node, inline, className, children, ...props }) {
                            const match = /language-(\w+)/.exec(className || '');
                            return !inline && match ? (
                              <SyntaxHighlighter
                                style={vscDarkPlus}
                                language={match[1]}
                                PreTag="div"
                                {...props}
                              >
                                {String(children).replace(/\n$/, '')}
                              </SyntaxHighlighter>
                            ) : (
                              <code className={className} {...props}>
                                {children}
                              </code>
                            );
                          }
                        }}
                      >
                        {streamingMessage}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="اكتب رسالتك هنا..."
            disabled={isLoading}
            rows="3"
          />
          <button 
            onClick={handleSend} 
            disabled={isLoading || !inputValue.trim()}
            className="send-btn"
          >
            {isLoading ? '⏳ جاري الإرسال...' : '📤 إرسال'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Agent;
