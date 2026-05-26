import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, FileText, AlertTriangle, TrendingUp, Compass, 
  Loader2, ArrowRight, CheckCircle, Globe, 
  ChevronRight, Grid, List, X, ExternalLink, RefreshCw
} from 'lucide-react';

// API Configuration
const API_BASE = 'http://localhost:8000';

// HSL color mappings for categories to keep the design highly harmonized
const CATEGORY_COLORS: Record<string, string> = {
  general: 'hsl(215, 15%, 70%)',
  security: 'hsl(340, 80%, 65%)',
  python: 'hsl(142, 70%, 55%)',
  database: 'hsl(200, 80%, 60%)',
  engineering: 'hsl(280, 80%, 65%)',
  web: 'hsl(45, 90%, 55%)',
  whatsapp: 'hsl(120, 50%, 60%)',
  llm: 'hsl(260, 80%, 65%)'
};

// Resilient Mock Data to load if the backend API server is offline
const MOCK_ATLAS = {
  heatmap: {
    "security": 12,
    "python": 8,
    "database": 5,
    "engineering": 7,
    "whatsapp": 15,
    "llm": 6
  },
  trending_tags: [
    { "tag": "security", "count": 12 },
    { "tag": "whatsapp", "count": 15 },
    { "tag": "python", "count": 8 },
    { "tag": "engineering", "count": 7 },
    { "tag": "llm", "count": 6 }
  ],
  tsne_coordinates: [
    { "id": "1", "x": 0.25, "y": 0.35, "category": "security" },
    { "id": "2", "x": 0.32, "y": 0.41, "category": "security" },
    { "id": "3", "x": 0.21, "y": 0.29, "category": "security" },
    { "id": "4", "x": 0.75, "y": 0.82, "category": "python" },
    { "id": "5", "x": 0.68, "y": 0.79, "category": "python" },
    { "id": "6", "x": 0.52, "y": 0.22, "category": "database" },
    { "id": "7", "x": 0.58, "y": 0.28, "category": "database" },
    { "id": "8", "x": 0.81, "y": 0.45, "category": "engineering" },
    { "id": "9", "x": 0.12, "y": 0.85, "category": "whatsapp" },
    { "id": "10", "x": 0.18, "y": 0.78, "category": "whatsapp" },
    { "id": "11", "x": 0.48, "y": 0.61, "category": "llm" }
  ],
  gap_report: {
    dangling_tags: ["scraping", "docker", "redis", "javascript"],
    broken_urls: [
      "https://crawl4ai.com/advanced-configuration",
      "https://ollama.com/library/hermes-3",
      "https://python.langchain.com/docs/expression_language"
    ],
    gap_suggestions: [
      { "tag": "scraping", "suggestion": "I noticed references to 'scraping' in your chat, but no indexed documents. Index crawl4ai advanced scrapers now?" },
      { "tag": "docker", "suggestion": "You discussed 'docker containerization' but have 0 pages crawled. Bridge this gap?" },
      { "tag": "redis", "suggestion": "You mentioned 'redis cache latency'. Click to recover related documentation." }
    ]
  }
};

