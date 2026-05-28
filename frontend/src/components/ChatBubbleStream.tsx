import React, { useState } from 'react';
import type { Message } from '../types';
import { Image as ImageIcon, Contact, Phone, Mail, Award, X, ZoomIn } from 'lucide-react';

interface ChatBubbleStreamProps {
  messages?: Message[];
}

export const ChatBubbleStream: React.FC<ChatBubbleStreamProps> = ({ messages = [] }) => {
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);

  if (!messages || messages.length === 0) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '150px' }}>
        <span style={{ fontSize: '0.88rem', color: 'var(--text-tertiary)' }}>No messages in this timeframe.</span>
      </div>
    );
  }

  // Helper to map original attachment filename to local AVIF server endpoint
  const getOptimizedMediaUrl = (filename: string): string => {
    const dotIdx = filename.lastIndexOf('.');
    const basename = dotIdx !== -1 ? filename.substring(0, dotIdx) : filename;
    return `http://localhost:8000/api/media/${basename}.avif`;
  };

  const isImageAttachment = (filename: string): boolean => {
    return /\.(jpg|jpeg|png|gif|webp|heic)$/i.test(filename);
  };

  const isVcardAttachment = (filename: string): boolean => {
    return /\.vcf$/i.test(filename);
  };

  // Helper to parse contact card metadata injected into message content
  const parseInjectedContact = (content: string) => {
    const contactRegex = /\[Parsed Contact Card [^\]]+\]:\s*Name:\s*([^,]+),\s*Phones:\s*([^,]+),\s*Emails:\s*([^,]+),\s*Org:\s*(.+)/i;
    const match = content.match(contactRegex);
    if (match) {
      return {
        name: match[1].trim(),
        phone: match[2].trim(),
        email: match[3].trim(),
        org: match[4].trim() === 'None' ? null : match[4].trim()
      };
    }
    return null;
  };

  return (
    <div 
      style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '14px', 
        background: '#0a0a0f', 
        border: '1px solid rgba(255,255,255,0.03)', 
        padding: '24px 20px', 
        borderRadius: '16px', 
        minHeight: '300px',
        position: 'relative'
      }}
    >
      <div style={{ textAlign: 'center', margin: '0 0 12px 0' }}>
        <span 
          style={{ 
            fontSize: '0.72rem', 
            color: 'var(--text-tertiary)', 
            background: 'rgba(255,255,255,0.03)', 
            border: '1px solid rgba(255,255,255,0.05)',
            padding: '5px 12px', 
            borderRadius: '20px',
            fontFamily: 'Outfit, sans-serif'
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
                  border: '1px solid rgba(255,255,255,0.05)', 
                  background: 'rgba(255,255,255,0.01)', 
                  backdropFilter: 'blur(10px)',
                  color: 'var(--text-secondary)', 
                  padding: '10px 18px', 
                  borderRadius: '12px', 
                  fontSize: '0.8rem', 
                  maxWidth: '80%', 
                  textAlign: 'center', 
                  fontStyle: 'italic',
                  lineHeight: '1.4'
                }}
              >
                {msg.content}
              </div>
            </div>
          );
        }

        // Check if there is contact details injected in the content
        const contactInfo = parseInjectedContact(msg.content);
        // Remove parsed contact block from display text if matched
        const cleanContent = contactInfo 
          ? msg.content.replace(/\[Parsed Contact Card [^\]]+\]:[^\n]*/i, '').trim()
          : msg.content;

        // Parse OCR tags if present
        const ocrMatch = cleanContent.match(/\[OCR Text extracted from [^\]]+\]:\s*([\s\S]+)/i);
        const displayContent = ocrMatch
          ? cleanContent.replace(/\[OCR Text extracted from [^\]]+\]:[\s\S]+/i, '').trim()
          : cleanContent;
        const ocrText = ocrMatch ? ocrMatch[1].trim() : null;

        return (
          <div key={idx} style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', margin: '6px 0' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start', maxWidth: '80%' }}>
              
              {/* Sender name above bubbles */}
              {!isUser && (
                <span 
                  style={{ 
                    fontSize: '0.75rem', 
                    color: 'var(--accent-indigo)', 
                    fontWeight: '600', 
                    marginBottom: '4px', 
                    marginLeft: '6px',
                    fontFamily: 'Outfit, sans-serif'
                  }}
                >
                  {msg.sender}
                </span>
              )}

              {/* Chat bubble body */}
              <div 
                style={{ 
                  background: isUser ? 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)' : 'rgba(255,255,255,0.03)', 
                  border: isUser ? 'none' : '1px solid rgba(255,255,255,0.04)',
                  color: isUser ? '#fff' : '#e4e4e7',
                  padding: displayContent || contactInfo ? '12px 16px' : 0, 
                  borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                  fontSize: '0.9rem',
                  lineHeight: '1.5',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px'
                }}
              >
                {/* Text Content */}
                {displayContent && (
                  <div>{displayContent}</div>
                )}

                {/* Contact Card Widget */}
                {contactInfo && (
                  <div 
                    style={{ 
                      background: 'rgba(255,255,255,0.05)', 
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: '8px', 
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                      minWidth: '220px',
                      boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.05)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '6px' }}>
                      <div style={{ background: '#4f46e5', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '24px', height: '24px' }}>
                        <Contact size={14} style={{ color: '#fff' }} />
                      </div>
                      <span style={{ fontWeight: 600, fontSize: '0.82rem', color: '#fff' }}>{contactInfo.name}</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {contactInfo.phone && contactInfo.phone !== 'None' && (
                        <a href={`tel:${contactInfo.phone}`} style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-indigo)', textDecoration: 'none' }}>
                          <Phone size={12} /> {contactInfo.phone}
                        </a>
                      )}
                      {contactInfo.email && contactInfo.email !== 'None' && (
                        <a href={`mailto:${contactInfo.email}`} style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-indigo)', textDecoration: 'none' }}>
                          <Mail size={12} /> {contactInfo.email}
                        </a>
                      )}
                      {contactInfo.org && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Award size={12} style={{ color: 'var(--accent-cyan)' }} /> {contactInfo.org}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Inline Image Attachment (converted to AVIF) */}
                {msg.attachments && msg.attachments.length > 0 && msg.attachments.some(isImageAttachment) && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: displayContent ? '4px' : 0 }}>
                    {msg.attachments.filter(isImageAttachment).map((filename, attIdx) => {
                      const avifUrl = getOptimizedMediaUrl(filename);
                      return (
                        <div 
                          key={attIdx} 
                          style={{ 
                            position: 'relative', 
                            borderRadius: '8px', 
                            overflow: 'hidden', 
                            border: '1px solid rgba(255,255,255,0.08)',
                            cursor: 'pointer',
                            width: '180px',
                            height: '120px',
                            boxShadow: '0 4px 10px rgba(0,0,0,0.3)',
                          }}
                          onClick={() => setLightboxImage(avifUrl)}
                        >
                          <img 
                            src={avifUrl} 
                            alt={filename} 
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            onError={(e) => {
                              // Fallback if local server doesn't host optimized media yet
                              (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=300';
                            }}
                          />
                          <div 
                            style={{ 
                              position: 'absolute', 
                              bottom: 0, 
                              left: 0, 
                              right: 0, 
                              background: 'rgba(0,0,0,0.6)', 
                              backdropFilter: 'blur(4px)',
                              padding: '4px 8px', 
                              fontSize: '0.62rem', 
                              color: 'var(--text-secondary)',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center'
                            }}
                          >
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }}>
                              {filename}
                            </span>
                            <ZoomIn size={10} style={{ color: 'var(--accent-cyan)' }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* OCR text display block */}
                {ocrText && (
                  <div 
                    style={{ 
                      background: 'rgba(6, 182, 212, 0.05)', 
                      borderLeft: '2px solid var(--accent-cyan)',
                      padding: '8px 10px',
                      borderRadius: '0 6px 6px 0',
                      fontSize: '0.78rem',
                      fontFamily: 'monospace',
                      color: 'var(--text-secondary)'
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-cyan)', marginBottom: '4px' }}>
                      OCR Extracted Text
                    </div>
                    {ocrText}
                  </div>
                )}

                {/* Gemma-4 Vision description summary */}
                {msg.summary && (
                  <div 
                    style={{ 
                      background: 'rgba(99, 102, 241, 0.05)', 
                      borderLeft: '2px solid var(--accent-indigo)',
                      padding: '8px 10px',
                      borderRadius: '0 6px 6px 0',
                      fontSize: '0.8rem',
                      color: 'var(--text-secondary)'
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-indigo)', marginBottom: '4px' }}>
                      Gemma-4 Vision Summary
                    </div>
                    {msg.summary}
                  </div>
                )}
              </div>

              {/* Small message timestamp */}
              <span 
                style={{ 
                  fontSize: '0.65rem', 
                  color: 'var(--text-tertiary)', 
                  marginTop: '4px', 
                  marginRight: isUser ? '4px' : 0, 
                  marginLeft: !isUser ? '4px' : 0,
                  fontFamily: 'Outfit, sans-serif'
                }}
              >
                {new Date(msg.datetime_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        );
      })}

      {/* Lightbox Modal Overlay */}
      {lightboxImage && (
        <div 
          style={{ 
            position: 'fixed', 
            top: 0, 
            left: 0, 
            right: 0, 
            bottom: 0, 
            background: 'rgba(5, 5, 10, 0.95)', 
            backdropFilter: 'blur(20px)',
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            zIndex: 99999,
            padding: '24px',
          }}
          onClick={() => setLightboxImage(null)}
        >
          <button 
            onClick={() => setLightboxImage(null)}
            style={{ 
              position: 'absolute', 
              top: '24px', 
              right: '24px', 
              background: 'rgba(255,255,255,0.05)', 
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '50%',
              padding: '8px',
              color: '#fff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease'
            }}
          >
            <X size={20} />
          </button>
          <img 
            src={lightboxImage} 
            alt="Optimized full viewport preview" 
            style={{ 
              maxWidth: '90%', 
              maxHeight: '90%', 
              objectFit: 'contain', 
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.1)',
              boxShadow: '0 12px 40px rgba(0,0,0,0.5)'
            }} 
          />
        </div>
      )}
    </div>
  );
};
