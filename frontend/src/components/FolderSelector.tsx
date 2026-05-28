import React, { useState } from 'react';
import { FolderOpen, Loader2, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';

interface FolderSelectorProps {
  onIngestionSuccess: () => void;
  addToast: (title: string, message: string, type?: 'success' | 'info' | 'error') => void;
}

export const FolderSelector: React.FC<FolderSelectorProps> = ({ onIngestionSuccess, addToast }) => {
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [filesCount, setFilesCount] = useState<{ txt: number; media: number; vcf: number; total: number }>({ txt: 0, media: 0, vcf: 0, total: 0 });
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  const handleSelectFolder = async () => {
    try {
      // Check browser support for directory picker
      if (!('showDirectoryPicker' in window)) {
        addToast(
          "Unsupported Browser", 
          "Your browser doesn't support directory selection. Please use a modern desktop browser (Chrome, Edge, Opera).", 
          "error"
        );
        return;
      }

      // 1. Prompt directory picker
      const dirHandle = await (window as any).showDirectoryPicker();
      setSelectedFolder(dirHandle.name);
      
      // 2. Pass 1: Locate the primary chat log (.txt)
      let chatLogFile: File | null = null;
      for await (const entry of dirHandle.values()) {
        if (entry.kind === 'file' && entry.name.toLowerCase().endsWith('.txt')) {
          chatLogFile = await entry.getFile();
          break;
        }
      }

      if (!chatLogFile) {
        addToast(
          "No Chat Log Found", 
          "The folder must contain at least one plain WhatsApp export text file (.txt).", 
          "error"
        );
        setSelectedFolder(null);
        return;
      }

      // Read chat log text locally and extract referenced images
      const chatText = await chatLogFile.text();
      const referencedImages = new Set<string>();
      
      // Matches standard and Hebrew/special character filenames with extensions inside (file attached)
      const attachmentRegex = /([^\(\:\n\r]+\.(?:jpg|jpeg|png|webp|heic))\s*\(file attached\)/gi;
      let match;
      while ((match = attachmentRegex.exec(chatText)) !== null) {
        referencedImages.add(match[1].trim().toLowerCase());
      }

      const fileList: File[] = [];
      let txtCount = 0;
      let mediaCount = 0;
      let vcfCount = 0;

      // 3. Pass 2: Filter and collect only the relevant files
      for await (const entry of dirHandle.values()) {
        if (entry.kind === 'file') {
          const file = await entry.getFile();
          const name = file.name.toLowerCase();

          if (name.endsWith('.txt')) {
            txtCount++;
            fileList.push(file);
          } else if (name.endsWith('.vcf')) {
            vcfCount++;
            fileList.push(file);
          } else if (/\.(jpg|jpeg|png|webp|heic)$/.test(name)) {
            // Upload only if the image is actually attached/referenced in the chat log!
            if (referencedImages.has(file.name.toLowerCase())) {
              mediaCount++;
              fileList.push(file);
            }
          }
        }
      }

      // 3. Update preview state
      setSelectedFiles(fileList);
      setFilesCount({
        txt: txtCount,
        media: mediaCount,
        vcf: vcfCount,
        total: fileList.length
      });

      if (txtCount === 0) {
        addToast(
          "No Chat Log Found", 
          "The folder must contain at least one plain WhatsApp export text file (.txt).", 
          "error"
        );
      } else {
        addToast(
          "Folder Pre-validated", 
          `Found chat log and ${mediaCount} attachments + ${vcfCount} contact cards.`, 
          "success"
        );
      }

    } catch (err: any) {
      if (err.name !== 'AbortError') {
        addToast("Selection Failed", err.message || "Failed to select directory.", "error");
      }
    }
  };

  const handleUploadFolder = async () => {
    if (selectedFiles.length === 0 || filesCount.txt === 0) {
      addToast("Upload Blocked", "Please select a valid folder containing a WhatsApp chat log (.txt).", "error");
      return;
    }

    setIsUploading(true);
    setUploadProgress(10);

    try {
      const formData = new FormData();
      
      // Append all selected files
      selectedFiles.forEach((file) => {
        formData.append("files", file, file.name);
      });

      setUploadProgress(40);

      // Perform multipart post request
      const response = await fetch("http://localhost:8000/api/ingest/folder", {
        method: "POST",
        body: formData
      });

      setUploadProgress(80);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      const result = await response.json();
      setUploadProgress(100);
      
      addToast(
        "Ingestion Successful", 
        `Successfully ingested ${filesCount.total} files. Indexed turns into ChromaDB!`, 
        "success"
      );

      // Reset states
      setSelectedFolder(null);
      setSelectedFiles([]);
      setFilesCount({ txt: 0, media: 0, vcf: 0, total: 0 });
      
      // Refresh parent dashboard
      onIngestionSuccess();

    } catch (err: any) {
      addToast("Ingestion Failed", err.message || "Could not ingest folder contents.", "error");
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <div 
      className="sidebar-block" 
      style={{ 
        border: '1px solid rgba(6, 182, 212, 0.15)', 
        background: 'rgba(6, 182, 212, 0.01)',
        padding: '12px',
        borderRadius: '8px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h5 style={{ margin: 0, fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FolderOpen size={14} style={{ color: 'var(--accent-cyan)' }} />
          Local Folder Ingest
        </h5>
        {selectedFolder && (
          <button 
            onClick={() => {
              setSelectedFolder(null);
              setSelectedFiles([]);
              setFilesCount({ txt: 0, media: 0, vcf: 0, total: 0 });
            }}
            disabled={isUploading}
            style={{ 
              background: 'none', 
              border: 'none', 
              color: 'var(--text-tertiary)', 
              fontSize: '0.7rem', 
              cursor: 'pointer',
              textDecoration: 'underline'
            }}
          >
            Clear
          </button>
        )}
      </div>

      {!selectedFolder ? (
        <button
          onClick={handleSelectFolder}
          className="ghost-btn"
          style={{
            padding: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            fontSize: '0.78rem',
            border: '1px dashed rgba(6, 182, 212, 0.3)',
            background: 'rgba(6, 182, 212, 0.04)',
            color: 'var(--accent-cyan)',
            width: '100%',
            cursor: 'pointer',
            borderRadius: '6px',
            transition: 'all 0.2s ease-in-out'
          }}
        >
          <FolderOpen size={16} />
          Select Whatsapp Export Folder
        </button>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div 
            style={{ 
              background: 'rgba(0,0,0,0.2)', 
              border: '1px solid rgba(255,255,255,0.06)', 
              borderRadius: '6px', 
              padding: '8px 10px',
              fontSize: '0.75rem',
              color: '#fff'
            }}
          >
            <div style={{ fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '4px', wordBreak: 'break-all' }}>
              📁 {selectedFolder}
            </div>
            <div style={{ color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span>📝 WhatsApp Log File: {filesCount.txt > 0 ? '✅ Found' : '❌ Missing'}</span>
              <span>🖼️ Optimized Media Files: {filesCount.media} found</span>
              <span>📇 Contact Cards (.vcf): {filesCount.vcf} found</span>
            </div>
          </div>

          {isUploading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Loader2 size={12} className="animate-spin" /> Ingesting multi-modal assets...
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '20px', overflow: 'hidden' }}>
                <div style={{ width: `${uploadProgress}%`, height: '100%', background: 'var(--accent-cyan)', transition: 'width 0.3s ease' }} />
              </div>
            </div>
          ) : (
            <button
              onClick={handleUploadFolder}
              disabled={filesCount.txt === 0}
              style={{
                width: '100%',
                padding: '8px',
                fontSize: '0.78rem',
                fontWeight: 600,
                background: filesCount.txt > 0 ? 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)' : 'rgba(255,255,255,0.05)',
                color: filesCount.txt > 0 ? '#fff' : 'var(--text-tertiary)',
                border: 'none',
                borderRadius: '6px',
                cursor: filesCount.txt > 0 ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                boxShadow: filesCount.txt > 0 ? '0 2px 8px rgba(6, 182, 212, 0.3)' : 'none'
              }}
            >
              <CheckCircle size={14} />
              Trigger Pipeline Upload
            </button>
          )}
        </div>
      )}
    </div>
  );
};