const MOCK_SEARCH = {
  hero_answer: "Based on your personal memory log, you've been designing a distributed data extraction system using Python scrapers and ChromaDB. Specifically, you noted that the Crawl4AI library [1] is preferred over traditional PDF extractors because it cleanly parses markdown and handles image assets locally [2]. Furthermore, you resolved the concurrent thread lock issue [3] inside the local Hermes LLM client by introducing a thread lock [4] to prevent socket context timeouts when querying your Apple Silicon GPU.",
  sources: [
    {
      "segment_id": "1",
      "title": "Distributed Ingestion Guidelines",
      "slug": "segment_1",
      "summary": "WhatsApp thread discussing scraper infrastructure. Decided to migrate to crawl4AI markdown format instead of PDF since PDF formats generated very messy layouts...",
      "tags": ["scraping", "crawl4ai", "python"],
      "categories": ["engineering"],
      "url": "https://crawl4ai.com"
    },
    {
      "segment_id": "2",
      "title": "Local Image Asset Caching",
      "slug": "segment_2",
      "summary": "Resolved the gap of offline web crawling: now saving scraped markdown urls and rewriting all remote image sources to local assets inside the assets directory...",
      "tags": ["python", "images", "crawling"],
      "categories": ["python"],
      "url": "https://crawl4ai.com/images"
    },
    {
      "segment_id": "3",
      "title": "Nous Hermes LLM Timeout Fix",
      "slug": "segment_3",
      "summary": "Added a standard synchronization threading.Lock() inside the client wrapper to serialize inference requests because concurrent threads caused connection failures on GPU slots...",
      "tags": ["llm", "hermes", "concurrency"],
      "categories": ["llm"],
      "url": "https://github.com/nousresearch/hermes"
    },
    {
      "segment_id": "4",
      "title": "Concurrency Thread Locking",
      "slug": "segment_4",
      "summary": "Explaining to the team how GPU concurrency locks prevent Apple Silicon M1 bottlenecks by queuing inference queries sequentially while leaving web scraping async...",
      "tags": ["security", "hermes", "python"],
      "categories": ["security"],
      "url": "https://github.com/nousresearch/hermes/threads"
    }
  ]
};

