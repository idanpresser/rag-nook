import React from 'react';
import type { Message } from '../types';

interface ChatBubbleStreamProps {
  messages?: Message[];
}

export const ChatBubbleStream: React.FC<ChatBubbleStreamProps> = ({ messages = [] }) => {
  if (!messages || messages.length === 0) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '150px' }}>
        <span style={{ fontSize: '0.88rem', color: 'var(--text-tertiary)' }}>No messages in this timeframe.</span>
      </div>
    );
  }

  return (
    <div 
      style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '12px', 
        background: '#08080c', 
        border: '1px solid rgba(255,255,255,0.03)', 
        padding: '24px 16px', 
        borderRadius: '12px', 
        minHeight: '300px' 
      }}
    >
      <div style={{ textAlign: 'center', margin: '0 0 12px 0' }}>
        <span 
          style={{ 
            fontSize: '0.72rem', 
            color: 'var(--text-tertiary)', 
            background: 'rgba(255,255,255,0.04)', 
            padding: '4px 10px', 
            borderRadius: '20px' 
          }}
        >
          Memory segment timeframe: {new Date(messages[0]?.datetime_utc).toLocaleString()}
        </span>
      </div>
      
      {messages.map((msg, idx) => {
        const isUser = msg.sender === 'Idan P';
        const isSys = msg.sender === 'System' || msg.media_type === 'system';
        
        if (isSys) {
          return (
            <div key={idx} style={{ display: 'flex', justifyContent: 'center', margin: '6px 0' }}>
              <div 
                style={{ 
                  border: '1px solid rgba(255,255,255,0.06)', 
                  background: 'rgba(255,255,255,0.02)', 
                  color: 'var(--text-secondary)', 
                  padding: '8px 16px', 
                  borderRadius: '10px', 
                  fontSize: '0.8rem', 
                  maxWidth: '80%', 
                  textAlign: 'center', 
                  fontStyle: 'italic' 
                }}
              >
                {msg.content}
              </div>
            </div>
          );
        }
        
        return (
          <div key={idx} style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', margin: '4px 0' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start', maxWidth: '75%' }}>
              {/* Sender name above bubbles */}
              {!isUser && (
                <span 
                  style={{ 
                    fontSize: '0.75rem', 
                    color: 'var(--accent-indigo)', 
                    fontWeight: '600', 
                    marginBottom: '2px', 
                    marginLeft: '6px' 
                  }}
                >
                  {msg.sender}
                </span>
              )}
              {/* Chat bubble body */}
              <div 
                style={{ 
                  background: isUser ? 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)' : 'rgba(255,255,255,0.04)', 
                  border: isUser ? 'none' : '1px solid rgba(255,255,255,0.04)',
                  color: isUser ? '#fff' : '#e4e4e7',
                  padding: '10px 14px', 
                  borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                  fontSize: '0.9rem',
                  lineHeight: '1.45',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                }}
              >
                {msg.content}
              </div>
              {/* Small message timestamp */}
              <span 
                style={{ 
                  fontSize: '0.65rem', 
                  color: 'var(--text-tertiary)', 
                  marginTop: '2px', 
                  marginRight: isUser ? '4px' : 0, 
                  marginLeft: !isUser ? '4px' : 0 
                }}
              >
                {new Date(msg.datetime_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
