import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, FileText, AlertTriangle, TrendingUp, Compass, 
  ArrowRight, Globe, ChevronRight, Grid, List, RefreshCw, ExternalLink, CheckCircle, Cpu,
  Sliders, ChevronDown, ChevronUp, Save, Play, Loader2, Database, Trash2, Plus, Send, Upload, Download
} from 'lucide-react';

import type { AtlasData, Source, IngestTask } from './types';
import { CATEGORY_COLORS } from './constants/colors';
import { KnowledgeGapMap } from './components/KnowledgeGapMap';
import { BridgeGapDrawer } from './components/BridgeGapDrawer';
import { InsightsConsoleModal } from './components/InsightsConsoleModal';

// API Configuration
const API_BASE = 'http://localhost:8000';

// Resilient Mock Data to load if the backend API server is offline
const MOCK_ATLAS: AtlasData = {
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
      { "tag": "scraping", "suggestion": "scraped website contains stale HTML elements; we need to recrawl dynamic selectors." },
      { "tag": "docker", "suggestion": "missing container instructions inside git; our next deployment will require vector volume stores." },
      { "tag": "redis", "suggestion": "concurrency queues rely on memory caching; configure a cluster connection pool." }
    ]
  }
};

const MOCK_SEARCH = {
  "hero_answer": "We have successfully resolved multiple critical backend bottlenecks. In segment [1], we handled Nous Hermes local LLM model connection timeouts by introducing a concurrency threading lock. In segment [2], we resolved the offline image retrieval gap by writing remote assets into local directories. For general scaling, our scraping logic was split into parallel pipelines [3] and sequential indexing vectors [4] to maintain local execution stability.",
  "sources": [
    {
      "segment_id": "1",
      "title": "Nous Hermes LLM Timeout Fix",
      "slug": "segment_1",
      "summary": "Added a standard synchronization threading.Lock() inside the client wrapper to serialize inference requests because concurrent threads caused connection failures on GPU slots...",
      "tags": ["llm", "hermes", "concurrency"],
      "categories": ["llm"],
      "url": "https://github.com/nousresearch/hermes",
      "type": "segment" as const,
      "messages": [
        { "datetime_utc": "2026-05-26T10:14:00Z", "sender": "System", "content": "Initializing Nous Hermes 3B on Local CUDA device", "media_type": "system", "tags": [], "scraped_urls": [] },
        { "datetime_utc": "2026-05-26T10:15:20Z", "sender": "Idan P", "content": "Hey team, the local LLM fails when multiple scraping threads finish together. We hit GPU connection pool limits.", "tags": ["llm", "hermes"], "scraped_urls": [] },
        { "datetime_utc": "2026-05-26T10:16:45Z", "sender": "Alex K", "content": "That is because the llama.cpp server is single-context. We must queue the requests sequentially. I will add a threading Lock.", "tags": ["llm", "concurrency"], "scraped_urls": [] }
      ]
    },
    {
      "segment_id": "2",
      "title": "Local Image Asset Caching",
      "slug": "segment_2",
      "summary": "Resolved the gap of offline web crawling: now saving scraped markdown urls and rewriting all remote image sources to local assets inside the assets directory...",
      "tags": ["python", "images", "crawling"],
      "categories": ["python"],
      "url": "https://crawl4ai.com/images",
      "type": "segment" as const,
      "messages": [
        { "datetime_utc": "2026-05-26T11:02:10Z", "sender": "Idan P", "content": "When crawling websites, the references link to external CDNs. If we are offline, our markdown view breaks.", "tags": ["images", "crawling"], "scraped_urls": [] },
        { "datetime_utc": "2026-05-26T11:04:30Z", "sender": "System", "content": "Assets fetcher downloaded 14 images to local directory.", "media_type": "system", "tags": [], "scraped_urls": [] }
      ]
    },
    {
      "segment_id": "3",
      "title": "Parallel Scrapers Architecture",
      "slug": "segment_3",
      "summary": "Implemented a dual-queue system. The network crawling queue works asynchronously with 4 concurrent threads, while the vector database RAG indexing queue operates purely sequentially...",
      "tags": ["engineering", "concurrency", "database"],
      "categories": ["engineering"],
      "url": "https://github.com/idaneyal/personal_memory",
      "type": "segment" as const,
      "messages": [
        { "datetime_utc": "2026-05-26T11:20:00Z", "sender": "Alex K", "content": "We need to split extraction to two separate queues: URL downloading (4 operations parallel) and serial LLM vector indexing.", "tags": ["engineering", "concurrency"], "scraped_urls": [] }
      ]
    },
    {
      "segment_id": "4",
      "title": "Dynamic Environment Config",
      "slug": "segment_4",
      "summary": "Moved all Magic Numbers, timeouts, local model endpoints, and LLM retry parameters out of backend code files and into a centralized environment loading config...",
      "tags": ["security", "engineering"],
      "categories": ["security"],
      "url": "https://github.com/idaneyal/personal_memory/config",
      "type": "segment" as const,
      "messages": [
        { "datetime_utc": "2026-05-26T12:05:00Z", "sender": "Idan P", "content": "Ensure LLM endpoints are dynamic so we can switch from Ollama to OpenAI easily.", "tags": ["security", "engineering"], "scraped_urls": [] }
      ]
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
  const [atlasData, setAtlasData] = useState<AtlasData | null>(MOCK_ATLAS);
  const [apiOnline, setApiOnline] = useState(false);
  
  // Interaction States
  const [focusedCategory, setFocusedCategory] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [isGapOpen, setIsGapOpen] = useState(false);
  const [sidebarTab, setSidebarTab] = useState<'overview' | 'ingestion' | 'settings'>('overview');

  // Premium Insights Reader States
  const [scrapedPageData, setScrapedPageData] = useState<any>(null);
  const [isLoadingScrapedPage, setIsLoadingScrapedPage] = useState<boolean>(false);
  const [modalTab, setModalTab] = useState<'chat' | 'resources'>('chat');
  const [viewingSubWebpage, setViewingSubWebpage] = useState<any>(null);
  
  // Ingestion Queue States
  const [ingestUrl, setIngestUrl] = useState('');
  const [ingestCategory, setIngestCategory] = useState('engineering');
  const [activeTasks, setActiveTasks] = useState<IngestTask[]>([]);
  const [toasts, setToasts] = useState<any[]>([]);

  // LM Studio SDK model management states
  const [lmsStatus, setLmsStatus] = useState<any>(null);
  const [actioningModel, setActioningModel] = useState<string | null>(null);

  // Advanced Settings state
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const [tempSegment, setTempSegment] = useState(0.2);
  const [tempWebpage, setTempWebpage] = useState(0.2);
  const [tempSearch, setTempSearch] = useState(0.3);
  const [maxTokens, setMaxTokens] = useState(128000);
  const [promptEtl, setPromptEtl] = useState('');
  const [promptSearch, setPromptSearch] = useState('');
  const [routingEtlModel, setRoutingEtlModel] = useState('');
  const [routingSearchModel, setRoutingSearchModel] = useState('');
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  // Pipeline execution states
  const [pipelineStatus, setPipelineStatus] = useState<any>(null);
  const [isResuming, setIsResuming] = useState(false);

  const fetchPipelineStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/pipeline/status`);
      if (res.ok) {
        const data = await res.json();
        setPipelineStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch pipeline status:", err);
    }
  };

  const handleResumePipeline = async () => {
    setIsResuming(true);
    try {
      const res = await fetch(`${API_BASE}/api/pipeline/resume`, {
        method: 'POST'
      });
      if (res.ok) {
        addToast("Pipeline Resumed", "Ingestion task successfully triggered in the background.");
        fetchPipelineStatus();
      } else {
        const err = await res.json();
        addToast("Action Failed", err.detail || "Could not resume the pipeline.");
      }
    } catch (err) {
      addToast("Connection Error", "Failed to connect to the backend server.");
    } finally {
      setIsResuming(false);
    }
  };

  // Direct quick ingestion states
  const [singleIngestText, setSingleIngestText] = useState('');
  const [isIngestingMessage, setIsIngestingMessage] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);

  const handleIngestMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!singleIngestText.trim()) return;
    setIsIngestingMessage(true);
    try {
      const res = await fetch(`${API_BASE}/api/ingest/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: singleIngestText, sender: 'User' })
      });
      if (res.ok) {
        addToast("Message Ingested", "Your message/link has been appended. Background indexing triggered!");
        setSingleIngestText('');
        fetchPipelineStatus();
      } else {
        const err = await res.json();
        addToast("Ingestion Failed", err.detail || "Could not ingest message.");
      }
    } catch (err) {
      addToast("Connection Error", "Failed to connect to the backend server.");
    } finally {
      setIsIngestingMessage(false);
    }
  };

  const handleIngestFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.name.endsWith('.txt')) {
      addToast("Invalid File Type", "Only plain text (.txt) files are supported.");
      return;
    }
    
    setIsUploadingFile(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await fetch(`${API_BASE}/api/ingest/file`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        addToast("File Ingested", `Successfully merged ${file.name} into active database and triggered background processing!`);
        fetchPipelineStatus();
      } else {
        const err = await res.json();
        addToast("Upload Failed", err.detail || "Could not process text file.");
      }
    } catch (err) {
      addToast("Connection Error", "Failed to connect to the server.");
    } finally {
      setIsUploadingFile(false);
      e.target.value = '';
    }
  };

  // Archive export and import states
  const [isExportingArchive, setIsExportingArchive] = useState(false);
  const [isImportingArchive, setIsImportingArchive] = useState(false);

  const handleExportArchive = async () => {
    if (isExportingArchive) return;
    setIsExportingArchive(true);
    try {
      addToast("Exporting Archive", "Compiling zip package of your database, markdown pages, images, and raw chat logs...");
      const res = await fetch(`${API_BASE}/api/archive/export`);
      if (res.ok) {
        const blob = await res.blob();
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `personal_memory_base_${new Date().toISOString().slice(0, 10)}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        addToast("Export Complete", "Memory base archive successfully downloaded!");
      } else {
        const err = await res.json();
        addToast("Export Failed", err.detail || "Could not generate backup archive.");
      }
    } catch (err) {
      addToast("Connection Error", "Failed to connect to the server.");
    } finally {
      setIsExportingArchive(false);
    }
  };

  const handleImportArchive = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.name.endsWith('.zip')) {
      addToast("Invalid File Type", "Only .zip memory archives are supported.");
      return;
    }
    
    if (!window.confirm("WARNING: Importing a memory archive will completely replace your active chat database, scraped pages, and indexing. Are you sure you want to proceed?")) {
      e.target.value = '';
      return;
    }
    
    setIsImportingArchive(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      addToast("Importing Memory Base", "Uploading, extracting, and hot-reloading your database archive...");
      const res = await fetch(`${API_BASE}/api/archive/import`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        addToast("Import Successful", "Memory base successfully restored! Reloading dashboard views.");
        fetchAtlas();
        fetchLmsStatus();
        fetchPipelineStatus();
        fetchBackups();
      } else {
        const err = await res.json();
        addToast("Import Failed", err.detail || "Could not restore archive.");
      }
    } catch (err) {
      addToast("Connection Error", "Failed to connect to the server.");
    } finally {
      setIsImportingArchive(false);
      e.target.value = '';
    }
  };

  // Database backup states
  const [backups, setBackups] = useState<any[]>([]);
  const [backupLabel, setBackupLabel] = useState('');
  const [isCreatingBackup, setIsCreatingBackup] = useState(false);
  const [isRestoringBackup, setIsRestoringBackup] = useState(false);

  const fetchBackups = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/backup/list`);
      if (res.ok) {
        const data = await res.json();
        setBackups(data);
      }
    } catch (err) {
      console.error("Failed to fetch backups:", err);
    }
  };

  const handleCreateBackup = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isCreatingBackup) return;
    setIsCreatingBackup(true);
    try {
      const res = await fetch(`${API_BASE}/api/backup/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: backupLabel || 'snapshot' })
      });
      if (res.ok) {
        const data = await res.json();
        addToast("Snapshot Created", data.message || `Snapshot ${data.name} created successfully.`);
        setBackupLabel('');
        fetchBackups();
      } else {
        const err = await res.json();
        addToast("Snapshot Failed", err.detail || "Could not create database snapshot.");
      }
    } catch (err) {
      addToast("Connection Error", "Failed to connect to the backend server.");
    } finally {
      setIsCreatingBackup(false);
    }
  };

  const handleRestoreBackup = async (name: string) => {
    if (isRestoringBackup) return;
    if (!window.confirm(`Are you sure you want to restore the snapshot "${name}"? This will replace the active vector database collection.`)) {
      return;
    }
    setIsRestoringBackup(true);
    try {
      const res = await fetch(`${API_BASE}/api/backup/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      if (res.ok) {
        addToast("Snapshot Restored", "Database successfully restored from snapshot. UI views will refresh.");
        fetchAtlas();
        fetchLmsStatus();
        fetchPipelineStatus();
        fetchBackups();
      } else {
        const err = await res.json();
        addToast("Restore Failed", err.detail || "Could not restore database snapshot.");
      }
    } catch (err) {
      addToast("Connection Error", "Failed to connect to the backend server.");
    } finally {
      setIsRestoringBackup(false);
    }
  };

  const handleDeleteBackup = async (name: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete the snapshot "${name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/backup/${name}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        addToast("Snapshot Deleted", "Database snapshot backup permanently deleted.");
        fetchBackups();
      } else {
        const err = await res.json();
        addToast("Delete Failed", err.detail || "Could not delete snapshot.");
      }
    } catch (err) {
      addToast("Connection Error", "Failed to connect to the backend server.");
    }
  };

  const fetchLmsStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/lms/models`);
      if (res.ok) {
        const data = await res.json();
        setLmsStatus(data);
        if (data.active_settings) {
          // Premium Interaction: Only sync backend values when not actively editing
          setTempSegment((prev) => showAdvancedSettings ? prev : data.active_settings.temperature_segment);
          setTempWebpage((prev) => showAdvancedSettings ? prev : data.active_settings.temperature_webpage);
          setTempSearch((prev) => showAdvancedSettings ? prev : data.active_settings.temperature_search);
          setMaxTokens((prev) => showAdvancedSettings ? prev : data.active_settings.max_tokens);
          setPromptEtl((prev) => showAdvancedSettings ? prev : data.active_settings.prompt_etl);
          setPromptSearch((prev) => showAdvancedSettings ? prev : data.active_settings.prompt_search);
          setRoutingEtlModel((prev) => showAdvancedSettings ? prev : (data.active_settings.routing_etl_model || ''));
          setRoutingSearchModel((prev) => showAdvancedSettings ? prev : (data.active_settings.routing_search_model || ''));
        }
      }
    } catch (err) {
      console.error("Failed to fetch LM Studio status:", err);
    }
  };

  const handleLoadModel = async (modelKey: string) => {
    setActioningModel(modelKey);
    try {
      const res = await fetch(`${API_BASE}/api/lms/model/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_key: modelKey })
      });
      if (res.ok) {
        addToast("Model Loaded", `Successfully loaded ${modelKey.split('/').pop()}`);
        fetchLmsStatus();
      } else {
        const err = await res.json();
        addToast("Load Failed", err.detail || "Could not load the selected model.");
      }
    } catch (err: any) {
      addToast("Connection Error", "Failed to connect to the backend server.");
    } finally {
      setActioningModel(null);
    }
  };

  const handleUnloadModel = async (modelKey: string) => {
    setActioningModel(modelKey);
    try {
      const res = await fetch(`${API_BASE}/api/lms/model/unload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_key: modelKey })
      });
      if (res.ok) {
        addToast("Model Unloaded", `Successfully unloaded ${modelKey.split('/').pop()}`);
        fetchLmsStatus();
      } else {
        const err = await res.json();
        addToast("Unload Failed", err.detail || "Could not unload the model.");
      }
    } catch (err: any) {
      addToast("Connection Error", "Failed to connect to the backend server.");
    } finally {
      setActioningModel(null);
    }
  };

  const handleSaveSettings = async () => {
    setIsSavingSettings(true);
    try {
      const res = await fetch(`${API_BASE}/api/lms/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          temperature_segment: tempSegment,
          temperature_webpage: tempWebpage,
          temperature_search: tempSearch,
          max_tokens: maxTokens,
          prompt_etl: promptEtl,
          prompt_search: promptSearch,
          routing_etl_model: routingEtlModel,
          routing_search_model: routingSearchModel
        })
      });
      if (res.ok) {
        addToast("Settings Saved", "LM Studio configurations updated successfully.");
        // Close advanced settings panel and refresh status to confirm sync
        setShowAdvancedSettings(false);
        fetchLmsStatus();
      } else {
        const err = await res.json();
        addToast("Save Failed", err.detail || "Could not save settings.");
      }
    } catch (err) {
      addToast("Connection Error", "Failed to connect to the backend server.");
    } finally {
      setIsSavingSettings(false);
    }
  };

  // Refs
  const searchInputRef = useRef<HTMLInputElement>(null);

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
    fetchLmsStatus();
    fetchPipelineStatus();
    fetchBackups();
    const interval = setInterval(() => {
      fetchAtlas();
      fetchLmsStatus();
      fetchPipelineStatus();
      fetchBackups();
    }, 5000); // Poll health, gap maps, model status, and pipeline status every 5 seconds
    return () => clearInterval(interval);
  }, []);


  // Handle source click - fetches scraped markdown dynamically if webpage type
  const handleSelectSource = async (src: Source) => {
    setSelectedSource(src);
    setModalTab('chat');
    setViewingSubWebpage(null);
    setScrapedPageData(null);
    
    if (src.type === 'webpage' || (src.slug && !src.messages)) {
      setIsLoadingScrapedPage(true);
      try {
        const res = await fetch(`${API_BASE}/api/scraped/${encodeURIComponent(src.slug)}`);
        if (res.ok) {
          const data = await res.json();
          setScrapedPageData(data);
        } else {
          setScrapedPageData({
            slug: src.slug,
            title: src.title,
            url: src.url,
            markdown: `# ${src.title}\n\nFailed to fetch markdown file from API. Snippet:\n\n${src.summary}`,
            executive_summary: src.summary,
            tags: src.tags,
            categories: src.categories
          });
        }
      } catch (err) {
        setScrapedPageData({
          slug: src.slug,
          title: src.title,
          url: src.url,
          markdown: `# ${src.title}\n\nFailed to connect to API server. Snippet:\n\n${src.summary}`,
          executive_summary: src.summary,
          tags: src.tags,
          categories: src.categories
        });
      } finally {
        setIsLoadingScrapedPage(false);
      }
    }
  };

  // Handle loading scraped webpage dynamically inside a segment context
  const handleSelectSubWebpage = async (slug: string, url: string, title: string, summary: string) => {
    setIsLoadingScrapedPage(true);
    setViewingSubWebpage({ slug, url, title });
    setScrapedPageData(null);
    try {
      const res = await fetch(`${API_BASE}/api/scraped/${encodeURIComponent(slug)}`);
      if (res.ok) {
        const data = await res.json();
        setScrapedPageData(data);
      } else {
        setScrapedPageData({
          slug,
          title,
          url,
          markdown: `# ${title}\n\nFailed to fetch markdown file. Snippet:\n\n${summary}`,
          executive_summary: summary,
          tags: [],
          categories: []
        });
      }
    } catch (err) {
      setScrapedPageData({
        slug,
        title,
        url,
        markdown: `# ${title}\n\nFailed to connect to server. Snippet:\n\n${summary}`,
        executive_summary: summary,
        tags: [],
        categories: []
      });
    } finally {
      setIsLoadingScrapedPage(false);
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

    const newTask: IngestTask = {
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
                          const source = (searchResults?.sources || MOCK_SEARCH.sources).find((s: any) => s.segment_id === cid);
                          return (
                            <span key={index} className="citation" onClick={() => source && handleSelectSource(source)}>
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
                    onClick={() => handleSelectSource(src)}
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
                    <tr key={src.segment_id} onClick={() => handleSelectSource(src)}>
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
          
          {/* Modern Glassmorphic Sidebar Tabs Switcher */}
          <div className="sidebar-tabs">
            <button 
              type="button"
              className={`sidebar-tab-btn ${sidebarTab === 'overview' ? 'active' : ''}`}
              onClick={() => setSidebarTab('overview')}
            >
              <TrendingUp size={14} />
              <span>Overview</span>
            </button>
            <button 
              type="button"
              className={`sidebar-tab-btn ${sidebarTab === 'ingestion' ? 'active' : ''}`}
              onClick={() => setSidebarTab('ingestion')}
            >
              <Compass size={14} />
              <span>Ingestion</span>
              {/* Telemetry dot: glow green if pipeline is actively running */}
              {pipelineStatus?.running && (
                <span className="sidebar-tab-badge glow-green" />
              )}
            </button>
            <button 
              type="button"
              className={`sidebar-tab-btn ${sidebarTab === 'settings' ? 'active' : ''}`}
              onClick={() => setSidebarTab('settings')}
            >
              <Sliders size={14} />
              <span>Settings</span>
              {/* Telemetry dot: glow indigo if backend API is online */}
              {apiOnline && (
                <span className="sidebar-tab-badge glow-indigo" />
              )}
            </button>
          </div>

          {/* Tab Content Areas */}
          {sidebarTab === 'overview' && (
            <div className="sidebar-scroll-container">
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
              <KnowledgeGapMap 
                atlasData={atlasData}
                searchResults={searchResults}
                mockSearchSources={MOCK_SEARCH.sources}
                executeSearch={executeSearch}
                handleSelectSource={handleSelectSource}
                setIsGapOpen={setIsGapOpen}
                addToast={addToast}
              />

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
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ color: CATEGORY_COLORS[gap.tag.toLowerCase()] || '#6366f1', fontWeight: 'bold', fontSize: '0.82rem', textTransform: 'uppercase' }}>
                          #{gap.tag}
                        </span>
                        <ChevronRight size={14} style={{ color: 'var(--text-tertiary)' }} />
                      </div>
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: '1.3' }}>
                        {gap.suggestion}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {sidebarTab === 'ingestion' && (
            <div className="sidebar-scroll-container">
              {/* Ingestion Pipeline Manager Panel */}
              <div className="sidebar-block" style={{ border: '1px solid rgba(6, 182, 212, 0.15)', background: 'rgba(6, 182, 212, 0.02)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h4 className="sidebar-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Compass size={16} style={{ color: 'var(--accent-cyan)' }} />
                    Pipeline Manager
                  </h4>
                  <button 
                    onClick={fetchPipelineStatus} 
                    style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', display: 'flex', padding: '4px' }}
                    title="Refresh Progress"
                  >
                    <RefreshCw size={12} className={pipelineStatus?.running ? 'animate-spin' : ''} />
                  </button>
                </div>

                {pipelineStatus ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    
                    {/* Overall status and glow indicator */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', padding: '8px 10px', borderRadius: '8px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span 
                          style={{ 
                            width: '8px', 
                            height: '8px', 
                            borderRadius: '50%', 
                            backgroundColor: pipelineStatus.running ? '#10b981' : '#f59e0b',
                            boxShadow: pipelineStatus.running ? '0 0 8px #10b981' : 'none',
                            display: 'inline-block' 
                          }} 
                        />
                        Status: <strong style={{ textTransform: 'uppercase', fontSize: '0.72rem', color: pipelineStatus.running ? '#10b981' : 'var(--text-secondary)' }}>{pipelineStatus.status.replace('_', ' ')}</strong>
                      </span>
                      
                      {pipelineStatus.running && (
                        <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Loader2 size={10} className="animate-spin" /> Processing
                        </span>
                      )}
                    </div>

                    {/* Progress Checklist */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '4px 0' }}>
                      
                      {/* Step 1: Chat Log Parser */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>1. Chat Log Parser</span>
                        <span 
                          style={{ 
                            fontSize: '0.68rem', 
                            padding: '1px 6px', 
                            borderRadius: '4px', 
                            fontWeight: '600',
                            background: pipelineStatus.steps.parsing.status === 'done' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255,255,255,0.04)',
                            color: pipelineStatus.steps.parsing.status === 'done' ? '#10b981' : 'var(--text-tertiary)'
                          }}
                        >
                          {pipelineStatus.steps.parsing.status}
                        </span>
                      </div>

                      {/* Step 2: Turn Segmenter */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>2. Turn Segmenter</span>
                        <span 
                          style={{ 
                            fontSize: '0.68rem', 
                            padding: '1px 6px', 
                            borderRadius: '4px', 
                            fontWeight: '600',
                            background: pipelineStatus.steps.segmentation.status === 'done' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255,255,255,0.04)',
                            color: pipelineStatus.steps.segmentation.status === 'done' ? '#10b981' : 'var(--text-tertiary)'
                          }}
                        >
                          {pipelineStatus.steps.segmentation.status}
                        </span>
                      </div>

                      {/* Step 3: Link Scraper */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>3. Link Scraper</span>
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                            {pipelineStatus.meta.completed_urls} / {pipelineStatus.meta.total_urls} URLs
                          </span>
                        </div>
                        {/* Tiny Progress bar */}
                        {pipelineStatus.meta.total_urls > 0 && (
                          <div style={{ width: '100%', height: '3px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                            <div 
                              style={{ 
                                width: `${(pipelineStatus.meta.completed_urls / pipelineStatus.meta.total_urls) * 100}%`, 
                                height: '100%', 
                                background: 'var(--accent-cyan)', 
                                transition: 'width 0.4s ease' 
                              }} 
                            />
                          </div>
                        )}
                      </div>

                      {/* Step 4: LLM Indexer */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>4. LLM Indexer</span>
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                            {pipelineStatus.meta.completed_segments} / {pipelineStatus.meta.total_segments} turns
                          </span>
                        </div>
                        {/* Tiny Progress bar */}
                        {pipelineStatus.meta.total_segments > 0 && (
                          <div style={{ width: '100%', height: '3px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                            <div 
                              style={{ 
                                width: `${(pipelineStatus.meta.completed_segments / pipelineStatus.meta.total_segments) * 100}%`, 
                                height: '100%', 
                                background: 'var(--accent-cyan)', 
                                transition: 'width 0.4s ease' 
                              }} 
                            />
                          </div>
                        )}
                      </div>

                    </div>

                    {/* Resume trigger button */}
                    {!pipelineStatus.running && (pipelineStatus.status !== 'completed') && (
                      <button
                        onClick={handleResumePipeline}
                        disabled={isResuming}
                        className="ghost-btn"
                        style={{ 
                          marginTop: '4px',
                          padding: '8px', 
                          fontSize: '0.8rem', 
                          borderColor: 'var(--accent-cyan)', 
                          color: 'var(--accent-cyan)', 
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center', 
                          gap: '6px',
                          width: '100%',
                          background: 'rgba(6, 182, 212, 0.05)'
                        }}
                      >
                        <Play size={12} fill="currentColor" />
                        {isResuming ? 'Resuming...' : 'Resume Ingestion'}
                      </button>
                    )}

                  </div>
                ) : (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>Loading pipeline status...</span>
                )}
              </div>

              {/* Quick Ingest Panel */}
              <div className="sidebar-block" style={{ border: '1px solid rgba(6, 182, 212, 0.15)', background: 'rgba(6, 182, 212, 0.02)' }}>
                <h4 className="sidebar-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                  <Plus size={16} style={{ color: 'var(--accent-cyan)' }} />
                  Quick Ingestion
                </h4>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  
                  {/* Message / Link input */}
                  <form onSubmit={handleIngestMessage} style={{ display: 'flex', gap: '6px' }}>
                    <input 
                      type="text" 
                      placeholder="Enter message or URL..." 
                      value={singleIngestText}
                      onChange={(e) => setSingleIngestText(e.target.value)}
                      style={{ 
                        flex: 1, 
                        padding: '6px 10px', 
                        fontSize: '0.8rem', 
                        borderRadius: '6px', 
                        border: '1px solid rgba(255,255,255,0.08)', 
                        background: 'rgba(0,0,0,0.2)', 
                        color: 'var(--text-primary)',
                        outline: 'none'
                      }}
                      disabled={isIngestingMessage || isUploadingFile}
                    />
                    <button 
                      type="submit" 
                      disabled={isIngestingMessage || isUploadingFile || !singleIngestText.trim()}
                      className="ghost-btn"
                      style={{ 
                        padding: '6px 10px', 
                        fontSize: '0.8rem', 
                        borderColor: 'var(--accent-cyan)', 
                        color: 'var(--accent-cyan)',
                        background: 'rgba(6, 182, 212, 0.05)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      {isIngestingMessage ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Send size={12} />
                      )}
                      Send
                    </button>
                  </form>

                  {/* Supplementary text file upload */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label 
                      style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center', 
                        gap: '8px', 
                        padding: '8px 12px', 
                        borderRadius: '6px', 
                        border: '1px dashed rgba(255,255,255,0.15)', 
                        background: 'rgba(0,0,0,0.15)', 
                        color: 'var(--text-secondary)', 
                        fontSize: '0.78rem',
                        cursor: isUploadingFile || isIngestingMessage ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s ease',
                        textAlign: 'center'
                      }}
                      className="file-upload-label"
                    >
                      {isUploadingFile ? (
                        <>
                          <Loader2 size={14} className="animate-spin" style={{ color: 'var(--accent-cyan)' }} />
                          <span>Merging & Processing...</span>
                        </>
                      ) : (
                        <>
                          <Upload size={14} style={{ color: 'var(--accent-cyan)' }} />
                          <span>Merge Supplementary .txt File</span>
                        </>
                      )}
                      <input 
                        type="file" 
                        accept=".txt"
                        onChange={handleIngestFile}
                        style={{ display: 'none' }}
                        disabled={isUploadingFile || isIngestingMessage}
                      />
                    </label>
                  </div>

                </div>
              </div>
            </div>
          )}

          {sidebarTab === 'settings' && (
            <div className="sidebar-scroll-container">
              {/* LM Studio Model Manager Panel */}
              <div className="sidebar-block" style={{ border: '1px solid rgba(99, 102, 241, 0.15)', background: 'rgba(99, 102, 241, 0.02)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h4 className="sidebar-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Cpu size={16} style={{ color: 'var(--accent-indigo)' }} />
                    LM Studio Manager
                  </h4>
                  <button 
                    onClick={fetchLmsStatus} 
                    style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', display: 'flex', padding: '4px' }}
                    title="Refresh Status"
                  >
                    <RefreshCw size={12} className={actioningModel ? 'animate-spin' : ''} />
                  </button>
                </div>

                {lmsStatus?.sdk_enabled ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {/* Active Model Status Badge */}
                    <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', padding: '10px', borderRadius: '8px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Loaded Model</span>
                      {lmsStatus.loaded.length > 0 ? (
                        lmsStatus.loaded.map((m: any) => (
                          <div key={m.identifier} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', maxWidth: '70%' }}>
                              <span style={{ fontSize: '0.9rem', fontWeight: '500', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {m.identifier.split('/').pop()}
                              </span>
                              <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={m.identifier}>
                                {m.identifier}
                              </span>
                            </div>
                            <button
                              onClick={() => handleUnloadModel(m.identifier)}
                              disabled={actioningModel !== null}
                              className="ghost-btn"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', borderColor: '#ef4444', color: '#ef4444', background: 'rgba(239, 68, 68, 0.05)', whiteSpace: 'nowrap' }}
                            >
                              {actioningModel === m.identifier ? '...' : 'Unload'}
                            </button>
                          </div>
                        ))
                      ) : (
                        <div style={{ marginTop: '6px', color: 'var(--text-secondary)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <AlertTriangle size={14} style={{ color: '#f59e0b' }} />
                          No model loaded (SDK Fallback Active)
                        </div>
                      )}
                    </div>

                    {/* Downloaded Models List */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Available Downloaded Models</span>
                      {lmsStatus.downloaded.filter((d: any) => d.type === 'llm').length > 0 ? (
                        lmsStatus.downloaded.filter((d: any) => d.type === 'llm').map((d: any) => {
                          const isLoaded = lmsStatus.loaded.some((m: any) => m.identifier === d.model_key);
                          return (
                            <div 
                              key={d.model_key} 
                              style={{ 
                                display: 'flex', 
                                justifyContent: 'space-between', 
                                alignItems: 'center', 
                                padding: '8px 10px', 
                                borderRadius: '8px', 
                                background: isLoaded ? 'rgba(99, 102, 241, 0.05)' : 'rgba(255,255,255,0.01)',
                                border: isLoaded ? '1px solid rgba(99, 102, 241, 0.1)' : '1px solid rgba(255,255,255,0.03)' 
                              }}
                            >
                              <div style={{ display: 'flex', flexDirection: 'column', maxWidth: '70%' }}>
                                <span style={{ fontSize: '0.82rem', fontWeight: '500', color: isLoaded ? 'var(--accent-indigo)' : 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {d.display_name}
                                </span>
                                <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={d.model_key}>
                                  {d.model_key}
                                </span>
                              </div>
                              {!isLoaded ? (
                                <button
                                  onClick={() => handleLoadModel(d.model_key)}
                                  disabled={actioningModel !== null}
                                  className="ghost-btn"
                                  style={{ padding: '4px 8px', fontSize: '0.75rem', borderColor: 'var(--accent-indigo)', color: 'var(--accent-indigo)', whiteSpace: 'nowrap' }}
                                >
                                  {actioningModel === d.model_key ? '...' : 'Load'}
                                </button>
                              ) : (
                                <span style={{ fontSize: '0.7rem', color: '#10b981', fontWeight: 'bold', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '3px', whiteSpace: 'nowrap' }}>
                                  <CheckCircle size={10} /> Active
                                </span>
                              )}
                            </div>
                          );
                        })
                      ) : (
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>No downloaded LLM models found.</span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', padding: '10px', borderRadius: '8px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    {lmsStatus?.status === 'disabled' ? (
                      <div>
                        <span style={{ fontWeight: '500', color: 'var(--text-primary)' }}>Standard Remote OpenAI/Ollama Mode</span>
                        <p style={{ margin: '4px 0 0 0', fontSize: '0.75rem', color: 'var(--text-tertiary)', lineHeight: '1.4' }}>
                          Programmatic model loading is inactive because endpoint is remote or SDK features are turned off.
                        </p>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f59e0b' }}>
                        <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                        <div>
                          <strong style={{ display: 'block', fontSize: '0.8rem' }}>LM Studio Offline</strong>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>Make sure the local server is running on port 1234.</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}


                {/* Advanced Settings section inside LM Studio Manager */}
                <div style={{ marginTop: '14px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '12px' }}>
                  <button 
                    onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                    style={{ 
                      width: '100%', 
                      background: 'none', 
                      border: 'none', 
                      color: 'var(--text-secondary)', 
                      cursor: 'pointer', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'space-between',
                      padding: '4px 0',
                      fontSize: '0.8rem',
                      fontWeight: '500'
                    }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Sliders size={14} style={{ color: 'var(--accent-indigo)' }} />
                      Advanced Settings
                    </span>
                    {showAdvancedSettings ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {showAdvancedSettings && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px', background: 'rgba(0,0,0,0.1)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.03)' }}>
                      
                      {/* Model Routing - ONLY show if SDK is enabled */}
                      {lmsStatus?.sdk_enabled && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Model Routing</span>
                          
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>ETL / Parser Model</label>
                            <select 
                              value={routingEtlModel}
                              onChange={(e) => setRoutingEtlModel(e.target.value)}
                              style={{ background: '#111', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', borderRadius: '4px', padding: '5px', fontSize: '0.78rem' }}
                            >
                              <option value="">Select model...</option>
                              {lmsStatus.downloaded.filter((d: any) => d.type === 'llm').map((d: any) => (
                                <option key={d.model_key} value={d.model_key}>{d.display_name}</option>
                              ))}
                            </select>
                          </div>

                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Search / RAG Model</label>
                            <select 
                              value={routingSearchModel}
                              onChange={(e) => setRoutingSearchModel(e.target.value)}
                              style={{ background: '#111', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', borderRadius: '4px', padding: '5px', fontSize: '0.78rem' }}
                            >
                              <option value="">Select model...</option>
                              {lmsStatus.downloaded.filter((d: any) => d.type === 'llm').map((d: any) => (
                                <option key={d.model_key} value={d.model_key}>{d.display_name}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                      )}

                      {/* Temperatures */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Temperatures</span>
                        
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem' }}>
                            <label style={{ color: 'var(--text-secondary)' }}>ETL Segment</label>
                            <span style={{ color: 'var(--accent-indigo)', fontWeight: 'bold' }}>{tempSegment.toFixed(2)}</span>
                          </div>
                          <input 
                            type="range" min="0.0" max="1.0" step="0.05"
                            value={tempSegment}
                            onChange={(e) => setTempSegment(parseFloat(e.target.value))}
                            style={{ width: '100%', accentColor: 'var(--accent-indigo)' }}
                          />
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem' }}>
                            <label style={{ color: 'var(--text-secondary)' }}>ETL Webpage</label>
                            <span style={{ color: 'var(--accent-indigo)', fontWeight: 'bold' }}>{tempWebpage.toFixed(2)}</span>
                          </div>
                          <input 
                            type="range" min="0.0" max="1.0" step="0.05"
                            value={tempWebpage}
                            onChange={(e) => setTempWebpage(parseFloat(e.target.value))}
                            style={{ width: '100%', accentColor: 'var(--accent-indigo)' }}
                          />
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem' }}>
                            <label style={{ color: 'var(--text-secondary)' }}>Search / RAG Answer</label>
                            <span style={{ color: 'var(--accent-indigo)', fontWeight: 'bold' }}>{tempSearch.toFixed(2)}</span>
                          </div>
                          <input 
                            type="range" min="0.0" max="1.0" step="0.05"
                            value={tempSearch}
                            onChange={(e) => setTempSearch(parseFloat(e.target.value))}
                            style={{ width: '100%', accentColor: 'var(--accent-indigo)' }}
                          />
                        </div>
                      </div>

                      {/* Max Tokens */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Max Output Tokens</label>
                        <input 
                          type="number" 
                          value={maxTokens}
                          onChange={(e) => setMaxTokens(parseInt(e.target.value) || 0)}
                          style={{ background: '#111', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', borderRadius: '4px', padding: '5px', fontSize: '0.78rem' }}
                        />
                      </div>

                      {/* System Prompts */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Personas & Custom Prompts</span>
                        
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>ETL Extraction System Prompt</label>
                          <textarea 
                            rows={3}
                            value={promptEtl}
                            onChange={(e) => setPromptEtl(e.target.value)}
                            style={{ background: '#111', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', borderRadius: '4px', padding: '6px', fontSize: '0.75rem', fontFamily: 'monospace', resize: 'vertical' }}
                          />
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>RAG Search Persona Prompt</label>
                          <textarea 
                            rows={3}
                            value={promptSearch}
                            onChange={(e) => setPromptSearch(e.target.value)}
                            style={{ background: '#111', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', borderRadius: '4px', padding: '6px', fontSize: '0.75rem', fontFamily: 'monospace', resize: 'vertical' }}
                          />
                        </div>
                      </div>

                      {/* Save Button */}
                      <button
                        onClick={handleSaveSettings}
                        disabled={isSavingSettings}
                        className="ghost-btn"
                        style={{ 
                          marginTop: '4px',
                          padding: '8px', 
                          fontSize: '0.8rem', 
                          borderColor: 'var(--accent-indigo)', 
                          color: 'var(--accent-indigo)', 
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center', 
                          gap: '6px',
                          width: '100%',
                          background: 'rgba(99,102,241,0.05)'
                        }}
                      >
                        <Save size={12} />
                        {isSavingSettings ? 'Saving...' : 'Save Configurations'}
                      </button>

                    </div>
                  )}
                </div>
              </div>

              {/* Database Snapshot Manager Panel */}
              <div className="sidebar-block" style={{ border: '1px solid rgba(99, 102, 241, 0.15)', background: 'rgba(99, 102, 241, 0.02)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h4 className="sidebar-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Database size={16} style={{ color: 'var(--accent-indigo)' }} />
                    Snapshot Manager
                  </h4>
                  <button 
                    onClick={fetchBackups} 
                    style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', display: 'flex', padding: '4px' }}
                    title="Refresh Snapshots"
                  >
                    <RefreshCw size={12} className={isCreatingBackup || isRestoringBackup ? 'animate-spin' : ''} />
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  
                  {/* Snapshot Creation Form */}
                  <form onSubmit={handleCreateBackup} style={{ display: 'flex', gap: '6px' }}>
                    <input 
                      type="text" 
                      placeholder="Snapshot label (e.g. backup)" 
                      value={backupLabel}
                      onChange={(e) => setBackupLabel(e.target.value)}
                      style={{ 
                        flex: 1, 
                        padding: '6px 10px', 
                        fontSize: '0.8rem', 
                        borderRadius: '6px', 
                        border: '1px solid rgba(255,255,255,0.08)', 
                        background: 'rgba(0,0,0,0.2)', 
                        color: 'var(--text-primary)',
                        outline: 'none'
                      }}
                      disabled={isCreatingBackup}
                    />
                    <button 
                      type="submit" 
                      disabled={isCreatingBackup || isRestoringBackup}
                      className="ghost-btn"
                      style={{ 
                        padding: '6px 10px', 
                        fontSize: '0.8rem', 
                        borderColor: 'var(--accent-indigo)', 
                        color: 'var(--accent-indigo)',
                        background: 'rgba(99, 102, 241, 0.05)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      {isCreatingBackup ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Plus size={12} />
                      )}
                      Snapshot
                    </button>
                  </form>

                  {/* Backups List */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto', paddingRight: '2px' }} className="custom-scrollbar">
                    {backups.length === 0 ? (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', fontStyle: 'italic', textAlign: 'center', padding: '12px 0' }}>
                        No database snapshots found.
                      </span>
                    ) : (
                      backups.map((backup) => (
                        <div 
                          key={backup.name}
                          style={{ 
                            display: 'flex', 
                            flexDirection: 'column', 
                            gap: '4px', 
                            padding: '8px 10px', 
                            borderRadius: '6px', 
                            background: 'rgba(255,255,255,0.02)', 
                            border: '1px solid rgba(255,255,255,0.04)',
                            position: 'relative'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', wordBreak: 'break-all', paddingRight: '48px' }}>
                              {backup.label}
                            </span>
                            
                            <div style={{ display: 'flex', gap: '6px', position: 'absolute', right: '10px', top: '8px' }}>
                              <button
                                onClick={() => handleRestoreBackup(backup.name)}
                                disabled={isRestoringBackup || isCreatingBackup}
                                style={{ 
                                  background: 'none', 
                                  border: 'none', 
                                  color: 'rgba(16, 185, 129, 0.8)', 
                                  cursor: 'pointer', 
                                  padding: '2px', 
                                  display: 'flex',
                                  alignItems: 'center'
                                }}
                                title="Restore snapshot"
                              >
                                <Play size={12} fill="rgba(16, 185, 129, 0.4)" />
                              </button>
                              <button
                                onClick={() => handleDeleteBackup(backup.name)}
                                disabled={isRestoringBackup || isCreatingBackup}
                                style={{ 
                                  background: 'none', 
                                  border: 'none', 
                                  color: 'rgba(239, 68, 68, 0.8)', 
                                  cursor: 'pointer', 
                                  padding: '2px', 
                                  display: 'flex',
                                  alignItems: 'center'
                                }}
                                title="Delete snapshot"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>
                            <span>{backup.created_at}</span>
                            <span>{backup.size_str}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Zipped Archive Backup/Restore Actions */}
                  <div style={{ display: 'flex', gap: '6px', marginTop: '6px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '10px' }}>
                    <button
                      onClick={handleExportArchive}
                      disabled={isExportingArchive || isImportingArchive || isCreatingBackup || isRestoringBackup}
                      className="ghost-btn"
                      style={{ 
                        flex: 1,
                        padding: '6px 8px', 
                        fontSize: '0.72rem', 
                        borderColor: 'var(--accent-indigo)', 
                        color: 'var(--accent-indigo)',
                        background: 'rgba(99, 102, 241, 0.03)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '4px',
                        cursor: 'pointer'
                      }}
                      title="Download unified zip backup archive"
                    >
                      {isExportingArchive ? <Loader2 size={10} className="animate-spin" /> : <Download size={10} />}
                      Backup Zip
                    </button>

                    <label 
                      style={{ 
                        flex: 1,
                        padding: '6px 8px', 
                        fontSize: '0.72rem', 
                        borderColor: 'var(--accent-indigo)', 
                        color: 'var(--accent-indigo)',
                        border: '1px solid var(--accent-indigo)',
                        borderRadius: '6px',
                        background: 'rgba(99, 102, 241, 0.03)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '4px',
                        cursor: isImportingArchive || isExportingArchive || isCreatingBackup || isRestoringBackup ? 'not-allowed' : 'pointer',
                        opacity: isImportingArchive || isExportingArchive || isCreatingBackup || isRestoringBackup ? 0.5 : 1
                      }}
                      title="Restore from a unified zip backup archive"
                    >
                      {isImportingArchive ? <Loader2 size={10} className="animate-spin" /> : <Upload size={10} />}
                      Restore Zip
                      <input 
                        type="file" 
                        accept=".zip"
                        onChange={handleImportArchive}
                        style={{ display: 'none' }}
                        disabled={isImportingArchive || isExportingArchive || isCreatingBackup || isRestoringBackup}
                      />
                    </label>
                  </div>

                </div>
              </div>
            </div>
          )}

        </aside>
      </main>

      {/* Ingestion & Recovery Queue Sideover Drawer */}
      <BridgeGapDrawer 
        isGapOpen={isGapOpen}
        setIsGapOpen={setIsGapOpen}
        ingestUrl={ingestUrl}
        setIngestUrl={setIngestUrl}
        ingestCategory={ingestCategory}
        setIngestCategory={setIngestCategory}
        activeTasks={activeTasks}
        atlasData={atlasData}
        handleIngestSubmit={handleIngestSubmit}
        addToast={addToast}
      />

      {/* Full Premium Insights & Markdown Reader Modal Popup */}
      <InsightsConsoleModal 
        selectedSource={selectedSource}
        onClose={() => { setSelectedSource(null); setViewingSubWebpage(null); setScrapedPageData(null); }}
        modalTab={modalTab}
        setModalTab={setModalTab}
        viewingSubWebpage={viewingSubWebpage}
        onBackToSegment={() => { setViewingSubWebpage(null); setScrapedPageData(null); }}
        scrapedPageData={scrapedPageData}
        isLoadingScrapedPage={isLoadingScrapedPage}
        handleSelectSubWebpage={handleSelectSubWebpage}
      />

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
