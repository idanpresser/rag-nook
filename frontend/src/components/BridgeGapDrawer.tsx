import React from 'react';
import { X, CheckCircle, Loader2 } from 'lucide-react';
import type { AtlasData, IngestTask } from '../types';

interface BridgeGapDrawerProps {
  isGapOpen: boolean;
  setIsGapOpen: (open: boolean) => void;
  ingestUrl: string;
  setIngestUrl: (url: string) => void;
  ingestCategory: string;
  setIngestCategory: (category: string) => void;
  activeTasks: IngestTask[];
  atlasData: AtlasData | null;
  handleIngestSubmit: (e: React.FormEvent) => void;
  addToast: (title: string, message: string) => void;
}

export const BridgeGapDrawer: React.FC<BridgeGapDrawerProps> = ({
  isGapOpen,
  setIsGapOpen,
  ingestUrl,
  setIngestUrl,
  ingestCategory,
  setIngestCategory,
  activeTasks,
  atlasData,
  handleIngestSubmit,
  addToast
}) => {
  if (!isGapOpen) return null;

  return (
    <div className="drawer-backdrop" onClick={() => setIsGapOpen(false)}>
      <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <h3 style={{ fontSize: '1.25rem' }}>Bridge The Gap</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>Trigger async web crawlers</span>
          </div>
          <button className="drawer-close" onClick={() => setIsGapOpen(false)}>
            <X size={16} />
          </button>
        </div>

        {/* Ingestion Trigger Form */}
        <form onSubmit={handleIngestSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h4 style={{ fontSize: '0.95rem', color: 'var(--text-secondary)' }}>Scrape & Index Document</h4>
          
          <div className="form-group">
            <label className="form-label">Crawl URL Target</label>
            <input 
              type="url" 
              required
              className="form-input" 
              placeholder="https://crawl4ai.com/documentation"
              value={ingestUrl}
              onChange={(e) => setIngestUrl(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">RAG Category Index</label>
            <select 
              className="form-input" 
              value={ingestCategory} 
              onChange={(e) => setIngestCategory(e.target.value)}
              style={{ background: '#181820' }}
            >
              <option value="engineering">Engineering</option>
              <option value="security">Security</option>
              <option value="python">Python Scrapers</option>
              <option value="database">Databases</option>
              <option value="llm">Local LLMs</option>
            </select>
          </div>

          <button type="submit" className="submit-btn">
            Approve & Ingest Context
          </button>
        </form>

        {/* Active Ingest Status Progress Bar */}
        {activeTasks.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '1.25rem' }}>
            <h4 style={{ fontSize: '0.95rem', color: 'var(--text-secondary)' }}>Scraper Progress Logs</h4>
            <div className="recovery-list">
              {activeTasks.map(task => (
                <div key={task.id} className="recovery-item">
                  <span className="recovery-url">{task.url}</span>
                  <div className="recovery-action-block">
                    <span style={{ fontSize: '0.75rem', textTransform: 'capitalize', color: task.progress === 100 ? '#10b981' : 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {task.progress === 100 ? <CheckCircle size={12} /> : <Loader2 size={12} className="animate-spin" />}
                      {task.status}
                    </span>
                    <span style={{ fontSize: '0.75rem', fontFamily: 'var(--mono)' }}>{task.progress}%</span>
                  </div>
                  
                  {/* Rich progress bar fill */}
                  <div style={{ width: '100%', height: '4px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ width: `${task.progress}%`, height: '100%', background: 'var(--accent-gradient)', transition: 'width 0.4s ease' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dangling silence reports */}
        <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '1.25rem' }}>
          <h4 style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>Silence Stale Links Queue</h4>
          <div className="recovery-list">
            {atlasData?.gap_report?.broken_urls?.slice(0, 3).map((bUrl: string, idx: number) => (
              <div key={idx} className="recovery-item" style={{ background: 'rgba(239, 68, 68, 0.02)', borderColor: 'rgba(239, 68, 68, 0.1)' }}>
                <span className="recovery-url" style={{ color: '#ef4444' }}>{bUrl}</span>
                <div className="recovery-action-block">
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>HEAD 404 Stale Connection</span>
                  <button 
                    style={{ border: 'none', background: 'var(--accent-cyan)', color: 'var(--bg-base)', padding: '2px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.72rem', fontWeight: 'bold' }}
                    onClick={() => {
                      setIngestUrl(bUrl);
                      addToast('Stale Link Selected', 'Loaded stale link URL into crawling form.');
                    }}
                  >
                    Recrawl
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
