import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

export default function LandingPage({ onLogout }) {
  const navigate = useNavigate();
  const member = JSON.parse(localStorage.getItem('member') || 'null');

  const handleLogout = async () => {
    try { await fetch('/logout', { method: 'POST' }); } catch (_) {}
    localStorage.removeItem('member');
    sessionStorage.removeItem('sessionId');
    if (onLogout) onLogout();
    navigate('/login');
  };

  return (
    <div className="lp-root">

      {/* ── Header (matches AgenticMemberPortalDemo exactly) ── */}
      <header className="app-header">
        <div className="header-left">
          <div className="logo">
            <img src="/src/assets/cognizant-logo.png" alt="Logo" className="logo-img" />
          </div>
        </div>
        <div className="header-center">
          <h1>Agentic Member Portal</h1>
        </div>
        <div className="header-right">
          {member && (
            <div className="member-info">
              <span className="member-name">{member.first_name} {member.last_name}</span>
            </div>
          )}
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      {/* ── Nav links ── */}
      <nav className="lp-nav">
        <a href="#home">Home</a>
        <a href="#services">Services</a>
        <a href="#benefits">Benefits</a>
        <a href="#contact">Contact</a>
      </nav>

      {/* ── Hero ── */}
      <section className="lp-hero" id="home">
        <div className="lp-hero-content">
          <div className="lp-hero-badge">🏥 Cigna Healthcare</div>
          <h1>Your Health,<br />Our Priority</h1>
          <p>Find the right doctor, book appointments, and manage your healthcare — all in one place with AI-powered assistance.</p>
          <div className="lp-hero-actions">
            <button className="lp-cta-btn" onClick={() => navigate('/chat')}>
              💬 Start Chat Assistant
            </button>
            <button className="lp-cta-btn lp-cta-provider" onClick={() => navigate('/provider')}>
              🏥 Provider Portal
            </button>
            <button className="lp-cta-btn lp-cta-payer" onClick={() => navigate('/payer')}>
              🏦 Payer Portal
            </button>
            <a href="#services" className="lp-secondary-btn">Learn More</a>
          </div>
          {member && (
            <div className="lp-welcome-chip">
              👋 Welcome back, <strong>{member.first_name}</strong> — {member.insurance_plan}
            </div>
          )}
        </div>
        <div className="lp-hero-visual">
          <div className="lp-hero-card">
            <div className="lp-hero-card-icon">🤖</div>
            <div className="lp-hero-card-text">
              <strong>AI Assistant</strong>
              <span>Find providers instantly</span>
            </div>
          </div>
          <div className="lp-hero-card">
            <div className="lp-hero-card-icon">📅</div>
            <div className="lp-hero-card-text">
              <strong>Book Appointments</strong>
              <span>In-person or telehealth</span>
            </div>
          </div>
          <div className="lp-hero-card">
            <div className="lp-hero-card-icon">✅</div>
            <div className="lp-hero-card-text">
              <strong>Prior Auth</strong>
              <span>Managed automatically</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Services ── */}
      <section className="lp-section" id="services">
        <div className="lp-section-inner">
          <div className="lp-section-label">What We Offer</div>
          <h2>Our Services</h2>
          <div className="lp-cards">
            {[
              { icon: '🔍', title: 'Find Providers', desc: 'Search in-network doctors near you by specialty, language, and consultation mode.' },
              { icon: '📅', title: 'Book Appointments', desc: 'Schedule in-person or telehealth visits instantly with real-time slot availability.' },
              { icon: '📋', title: 'Validate Provider', desc: 'Validates providers upon your plan, benefits, prior authorizations, and out-of-pocket costs and recommends.' },
            ].map(c => (
              <div className="lp-card" key={c.title}>
                <div className="lp-card-icon">{c.icon}</div>
                <h3>{c.title}</h3>
                <p>{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Benefits ── */}
      <section className="lp-section lp-section-alt" id="benefits">
        <div className="lp-section-inner">
          <div className="lp-section-label">Member Perks</div>
          <h2>Member Benefits</h2>
          <div className="lp-cards">
            {[
              { icon: '�', title: 'Language Specificity', desc: 'Access to services in multiple languages to cater to diverse member needs.' },
              { icon: '🏥', title: 'Hospital Network', desc: 'Wide network of top-rated hospitals, clinics, and specialists.' },
              { icon: '🌐', title: 'Telehealth 24/7', desc: 'Connect with a doctor anytime, from anywhere — no travel needed.' },
            ].map(c => (
              <div className="lp-card" key={c.title}>
                <div className="lp-card-icon">{c.icon}</div>
                <h3>{c.title}</h3>
                <p>{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Contact ── */}
      <section className="lp-section" id="contact">
        <div className="lp-section-inner lp-contact-inner">
          <div className="lp-section-label">Get In Touch</div>
          <h2>Contact Us</h2>
          <p className="lp-contact-text">Our support team is available Mon–Fri, 8am–6pm CST.</p>
          <div className="lp-contact-chips">
            <span className="lp-contact-chip">📞 1-800-CIGNA</span>
            <span className="lp-contact-chip">✉️ support@cigna.com</span>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="app-footer">© 2026 Cigna Healthcare. All rights reserved.</footer>

      {/* ── Floating chat button ── */}
      <button className="lp-fab" onClick={() => navigate('/chat')} title="Open Chat Assistant">
        💬
      </button>

    </div>
  );
}
