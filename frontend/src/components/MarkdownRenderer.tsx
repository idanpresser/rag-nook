import React from 'react';

interface MarkdownRendererProps {
  text: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ text }) => {
  if (!text) return null;
  
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockContent: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    
    if (trimmed.startsWith('```')) {
      if (inCodeBlock) {
        // End of code block
        elements.push(
          <pre key={`code-${i}`} style={{ background: '#09090d', border: '1px solid rgba(255,255,255,0.06)', padding: '14px', borderRadius: '8px', overflowX: 'auto', fontFamily: 'var(--mono)', fontSize: '0.85rem', color: '#e4e4e7', margin: '14px 0', boxShadow: 'inset 0 1px 4px rgba(0,0,0,0.4)' }}>
            <code style={{ color: '#818cf8', whiteSpace: 'pre-wrap' }}>{codeBlockContent.join('\n')}</code>
          </pre>
        );
        codeBlockContent = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }
    
    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }
    
    if (!trimmed) {
      elements.push(<div key={`space-${i}`} className="h-3" />);
      continue;
    }
    
    // Headers
    if (trimmed.startsWith('### ')) {
      elements.push(<h4 key={i} className="text-md font-semibold text-cyan-400 mt-5 mb-2" style={{ fontFamily: 'var(--heading)', letterSpacing: '-0.01em' }}>{trimmed.slice(4)}</h4>);
      continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(<h3 key={i} className="text-lg font-bold text-indigo-400 mt-6 mb-3" style={{ fontFamily: 'var(--heading)', letterSpacing: '-0.015em' }}>{trimmed.slice(3)}</h3>);
      continue;
    }
    if (trimmed.startsWith('# ')) {
      elements.push(<h2 key={i} className="text-xl font-extrabold text-white mt-7 mb-4" style={{ fontFamily: 'var(--heading)', letterSpacing: '-0.02em' }}>{trimmed.slice(2)}</h2>);
      continue;
    }
    
    // Blockquotes
    if (trimmed.startsWith('> ')) {
      elements.push(<blockquote key={i} className="pl-4 italic text-zinc-400 my-3" style={{ borderLeft: '4px solid var(--accent-indigo)', background: 'rgba(255,255,255,0.01)', padding: '8px 12px', borderRadius: '0 6px 6px 0' }}>{trimmed.slice(2)}</blockquote>);
      continue;
    }
    
    // Bullet lists
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(<li key={i} className="ml-5 list-disc text-zinc-300 my-1.5">{trimmed.slice(2)}</li>);
      continue;
    }
    
    // Inline styles (bold, links, code)
    let currentText = trimmed;
    const boldLinkRegex = /(\*\*.*?\*\*|\[.*?\]\(.*?\)|`.*?`)/g;
    const parts = currentText.split(boldLinkRegex);
    
    const parsedLine = parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={index} style={{ background: 'rgba(255,255,255,0.06)', padding: '2px 5px', borderRadius: '4px', fontFamily: 'var(--mono)', fontSize: '0.85rem', color: 'var(--accent-cyan)' }}>{part.slice(1, -1)}</code>;
      }
      if (part.startsWith('[') && part.includes('](')) {
        const linkMatch = part.match(/\[(.*?)\]\((.*?)\)/);
        if (linkMatch) {
          const linkText = linkMatch[1];
          const linkUrl = linkMatch[2];
          return (
            <a 
              key={index} 
              href={linkUrl} 
              target="_blank" 
              rel="noopener noreferrer" 
              style={{ color: 'var(--accent-cyan)', textDecoration: 'underline' }}
              onClick={(e) => e.stopPropagation()}
            >
              {linkText}
            </a>
          );
        }
      }
      return part;
    });
    
    elements.push(<p key={i} className="text-zinc-300 leading-relaxed mb-3.5" style={{ fontSize: '0.94rem' }}>{parsedLine}</p>);
  }
  
  return <>{elements}</>;
};
