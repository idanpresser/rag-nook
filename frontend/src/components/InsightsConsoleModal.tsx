import React from 'react';
import { X, ExternalLink, Loader2, ChevronRight } from 'lucide-react';
import type { Source, ScrapedURLMetadata } from '../types';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ChatBubbleStream } from './ChatBubbleStream';

interface InsightsConsoleModalProps {
  selectedSource: Source | null;
  onClose: () => void;
  modalTab: 'chat' | 'resources';
  setModalTab: (tab: 'chat' | 'resources') => void;
  viewingSubWebpage: ScrapedURLMetadata | null;
  onBackToSegment: () => void;
  scrapedPageData: any;
  isLoadingScrapedPage: boolean;
  handleSelectSubWebpage: (slug: string, url: string, title: string, summary: string) => Promise<void>;
}

export const InsightsConsoleModal: React.FC<InsightsConsoleModalProps> = ({
  selectedSource,
  onClose,
  modalTab,
  setModalTab,
  viewingSubWebpage,
  onBackToSegment,
  scrapedPageData,
  isLoadingScrapedPage,
  handleSelectSubWebpage
}) => {
  if (!selectedSource) return null;

  return (
    <div className="markdown-modal-backdrop" onClick={onClose}>
      <div 
        className="markdown-modal-container" 
        onClick={(e) => e.stopPropagation()} 
        style={{ 
          background: 'rgba(15, 15, 23, 0.94)', 
          backdropFilter: 'blur(20px)', 
          border: '1px solid rgba(255, 255, 255, 0.08)', 
          borderRadius: '16px', 
          display: 'flex', 
          flexDirection: 'column', 
          width: '85vw', 
          maxWidth: '1000px', 
          height: '85vh', 
          boxShadow: '0 24px 64px rgba(0,0,0,0.6)', 
          overflow: 'hidden' 
        }}
      >
        {/* Header section with Dynamic Title / Back Arrow */}
        <div 
          style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)', 
            padding: '1.25rem 1.5rem', 
            background: 'rgba(255, 255, 255, 0.01)' 
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {viewingSubWebpage && (
              <button 
                onClick={onBackToSegment} 
                style={{ 
                  border: 'none', 
                  background: 'rgba(255,255,255,0.05)', 
                  color: 'var(--accent-cyan)', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  width: '28px', 
                  height: '28px', 
                  borderRadius: '6px', 
                  cursor: 'pointer' 
                }}
              >
                ←
              </button>
            )}
            <div>
              <span 
                className="source-category-tag" 
                style={{ 
                  textTransform: 'uppercase', 
                  fontSize: '0.68rem', 
                  letterSpacing: '0.05em', 
                  marginBottom: '4px', 
                  display: 'inline-block' 
                }}
              >
                {viewingSubWebpage ? "Scraped Website" : selectedSource.type === 'segment' ? 'Memory Chat Segment' : 'Scraped Website'}
              </span>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', letterSpacing: '-0.02em', color: '#fff' }}>
                {viewingSubWebpage ? viewingSubWebpage.title : selectedSource.title}
              </h2>
            </div>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* View original link button */}
            {((viewingSubWebpage && viewingSubWebpage.url) || (!viewingSubWebpage && selectedSource.url)) && (
              <a 
                href={viewingSubWebpage ? viewingSubWebpage.url : selectedSource.url} 
                target="_blank" 
                rel="noopener noreferrer" 
                style={{ 
                  fontSize: '0.8rem', 
                  color: 'var(--accent-cyan)', 
                  background: 'rgba(6, 182, 212, 0.08)', 
                  border: '1px solid rgba(6, 182, 212, 0.15)', 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '6px', 
                  padding: '6px 12px', 
                  borderRadius: '6px', 
                  fontWeight: '600', 
                  textDecoration: 'none' 
                }}
              >
                Open Live Site <ExternalLink size={12} />
              </a>
            )}
            
            <button 
              className="drawer-close" 
              onClick={onClose}
              style={{ 
                background: 'rgba(255,255,255,0.04)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                padding: '6px', 
                borderRadius: '50%', 
                color: 'var(--text-secondary)' 
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>
        
        {/* Dual Tabs Selector for Conversation Segment logs */}
        {selectedSource.type === 'segment' && !viewingSubWebpage && (
          <div style={{ display: 'flex', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', background: 'rgba(255, 255, 255, 0.005)' }}>
            <button 
              className={`mode-btn ${modalTab === 'chat' ? 'active' : ''}`}
              onClick={() => setModalTab('chat')}
              style={{ 
                border: 'none', 
                background: 'none', 
                color: modalTab === 'chat' ? 'var(--accent-cyan)' : 'var(--text-tertiary)', 
                borderBottom: modalTab === 'chat' ? '2px solid var(--accent-cyan)' : 'none', 
                padding: '12px 24px', 
                cursor: 'pointer', 
                fontSize: '0.9rem', 
                fontWeight: '500', 
                borderRadius: 0 
              }}
            >
              💬 Chat Memory bubbles
            </button>
            {selectedSource.scraped_urls && selectedSource.scraped_urls.length > 0 && (
              <button 
                className={`mode-btn ${modalTab === 'resources' ? 'active' : ''}`}
                onClick={() => setModalTab('resources')}
                style={{ 
                  border: 'none', 
                  background: 'none', 
                  color: modalTab === 'resources' ? 'var(--accent-indigo)' : 'var(--text-tertiary)', 
                  borderBottom: modalTab === 'resources' ? '2px solid var(--accent-indigo)' : 'none', 
                  padding: '12px 24px', 
                  cursor: 'pointer', 
                  fontSize: '0.9rem', 
                  fontWeight: '500', 
                  borderRadius: 0 
                }}
              >
                🕸️ Scraped Websites ({selectedSource.scraped_urls.length})
              </button>
            )}
          </div>
        )}

        {/* Core Modal Body Content Scroll */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
          
          {/* Case 1: Displaying a scraped webpage (directly or sub-selected) */}
          {(selectedSource.type === 'webpage' || viewingSubWebpage) ? (
            isLoadingScrapedPage ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
                <Loader2 size={36} className="animate-spin text-cyan-400" style={{ color: 'var(--accent-cyan)' }} />
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Decrypting scraped website from cache...</span>
              </div>
            ) : scrapedPageData ? (
              <div className="rendered-markdown" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                
                {/* Fixed top glassmorphic summary callout */}
                {scrapedPageData.executive_summary && (
                  <div 
                    style={{ 
                      background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(6, 182, 212, 0.05) 100%)', 
                      border: '1px solid rgba(6, 182, 212, 0.15)', 
                      padding: '16px', 
                      borderRadius: '12px', 
                      boxShadow: '0 8px 32px rgba(0,0,0,0.15)', 
                      backdropFilter: 'blur(8px)' 
                    }}
                  >
                    <span 
                      style={{ 
                        fontSize: '0.72rem', 
                        fontWeight: 'bold', 
                        color: 'var(--accent-cyan)', 
                        textTransform: 'uppercase', 
                        letterSpacing: '0.05em', 
                        display: 'block', 
                        marginBottom: '6px' 
                      }}
                    >
                      AI Webpage Executive Summary
                    </span>
                    <p style={{ fontSize: '0.88rem', color: '#e4e4e7', lineHeight: '1.5' }}>
                      {scrapedPageData.executive_summary}
                    </p>
                  </div>
                )}
                
                {/* Rendered markdown body using custom parser */}
                <div style={{ padding: '4px 0' }}>
                  <MarkdownRenderer text={scrapedPageData.markdown} />
                </div>
                
                {/* Page tags */}
                {scrapedPageData.tags && scrapedPageData.tags.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '1.25rem', marginTop: '1rem' }}>
                    {scrapedPageData.tags.map((t: string) => (
                      <span key={t} className="pill-tag">#{t}</span>
                    ))}
                    {scrapedPageData.categories && scrapedPageData.categories.map((c: string) => (
                      <span key={c} className="pill-tag" style={{ borderColor: 'rgba(99, 102, 241, 0.25)', color: 'var(--accent-indigo)' }}>{c}</span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ color: '#ef4444' }}>Unable to load cached markdown page content.</span>
              </div>
            )
          ) : (
            
            /* Case 2: Displaying a segment */
            modalTab === 'chat' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                
                {/* AI segment summary callout */}
                {selectedSource.summary && (
                  <div style={{ background: 'rgba(255,255,255,0.015)', border: '1px solid rgba(255,255,255,0.05)', padding: '16px', borderRadius: '12px' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 'bold', color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '6px' }}>
                      AI Turn Executive Summary
                    </span>
                    <p style={{ fontSize: '0.88rem', color: '#e4e4e7', lineHeight: '1.5' }}>
                      {selectedSource.summary}
                    </p>
                  </div>
                )}
                
                {/* Chat Bubble History Stream component */}
                <ChatBubbleStream messages={selectedSource.messages} />
                
                {/* Segment tags */}
                {selectedSource.tags && selectedSource.tags.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '1.25rem' }}>
                    {selectedSource.tags.map((t) => (
                      <span key={t} className="pill-tag">#{t}</span>
                    ))}
                    <span className="pill-tag" style={{ borderColor: 'rgba(99, 102, 241, 0.25)', color: 'var(--accent-indigo)' }}>segment_id: {selectedSource.segment_id}</span>
                  </div>
                )}

              </div>
            ) : (
              
              /* Tab 2: Crawled Resources inside Segment */
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>The following web links were scraped and indexed from inside this segment:</span>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
                  {selectedSource.scraped_urls?.map((sUrl, idx) => (
                    <div 
                      key={idx}
                      onClick={() => handleSelectSubWebpage(sUrl.slug, sUrl.url, sUrl.title, sUrl.executive_summary)}
                      style={{ 
                        background: 'rgba(255,255,255,0.015)', 
                        border: '1px solid rgba(255,255,255,0.05)', 
                        padding: '16px', 
                        borderRadius: '10px', 
                        cursor: 'pointer', 
                        display: 'flex', 
                        flexDirection: 'column', 
                        gap: '6px', 
                        transition: 'all 0.2s ease', 
                        position: 'relative' 
                      }}
                      className="hover-glow-card"
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: 'bold', color: 'var(--accent-cyan)' }}>{sUrl.title}</h4>
                        <ChevronRight size={16} style={{ color: 'var(--text-tertiary)' }} />
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', fontFamily: 'var(--mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {sUrl.url}
                      </span>
                      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {sUrl.executive_summary}
                      </p>
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
                        {sUrl.tags?.map((t) => (
                          <span key={t} className="pill-tag" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>#{t}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )

          )}

        </div>
        
        {/* Modal Bottom Footer Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid rgba(255, 255, 255, 0.08)', padding: '1rem 1.5rem', background: 'rgba(255, 255, 255, 0.01)' }}>
          <button 
            className="submit-btn" 
            style={{ padding: '8px 20px', marginTop: 0 }}
            onClick={onClose}
          >
            Close Insights Console
          </button>
        </div>
      </div>
    </div>
  );
};