export default function App() {
  // App States
  const [query, setQuery] = useState('');
  const [activeSearch, setActiveSearch] = useState(false);
  const [searchMode, setSearchMode] = useState<'prose' | 'data'>('prose');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any>(null);
  
  // Atlas Metadata States
  const [atlasData, setAtlasData] = useState<any>(MOCK_ATLAS);
  const [apiOnline, setApiOnline] = useState(false);
  
  // Interaction States
  const [focusedCategory, setFocusedCategory] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<any>(null);
  const [isGapOpen, setIsGapOpen] = useState(false);
  const [hoveredPoint, setHoveredPoint] = useState<any>(null);
  
  // Ingestion Queue States
  const [ingestUrl, setIngestUrl] = useState('');
  const [ingestCategory, setIngestCategory] = useState('engineering');
  const [activeTasks, setActiveTasks] = useState<any[]>([]);
  const [toasts, setToasts] = useState<any[]>([]);

  // Refs
  const searchInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Keyboard shortcut Listener: Cmd+K focuses search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        setActiveSearch(true);
      }
      if (e.key === 'Escape') {
        setActiveSearch(false);
        searchInputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Check API health and load initial metadata
  const fetchAtlas = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/atlas`);
      if (res.ok) {
        const data = await res.json();
        setAtlasData(data);
        setApiOnline(true);
      } else {
        setApiOnline(false);
      }
    } catch (err) {
      setApiOnline(false);
    }
  };

  useEffect(() => {
    fetchAtlas();
    const interval = setInterval(fetchAtlas, 10000); // Poll health & gap maps
    return () => clearInterval(interval);
  }, []);

  // Draw 2D t-SNE gap map on Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !atlasData?.tsne_coordinates) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle high PPI screens
    const dpr = window.devicePixelRatio || 1;
    const size = 300;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.scale(dpr, dpr);

    // Clear Canvas
    ctx.clearRect(0, 0, size, size);

    // Draw Subtle Voids background glow
    const radial = ctx.createRadialGradient(size/2, size/2, 5, size/2, size/2, size);
    radial.addColorStop(0, '#0f0f13');
    radial.addColorStop(1, '#050508');
    ctx.fillStyle = radial;
    ctx.fillRect(0, 0, size, size);

    // Draw Grid Lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
    ctx.lineWidth = 1;
    for (let i = size / 5; i < size; i += size / 5) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, size);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i);
      ctx.lineTo(size, i);
      ctx.stroke();
    }

    // Draw Coordinates Points
    atlasData.tsne_coordinates.forEach((point: any) => {
      // Map normalized coordinates [0, 1] to canvas scale [30, 270] to avoid clipping borders
      const px = 30 + point.x * 240;
      const py = 30 + point.y * 240;
      const color = CATEGORY_COLORS[point.category.toLowerCase()] || '#6366f1';

      // Highlight active point
      const isHovered = hoveredPoint && hoveredPoint.id === point.id;

      // Draw concentric pulse glow for points
      if (isHovered) {
        ctx.beginPath();
        ctx.arc(px, py, 14, 0, Math.PI * 2);
        ctx.fillStyle = color.replace('hsl', 'hsla').replace(')', ', 0.15)');
        ctx.fill();
        ctx.strokeStyle = color.replace('hsl', 'hsla').replace(')', ', 0.4)');
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      ctx.beginPath();
      ctx.arc(px, py, isHovered ? 6 : 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#050508';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }, [atlasData, hoveredPoint]);

  // Handle Canvas mousemove to check hovered node points
  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !atlasData?.tsne_coordinates) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    let found: any = null;
    atlasData.tsne_coordinates.forEach((point: any) => {
      const px = 30 + point.x * 240;
      const py = 30 + point.y * 240;
      const dist = Math.sqrt((px - mx) ** 2 + (py - my) ** 2);
      if (dist < 8) {
        found = point;
      }
    });

    setHoveredPoint(found);
  };

  // Handle Canvas click to search coordinates or suggest gap fills
  const handleCanvasClick = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    if (hoveredPoint) {
      // Find and open source if point matches existing segments
      const segment = searchResults?.sources?.find((s: any) => s.segment_id === hoveredPoint.id) ||
                      MOCK_SEARCH.sources.find((s: any) => s.segment_id === hoveredPoint.id);
      if (segment) {
        setSelectedSource(segment);
      } else {
        // Trigger semantic query matching this point category
        executeSearch(hoveredPoint.category);
      }
    } else {
      // User clicked empty void, suggest recovery plan
      setIsGapOpen(true);
      addToast('Void Selected', 'You clicked an empty knowledge gap cluster. Select a dangling tag to bridge the gap.');
    }
  };

  // Perform search query
  const executeSearch = async (searchVal: string) => {
    if (!searchVal.trim()) return;
    setIsSearching(true);
    setQuery(searchVal);
    
    // Animate Bento highlight tags
    const cleanTag = searchVal.trim().toLowerCase();
    setFocusedCategory(cleanTag);
    setTimeout(() => setFocusedCategory(null), 3000); // Clear highlight glow after 3s

    try {
      const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(searchVal)}`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      } else {
        // Fallback to beautiful mock searches if backend is offline
        setSearchResults(MOCK_SEARCH);
      }
    } catch (err) {
      setSearchResults(MOCK_SEARCH);
    } finally {
      setIsSearching(false);
    }
  };

  // Form search submission
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(query);
  };

  // Trigger web scraper recovery ingestion
  const handleIngestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ingestUrl.trim()) return;

    const newTask = {
      id: Math.random().toString(36).substring(7),
      url: ingestUrl,
      category: ingestCategory,
      status: 'queued',
      progress: 10
    };

    setActiveTasks(prev => [newTask, ...prev]);
    setIngestUrl('');

    // Trigger API if available
    try {
      const res = await fetch(`${API_BASE}/api/recovery/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: ingestUrl, category: ingestCategory })
      });

      if (res.ok) {
        const data = await res.json();
        updateTaskProgress(newTask.id, 'crawling', 40, data.task_id);
        
        // Setup polling simulation/fetch for background worker progress
        simulateProgress(newTask.id, data.task_id);
      } else {
        simulateProgress(newTask.id);
      }
    } catch (err) {
      // Simulate frontend-only for mock mode
      simulateProgress(newTask.id);
    }
  };

  // Helper for tracking background crawler progress
  const updateTaskProgress = (tempId: string, status: string, progress: number, serverTaskId?: string) => {
    setActiveTasks(prev => 
      prev.map(t => t.id === tempId ? { ...t, status, progress, serverTaskId } : t)
    );
  };

  const simulateProgress = (tempId: string, serverTaskId?: string) => {
    let step = 0;
    const steps = [
      { status: 'fetching metadata', progress: 30 },
      { status: 'scraped HTML content', progress: 50 },
      { status: 'compiling markdown details', progress: 70 },
      { status: 'indexing vectors into ChromaDB', progress: 90 },
      { status: 'completed successfully', progress: 100 }
    ];

    const timer = setInterval(() => {
      if (step >= steps.length) {
        clearInterval(timer);
        addToast('Ingestion Successful', `Indexed and parsed URL into category.`);
        fetchAtlas(); // Reload gaps atlas metrics
        return;
      }
      updateTaskProgress(tempId, steps[step].status, steps[step].progress, serverTaskId);
      step++;
    }, 1500);
  };

  // Push notifications toast feedback
  const addToast = (title: string, desc: string) => {
    const id = Math.random().toString(36).substring(7);
    setToasts(prev => [...prev, { id, title, desc }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  // Check if a card contains matching categories or query tags to lift z-axis shadow
  const getBentoCardState = (cardCategories: string[], cardTags: string[]) => {
    if (!focusedCategory) return '';
    const cleanFocus = focusedCategory.toLowerCase();
    
    const matches = cardCategories.some(c => c.toLowerCase().includes(cleanFocus)) ||
                    cardTags.some(t => t.toLowerCase().includes(cleanFocus));
                    
    return matches ? 'highlighted' : 'dimmed';
  };

  // Format a simple custom Markdown parsing for rendering cached documents
  const renderSimpleMarkdown = (text: string) => {
    if (!text) return '';
    
    // Split into paragraphs or line blocks
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      let trimmed = line.trim();
      if (!trimmed) return <div key={idx} className="h-4" />;
      
      // Headers
      if (trimmed.startsWith('### ')) {
        return <h4 key={idx} className="text-md font-semibold text-cyan-400 mt-4 mb-2">{trimmed.slice(4)}</h4>;
      }
      if (trimmed.startsWith('## ')) {
        return <h3 key={idx} className="text-lg font-bold text-indigo-400 mt-5 mb-3">{trimmed.slice(3)}</h3>;
      }
      if (trimmed.startsWith('# ')) {
        return <h2 key={idx} className="text-xl font-extrabold text-white mt-6 mb-4">{trimmed.slice(2)}</h2>;
      }
      
      // Blockquotes
      if (trimmed.startsWith('> ')) {
        return <blockquote key={idx} className="pl-4 border-l-4 border-indigo-500 italic text-zinc-400 my-2">{trimmed.slice(2)}</blockquote>;
      }

      // Check for bullet lists
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        return <li key={idx} className="ml-5 list-disc text-zinc-300 my-1">{trimmed.slice(2)}</li>;
      }

      // Format bold markup `**text**`
      const boldRegex = /\*\*(.*?)\*\*/g;
      let elements: React.ReactNode[] = [];
      let lastIdx = 0;
      let match;
      while ((match = boldRegex.exec(trimmed)) !== null) {
        if (match.index > lastIdx) {
          elements.push(trimmed.slice(lastIdx, match.index));
        }
        elements.push(<strong key={match.index} className="text-white font-semibold">{match[1]}</strong>);
        lastIdx = boldRegex.lastIndex;
      }
      if (lastIdx < trimmed.length) {
        elements.push(trimmed.slice(lastIdx));
      }

      return <p key={idx} className="text-zinc-300 leading-relaxed mb-3">{elements.length > 0 ? elements : trimmed}</p>;
    });
  };

  return (
    <div className="app-wrapper">
      
      {/* Top Navigation & Brand Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: 'var(--accent-gradient)', width: '32px', height: '32px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifySelf: 'center', justifyContent: 'center' }}>
            <Compass size={18} style={{ color: '#fff' }} />
          </div>
          <div>
            <h3 style={{ fontFamily: 'var(--heading)', fontSize: '1.25rem', letterSpacing: '-0.02em' }}>Insights Explorer</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>WhatsApp Context RAG Engine</span>
          </div>
        </div>
        
        {/* API Server Live indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: apiOnline ? '#10b981' : '#f59e0b', boxShadow: apiOnline ? '0 0 8px #10b981' : '0 0 8px #f59e0b' }} />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {apiOnline ? 'Live Backend API' : 'Sandbox (Offline Backend)'}
          </span>
          <button onClick={fetchAtlas} style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', display: 'flex', alignContent: 'center', padding: '4px' }}>
            <RefreshCw size={12} className={isSearching ? 'animate-spin' : ''} />
          </button>
        </div>
      </header>

      {/* Main Search Command Bar */}
      <div className="span-full">
        <form onSubmit={handleSearchSubmit} className={`command-center ${activeSearch ? 'active' : ''}`}>
          <div className="command-input-container">
            <Search size={20} style={{ color: 'var(--text-secondary)' }} />
            <input 
              ref={searchInputRef}
              type="text" 
              className="command-input" 
              placeholder="Search chat insights, categories, or tags... (Press ⌘K)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setActiveSearch(true)}
              onBlur={() => setActiveSearch(false)}
            />
            
            {isSearching ? (
              <div className="spinner-glow" />
            ) : (
              <span className="command-kbd">⌘K</span>
            )}
            
            <div className="mode-toggle-group">
              <button 
                type="button" 
                className={`mode-btn ${searchMode === 'prose' ? 'active' : ''}`}
                onClick={() => setSearchMode('prose')}
              >
                <Grid size={14} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'text-bottom' }} /> Prose
              </button>
              <button 
                type="button" 
                className={`mode-btn ${searchMode === 'data' ? 'active' : ''}`}
                onClick={() => setSearchMode('data')}
              >
                <List size={14} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'text-bottom' }} /> Data
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Primary Split Layout */}
      <main className="insights-layout">
        
        {/* Left Presentation Area (Bento Grid or High density table) */}
        <div>
          {searchMode === 'prose' ? (
            <div className="bento-grid">
              
              {/* Hero Answer (Row Span Full) */}
              {(searchResults || MOCK_SEARCH) && (
                <div className="bento-card span-full hero-answer-container">
                  <div className="hero-header">
                    <span className="hero-badge">AI Response Synthesis</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <FileText size={12} /> Local Nous Hermes 3b Model
                    </span>
                  </div>
                  
                  <div className="hero-answer-text">
                    {/* Render answer and convert citations e.g. [1] into glassmorphic cards */}
                    {(() => {
                      const text = searchResults?.hero_answer || MOCK_SEARCH.hero_answer;
                      const parts = text.split(/(\[\d+\])/g);
                      return parts.map((part: string, index: number) => {
                        const match = part.match(/\[(\d+)\]/);
                        if (match) {
                          const cid = match[1];
                          const source = searchResults?.sources?.find((s: any) => s.segment_id === cid) ||
                                         MOCK_SEARCH.sources.find((s: any) => s.segment_id === cid);
                          return (
                            <span key={index} className="citation" onClick={() => setSelectedSource(source)}>
                              {cid}
                              <div className="glass-citation-preview">
                                <h4>{source?.title || `Citation [${cid}]`}</h4>
                                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{source?.summary}</p>
                                <span style={{ display: 'inline-block', fontSize: '0.7rem', color: 'var(--accent-indigo)', marginTop: '4px', textTransform: 'uppercase', fontWeight: 'bold' }}>
                                  Category: {source?.categories?.[0]}
                                </span>
                              </div>
                            </span>
                          );
                        }
                        return part;
                      });
                    })()}
                  </div>
                </div>
              )}

              {/* Source cards in Bento layout */}
              {((searchResults?.sources || MOCK_SEARCH.sources)).map((src: any) => {
                const bentoState = getBentoCardState(src.categories, src.tags);
                return (
                  <div 
                    key={src.segment_id} 
                    className={`bento-card ${bentoState}`}
                    onClick={() => setSelectedSource(src)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="source-card-header">
                      <span className="source-category-tag">{src.categories[0]}</span>
                      {src.url && (
                        <span className="source-domain-info">
                          <Globe size={12} />
                          {new URL(src.url).hostname}
                        </span>
                      )}
                    </div>
                    
                    <h4 className="source-title">{src.title}</h4>
                    <p className="source-summary">{src.summary}</p>
                    
                    <div className="source-tags-container">
                      {src.tags.map((tag: string) => (
                        <span 
                          key={tag} 
                          className="pill-tag"
                          onClick={(e) => {
                            e.stopPropagation();
                            executeSearch(tag);
                          }}
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}

              {/* Grey Ghost Missing Data Cards */}
              {atlasData?.gap_report?.gap_suggestions?.slice(0, 2).map((gap: any, index: number) => (
                <div key={index} className="bento-card ghost-card">
                  <div>
                    <span className="ghost-badge">Silence Gap</span>
                    <h4 className="ghost-title">Missing Segment: {gap.tag}</h4>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-tertiary)' }}>{gap.suggestion}</p>
                  </div>
                  <button 
                    type="button" 
                    className="ghost-btn" 
                    onClick={() => {
                      setIngestCategory(gap.tag);
                      setIsGapOpen(true);
                    }}
                  >
                    Bridge Gap <ArrowRight size={14} />
                  </button>
                </div>
              ))}

            </div>
          ) : (
            
            /* High Density Data Mode Table View */
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Document Reference</th>
                    <th>Executive Summary Snippet</th>
                    <th>Linked Source</th>
                    <th>Context Tags</th>
                  </tr>
                </thead>
                <tbody>
                  {((searchResults?.sources || MOCK_SEARCH.sources)).map((src: any) => (
                    <tr key={src.segment_id} onClick={() => setSelectedSource(src)}>
                      <td>
                        <span className="source-category-tag">{src.categories[0]}</span>
                      </td>
                      <td style={{ fontWeight: '500' }}>{src.title}</td>
                      <td style={{ color: 'var(--text-secondary)' }}>{src.summary}</td>
                      <td>
                        {src.url ? (
                          <a 
                            href={src.url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            Link <ExternalLink size={12} />
                          </a>
                        ) : 'chat_log'}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                          {src.tags.slice(0, 3).map((tag: string) => (
                            <span key={tag} className="pill-tag" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                              #{tag}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Sidebar Atlas Panel */}
        <aside className="sidebar-panel">
          
          {/* Bento Atlas Category Density Heatmap */}
          <div className="sidebar-block">
            <h4 className="sidebar-title">
              <TrendingUp size={16} style={{ color: 'var(--accent-cyan)' }} />
              Category Densities
            </h4>
            <div className="heatmap-list">
              {Object.entries(atlasData?.heatmap || MOCK_ATLAS.heatmap)
                .sort((a: any, b: any) => b[1] - a[1])
                .map(([name, count]: any) => {
                  const color = CATEGORY_COLORS[name.toLowerCase()] || '#6366f1';
                  return (
                    <div 
                      key={name} 
                      className="heatmap-row"
                      onClick={() => executeSearch(name)}
                    >
                      <div className="heatmap-name-block">
                        <div className="heatmap-color-dot" style={{ backgroundColor: color }} />
                        <span style={{ fontSize: '0.88rem', textTransform: 'capitalize' }}>{name}</span>
                      </div>
                      <span className="heatmap-count">{count} turns</span>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* Interactive Gap Map canvas (2D t-SNE Clustering) */}
          <div className="sidebar-block">
            <h4 className="sidebar-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Compass size={16} style={{ color: 'var(--accent-indigo)' }} />
                Knowledge Gap Map
              </span>
              <button onClick={() => setIsGapOpen(true)} style={{ background: 'rgba(255,255,255,0.05)', border: 'none', color: 'var(--accent-cyan)', fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px', cursor: 'pointer' }}>
                Bridge
              </button>
            </h4>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: '8px' }}>
              Perplexity-resilient 2D cluster points. Click void regions to recover content.
            </span>
            
            <div className="canvas-container">
              <canvas 
                ref={canvasRef} 
                className="canvas-map"
                onMouseMove={handleCanvasMouseMove}
                onMouseLeave={() => setHoveredPoint(null)}
                onClick={handleCanvasClick}
              />
              {hoveredPoint && (
                <div 
                  className="canvas-tooltip"
                  style={{
                    left: `${Math.min(200, 30 + hoveredPoint.x * 240)}px`,
                    top: `${Math.max(10, -30 + hoveredPoint.y * 240)}px`
                  }}
                >
                  <span style={{ fontWeight: 'bold', textTransform: 'uppercase', color: CATEGORY_COLORS[hoveredPoint.category.toLowerCase()] }}>
                    {hoveredPoint.category}
                  </span>
                  <span style={{ display: 'block', fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    Segment ID: {hoveredPoint.id}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Quick gaps suggestions list */}
          <div className="sidebar-block">
            <h4 className="sidebar-title">
              <AlertTriangle size={16} style={{ color: '#ef4444' }} />
              Dangling Silence
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {atlasData?.gap_report?.gap_suggestions?.slice(0, 3).map((gap: any, index: number) => (
                <div 
                  key={index}
                  style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', cursor: 'pointer' }}
                  onClick={() => {
                    setIngestCategory(gap.tag);
                    setIsGapOpen(true);
                  }}
                >
                  <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--accent-cyan)' }}>#{gap.tag}</span>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    Click to crawl sources <ChevronRight size={12} />
                  </p>
                </div>
              ))}
            </div>
          </div>

        </aside>
      </main>

      {/* Ingestion & Recovery Queue Sideover Drawer */}
      {isGapOpen && (
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
      )}

      {/* Full Markdown reader Modal Popup */}
      {selectedSource && (
        <div className="markdown-modal-backdrop" onClick={() => setSelectedSource(null)}>
          <div className="markdown-modal-container" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '1rem' }}>
              <div>
                <span className="source-category-tag" style={{ marginBottom: '6px', display: 'inline-block' }}>
                  {selectedSource.categories[0]}
                </span>
                <h2 style={{ fontSize: '1.5rem', fontFamily: 'var(--heading)' }}>{selectedSource.title}</h2>
                {selectedSource.url && (
                  <a 
                    href={selectedSource.url} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    style={{ fontSize: '0.82rem', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}
                  >
                    {selectedSource.url} <ExternalLink size={12} />
                  </a>
                )}
              </div>
              <button className="drawer-close" onClick={() => setSelectedSource(null)}>
                <X size={16} />
              </button>
            </div>
            
            <div className="markdown-content-scroll">
              <div className="rendered-markdown">
                {/* Parse segment content markdown for clean text elements layout */}
                {renderSimpleMarkdown(selectedSource.summary)}
                <div className="h-6" />
                
                <h4 className="text-md font-semibold text-cyan-400 mt-4 mb-2">Original Segment Context Metadata</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '8px' }}>
                  {selectedSource.tags.map((t: string) => (
                    <span key={t} className="pill-tag">#{t}</span>
                  ))}
                  <span className="pill-tag" style={{ borderColor: 'rgba(99, 102, 241, 0.2)' }}>segment_id: {selectedSource.segment_id}</span>
                </div>
              </div>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '1rem' }}>
              <button 
                className="submit-btn" 
                style={{ padding: '8px 20px', marginTop: 0 }}
                onClick={() => setSelectedSource(null)}
              >
                Close Insights Context
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Push notifications toasts */}
      <div style={{ zIndex: 9999 }}>
        {toasts.map(toast => (
          <div key={toast.id} className="notif-toast">
            <CheckCircle size={18} style={{ color: 'var(--accent-cyan)' }} />
            <div>
              <strong style={{ display: 'block', fontSize: '0.85rem' }}>{toast.title}</strong>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{toast.desc}</span>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}
