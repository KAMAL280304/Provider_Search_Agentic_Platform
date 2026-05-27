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

const SPECIALTIES = ['Orthopaedic Surgery','Neurology','Cardiology','Radiology','Endocrinology','Dermatology','Gastroenterology','Rheumatology','Internal Medicine','Family Medicine'];

const S = {
  root:    { minHeight:'100vh', background:'#f0f4ff', fontFamily:"'Inter',-apple-system,sans-serif", color:'#1e1e5c' },
  header:  { background:'#1e1e5c', color:'#fff', padding:'0 32px', height:56, display:'flex', alignItems:'center', justifyContent:'space-between' },
  hTitle:  { fontSize:16, fontWeight:700, letterSpacing:0.3 },
  hRight:  { display:'flex', alignItems:'center', gap:12 },
  badge:   { background:'#2d308d', border:'1px solid #4a52c4', borderRadius:20, padding:'3px 12px', fontSize:11, fontWeight:600, color:'#a5b4fc' },
  backBtn: { background:'transparent', border:'1px solid rgba(255,255,255,0.3)', borderRadius:8, padding:'5px 14px', color:'#fff', fontSize:12, cursor:'pointer' },
  body:    { maxWidth:1200, margin:'0 auto', padding:'28px 24px' },
  grid:    { display:'grid', gridTemplateColumns:'280px 1fr', gap:24, alignItems:'start' },
  panel:   { background:'#fff', borderRadius:14, border:'1px solid #e0e7ff', overflow:'hidden' },
  panelH:  { padding:'14px 18px', borderBottom:'1px solid #e0e7ff', fontWeight:700, fontSize:13, color:'#1e1e5c', background:'#f8faff', display:'flex', alignItems:'center', gap:8 },
  memberBtn: (active) => ({
    width:'100%', textAlign:'left', padding:'12px 18px', border:'none', borderBottom:'1px solid #f0f4ff',
    background: active ? '#e0e7ff' : '#fff', cursor:'pointer', transition:'background 0.15s',
    borderLeft: active ? '3px solid #2d308d' : '3px solid transparent',
  }),
  mName:   { fontSize:13, fontWeight:600, color:'#1e1e5c' },
  mCity:   { fontSize:11, color:'#64748b', marginTop:2 },
  section: { marginBottom:20 },
  secH:    { fontSize:12, fontWeight:700, textTransform:'uppercase', letterSpacing:0.8, color:'#64748b', marginBottom:10, display:'flex', alignItems:'center', gap:6 },
  card:    { background:'#f8faff', border:'1px solid #e0e7ff', borderRadius:10, padding:'14px 16px', marginBottom:10 },
  row:     { display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:12 },
  label:   { fontSize:11, color:'#94a3b8', marginBottom:2 },
  value:   { fontSize:13, fontWeight:600, color:'#1e1e5c' },
  pill:    (color) => ({ display:'inline-block', padding:'2px 10px', borderRadius:20, fontSize:11, fontWeight:700, background: color==='green'?'#dcfce7':color==='yellow'?'#fef9c3':color==='red'?'#fee2e2':'#e0e7ff', color: color==='green'?'#166534':color==='yellow'?'#854d0e':color==='red'?'#991b1b':'#1e1e5c' }),
  btn:     (color) => ({ padding:'7px 18px', borderRadius:8, border:'none', fontWeight:700, fontSize:12, cursor:'pointer', background: color==='blue'?'#2d308d':color==='green'?'#16a34a':color==='red'?'#dc2626':'#64748b', color:'#fff', transition:'opacity 0.2s' }),
  input:   { width:'100%', padding:'8px 12px', border:'1.5px solid #e0e7ff', borderRadius:8, fontSize:13, fontFamily:'inherit', outline:'none', boxSizing:'border-box' },
  select:  { width:'100%', padding:'8px 12px', border:'1.5px solid #e0e7ff', borderRadius:8, fontSize:13, fontFamily:'inherit', outline:'none', background:'#fff', boxSizing:'border-box' },
  toast:   (type) => ({ position:'fixed', top:20, right:20, zIndex:999, padding:'12px 20px', borderRadius:10, fontWeight:600, fontSize:13, background: type==='success'?'#dcfce7':type==='error'?'#fee2e2':'#e0e7ff', color: type==='success'?'#166534':type==='error'?'#991b1b':'#1e1e5c', border:`1px solid ${type==='success'?'#86efac':type==='error'?'#fca5a5':'#a5b4fc'}`, boxShadow:'0 4px 16px rgba(0,0,0,0.12)' }),
};

