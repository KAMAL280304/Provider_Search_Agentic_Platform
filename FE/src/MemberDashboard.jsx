import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
// import cogniLogo from '../assets/cognizant-logo.png';
import MessageBubble from './Components/MessageBubble';
import FAQSidebar from './Components/FAQSidebar';
import { getBackendMemberId } from './utils/memberMapping';
import { jsPDF } from 'jspdf';
import './Dashboard.css';

const STYLES = {
  flexCenter: { display: 'flex', alignItems: 'center', justifyContent: 'center' },
  avatar: { width: '36px', height: '36px', minWidth: '36px', minHeight: '36px', borderRadius: '50%', background: '#5C6BC0', color: 'white', fontSize: '13px', fontWeight: '600', flexShrink: 0, cursor: 'pointer' },
  toggleBtn: { fontSize: '15px', color: '#FFFFFF', background: '#1e1e5c', border: 'none', borderRadius: '4px', cursor: 'pointer', padding: '0', width: '24px', height: '24px', lineHeight: '1' },
  profileHeader: { padding: '8px 12px', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  chatBtn: { padding: '2px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '16px', color: '#333', opacity: 0.8 }
};

function MemberDashboard() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const [showProfile, setShowProfile] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showFAQ, setShowFAQ] = useState(false);
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [faqs, setFaqs] = useState([]);
  
  const chatMessagesRef = useRef(null);
  const inputRef = useRef(null);

  const loadHistory = async () => {
    const planName = localStorage.getItem('planName');
    const token = localStorage.getItem('token');
    if (planName) {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/conversations?plan_id=${planName}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        setConversations(data.conversations || []);
      } catch (error) {
        console.error('Failed to load history:', error);
      }
    }
  };

  const loadFAQs = async () => {
    const planName = localStorage.getItem('planName');
    const role = localStorage.getItem('role');
    if (planName) {
      try {
        const isAgent = role === 'agent' || role === 'agent1' || role === 'agent2' || role === 'role1';
        const params = new URLSearchParams({ member_id: planName, is_member: !isAgent });
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/faq?${params}`);
        const data = await response.json();
        setFaqs(data.faqs || []);
      } catch (error) {
        console.error('Failed to load FAQs:', error);
      }
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('token');
    const storedRole = localStorage.getItem('role');
    
    if (!token || (storedRole !== 'role2' && storedRole !== 'member1' && storedRole !== 'member2')) {
      navigate('/');
    }

    setSessionId(null);
    setMessages([{
      id: 1,
      type: 'assistant',
      content: "Welcome. I am your Benefits Assistant. You may ask about your health plan's covered services, cost-sharing amounts, included medical benefits, prescription drug coverage or other plan-related details — I'm here to help!",
      isUser: false,
      hasTable: false,
      timestamp: new Date().toISOString()
    }]);

    loadHistory();
    loadFAQs();
  }, [navigate]);

  useEffect(() => {
    const chatContainer = chatMessagesRef.current;
    if (!chatContainer) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = chatContainer;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
      const hasScroll = scrollHeight > clientHeight;
      setShowJumpToBottom(hasScroll && distanceFromBottom > 70);
    };

    chatContainer.addEventListener('scroll', handleScroll);
    return () => chatContainer.removeEventListener('scroll', handleScroll);
  }, []);

  const jumpToBottom = () => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTo({
        top: chatMessagesRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  const getMemberInfo = () => {
    const activeMemberId = localStorage.getItem('activeMemberId');
    const memberId = localStorage.getItem('memberId');
    const backendMemberId = getBackendMemberId(memberId);
    const id = activeMemberId || backendMemberId;
    
    if (id === 'MBR001') {
      return {
        name: 'Sarah Williams',
        initials: 'SW',
        memberId: 'MBR001',
        planName: 'Cigna Preferred Medicare',
        gender: 'Female',
        age: '63',
        location: 'Phoenix, AZ',
        phone: '602-555-1847',
        email: 'sarah.williams@email.com'
      };
    }
    return {
      name: 'Allen Joe',
      initials: 'AJ',
      memberId: 'MBR002',
      planName: 'Aetna Medicare Signature',
      gender: 'Male',
      age: '68',
      location: 'Phoenix, AZ',
      phone: '601-565-1711',
      email: 'allen.joe@email.com'
    };
  };

  const memberInfo = getMemberInfo();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('memberId');
    localStorage.removeItem('planName');
    navigate('/');
  };

  const sendMessage = async (content) => {
    if (!content.trim() || isLoading) return;
    
    const planName = localStorage.getItem('planName');
    
    setSuggestedQuestions([]);

    const newMessage = {
      id: Date.now(),
      type: 'user',
      content: content.trim(),
      isUser: true,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, newMessage]);
    setInputValue('');
    setIsLoading(true);
    
    // Auto-scroll to bottom when sending message
    setTimeout(() => {
      if (chatMessagesRef.current) {
        chatMessagesRef.current.scrollTo({
          top: chatMessagesRef.current.scrollHeight,
          behavior: 'smooth'
        });
      }
    }, 100);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: content.trim(),
          member_id: planName,
          thread_id: sessionId,
          is_member: true
        })
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data = await response.json();
      
      if (data.thread_id && data.thread_id !== sessionId) {
        setSessionId(data.thread_id);
        loadHistory();
      }
      
      let messageCitations = [];
      if (data.citations && Array.isArray(data.citations) && data.citations.length > 0) {
        messageCitations = data.citations.map((c, i) => {
          let quote = '';
          if (c.content && c.content.length > 0) {
            quote = c.content.map(item => item.text || '').join('\n');
          }
          return {
            index: i + 1,
            quote: quote,
            file_name: c.file_name || 'Unknown Document',
            page: null,
            content: c.content || [],
            raw: c
          };
        });
      }
      
      const botMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: data.response,
        isUser: false,
        timestamp: new Date().toISOString(),
        citations: messageCitations
      };
      
      setMessages(prev => [...prev, botMessage]);
      
      if (data.followup_questions && data.followup_questions.length > 0) {
        setSuggestedQuestions(data.followup_questions);
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
        isUser: false,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = () => {
    sendMessage(inputValue);
    if (inputRef.current) {
      inputRef.current.style.height = '40px';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const loadConversation = async (clickedSessionId) => {
    if (clickedSessionId === sessionId) return;
    setSuggestedQuestions([]);
    try {
      const planName = localStorage.getItem('planName');
      const token = localStorage.getItem('token');
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/conversations/${clickedSessionId}?plan_id=${planName}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      
      if (data.messages && data.messages.length > 0) {
        const loadedMessages = data.messages.map((msg, index) => ({
          id: Date.now() + index,
          type: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content,
          isUser: msg.role === 'user',
          timestamp: msg.timestamp || new Date().toISOString(),
          citations: msg.citations || []
        }));
        setMessages(loadedMessages);
        setSessionId(clickedSessionId);
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <div className="logo">
            <span>Cognizant Logo</span>
          </div>
        </div>
        <div className="header-center">
          <h1>Healthcare Payer Solutions</h1>
        </div>
        <div className="header-right">
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="main-content">
        {showProfile && (
          <aside className="left-zone" style={{ position: 'relative' }}>
            <div className="profile-sidebar">
              <div className="profile-header" style={STYLES.profileHeader}>
                <span style={{ color: '#000000', whiteSpace: 'nowrap', fontWeight: '600' }}>👤 Member Profile</span>
                <button onClick={() => setShowProfile(false)} style={{ ...STYLES.toggleBtn, ...STYLES.flexCenter, fontSize: '14px' }} title="Close panel">❮❮</button>
              </div>
              <div className="profile-avatar">
                <div className="avatar-circle">{memberInfo.initials}</div>
                <span className="status-badge">• Active Member</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '2px', padding: '8px 12px' }}>
                <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#000000', whiteSpace: 'nowrap' }}>{memberInfo.name}</div>
              </div>
              <div className="profile-info">
                <div className="profile-info-row">
                  <span className="profile-info-label">ID</span>
                  <span className="profile-info-value">{memberInfo.memberId}</span>
                </div>
                <div className="profile-info-row">
                  <span className="profile-info-label">Plan</span>
                  <span className="profile-info-value">{memberInfo.planName}</span>
                </div>
                <div className="profile-info-row">
                  <span className="profile-info-label">Gender</span>
                  <span className="profile-info-value">{memberInfo.gender}</span>
                </div>
                <div className="profile-info-row">
                  <span className="profile-info-label">Age</span>
                  <span className="profile-info-value">{memberInfo.age}</span>
                </div>
                <div className="profile-info-row">
                  <span className="profile-info-label">Location</span>
                  <span className="profile-info-value">{memberInfo.location}</span>
                </div>
                <div className="profile-info-row">
                  <span className="profile-info-label">Phone</span>
                  <span className="profile-info-value">{memberInfo.phone}</span>
                </div>
                <div className="profile-info-row">
                  <span className="profile-info-label">Email</span>
                  <span className="profile-info-value">{memberInfo.email}</span>
                </div>
              </div>
            </div>
          </aside>
        )}

        {!showProfile && (
          <button className="sidebar-toggle left-toggle" onClick={() => setShowProfile(true)} style={{ ...STYLES.toggleBtn, ...STYLES.flexCenter, left: '5px', position: 'absolute', zIndex: 10 }}>❯❯</button>
        )}

        <section className="center-zone" style={{ position: 'relative' }}>
          <div className="chat-panel-agent">
            <div className="chat-header">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginLeft: '20px', marginRight: '20px' }}>
                <h2 style={{ fontSize: '24px', fontWeight: '700', margin: '0', color: '#000048' }}>Benefit Inquiry Assistant</h2>
                <button 
                  onClick={() => {
                    setShowFAQ(!showFAQ);
                    if (!showFAQ) setShowHistory(false);
                  }}
                  className="change-member-btn"
                  title={showFAQ ? 'Hide FAQs' : 'Show FAQs'}
                >
                  📚 FAQs
                </button>
              </div>
            </div>
            <div className="chat-messages" ref={chatMessagesRef}>
              {messages.map((msg, index) => {
                const isUserMessage = msg.isUser;
                const hasResponse = isUserMessage && (index < messages.length - 1 || isLoading);
                
                return (
                  <div key={msg.id}>
                    <MessageBubble
                      message={msg.content}
                      isUser={msg.isUser}
                      showRead={hasResponse}
                      timestamp={msg.timestamp}
                      citations={msg.citations || []}
                    />
                  </div>
                );
              })}
              {isLoading && (
                <div style={{ alignSelf: 'flex-start', margin: '10px', color: '#666', fontSize: '32px', fontWeight: '900' }}>
                  <style>{`
                    @keyframes wave {
                      0%, 60%, 100% { transform: translateY(0); }
                      30% { transform: translateY(-8px); }
                    }
                  `}</style>
                  <span style={{ display: 'inline-block', animation: 'wave 1.4s infinite' }}>.</span>
                  <span style={{ display: 'inline-block', animation: 'wave 1.4s infinite 0.2s' }}>.</span>
                  <span style={{ display: 'inline-block', animation: 'wave 1.4s infinite 0.4s' }}>.</span>
                </div>
              )}
              {suggestedQuestions.length > 0 && (
                <div className="followup-questions">
                  {suggestedQuestions.map((question, index) => (
                    <button
                      key={index}
                      className="followup-btn"
                      onClick={() => {
                        setInputValue(question);
                        setTimeout(() => inputRef.current?.focus(), 0);
                      }}
                    >
                      {question}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {showJumpToBottom && (
              <button 
                onClick={jumpToBottom}
                style={{
                  position: 'absolute',
                  bottom: '80px',
                  right: '20px',
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  backgroundColor: 'white',
                  color: '#1e1e5c',
                  border: '1px solid #ddd',
                  cursor: 'pointer',
                  fontSize: '18px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                  zIndex: 10,
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#e3f2fd'}
                onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
                title="Jump to bottom"
              >
                ↓
              </button>
            )}
            <div className="input-bar">
              <div className="input-wrapper" style={{ padding: '8px 16px' }}>
                <textarea 
                  ref={inputRef}
                  className="chat-input" 
                  placeholder="Ask me about your benefits, coverage or costs…"
                  value={inputValue}
                  onChange={(e) => {
                    setInputValue(e.target.value);
                    e.target.style.height = 'auto';
                    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
                  }}
                  onKeyDown={handleKeyDown}
                  rows="1"
                  disabled={isLoading}
                  style={{ 
                    minHeight: '40px',
                    maxHeight: '200px', 
                    resize: 'none', 
                    overflowY: 'hidden',
                    whiteSpace: 'pre-wrap',
                    wordWrap: 'break-word',
                    overflowWrap: 'break-word',
                    padding: '8px 6px',
                    lineHeight: '24px'
                  }}
                />
                <div className="input-actions">
                  <button className="send-btn" onClick={handleSend} title="Send message" disabled={isLoading}>➤</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {showFAQ && (
          <aside className="right-zone" style={{ width: '240px', minWidth: '240px', maxWidth: '240px', overflowY: 'hidden', overflowX: 'hidden', flexShrink: 0 }}>
            <div className="profile-sidebar" style={{ overflowX: 'hidden', width: '240px' }}>
              <div className="profile-header" style={{ padding: '8px 12px', marginBottom: '12px' }}>
                <span style={{ color: '#000000', whiteSpace: 'nowrap', fontWeight: '600' }}>📚 FAQs</span>
              </div>
              <FAQSidebar faqs={faqs} onQuestionClick={(question, directSend) => {
                if (directSend) {
                  sendMessage(question);
                } else {
                  setInputValue(question);
                  setTimeout(() => inputRef.current?.focus(), 0);
                }
              }} />
            </div>
          </aside>
        )}

        {showHistory && (
          <aside className="right-zone" style={{ width: '240px', minWidth: '240px', maxWidth: '240px', overflowY: 'hidden', overflowX: 'hidden', flexShrink: 0 }}>
            <div className="profile-sidebar" style={{ overflowX: 'hidden', width: '240px' }}>
              <div className="profile-header" style={{ padding: '8px 12px', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flex: 1 }}>
                  <button onClick={() => setShowHistory(false)} style={{ ...STYLES.toggleBtn, ...STYLES.flexCenter }} title="Close panel">❯❯</button>
                  <span style={{ color: '#000000', whiteSpace: 'nowrap', fontWeight: '600', marginLeft: '4px' }}>Chat History</span>
                </div>
              </div>
              <div style={{ overflowY: 'auto', overflowX: 'hidden', maxHeight: 'calc(100vh - 200px)' }}>
                {[...conversations].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)).map((conv, index) => (
                  <div 
                    key={conv.session_id}
                    style={{
                      padding: '6px 12px',
                      marginBottom: '2px',
                      background: conv.session_id === sessionId ? '#e8f0fe' : 'transparent',
                      borderLeft: conv.session_id === sessionId ? '3px solid #1e40af' : 'none',
                      cursor: 'pointer',
                      fontSize: '13px',
                      color: '#333',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      transition: 'background 0.2s'
                    }}
                    onClick={() => loadConversation(conv.session_id)}
                    onMouseEnter={(e) => e.currentTarget.style.background = conv.session_id === sessionId ? '#e8f0fe' : '#f5f5f5'}
                    onMouseLeave={(e) => e.currentTarget.style.background = conv.session_id === sessionId ? '#e8f0fe' : 'transparent'}
                  >
                    <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {conv.messages && conv.messages.length > 0 && conv.messages[0].role === 'user' 
                        ? conv.messages[0].content.substring(0, 30) + (conv.messages[0].content.length > 30 ? '...' : '')
                        : `Chat ${index + 1}`}
                    </div>
                    <div style={{ display: 'flex', gap: '10px', marginLeft: '8px' }}>
                      <button style={STYLES.chatBtn} title="Download" onClick={(e) => {
                          e.stopPropagation();
                          const doc = new jsPDF();
                          const pageWidth = doc.internal.pageSize.getWidth();
                          const pageHeight = doc.internal.pageSize.getHeight();
                          const margin = 15;
                          const maxWidth = pageWidth - (margin * 2);
                          const lineHeight = 6;
                          
                          doc.setFontSize(16);
                          doc.text('Chat History', margin, 20);
                          doc.setFontSize(10);
                          doc.text(`Date: ${new Date(conv.created_at || Date.now()).toLocaleString()}`, margin, 28);
                          doc.text(`Member: ${memberInfo.name} (${memberInfo.memberId})`, margin, 34);
                          
                          let yPos = 44;
                          conv.messages?.forEach((msg, index) => {
                            if (index === 0 && msg.role !== 'user' && msg.content.includes('Welcome')) return;
                            
                            if (yPos + lineHeight > pageHeight - margin) {
                              doc.addPage();
                              yPos = margin;
                            }
                            
                            doc.setFontSize(11);
                            doc.setFont(undefined, 'bold');
                            doc.text(msg.role === 'user' ? 'User:' : 'Assistant:', margin, yPos);
                            yPos += lineHeight + 2;
                            
                            doc.setFont(undefined, 'normal');
                            doc.setFontSize(10);
                            
                            const textLines = doc.splitTextToSize(msg.content, maxWidth);
                            textLines.forEach((line) => {
                              if (yPos + lineHeight > pageHeight - margin) {
                                doc.addPage();
                                yPos = margin;
                              }
                              
                              const parts = line.split(/\*\*(.*?)\*\*/);
                              let xPos = margin;
                              parts.forEach((part, i) => {
                                if (i % 2 === 1) {
                                  doc.setFont(undefined, 'bold');
                                  doc.text(part, xPos, yPos);
                                  xPos += doc.getTextWidth(part);
                                  doc.setFont(undefined, 'normal');
                                } else if (part) {
                                  doc.text(part, xPos, yPos);
                                  xPos += doc.getTextWidth(part);
                                }
                              });
                              
                              yPos += lineHeight;
                            });
                            
                            yPos += 6;
                          });
                          
                          const now = new Date(conv.created_at || Date.now());
                          const memberId = memberInfo.memberId;
                          const memberName = memberInfo.name.replace(/\s+/g, '_');
                          const date = now.toISOString().split('T')[0];
                          const time = now.toTimeString().split(' ')[0].replace(/:/g, '-');
                          const filename = `${memberId}_${memberName}_${date}_${time}.pdf`;
                          
                          doc.save(filename);
                        }}
                        onMouseEnter={(e) => { e.target.style.opacity = '1'; e.target.style.color = '#000'; }}
                        onMouseLeave={(e) => { e.target.style.opacity = '0.8'; e.target.style.color = '#333'; }}
                      >
                        ⤓
                      </button>
                      <button style={STYLES.chatBtn} title="Delete" onClick={async (e) => {
                          e.stopPropagation();
                          try {
                            const planName = localStorage.getItem('planName');
                            const token = localStorage.getItem('token');
                            await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/conversations/${conv.session_id}?plan_id=${planName}`, { 
                              method: 'DELETE',
                              headers: { 'Authorization': `Bearer ${token}` }
                            });
                            setConversations(conversations.filter(c => c.session_id !== conv.session_id));
                            if (conv.session_id === sessionId) {
                              setSessionId(null);
                              setShowJumpToBottom(false);
                              setMessages([{
                                id: 1,
                                type: 'assistant',
                                content: "Welcome. I am your Benefits Assistant. You may ask about your health plan's covered services, cost-sharing amounts, included medical benefits, prescription drug coverage or other plan-related details — I'm here to help!",
                                isUser: false,
                                hasTable: false,
                                timestamp: new Date().toISOString()
                              }]);
                              setSuggestedQuestions([]);
                            }
                          } catch (error) {
                            console.error('Delete failed:', error);
                          }
                        }}
                        onMouseEnter={(e) => { e.target.style.opacity = '1'; e.target.style.color = '#000'; }}
                        onMouseLeave={(e) => { e.target.style.opacity = '0.8'; e.target.style.color = '#333'; }}
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                ))}
                {conversations.length === 0 && (
                  <div style={{ padding: '10px', textAlign: 'center', color: '#999', fontSize: '12px' }}>
                    No chat history yet
                  </div>
                )}
              </div>
            </div>
          </aside>
        )}

        {!showHistory && (
          <button className="sidebar-toggle right-toggle" onClick={() => {
            setShowHistory(true);
            setShowFAQ(false);
          }} style={{ ...STYLES.toggleBtn, ...STYLES.flexCenter, right: '5px', position: 'absolute', zIndex: 10 }}>❮❮</button>
        )}
      </main>
      <div className="app-footer">
        © 2026 Cognizant, all rights reserved.
      </div>
    </div>
  );
}

export default MemberDashboard;
