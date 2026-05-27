import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

const MEMBERS = [
  { id: 'MEM-10001', name: 'Alex Johnson',       city: 'Los Angeles, CA' },
  { id: 'MEM-10002', name: 'Sarah Anne Mitchell', city: 'Los Angeles, CA' },
  { id: 'MEM-10003', name: 'James Williams',      city: 'New York, NY'    },
  { id: 'MEM-10004', name: 'Sofia Martinez',      city: 'Miami, FL'       },
  { id: 'MEM-10005', name: 'David Chen',          city: 'Chicago, IL'     },
  { id: 'MEM-10006', name: 'Priya Patel',         city: 'Seattle, WA'     },
];

const S = {
  root:    { minHeight:'100vh', background:'#f0f6ff', fontFamily:"'Inter',-apple-system,sans-serif", color:'#1e1e5c' },
  header:  { background:'#0f3460', color:'#fff', padding:'0 32px', height:56, display:'flex', alignItems:'center', justifyContent:'space-between' },
  hTitle:  { fontSize:16, fontWeight:700, letterSpacing:0.3 },
  hRight:  { display:'flex', alignItems:'center', gap:12 },
  badge:   { background:'#1a4a7a', border:'1px solid #2d6aa0', borderRadius:20, padding:'3px 12px', fontSize:11, fontWeight:600, color:'#93c5fd' },
  backBtn: { background:'transparent', border:'1px solid rgba(255,255,255,0.3)', borderRadius:8, padding:'5px 14px', color:'#fff', fontSize:12, cursor:'pointer' },
  body:    { maxWidth:1200, margin:'0 auto', padding:'28px 24px' },
  statsRow:{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, marginBottom:24 },
  statCard:{ background:'#fff', borderRadius:12, border:'1px solid #e0e7ff', padding:'16px 20px' },
  statNum: { fontSize:28, fontWeight:800, color:'#0f3460' },
  statLbl: { fontSize:12, color:'#64748b', marginTop:2 },
  grid:    { display:'grid', gridTemplateColumns:'280px 1fr', gap:24, alignItems:'start' },
  panel:   { background:'#fff', borderRadius:14, border:'1px solid #e0e7ff', overflow:'hidden' },
  panelH:  { padding:'14px 18px', borderBottom:'1px solid #e0e7ff', fontWeight:700, fontSize:13, color:'#0f3460', background:'#f0f6ff', display:'flex', alignItems:'center', gap:8 },
  memberBtn: (active) => ({
    width:'100%', textAlign:'left', padding:'12px 18px', border:'none', borderBottom:'1px solid #f0f4ff',
    background: active ? '#dbeafe' : '#fff', cursor:'pointer', transition:'background 0.15s',
    borderLeft: active ? '3px solid #0f3460' : '3px solid transparent',
  }),
  mName:   { fontSize:13, fontWeight:600, color:'#1e1e5c' },
  mSub:    { fontSize:11, color:'#64748b', marginTop:2 },
  card:    { background:'#f8faff', border:'1px solid #e0e7ff', borderRadius:10, padding:'14px 16px', marginBottom:12 },
  row:     { display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:12, flexWrap:'wrap' },
  label:   { fontSize:11, color:'#94a3b8', marginBottom:2 },
  value:   { fontSize:13, fontWeight:600, color:'#1e1e5c' },
  pill:    (color) => ({ display:'inline-block', padding:'2px 10px', borderRadius:20, fontSize:11, fontWeight:700, background: color==='green'?'#dcfce7':color==='yellow'?'#fef9c3':color==='red'?'#fee2e2':color==='blue'?'#dbeafe':'#e0e7ff', color: color==='green'?'#166534':color==='yellow'?'#854d0e':color==='red'?'#991b1b':color==='blue'?'#1e40af':'#1e1e5c' }),
  btnGreen:{ padding:'7px 18px', borderRadius:8, border:'none', fontWeight:700, fontSize:12, cursor:'pointer', background:'#16a34a', color:'#fff' },
  btnRed:  { padding:'7px 18px', borderRadius:8, border:'none', fontWeight:700, fontSize:12, cursor:'pointer', background:'#dc2626', color:'#fff' },
  btnGray: { padding:'7px 18px', borderRadius:8, border:'none', fontWeight:700, fontSize:12, cursor:'pointer', background:'#64748b', color:'#fff' },
  toast:   (type) => ({ position:'fixed', top:20, right:20, zIndex:999, padding:'12px 20px', borderRadius:10, fontWeight:600, fontSize:13, background: type==='success'?'#dcfce7':type==='error'?'#fee2e2':'#dbeafe', color: type==='success'?'#166534':type==='error'?'#991b1b':'#1e40af', border:`1px solid ${type==='success'?'#86efac':type==='error'?'#fca5a5':'#93c5fd'}`, boxShadow:'0 4px 16px rgba(0,0,0,0.12)' }),
  empty:   { color:'#94a3b8', fontSize:13, padding:'16px 0', textAlign:'center' },
};