function Toast({ msg, type, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, []);
  return <div style={S.toast(type)}>{msg}</div>;
}

function StatusPill({ status }) {
  if (!status) return <span style={S.pill('gray')}>None</span>;
  const map = { none:'yellow', pending:'yellow', approved:'green', declined:'red', completed:'green' };
  return <span style={S.pill(map[status] || 'gray')}>{status.toUpperCase()}</span>;
}

export default function ProviderDashboard() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState('MEM-10001');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  // Form states
  const [mriForm, setMriForm] = useState({ body_part:'', reason:'', prescribed_by_name:'', prescribed_by_specialty:'Orthopaedic Surgery' });
  const [paForm, setPaForm] = useState({ ordering_doctor:'', procedure:'MRI Scan' });
  const [refForm, setRefForm] = useState({ specialist:'', approved_by:'', reason:'' });
  const [notesForm, setNotesForm] = useState({});   // keyed by booking sig
  const [showMriForm, setShowMriForm] = useState(false);
  const [showPaForm, setShowPaForm] = useState(false);
  const [showRefForm, setShowRefForm] = useState(null);   // booking sig or null
  const [showNotesForm, setShowNotesForm] = useState(null); // booking sig or null

  // Auto-fill MRI form — pre-fill ordering physician from referral/PCP context
  const openMriForm = (booking) => {
    // The specialist who completed the visit is the prescribing doctor
    const prescriber = booking?.provider_name || data?.assigned_pcp?.name || '';
    // Infer specialty from referral context
    const referralSpecialty = data?.referral?.specialist || '';
    const inferSpecialty = (s) => {
      if (!s) return 'Orthopaedic Surgery';
      const sl = s.toLowerCase();
      if (sl.includes('ortho') || sl.includes('knee') || sl.includes('joint')) return 'Orthopaedic Surgery';
      if (sl.includes('neuro')) return 'Neurology';
      if (sl.includes('cardio') || sl.includes('heart')) return 'Cardiology';
      if (sl.includes('radio') || sl.includes('imaging')) return 'Radiology';
      if (sl.includes('gastro')) return 'Gastroenterology';
      if (sl.includes('derma')) return 'Dermatology';
      return 'Orthopaedic Surgery';
    };
    setMriForm({
      body_part: '',
      reason: '',
      prescribed_by_name: prescriber,
      prescribed_by_specialty: inferSpecialty(referralSpecialty),
    });
    setShowMriForm(true);
  };

  // Auto-fill prior auth form from prescription data
  const openPaForm = () => {
    const rx = data?.mri_rx;
    const doc = typeof rx?.prescribed_by === 'object' ? rx?.prescribed_by?.name : rx?.prescribed_by || '';
    setPaForm({
      ordering_doctor: doc,
      procedure: rx?.body_part ? `MRI — ${rx.body_part}` : 'MRI Scan',
    });
    setShowPaForm(true);
  };

  // Open referral form pre-filled with PCP name
  const openRefForm = (bookingSig, booking) => {
    setRefForm({
      specialist: '',
      approved_by: booking?.provider_name || data?.assigned_pcp?.name || '',
      reason: booking?.reason || '',
    });
    setShowRefForm(bookingSig);
  };

  const showToast = (msg, type='success') => setToast({ msg, type });

  const load = useCallback(async (mid) => {
    setLoading(true);
    try {
      const r = await fetch(`/dashboard/member/${mid}`);
      const d = await r.json();
      setData(d);
    } catch { showToast('Failed to load member data', 'error'); }
    setLoading(false);
  }, []);

  useEffect(() => { load(selected); }, [selected]);

  const post = async (url, body) => {
    const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    return r.json();
  };

  // Mark appointment as completed → unlocks Create Referral (PCP) or Write Prescription (specialist)
  const completeAppointment = async (booking, notes='') => {
    const res = await post('/dashboard/provider/complete-appointment', {
      member_id:     selected,
      provider_name: booking.provider_name,
      date:          booking.date,
      time_start:    booking.time_start,
      visit_notes:   notes,
    });
    if (res.success) { showToast('Visit marked as completed ✓'); setShowNotesForm(null); load(selected); }
    else showToast('Could not mark as completed — appointment not found', 'error');
  };

  // PCP creates referral independently after completing the visit
  const createReferral = async (booking) => {
    if (!refForm.specialist || !refForm.approved_by) { showToast('Fill all fields', 'error'); return; }
    const res = await post('/dashboard/provider/create-referral', {
      member_id:   selected,
      specialist:  refForm.specialist,
      approved_by: refForm.approved_by,
      reason:      refForm.reason,
    });
    if (res.success) {
      showToast(`Referral created for ${refForm.specialist} ✓ — member's agent will notify them on next login`);
      setShowRefForm(null);
      load(selected);
    } else showToast('Failed to create referral', 'error');
  };

  const sendMriPrescription = async () => {
    if (!mriForm.body_part || !mriForm.reason || !mriForm.prescribed_by_name) { showToast('Fill all fields', 'error'); return; }
    const res = await post('/dashboard/provider/send-mri-prescription', { member_id: selected, ...mriForm });
    if (res.success) { showToast('Prescription sent ✓'); setShowMriForm(false); load(selected); }
    else showToast('Failed to send prescription', 'error');
  };

  const toggleMriRequired = async (booking, mri_required) => {
    const res = await post('/dashboard/provider/toggle-mri-required', {
      member_id:     selected,
      provider_name: booking.provider_name,
      date:          booking.date,
      time_start:    booking.time_start,
      mri_required,
    });
    if (res.success) {
      showToast(mri_required ? '🔬 MRI Required flagged — agent will notify member on next login' : 'MRI Required flag removed');
      load(selected);
    } else showToast('Failed to update MRI flag', 'error');
  };

  const submitPriorAuth = async () => {
    if (!paForm.ordering_doctor) { showToast('Enter ordering doctor name', 'error'); return; }
    const res = await post('/dashboard/provider/submit-prior-auth', { member_id: selected, ...paForm });
    if (res.success) { showToast(`Prior auth submitted — Ref# ${res.ref} ✓`); setShowPaForm(false); load(selected); }
    else showToast('Failed to submit prior auth', 'error');
  };

  const approveReferral = async () => {
    if (!refForm.specialist || !refForm.approved_by) { showToast('Fill all fields', 'error'); return; }
    const res = await post('/dashboard/provider/approve-referral', { member_id: selected, ...refForm });
    if (res.success) { showToast('Referral approved ✓ — agent will notify member automatically'); setShowRefForm(null); load(selected); }
    else showToast('Failed to approve referral', 'error');
  };

  const acceptPcpAssignment = async () => {
    const res = await post('/dashboard/provider/accept-pcp-assignment', { member_id: selected });
    if (res.success) { showToast('PCP assignment accepted ✓'); load(selected); }
    else showToast('Failed', 'error');
  };

  const mri   = data?.mri_rx;
  const pa    = data?.prior_auth;
  const referral = data?.referral;
  const bookings = data?.bookings || [];
  const pcpChanges = (data?.pcp_changes || []).filter(c => c.status === 'completed' && !c.provider_accepted);
  const notifs = data?.notifications || [];

  // Completed appointments that could have an action (referral for PCP, prescription for specialist)
  const completedBookings = bookings.filter(b => b.status === 'completed');
  const pendingBookings   = bookings.filter(b => b.status !== 'completed');
  const pcpNames = new Set([
    data?.assigned_pcp?.name?.toLowerCase(),
    ...(data?.pcp_changes || []).map(c => c.new_pcp_name?.toLowerCase()),
  ].filter(Boolean));
  const isPCPBooking = (b) => {
    const reason = (b.reason || '').toLowerCase();
    const name   = (b.provider_name || '').toLowerCase();
    return reason.includes('primary care') || reason.includes('pcp') ||
           pcpNames.has(name) || name.includes('family') || name.includes('internal medicine');
  };

  return (
    <div style={S.root}>
      {toast && <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />}

      <header style={S.header}>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          <span style={{ fontSize:20 }}>🏥</span>
          <span style={S.hTitle}>Provider Portal — Medilife Healthcare</span>
        </div>
        <div style={S.hRight}>
          <span style={S.badge}>Provider View</span>
          <button style={S.backBtn} onClick={() => navigate('/')}>← Back to Portal</button>
        </div>
      </header>

      <div style={S.body}>
        <div style={{ marginBottom:20 }}>
          <div style={{ fontSize:22, fontWeight:800, color:'#1e1e5c' }}>Provider Dashboard</div>
          <div style={{ fontSize:13, color:'#64748b', marginTop:4 }}>Manage prescriptions, prior auth submissions, referrals and PCP assignments</div>
        </div>

        <div style={S.grid}>
          {/* Member list */}
          <div style={S.panel}>
            <div style={S.panelH}>👥 Members</div>
            {MEMBERS.map(m => (
              <button key={m.id} style={S.memberBtn(selected === m.id)} onClick={() => setSelected(m.id)}>
                <div style={S.mName}>{m.name}</div>
                <div style={S.mCity}>{m.id} · {m.city}</div>
              </button>
            ))}
          </div>

          {/* Detail panel */}
          <div>
            {loading && <div style={{ textAlign:'center', padding:40, color:'#94a3b8' }}>Loading…</div>}
            {!loading && data && (
              <>
                {/* Member header */}
                <div style={{ ...S.panel, marginBottom:20, padding:'16px 20px' }}>
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                    <div>
                      <div style={{ fontSize:18, fontWeight:800 }}>{data.name}</div>
                      <div style={{ fontSize:12, color:'#64748b', marginTop:2 }}>{data.city} · {data.plan}</div>
                    </div>
                    <div style={{ textAlign:'right' }}>
                      <div style={S.label}>Assigned PCP</div>
                      <div style={{ fontSize:13, fontWeight:600 }}>{data.assigned_pcp?.name || '—'}</div>
                    </div>
                  </div>
                </div>

                {/* ── Appointments booked via Agent ── */}
                <div style={{ ...S.panel, marginBottom:20 }}>
                  <div style={S.panelH}>📅 Appointments <span style={{ fontWeight:400, color:'#94a3b8', fontSize:11, marginLeft:6 }}>booked via member portal</span></div>
                  <div style={{ padding:'12px 18px' }}>
                    {bookings.length === 0 ? (
                      <div style={{ color:'#94a3b8', fontSize:13, padding:'8px 0' }}>No appointments booked yet.</div>
                    ) : (
                      bookings.slice().reverse().map((b, i) => {
                        const sig = `${b.provider_name}|${b.date}|${b.time_start}`;
                        const isCompleted = b.status === 'completed';
                        const isAPC = isPCPBooking(b);   // is this a PCP visit?
                        const hasReferral = referral?.status === 'approved';
                        const hasPrescription = mri?.prescription_mri;

                        return (
                          <div key={i} style={{ ...S.card, marginBottom:12, borderLeft: isCompleted ? '3px solid #16a34a' : '3px solid #e0e7ff' }}>
                            <div style={S.row}>
                              <div>
                                <div style={S.label}>Provider</div>
                                <div style={S.value}>{b.provider_name || '—'}</div>
                              </div>
                              <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                                <span style={S.pill(b.consultation_type === 'Telehealth' ? 'blue' : 'green')}>
                                  {b.consultation_type || 'In-Person'}
                                </span>
                                <span style={S.pill(isCompleted ? 'green' : 'yellow')}>
                                  {isCompleted ? 'COMPLETED' : 'UPCOMING'}
                                </span>
                              </div>
                            </div>
                            <div style={{ marginTop:8, ...S.row }}>
                              <div>
                                <div style={S.label}>Date & Time</div>
                                <div style={S.value}>{b.date || '—'} {b.time_start ? `at ${b.time_start}` : ''}</div>
                              </div>
                              {b.reason && (
                                <div style={{ textAlign:'right' }}>
                                  <div style={S.label}>Reason</div>
                                  <div style={{ fontSize:12, color:'#334155', maxWidth:180, textAlign:'right' }}>{b.reason}</div>
                                </div>
                              )}
                            </div>

                            {b.visit_notes && (
                              <div style={{ marginTop:8 }}>
                                <div style={S.label}>Visit Notes</div>
                                <div style={{ fontSize:12, color:'#334155', background:'#f8faff', borderRadius:6, padding:'6px 10px' }}>{b.visit_notes}</div>
                              </div>
                            )}

                            {/* ── Actions based on appointment status ── */}
                            <div style={{ marginTop:12, display:'flex', flexWrap:'wrap', gap:8 }}>

                              {/* Mark as Completed — only for upcoming appointments */}
                              {!isCompleted && (
                                showNotesForm === sig ? (
                                  <div style={{ width:'100%', background:'#f0f4ff', borderRadius:8, padding:12 }}>
                                    <div style={{ fontSize:12, fontWeight:700, marginBottom:8, color:'#1e1e5c' }}>Visit Notes (optional)</div>
                                    <textarea
                                      style={{ ...S.input, height:70, resize:'vertical' }}
                                      placeholder="e.g. Patient presented with right knee pain. Referred to Orthopaedics for evaluation."
                                      value={notesForm[sig] || ''}
                                      onChange={e => setNotesForm(p => ({...p, [sig]: e.target.value}))}
                                    />
                                    <div style={{ display:'flex', gap:8, marginTop:8 }}>
                                      <button style={S.btn('green')} onClick={() => completeAppointment(b, notesForm[sig] || '')}>
                                        ✓ Confirm Visit Completed
                                      </button>
                                      <button style={S.btn('gray')} onClick={() => setShowNotesForm(null)}>Cancel</button>
                                    </div>
                                  </div>
                                ) : (
                                  <button style={S.btn('blue')} onClick={() => setShowNotesForm(sig)}>
                                    ✓ Mark Visit as Completed
                                  </button>
                                )
                              )}

                              {/* Create Referral — only for completed PCP visits, if no referral yet */}
                              {isCompleted && isAPC && !hasReferral && (
                                showRefForm === sig ? (
                                  <div style={{ width:'100%', background:'#f0f4ff', borderRadius:8, padding:12 }}>
                                    <div style={{ fontSize:12, fontWeight:700, marginBottom:10, color:'#1e1e5c' }}>Create Specialist Referral</div>
                                    <div style={{ marginBottom:8 }}>
                                      <div style={S.label}>Refer to Specialist / Service</div>
                                      <select style={S.select} value={refForm.specialist} onChange={e => setRefForm(p => ({...p, specialist: e.target.value}))}>
                                        <option value=''>— Select Specialty —</option>
                                        {SPECIALTIES.map(s => <option key={s}>{s}</option>)}
                                      </select>
                                    </div>
                                    <div style={{ marginBottom:8 }}>
                                      <div style={S.label}>Referring PCP</div>
                                      <input style={S.input} value={refForm.approved_by}
                                        onChange={e => setRefForm(p => ({...p, approved_by: e.target.value}))}
                                        placeholder="Dr. Name" />
                                    </div>
                                    <div style={{ marginBottom:12 }}>
                                      <div style={S.label}>Clinical Reason</div>
                                      <input style={S.input} value={refForm.reason}
                                        onChange={e => setRefForm(p => ({...p, reason: e.target.value}))}
                                        placeholder="e.g. Persistent right knee pain, suspected meniscus tear" />
                                    </div>
                                    <div style={{ display:'flex', gap:8 }}>
                                      <button style={S.btn('green')} onClick={() => createReferral(b)}>
                                        📋 Create & Send Referral
                                      </button>
                                      <button style={S.btn('gray')} onClick={() => setShowRefForm(null)}>Cancel</button>
                                    </div>
                                  </div>
                                ) : (
                                  <button style={S.btn('green')} onClick={() => openRefForm(sig, b)}>
                                    📋 Create Referral
                                  </button>
                                )
                              )}

                              {/* Referral already created badge */}
                              {isCompleted && isAPC && hasReferral && (
                                <div style={{ padding:'6px 12px', background:'#dcfce7', borderRadius:8, fontSize:12, color:'#166534', fontWeight:600 }}>
                                  ✅ Referral issued → {referral.specialist} (valid through {referral.valid_through})
                                </div>
                              )}

                              {/* Write Prescription — only for completed specialist visits (non-PCP), if no prescription yet */}
                              {isCompleted && !isAPC && !hasPrescription && (
                                <button style={S.btn('blue')} onClick={() => openMriForm(b)}>
                                  ✍️ Write Prescription
                                </button>
                              )}

                              {/* Prescription already written badge */}
                              {isCompleted && !isAPC && hasPrescription && (
                                <div style={{ padding:'6px 12px', background:'#dbeafe', borderRadius:8, fontSize:12, color:'#1d4ed8', fontWeight:600 }}>
                                  📄 Prescription on file — {mri?.body_part}
                                </div>
                              )}

                              {/* MRI Required toggle — only for completed specialist (non-PCP) visits */}
                              {isCompleted && !isAPC && (
                                <button
                                  style={{
                                    ...S.btn(b.mri_required ? 'red' : 'gray'),
                                    background: b.mri_required ? '#7c3aed' : '#e2e8f0',
                                    color: b.mri_required ? '#fff' : '#475569',
                                  }}
                                  onClick={() => toggleMriRequired(b, !b.mri_required)}
                                  title={b.mri_required ? 'Click to remove MRI Required flag' : 'Click to flag that MRI scan is needed'}
                                >
                                  🔬 {b.mri_required ? 'MRI Required ✓' : 'Mark MRI Required'}
                                </button>
                              )}

                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* ── Prescription ── */}
                <div style={S.panel}>
                  <div style={S.panelH}>🩻 Prescription</div>
                  <div style={{ padding:'16px 18px' }}>
                    {mri && mri.prescription_mri ? (
                      <div style={S.card}>
                        <div style={S.row}>
                          <div>
                            <div style={S.label}>Procedure</div>
                            <div style={S.value}>MRI — {mri.body_part || mri.procedure || '—'}</div>
                          </div>
                          <div>
                            <div style={S.label}>Prior Auth</div>
                            <StatusPill status={pa?.status || 'none'} />
                          </div>
                        </div>
                        <div style={{ marginTop:10, ...S.row }}>
                          <div>
                            <div style={S.label}>Ordered by</div>
                            <div style={S.value}>{typeof mri.prescribed_by === 'object' ? mri.prescribed_by.name : mri.prescribed_by}</div>
                          </div>
                          <div>
                            <div style={S.label}>Date</div>
                            <div style={S.value}>{mri.prescribed_date || mri.date || '—'}</div>
                          </div>
                        </div>
                        <div style={{ marginTop:10 }}>
                          <div style={S.label}>Reason</div>
                          <div style={S.value}>{mri.reason || '—'}</div>
                        </div>
                        {(!pa || pa.status === 'none') && (
                          <div style={{ marginTop:14 }}>
                            {!showPaForm ? (
                              <button style={S.btn('blue')} onClick={openPaForm}>
                                📤 Submit Prior Auth to Cigna
                              </button>
                            ) : (
                              <div style={{ background:'#f0f4ff', borderRadius:8, padding:14, marginTop:8 }}>
                                <div style={{ fontSize:12, fontWeight:700, marginBottom:10, color:'#1e1e5c' }}>Submit Prior Authorization</div>
                                <div style={{ marginBottom:8 }}>
                                  <div style={S.label}>Ordering Doctor</div>
                                  <input style={S.input} value={paForm.ordering_doctor} onChange={e => setPaForm(p => ({...p, ordering_doctor: e.target.value}))} placeholder="Dr. Name" />
                                </div>
                                <div style={{ marginBottom:12 }}>
                                  <div style={S.label}>Procedure</div>
                                  <input style={S.input} value={paForm.procedure} onChange={e => setPaForm(p => ({...p, procedure: e.target.value}))} />
                                </div>
                                <div style={{ display:'flex', gap:8 }}>
                                  <button style={S.btn('green')} onClick={submitPriorAuth}>Submit to Cigna</button>
                                  <button style={S.btn('gray')} onClick={() => setShowPaForm(false)}>Cancel</button>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                        {pa?.status === 'pending' && (
                          <div style={{ marginTop:10, padding:'8px 12px', background:'#fef9c3', borderRadius:8, fontSize:12, color:'#854d0e', fontWeight:600 }}>
                            ⏳ Prior auth submitted — awaiting Cigna approval (Ref# {pa.auth_reference_number || '—'})
                          </div>
                        )}
                        {pa?.status === 'approved' && (
                          <div style={{ marginTop:10, padding:'8px 12px', background:'#dcfce7', borderRadius:8, fontSize:12, color:'#166534', fontWeight:600 }}>
                            ✅ Prior auth APPROVED by Cigna — valid through {pa.valid_through}
                          </div>
                        )}
                        {pa?.status === 'declined' && (
                          <div style={{ marginTop:10, padding:'8px 12px', background:'#fee2e2', borderRadius:8, fontSize:12, color:'#991b1b', fontWeight:600 }}>
                            ❌ Prior auth DECLINED by Cigna — {pa.decline_reason}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div>
                        <div style={{ color:'#94a3b8', fontSize:13, marginBottom:14 }}>No prescription on file for this member.</div>
                        {!showMriForm ? (
                          <button style={S.btn('blue')} onClick={openMriForm}>
                            ✍️ Write Prescription
                          </button>
                        ) : (
                          <div style={{ background:'#f0f4ff', borderRadius:10, padding:16 }}>
                            <div style={{ fontSize:13, fontWeight:700, marginBottom:12, color:'#1e1e5c' }}>New Prescription</div>
                            {[
                              { label:'Body Part / Area', key:'body_part', placeholder:'e.g. Right Knee, Lumbar Spine, Left Shoulder' },
                              { label:'Clinical Reason', key:'reason', placeholder:'e.g. Chronic knee pain, suspected meniscus tear' },
                              { label:'Ordering Physician Name', key:'prescribed_by_name', placeholder:'Dr. Full Name' },
                            ].map(f => (
                              <div key={f.key} style={{ marginBottom:10 }}>
                                <div style={S.label}>{f.label}</div>
                                <input style={S.input} value={mriForm[f.key]} onChange={e => setMriForm(p => ({...p, [f.key]: e.target.value}))} placeholder={f.placeholder} />
                              </div>
                            ))}
                            <div style={{ marginBottom:14 }}>
                              <div style={S.label}>Specialty</div>
                              <select style={S.select} value={mriForm.prescribed_by_specialty} onChange={e => setMriForm(p => ({...p, prescribed_by_specialty: e.target.value}))}>
                                {SPECIALTIES.map(s => <option key={s}>{s}</option>)}
                              </select>
                            </div>
                            <div style={{ display:'flex', gap:8 }}>
                              <button style={S.btn('green')} onClick={sendMriPrescription}>Send Prescription</button>
                              <button style={S.btn('gray')} onClick={() => setShowMriForm(false)}>Cancel</button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* ── Referral Status ── */}
                {referral && (
                  <div style={{ ...S.panel, marginTop:20 }}>
                    <div style={S.panelH}>📋 Referral</div>
                    <div style={{ padding:'16px 18px' }}>
                      <div style={S.card}>
                        <div style={S.row}>
                          <div>
                            <div style={S.label}>Specialist</div>
                            <div style={S.value}>{referral.specialist}</div>
                          </div>
                          <StatusPill status={referral.status} />
                        </div>
                        <div style={{ marginTop:8, ...S.row }}>
                          <div>
                            <div style={S.label}>Issued by</div>
                            <div style={S.value}>{referral.approved_by}</div>
                          </div>
                          <div style={{ textAlign:'right' }}>
                            <div style={S.label}>Valid through</div>
                            <div style={S.value}>{referral.valid_through || '—'}</div>
                          </div>
                        </div>
                        {referral.reason && (
                          <div style={{ marginTop:8 }}>
                            <div style={S.label}>Reason</div>
                            <div style={{ fontSize:12, color:'#334155' }}>{referral.reason}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* ── PCP Assignments ── */}
                {pcpChanges.length > 0 && (
                  <div style={{ ...S.panel, marginTop:20 }}>
                    <div style={S.panelH}>👨‍⚕️ Incoming PCP Assignment</div>
                    <div style={{ padding:'16px 18px' }}>
                      {pcpChanges.map((c, i) => (
                        <div key={i} style={S.card}>
                          <div style={S.row}>
                            <div>
                              <div style={S.label}>New Patient</div>
                              <div style={S.value}>{data.name}</div>
                            </div>
                            <div>
                              <div style={S.label}>Assigned PCP</div>
                              <div style={S.value}>{c.new_pcp_name}</div>
                            </div>
                          </div>
                          <div style={{ marginTop:10, ...S.row }}>
                            <div>
                              <div style={S.label}>NPI</div>
                              <div style={S.value}>{c.new_pcp_npi}</div>
                            </div>
                            <div>
                              <div style={S.label}>Approved by Cigna</div>
                              <div style={S.value}>{c.completed_at?.slice(0,10) || '—'}</div>
                            </div>
                          </div>
                          <div style={{ marginTop:12 }}>
                            <button style={S.btn('green')} onClick={acceptPcpAssignment}>✓ Accept Patient</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ── Notifications from Agent ── */}
                {notifs.length > 0 && (
                  <div style={{ ...S.panel, marginTop:20 }}>
                    <div style={S.panelH}>🔔 Notifications from Agent</div>
                    <div style={{ padding:'12px 18px' }}>
                      {notifs.slice().reverse().map((n, i) => (
                        <div key={i} style={{ ...S.card, marginBottom:8 }}>
                          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                            <span style={S.pill(n.notification_type === 'prior_auth_request' ? 'yellow' : n.notification_type === 'follow_up_reminder' ? 'green' : 'blue')}>
                              {n.notification_type?.replace(/_/g,' ').toUpperCase()}
                            </span>
                            <span style={{ fontSize:11, color:'#94a3b8' }}>{n.created_at?.slice(0,10)}</span>
                          </div>
                          <div style={{ fontSize:12, color:'#334155', marginTop:6 }}>{n.message}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
