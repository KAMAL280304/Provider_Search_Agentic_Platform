import React from 'react';
import { FaPaperclip, FaTimes, FaFileAlt } from 'react-icons/fa';

const STYLES = {
  bubble: (isUser) => ({ maxWidth: '70%', margin: '10px', padding: '16px 20px', borderRadius: '18px', wordWrap: 'break-word', alignSelf: isUser ? 'flex-end' : 'flex-start', backgroundColor: isUser ? '#2D308D' : '#f5f5f5', color: isUser ? 'white' : '#333', marginLeft: isUser ? 'auto' : '10px', marginRight: isUser ? '10px' : 'auto', fontSize: '15px', lineHeight: '1.3', fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif", cursor: 'pointer' }),
  timestamp: (isUser) => ({ fontSize: '11px', color: '#999', margin: '2px 10px 0 10px', alignSelf: isUser ? 'flex-end' : 'flex-start' }),
  textContent: { userSelect: 'text', cursor: 'text' }
};

const SUGGESTION_RE = /^(would you like to (book|see|schedule|compare|search|find|check|view)|shall i (book|search|find|show|check)|do you (want to book|prefer|need a)|would you prefer|would you rather|are you looking to|are you (looking|hoping|wanting|trying) to)/i;
const EXCLUDE_RE = /^(is there anything|can i (help|assist)|anything else|how (can|may) i|is there something)/i;

function extractSuggestions(text, context = '') {
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const results = [];

  // Extract last mentioned doctor from context for schedule chips
  const contextDrMatch = context.match(/(?:appointment with|with|book with)\s+(Dr\.?\s+[A-Z][A-Za-z\s,\.]+?)(?:\s+on|\s+at|\.|,|$)/i);
  const contextDoctor = contextDrMatch ? contextDrMatch[1].trim().replace(/[,.]$/, '') : null;

  for (const line of lines) {
    const parts = line.split(/(?<=[?])\s+/);
    for (const part of parts) {
      const s = part.trim();
      if (!s.endsWith('?') || !SUGGESTION_RE.test(s) || EXCLUDE_RE.test(s)) continue;
      parseQuestion(s, results, contextDoctor);
    }
    if (line.endsWith('?') && SUGGESTION_RE.test(line) && !EXCLUDE_RE.test(line)) {
      parseQuestion(line, results, contextDoctor);
    }
  }

  return results.filter((r, i, arr) => arr.findIndex(x => x.label === r.label) === i);
}

function parseQuestion(s, results, contextDoctor = null) {
  const bookMatch = s.match(/book(?:\s+(?:with|an appointment with))?\s+([^,?]+)/i);
  const seeOtherMatch = s.match(/see other (options|providers|results)/i);
  const scheduleMatch = s.match(/schedule another appointment/i);
  const followUpMatch = s.match(/follow(?:\s*|-)?up(?:\s+with\s+([^,?]+))?/i);
  const differentConcernMatch = s.match(/different health concern/i);

  if (bookMatch || seeOtherMatch) {
    if (bookMatch) {
      const name = bookMatch[1].trim().replace(/[,.]$/, '');
      results.push({ label: `Book with ${name}`, message: `Book appointment with ${name}` });
    }
    if (seeOtherMatch) {
      results.push({ label: 'See other options', message: 'Show me other provider options' });
    }
    return;
  }

  if (scheduleMatch || followUpMatch) {
    const drMatch = s.match(/(?:with\s+)(Dr\.?\s+[A-Z][A-Za-z\s,\.]+?)(?:\s*[,?]|$)/i);
    const doctor = (drMatch && drMatch[1].trim().replace(/[,.]$/, '')) || contextDoctor;
    if (doctor) {
      results.push({ label: `Schedule with ${doctor}`, message: `Schedule another appointment with ${doctor}` });
    } else {
      results.push({ label: 'Schedule another appointment', message: 'Schedule another appointment' });
    }
    if (differentConcernMatch) {
      results.push({ label: 'Different health concern', message: 'I have a different health concern' });
    }
    return;
  }

  if (differentConcernMatch) {
    results.push({ label: 'Different health concern', message: 'I have a different health concern' });
    // Also check for the other part of the or-split
    const orParts = s.split(/\s+or\s+/i).map(p => p.trim()).filter(Boolean);
    if (orParts.length >= 2) {
      for (const part of orParts) {
        const label = part.charAt(0).toUpperCase() + part.slice(1);
        if (!results.find(r => r.label === label)) results.push({ label, message: label });
      }
    }
    return;
  }

  const stripped = s.replace(SUGGESTION_RE, '').replace(/^[\s,to]*/i, '').replace(/\?$/, '').trim();
  const orParts = stripped.split(/\s+or\s+/i).map(p => p.trim()).filter(Boolean);

  if (orParts.length >= 2) {
    for (const part of orParts) {
      const label = part.charAt(0).toUpperCase() + part.slice(1);
      results.push({ label, message: label });
    }
  } else {
    results.push({ label: s, message: s });
  }
}

export { extractSuggestions };

const MessageBubble = ({ message, isUser, showRead, timestamp, citations = [], onSuggestion, hideSuggestions, context = '' }) => {
  const [showTimestamp, setShowTimestamp] = React.useState(false);
  const [showReadStatus, setShowReadStatus] = React.useState(false);
  const [hoveredCitation, setHoveredCitation] = React.useState(null);
  const [tooltipPosition, setTooltipPosition] = React.useState({ x: 0, y: 0 });
  const [showCitationModal, setShowCitationModal] = React.useState(false);
  const [selectedCitation, setSelectedCitation] = React.useState(null);
  const [usedSuggestion, setUsedSuggestion] = React.useState(null);

  const suggestions = !isUser ? extractSuggestions(message, context) : [];

  const formatMessage = (text) => {
    const lines = text.split('\n');
    let html = '';

    const applyInline = (str) => {
      let s = str.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      s = s.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
      // Auto-bold ALL-CAPS acronyms like RICE, FAST, CPR, ER
      s = s.replace(/\b([A-Z]{2,}(?:\.[A-Z])*\.?)\b/g, '<strong>$1</strong>');
      return s;
    };

    const isDisclaimer = (str) =>
      /^(\*?)(note|disclaimer|important|\*note|\*disclaimer)/i.test(str.trim());

    const isBullet = (str) =>
      /^[-•*]\s+/.test(str) || /^\d+[.)]\s+\S/.test(str);

    const getBulletContent = (str) =>
      str.replace(/^[-•*]\s+/, '').replace(/^\d+[.)]\s+/, '');

    for (const line of lines) {
      const trimmed = line.trim();

      if (!trimmed) {
        html += '<div style="height: 8px;"></div>';
        continue;
      }

      if (isDisclaimer(trimmed)) {
        html += `<div style="margin-top: 10px; font-size: 11px; color: #94a3b8; font-style: italic; line-height: 1.4;">${applyInline(trimmed)}</div>`;
      } else if (isBullet(trimmed)) {
        const content = applyInline(getBulletContent(trimmed));
        html += `<div style="margin-left: 16px; margin-bottom: 5px; display: flex; gap: 6px;"><span style="color: #2D308D; font-weight: 700; flex-shrink: 0;">•</span><span style="line-height: 1.55;">${content}</span></div>`;
      } else if (trimmed.endsWith(':') && trimmed.length < 120) {
        html += `<div style="font-weight: 700; margin-top: 10px; margin-bottom: 4px; color: #1e1e5c;">${applyInline(trimmed)}</div>`;
      } else {
        html += `<div style="margin-bottom: 6px; line-height: 1.55;">${applyInline(trimmed)}</div>`;
      }
    }

    return html;
  };

  const cleanIncompleteSentences = (text) => {
    if (!text) return '';
    const sentences = text.split(/(?<=[.!?])\s+/);
    let cleaned = [...sentences];
    if (cleaned.length > 0 && cleaned[0]) {
      const first = cleaned[0].trim();
      if (first && !first.match(/^[A-Z•\-*·]/) && first.length < 200) cleaned.shift();
    }
    if (cleaned.length > 0 && cleaned[cleaned.length - 1]) {
      const last = cleaned[cleaned.length - 1].trim();
      if (last && !last.match(/[.!?]$/) && last.length < 200) cleaned.pop();
    }
    return cleaned.join(' ');
  };

  const handleCitationHover = (e) => {
    const target = e.target;
    if (target.classList.contains('citation')) {
      const citationNum = parseInt(target.getAttribute('data-citation'));
      const citation = citations.find(c => c.index === citationNum);
      if (citation) { setHoveredCitation(citation); setTooltipPosition({ x: e.clientX, y: e.clientY }); }
    }
  };

  const handleCitationClick = (e) => {
    const target = e.target;
    if (target.classList.contains('citation')) {
      const citationNum = parseInt(target.getAttribute('data-citation'));
      const citation = citations.find(c => c.index === citationNum);
      if (citation) { setSelectedCitation(citation); setShowCitationModal(true); }
    }
  };

  const handleCitationLeave = (e) => {
    if (e.target.classList.contains('citation')) setHoveredCitation(null);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', alignItems: isUser ? 'flex-end' : 'flex-start' }}>
      <div
        style={STYLES.bubble(isUser)}
        onClick={(e) => { if (e.target === e.currentTarget) { setShowTimestamp(!showTimestamp); if (isUser && showRead) setShowReadStatus(!showReadStatus); } handleCitationClick(e); }}
        onMouseOver={handleCitationHover}
        onMouseOut={handleCitationLeave}
      >
        {isUser
          ? <div style={{ ...STYLES.textContent, whiteSpace: 'pre-wrap' }}>{message}</div>
          : <div style={STYLES.textContent} dangerouslySetInnerHTML={{ __html: formatMessage(message) }} />
        }
      </div>

      {!isUser && !hideSuggestions && suggestions.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginLeft: '10px', marginTop: '6px', maxWidth: '70%', justifyContent: 'flex-end', alignSelf: 'flex-end', marginRight: '10px' }}>
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => { if (onSuggestion && !usedSuggestion) { setUsedSuggestion(s.label); onSuggestion(s.message); } }}
              disabled={!!usedSuggestion}
              style={{
                padding: '7px 14px',
                background: usedSuggestion === s.label ? '#2D308D' : '#ffffff',
                border: '1.5px solid #2D308D',
                borderRadius: '20px',
                color: usedSuggestion === s.label ? '#ffffff' : '#2D308D',
                fontSize: '13px', fontWeight: 600,
                cursor: usedSuggestion ? 'default' : 'pointer',
                transition: 'all 0.2s',
                opacity: usedSuggestion && usedSuggestion !== s.label ? 0.4 : 1,
              }}
              onMouseEnter={e => { if (!usedSuggestion) e.currentTarget.style.background = '#eef2ff'; }}
              onMouseLeave={e => { if (!usedSuggestion) e.currentTarget.style.background = '#ffffff'; }}
            >
              {s.label}
            </button>
          ))}
        </div>
      )}

      {!isUser && citations && citations.length > 0 && (
        <div style={{ marginLeft: '10px', marginTop: '8px', fontSize: '12px', color: '#666', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontWeight: '600', display: 'flex', alignItems: 'center', gap: 5 }}>
            <FaPaperclip size={12} /> Sources ({citations.length}):
          </span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {citations.map((cit, idx) => (
              <button key={idx} onClick={(e) => { e.preventDefault(); setSelectedCitation(cit); setShowCitationModal(true); }}
                style={{ padding: '6px 12px', background: '#e0e7ff', border: '1px solid #c7d2fe', borderRadius: '6px', color: '#1e40af', cursor: 'pointer', fontSize: '12px', fontWeight: '500', transition: 'all 0.2s' }}
                onMouseEnter={e => { e.target.style.background = '#c7d2fe'; }}
                onMouseLeave={e => { e.target.style.background = '#e0e7ff'; }}
              >
                {cit.file_name || 'Document'}
              </button>
            ))}
          </div>
        </div>
      )}

      {hoveredCitation && (
        <div style={{ position: 'fixed', left: tooltipPosition.x + 10, top: tooltipPosition.y + 10, background: 'white', border: '1px solid #ddd', borderRadius: '8px', padding: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.15)', maxWidth: '400px', zIndex: 1000, fontSize: '13px', color: '#333', lineHeight: '1.5' }}>
          {hoveredCitation.quote || 'Citation content'}
        </div>
      )}

      {showCitationModal && selectedCitation && (
        <>
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1999 }} onClick={() => { setShowCitationModal(false); setSelectedCitation(null); }} />
          <div style={{ position: 'fixed', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', background: 'white', borderRadius: '12px', padding: '0', zIndex: 2000, width: 'min(900px, 95%)', maxHeight: '90vh', boxShadow: '0 20px 60px rgba(0,0,0,0.3)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '24px 28px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '20px', fontWeight: '700', color: '#111827', wordBreak: 'break-word', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FaFileAlt size={18} style={{ color: '#6b7280', flexShrink: 0 }} />
                  {selectedCitation.file_name || 'Source Document'}
                </div>
                {selectedCitation.page && <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>Page {selectedCitation.page}</div>}
              </div>
              <button onClick={() => { setShowCitationModal(false); setSelectedCitation(null); }}
                style={{ background: '#f3f4f6', border: 'none', width: '32px', height: '32px', borderRadius: '6px', cursor: 'pointer', color: '#6b7280', fontSize: '18px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}><FaTimes size={14} /></button>
            </div>
            <div style={{ padding: '24px 28px', overflowY: 'auto', flex: 1 }}>
              {selectedCitation.content && Array.isArray(selectedCitation.content) && selectedCitation.content.length > 0 ? (
                selectedCitation.content.map((chunk, idx) => {
                  const text = typeof chunk === 'string' ? chunk : (chunk.text || '');
                  const cleanedText = cleanIncompleteSentences(text);
                  return (
                    <div key={idx} style={{ background: '#f9fafb', padding: '16px', borderRadius: '8px', border: '1px solid #e5e7eb', marginBottom: '12px', fontSize: '14px', lineHeight: '1.6', color: '#374151', wordWrap: 'break-word', overflowWrap: 'break-word' }}>
                      {cleanedText}
                    </div>
                  );
                })
              ) : (
                <div style={{ background: '#f9fafb', padding: '20px', borderRadius: '8px', border: '1px solid #e5e7eb', textAlign: 'center', color: '#6b7280' }}>No citation content available</div>
              )}
            </div>
          </div>
        </>
      )}

      {showTimestamp && <div style={STYLES.timestamp(isUser)}>{timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>}
      {isUser && showRead && showReadStatus && <div style={{ fontSize: '10px', color: '#999', margin: '0 10px 0 10px', alignSelf: 'flex-end' }}>Read</div>}
    </div>
  );
};

export default MessageBubble;