function Toast({ msg, type, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, []);
  return <div style={S.toast(type)}>{msg}</div>;
}

function StatusPill({ status }) {
  if (!status) return <span style={S.pill('gray')}>None</span>;
  const map = { none:'yellow', pending:'yellow', approved:'green', declined:'red', completed:'green' };
  return <span style={S.pill(map[status] || 'gray')}>{status.toUpperCase()}</span>;
}

export default function PayerDashboard() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState('MEM-10001');
  const [allData, setAllData] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type='success') => setToast({ msg, type });

  const loadAll = useCallback(async () => {
    try {
      const r = await fetch('/dashboard/members');
      const d = await r.json();
      setAllData(d.members || []);
    } catch {}
  }, []);

  const loadOne = useCallback(async (mid) => {
    setLoading(true);
    try {
      const r = await fetch(`/dashboard/member/${mid}`);
      const d = await r.json();
      setData(d);
    } catch { showToast('Failed to load member data', 'error'); }
    setLoading(false);
  }, []);

  useEffect(() => { loadAll(); }, []);
  useEffect(() => { loadOne(selected); }, [selected]);

  const post = async (url, body) => {
    const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    return r.json();
  };

  const priorAuthDecision = async (decision) => {
    const res = await post('/dashboard/payer/prior-auth-decision', { member_id: selected, decision });
    if (res.success) { showToast(`Prior auth ${decision} ✓`); loadOne(selected); loadAll(); }
    else showToast(res.detail || 'Failed', 'error');
  };

  const pcpChangeDecision = async (decision) => {
    const res = await post('/dashboard/payer/pcp-change-decision', { member_id: selected, decision });
    if (res.success) { showToast(`PCP change ${decision} ✓`); loadOne(selected); loadAll(); }
    else showToast(res.detail || 'Failed', 'error');
  };

  const planChangeDecision = async (decision) => {
    const res = await post('/dashboard/payer/plan-change-decision', { member_id: selected, decision });
    if (res.success) { showToast(`Plan change ${decision} ✓`); loadOne(selected); loadAll(); }
    else showToast(res.detail || 'Failed', 'error');
  };

  // Stats across all members
  const pendingPA    = allData.filter(m => m.prior_auth?.status === 'pending').length;
  const pendingPCP   = allData.filter(m => (m.pcp_changes || []).some(c => c.status === 'pending')).length;
  const pendingPlan  = allData.filter(m => m.plan_change && !m.plan_change.payer_decision).length;
  const totalPending = pendingPA + pendingPCP + pendingPlan;

  const pa         = data?.prior_auth;
  const pcpChanges = (data?.pcp_changes || []).filter(c => c.status === 'pending');
  const planChange = data?.plan_change && !data.plan_change.payer_decision ? data.plan_change : null;

  // Badge for member list
  const memberBadge = (mid) => {
    const m = allData.find(x => x.member_id === mid);
    if (!m) return null;
    const count = (m.prior_auth?.status === 'pending' ? 1 : 0)
      + (m.pcp_changes || []).filter(c => c.status === 'pending').length
      + (m.plan_change && !m.plan_change.payer_decision ? 1 : 0);
    if (!count) return null;
    return <span style={{ marginLeft:'auto', background:'#dc2626', color:'#fff', borderRadius:20, padding:'1px 7px', fontSize:10, fontWeight:700 }}>{count}</span>;
  };

  return (
    <div style={S.root}>
      {toast && <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />}

      <header style={S.header}>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          <span style={{ fontSize:20 }}>🏦</span>
          <span style={S.hTitle}>Cigna Payer Portal — Medilife Healthcare</span>
        </div>
        <div style={S.hRight}>
          <span style={S.badge}>Payer View</span>
          <button style={S.backBtn} onClick={() => navigate('/')}>← Back to Portal</button>
        </div>
      </header>

      <div style={S.body}>
        <div style={{ marginBottom:20 }}>
          <div style={{ fontSize:22, fontWeight:800, color:'#0f3460' }}>Payer Dashboard</div>
          <div style={{ fontSize:13, color:'#64748b', marginTop:4 }}>Review and action prior auth requests, PCP changes, and plan change requests</div>
        </div>

        {/* Stats */}
        <div style={S.statsRow}>
          {[
            { label:'Total Pending Actions', value: totalPending, icon:'⚡', color:'#dc2626' },
            { label:'Prior Auth Pending',    value: pendingPA,    icon:'🩻', color:'#d97706' },
            { label:'PCP Change Pending',    value: pendingPCP,   icon:'👨‍⚕️', color:'#7c3aed' },
            { label:'Plan Change Pending',   value: pendingPlan,  icon:'📋', color:'#0f3460' },
          ].map(s => (
            <div key={s.label} style={S.statCard}>
              <div style={{ fontSize:22, marginBottom:4 }}>{s.icon}</div>
              <div style={{ ...S.statNum, color: s.color }}>{s.value}</div>
              <div style={S.statLbl}>{s.label}</div>
            </div>
          ))}
        </div>

        <div style={S.grid}>
          {/* Member list */}
          <div style={S.panel}>
            <div style={S.panelH}>👥 Members</div>
            {MEMBERS.map(m => (
              <button key={m.id} style={{ ...S.memberBtn(selected === m.id), display:'flex', alignItems:'center' }} onClick={() => setSelected(m.id)}>
                <div style={{ flex:1 }}>
                  <div style={S.mName}>{m.name}</div>
                  <div style={S.mSub}>{m.id} · {m.city}</div>
                </div>
                {memberBadge(m.id)}
              </button>
            ))}
          </div>

          {/* Detail */}
          <div>
            {loading && <div style={{ textAlign:'center', padding:40, color:'#94a3b8' }}>Loading…</div>}
            {!loading && data && (
              <>
                {/* Member header */}
                <div style={{ ...S.panel, marginBottom:20, padding:'16px 20px' }}>
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:12 }}>
                    <div>
                      <div style={{ fontSize:18, fontWeight:800 }}>{data.name}</div>
                      <div style={{ fontSize:12, color:'#64748b', marginTop:2 }}>{data.city}</div>
                    </div>
                    <div style={{ textAlign:'right' }}>
                      <div style={S.label}>Current Plan</div>
                      <div style={{ fontSize:13, fontWeight:600 }}>{data.plan}</div>
                    </div>
                    <div style={{ textAlign:'right' }}>
                      <div style={S.label}>Assigned PCP</div>
                      <div style={{ fontSize:13, fontWeight:600 }}>{data.assigned_pcp?.name || '—'}</div>
                    </div>
                  </div>
                </div>

                {/* ── Prior Auth ── */}
                <div style={S.panel}>
                  <div style={S.panelH}>🩻 Prior Authorization Request</div>
                  <div style={{ padding:'16px 18px' }}>
                    {pa && pa.status === 'pending' ? (
                      <div style={S.card}>
                        <div style={{ ...S.row, marginBottom:10 }}>
                          <div>
                            <div style={S.label}>Procedure</div>
                            <div style={S.value}>{pa.procedure || 'MRI Scan'}</div>
                          </div>
                          <div>
                            <div style={S.label}>Status</div>
                            <StatusPill status={pa.status} />
                          </div>
                        </div>
                        <div style={{ ...S.row, marginBottom:10 }}>
                          <div>
                            <div style={S.label}>Submitted by</div>
                            <div style={S.value}>{pa.submitted_by || '—'}</div>
                          </div>
                          <div>
                            <div style={S.label}>Submitted on</div>
                            <div style={S.value}>{pa.submitted_date || '—'}</div>
                          </div>
                          <div>
                            <div style={S.label}>Ref#</div>
                            <div style={S.value}>{pa.auth_reference_number || '—'}</div>
                          </div>
                        </div>
                        <div style={{ display:'flex', gap:10, marginTop:14 }}>
                          <button style={S.btnGreen} onClick={() => priorAuthDecision('approved')}>✓ Approve</button>
                          <button style={S.btnRed}   onClick={() => priorAuthDecision('declined')}>✗ Decline</button>
                        </div>
                      </div>
                    ) : pa?.status === 'approved' ? (
                      <div style={{ ...S.card, background:'#f0fdf4', border:'1px solid #86efac' }}>
                        <div style={{ ...S.row }}>
                          <div><div style={S.label}>Status</div><StatusPill status="approved" /></div>
                          <div><div style={S.label}>Approved on</div><div style={S.value}>{pa.approved_date}</div></div>
                          <div><div style={S.label}>Valid through</div><div style={S.value}>{pa.valid_through}</div></div>
                          <div><div style={S.label}>Ref#</div><div style={S.value}>{pa.auth_reference_number || '—'}</div></div>
                        </div>
                      </div>
                    ) : pa?.status === 'declined' ? (
                      <div style={{ ...S.card, background:'#fff5f5', border:'1px solid #fca5a5' }}>
                        <div style={S.row}>
                          <div><div style={S.label}>Status</div><StatusPill status="declined" /></div>
                          <div><div style={S.label}>Declined on</div><div style={S.value}>{pa.declined_date || '—'}</div></div>
                        </div>
                        <div style={{ marginTop:8, fontSize:12, color:'#991b1b' }}>{pa.decline_reason}</div>
                      </div>
                    ) : (
                      <div style={S.empty}>No prior auth request on file for this member.</div>
                    )}
                  </div>
                </div>

                {/* ── PCP Change ── */}
                <div style={{ ...S.panel, marginTop:20 }}>
                  <div style={S.panelH}>👨‍⚕️ PCP Change Request</div>
                  <div style={{ padding:'16px 18px' }}>
                    {pcpChanges.length > 0 ? pcpChanges.map((c, i) => (
                      <div key={i} style={S.card}>
                        <div style={{ ...S.row, marginBottom:10 }}>
                          <div>
                            <div style={S.label}>Member</div>
                            <div style={S.value}>{data.name}</div>
                          </div>
                          <div>
                            <div style={S.label}>Current PCP</div>
                            <div style={S.value}>{c.old_pcp_name || data.assigned_pcp?.name || '—'}</div>
                          </div>
                        </div>
                        <div style={{ ...S.row, marginBottom:10 }}>
                          <div>
                            <div style={S.label}>Requested New PCP</div>
                            <div style={S.value}>{c.new_pcp_name}</div>
                          </div>
                          <div>
                            <div style={S.label}>NPI</div>
                            <div style={S.value}>{c.new_pcp_npi}</div>
                          </div>
                          <div>
                            <div style={S.label}>Reason</div>
                            <div style={S.value}>{c.reason || '—'}</div>
                          </div>
                        </div>
                        <div style={{ marginTop:8, fontSize:11, color:'#64748b' }}>Requested: {c.requested_at?.slice(0,10)}</div>
                        <div style={{ display:'flex', gap:10, marginTop:14 }}>
                          <button style={S.btnGreen} onClick={() => pcpChangeDecision('approved')}>✓ Approve Change</button>
                          <button style={S.btnRed}   onClick={() => pcpChangeDecision('declined')}>✗ Decline</button>
                        </div>
                      </div>
                    )) : (
                      <div style={S.empty}>No pending PCP change requests.</div>
                    )}
                    {/* Show completed PCP changes */}
                    {(data.pcp_changes || []).filter(c => c.status !== 'pending').map((c, i) => (
                      <div key={`done-${i}`} style={{ ...S.card, opacity:0.7 }}>
                        <div style={S.row}>
                          <div><div style={S.label}>New PCP</div><div style={S.value}>{c.new_pcp_name}</div></div>
                          <div><div style={S.label}>Status</div><StatusPill status={c.status} /></div>
                          <div><div style={S.label}>Completed</div><div style={S.value}>{c.completed_at?.slice(0,10) || '—'}</div></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* ── Plan Change ── */}
                <div style={{ ...S.panel, marginTop:20 }}>
                  <div style={S.panelH}>📋 Plan Change Request</div>
                  <div style={{ padding:'16px 18px' }}>
                    {planChange ? (
                      <div style={S.card}>
                        <div style={{ ...S.row, marginBottom:10 }}>
                          <div>
                            <div style={S.label}>Previous Plan</div>
                            <div style={S.value}>{planChange.previous_plan}</div>
                          </div>
                          <div>
                            <div style={S.label}>Requested Plan</div>
                            <div style={S.value}>{data.plan}</div>
                          </div>
                        </div>
                        <div style={{ marginTop:8, fontSize:11, color:'#64748b' }}>Requested: {planChange.changed_at?.slice(0,10)}</div>
                        <div style={{ display:'flex', gap:10, marginTop:14 }}>
                          <button style={S.btnGreen} onClick={() => planChangeDecision('approved')}>✓ Approve Plan Change</button>
                          <button style={S.btnRed}   onClick={() => planChangeDecision('declined')}>✗ Decline</button>
                        </div>
                      </div>
                    ) : data.plan_change?.payer_decision ? (
                      <div style={{ ...S.card, opacity:0.75 }}>
                        <div style={S.row}>
                          <div><div style={S.label}>Previous Plan</div><div style={S.value}>{data.plan_change.previous_plan}</div></div>
                          <div><div style={S.label}>Decision</div><StatusPill status={data.plan_change.payer_decision} /></div>
                          <div><div style={S.label}>Decided</div><div style={S.value}>{data.plan_change.payer_decided_at?.slice(0,10) || '—'}</div></div>
                        </div>
                      </div>
                    ) : (
                      <div style={S.empty}>No pending plan change requests.</div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
