import React, { useState } from 'react';
import { FolderOpen, Loader2, CheckCircle, AlertCircle, RefreshCw, Database, GitMerge, Trash2, ShieldAlert, X } from 'lucide-react';

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
  
  // Transition modes states
  const [showModal, setShowModal] = useState<boolean>(false);
  const [isChecking, setIsChecking] = useState<boolean>(false);

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

    setIsChecking(true);

    try {
      // Check if existing chat data is present in active workspace
      const checkResponse = await fetch("http://localhost:8000/api/ingest/check");
      if (checkResponse.ok) {
        const checkData = await checkResponse.json();
        if (checkData.has_existing_data) {
          // Open transition modal to let the user choose database mode
          setShowModal(true);
          setIsChecking(false);
          return;
        }
      }
    } catch (err) {
      console.warn("Could not check active database presence, proceeding with default discard mode:", err);
    }

    setIsChecking(false);
    // If no existing chat data, proceed to upload and index fresh (discard mode)
    await executeFolderIngest("discard");
  };

  const executeFolderIngest = async (mode: 'discard' | 'merge' | 'backup_discard') => {
    setIsUploading(true);
    setUploadProgress(10);
    setShowModal(false);

    try {
      const formData = new FormData();
      
      // Append all selected files
      selectedFiles.forEach((file) => {
        formData.append("files", file, file.name);
      });

      setUploadProgress(40);

      // Perform multipart post request passing the chosen transition mode query param
      const response = await fetch(`http://localhost:8000/api/ingest/folder?mode=${mode}`, {
        method: "POST",
        body: formData
      });

      setUploadProgress(80);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      await response.json();
      setUploadProgress(100);
      
      let successMsg = "";
      if (mode === "merge") {
        successMsg = `Chronologically merged chat turns and index updated!`;
      } else if (mode === "backup_discard") {
        successMsg = `Database backed up snapshot, active DB wiped and fresh ingestion completed!`;
      } else {
        successMsg = `Database wiped and fresh chat log ingested!`;
      }

      addToast(
        "Ingestion Successful", 
        `Successfully ingested ${filesCount.total} files. ${successMsg}`, 
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
    <>
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
              disabled={isUploading || isChecking}
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
            ) : isChecking ? (
              <button
                disabled
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  background: 'rgba(255,255,255,0.05)',
                  color: 'var(--text-secondary)',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <Loader2 size={14} className="animate-spin" />
                Scanning Database State...
              </button>
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

      {/* Glassmorphic Transition Selection Modal */}
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 99999,
          background: 'rgba(5, 5, 8, 0.75)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <style dangerouslySetInnerHTML={{__html: `
            @keyframes fadeInScale {
              from {
                opacity: 0;
                transform: scale(0.96);
              }
              to {
                opacity: 1;
                transform: scale(1);
              }
            }
          `}} />
          <div style={{
            background: 'linear-gradient(135deg, rgba(22, 22, 30, 0.95) 0%, rgba(12, 12, 18, 0.98) 100%)',
            border: '1px solid rgba(6, 182, 212, 0.25)',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 45px rgba(6, 182, 212, 0.08)',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '560px',
            padding: '24px',
            color: '#fff',
            fontFamily: "'Outfit', sans-serif",
            animation: 'fadeInScale 0.25s ease-out'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldAlert size={20} style={{ color: 'var(--accent-cyan)' }} />
                Existing Chat Database Detected
              </h3>
              <button 
                onClick={() => setShowModal(false)}
                style={{
                  background: 'rgba(255,255,255,0.06)',
                  border: 'none',
                  borderRadius: '50%',
                  width: '28px',
                  height: '28px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.12)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.06)'}
              >
                <X size={14} />
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.7)', lineHeight: '1.5', margin: '0 0 20px 0' }}>
              We found an active database on this system. How would you like to proceed with importing the new WhatsApp folder?
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
              {/* Option 1: Backup and Discard */}
              <button 
                onClick={() => executeFolderIngest("backup_discard")}
                style={{
                  textAlign: 'left',
                  background: 'rgba(6, 182, 212, 0.03)',
                  border: '1px solid rgba(6, 182, 212, 0.18)',
                  borderRadius: '10px',
                  padding: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  gap: '12px',
                  alignItems: 'flex-start',
                  transition: 'all 0.2s ease',
                  outline: 'none'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(6, 182, 212, 0.08)';
                  e.currentTarget.style.borderColor = 'rgba(6, 182, 212, 0.4)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(6, 182, 212, 0.03)';
                  e.currentTarget.style.borderColor = 'rgba(6, 182, 212, 0.18)';
                  e.currentTarget.style.transform = 'none';
                }}
              >
                <div style={{ 
                  background: 'rgba(6, 182, 212, 0.1)', 
                  borderRadius: '8px', 
                  padding: '8px',
                  color: 'var(--accent-cyan)',
                  marginTop: '2px'
                }}>
                  <Database size={16} />
                </div>
                <div>
                  <h4 style={{ margin: '0 0 3px 0', fontSize: '0.85rem', fontWeight: 600, color: '#fff' }}>
                    💾 Save Old & Start Fresh
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.45)', lineHeight: '1.4', display: 'block' }}>
                    Creates a snapshot backup of your current database, wipes the active workspace, and starts completely fresh with no old messages.
                  </span>
                </div>
              </button>

              {/* Option 2: Chronological Merge */}
              <button 
                onClick={() => executeFolderIngest("merge")}
                style={{
                  textAlign: 'left',
                  background: 'rgba(16, 185, 129, 0.03)',
                  border: '1px solid rgba(16, 185, 129, 0.18)',
                  borderRadius: '10px',
                  padding: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  gap: '12px',
                  alignItems: 'flex-start',
                  transition: 'all 0.2s ease',
                  outline: 'none'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(16, 185, 129, 0.08)';
                  e.currentTarget.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(16, 185, 129, 0.03)';
                  e.currentTarget.style.borderColor = 'rgba(16, 185, 129, 0.18)';
                  e.currentTarget.style.transform = 'none';
                }}
              >
                <div style={{ 
                  background: 'rgba(16, 185, 129, 0.1)', 
                  borderRadius: '8px', 
                  padding: '8px',
                  color: '#10b981',
                  marginTop: '2px'
                }}>
                  <GitMerge size={16} />
                </div>
                <div>
                  <h4 style={{ margin: '0 0 3px 0', fontSize: '0.85rem', fontWeight: 600, color: '#fff' }}>
                    🔄 Combine Chats (Merge)
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.45)', lineHeight: '1.4', display: 'block' }}>
                    Combines the old and new chat logs chronologically, merging contact databases and re-indexing the unified timeline perfectly.
                  </span>
                </div>
              </button>

              {/* Option 3: Wipe and Discard */}
              <button 
                onClick={() => executeFolderIngest("discard")}
                style={{
                  textAlign: 'left',
                  background: 'rgba(244, 63, 94, 0.03)',
                  border: '1px solid rgba(244, 63, 94, 0.18)',
                  borderRadius: '10px',
                  padding: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  gap: '12px',
                  alignItems: 'flex-start',
                  transition: 'all 0.2s ease',
                  outline: 'none'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(244, 63, 94, 0.08)';
                  e.currentTarget.style.borderColor = 'rgba(244, 63, 94, 0.4)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(244, 63, 94, 0.03)';
                  e.currentTarget.style.borderColor = 'rgba(244, 63, 94, 0.18)';
                  e.currentTarget.style.transform = 'none';
                }}
              >
                <div style={{ 
                  background: 'rgba(244, 63, 94, 0.1)', 
                  borderRadius: '8px', 
                  padding: '8px',
                  color: '#f43f5e',
                  marginTop: '2px'
                }}>
                  <Trash2 size={16} />
                </div>
                <div>
                  <h4 style={{ margin: '0 0 3px 0', fontSize: '0.85rem', fontWeight: 600, color: '#fff' }}>
                    🗑️ Discard Old Data & Start Fresh
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.45)', lineHeight: '1.4', display: 'block' }}>
                    Wipes the existing chat log, SQLite contacts, and ChromaDB vector database collections. No backups are created.
                  </span>
                </div>
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button 
                onClick={() => setShowModal(false)}
                style={{
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.12)',
                  color: 'rgba(255,255,255,0.6)',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontSize: '0.78rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                  e.currentTarget.style.color = '#fff';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = 'rgba(255,255,255,0.6)';
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

