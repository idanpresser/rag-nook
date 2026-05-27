import React, { useState, useEffect, useRef } from 'react';
import { Compass } from 'lucide-react';
import type { AtlasData, Source } from '../types';
import { CATEGORY_COLORS } from '../constants/colors';

interface KnowledgeGapMapProps {
  atlasData: AtlasData | null;
  searchResults: any;
  mockSearchSources: Source[];
  executeSearch: (searchVal: string) => void;
  handleSelectSource: (source: Source) => void;
  setIsGapOpen: (open: boolean) => void;
  addToast: (title: string, message: string) => void;
}

export const KnowledgeGapMap: React.FC<KnowledgeGapMapProps> = ({
  atlasData,
  searchResults,
  mockSearchSources,
  executeSearch,
  handleSelectSource,
  setIsGapOpen,
  addToast
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredPoint, setHoveredPoint] = useState<any>(null);

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
      ctx.beginPath();
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
                      mockSearchSources.find((s: any) => s.segment_id === hoveredPoint.id);
      if (segment) {
        handleSelectSource(segment);
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

  return (
    <div className="sidebar-block">
      <h4 className="sidebar-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Compass size={16} style={{ color: 'var(--accent-indigo)' }} />
          Knowledge Gap Map
        </span>
        <button 
          onClick={() => setIsGapOpen(true)} 
          style={{ 
            background: 'rgba(255,255,255,0.05)', 
            border: 'none', 
            color: 'var(--accent-cyan)', 
            fontSize: '0.75rem', 
            padding: '2px 8px', 
            borderRadius: '4px', 
            cursor: 'pointer' 
          }}
        >
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
            <span style={{ fontWeight: 'bold', textTransform: 'uppercase', color: CATEGORY_COLORS[hoveredPoint.category.toLowerCase()] || 'var(--accent-indigo)' }}>
              {hoveredPoint.category}
            </span>
            <span style={{ display: 'block', fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Segment ID: {hoveredPoint.id}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
