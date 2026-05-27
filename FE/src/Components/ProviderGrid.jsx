// import React, { useState } from 'react';
// import { FaHospital, FaVideo, FaPhone, FaIdCard } from 'react-icons/fa';
// import { FaLocationDot, FaCircleCheck, FaCircleXmark } from 'react-icons/fa6';
// import { MdLocalHospital } from 'react-icons/md';
// import ProviderModal from './ProviderModal';

// function ConsultationBadge({ mode }) {
//   if (mode === 'In-Person') return <span className="consult-badge consult-inperson"><MdLocalHospital size={13} /> In-Person</span>;
//   if (mode === 'Telehealth') return <span className="consult-badge consult-telehealth"><FaVideo size={12} /> Telehealth</span>;
//   if (mode === 'Both') return (
//     <span className="consult-badge-group">
//       <span className="consult-badge consult-inperson"><MdLocalHospital size={13} /> In-Person</span>
//       <span className="consult-badge consult-telehealth"><FaVideo size={12} /> Telehealth</span>
//     </span>
//   );
//   return null;
// }

// function NetworkBadge({ status, tier }) {
//   if (status === 'in-network') return (
//     <span className="badge badge-in-network"><FaCircleCheck size={11} /> In-Network{tier ? ` · ${tier}` : ''}</span>
//   );
//   return <span className="badge badge-out-of-network"><FaCircleXmark size={11} /> Out-of-Network</span>;
// }

// function ProviderCard({ provider, index, onClick }) {
//   return (
//     <div className={`provider-card ${provider.status}`} onClick={() => onClick(provider)} style={{ cursor: 'pointer' }}>
//       <div className="provider-card-top">
//         <div className="provider-index">{index + 1}</div>
//         <div className="provider-card-info">
//           <div className="provider-card-title">{provider.name}</div>
//           {provider.specialty && <div className="provider-card-specialty">{provider.specialty}</div>}
//         </div>
//         <NetworkBadge status={provider.status} tier={provider.tier} />
//       </div>
//       <div className="provider-card-details">
//         {(provider.distance || provider.address) && (
//   <div className="provider-detail-row">
//     <FaLocationDot size={13} className="detail-icon" />
//     <span>
//       {provider.address}
//       {provider.distance ? ` (${provider.distance})` : ''}</span>
//           </div>
//         )}
//         {provider.phone && (
//           <div className="provider-detail-row">
//             <FaPhone size={12} className="detail-icon" />
//             <a href={`tel:${provider.phone}`} className="provider-phone" onClick={e => e.stopPropagation()}>{provider.phone}</a>
//           </div>
//         )}
//         {provider.npi && (
//           <div className="provider-detail-row">
//             <FaIdCard size={13} className="detail-icon" />
//             <span className="provider-npi">NPI: {provider.npi}</span>
//           </div>
//         )}
//         {provider.consultation && (
//           <div className="provider-detail-row">
//             <ConsultationBadge mode={provider.consultation} />
//           </div>
//         )}
//       </div>
//       <div className="pm-card-hint">Click to book →</div>
//     </div>
//   );
// }

// export default function ProviderGrid({ providers, onBook }) {
//   const [activeProvider, setActiveProvider] = useState(null);

//   if (!providers || providers.length === 0) return null;

//   const inNetwork = providers.filter(p => p.status === 'in-network');
//   const outOfNetwork = providers.filter(p => p.status === 'out-of-network');

//   return (
//     <>
//       <div className="provider-results-wrap">
//         {inNetwork.length > 0 && (
//           <div className="provider-section">
//             <div className="provider-section-label in-network-label">
//               <FaCircleCheck size={12} /> In-Network ({inNetwork.length})
//             </div>
//             <div className="provider-grid">
//               {inNetwork.map((p, i) => (
//                 <ProviderCard key={p.npi || i} provider={p} index={i} onClick={setActiveProvider} />
//               ))}
//             </div>
//           </div>
//         )}
//         {outOfNetwork.length > 0 && (
//           <div className="provider-section">
//             <div className="provider-section-label out-of-network-label">
//               <FaCircleXmark size={12} /> Out-of-Network ({outOfNetwork.length})
//             </div>
//             <div className="provider-grid">
//               {outOfNetwork.map((p, i) => (
//                 <ProviderCard key={p.npi || i} provider={p} index={inNetwork.length + i} onClick={setActiveProvider} />
//               ))}
//             </div>
//           </div>
//         )}
//       </div>

//       {activeProvider && (
//         <ProviderModal
//           provider={activeProvider}
//           onClose={() => setActiveProvider(null)}
//           onBook={(msg) => { if (onBook) onBook(msg); }}
//         />
//       )}
//     </>
//   );
// }














// import React, { useState } from 'react';
// import { FaVideo, FaPhone, FaIdCard } from 'react-icons/fa';
// import { FaLocationDot, FaCircleCheck, FaCircleXmark } from 'react-icons/fa6';
// import { MdLocalHospital } from 'react-icons/md';
// import ProviderModal from './ProviderModal';

// const INITIAL_VISIBLE = 1;

// function ConsultationBadge({ mode }) {
//   if (mode === 'In-Person') return <span className="consult-badge consult-inperson"><MdLocalHospital size={13} /> In-Person</span>;
//   if (mode === 'Telehealth') return <span className="consult-badge consult-telehealth"><FaVideo size={12} /> Telehealth</span>;
//   if (mode === 'Both') return (
//     <span className="consult-badge-group">
//       <span className="consult-badge consult-inperson"><MdLocalHospital size={13} /> In-Person</span>
//       <span className="consult-badge consult-telehealth"><FaVideo size={12} /> Telehealth</span>
//     </span>
//   );
//   return null;
// }

// function NetworkBadge({ status }) {
//   if (status === 'in-network') return (
//     <span className="badge badge-in-network"><FaCircleCheck size={11} /> In-Network</span>
//   );
//   return <span className="badge badge-out-of-network"><FaCircleXmark size={11} /> Out-of-Network</span>;
// }

// function ProviderCard({ provider, index, onClick }) {
//   return (
//     <div className={`provider-card ${provider.status}`} onClick={() => onClick(provider)} style={{ cursor: 'pointer' }}>
//       <div className="provider-card-top">
//         <div className="provider-index">{index + 1}</div>
//         <div className="provider-card-info">
//           <div className="provider-card-title">{provider.name}</div>
//           {provider.specialty && <div className="provider-card-specialty">{provider.specialty}</div>}
//         </div>
//         <NetworkBadge status={provider.status} />
//       </div>
//       <div className="provider-card-details">
//         {(provider.distance || provider.address) && (
//           <div className="provider-detail-row">
//             <FaLocationDot size={13} className="detail-icon" />
//             <span>{provider.address}{provider.distance ? ` (${provider.distance})` : ''}</span>
//           </div>
//         )}
//         {provider.phone && (
//           <div className="provider-detail-row">
//             <FaPhone size={12} className="detail-icon" />
//             <a href={`tel:${provider.phone}`} className="provider-phone" onClick={e => e.stopPropagation()}>{provider.phone}</a>
//           </div>
//         )}
//         {provider.npi && (
//           <div className="provider-detail-row">
//             <FaIdCard size={13} className="detail-icon" />
//             <span className="provider-npi">NPI: {provider.npi}</span>
//           </div>
//         )}
//         {provider.consultation && (
//           <div className="provider-detail-row">
//             <ConsultationBadge mode={provider.consultation} />
//           </div>
//         )}
//       </div>
//       <div className="pm-card-hint">Click to book →</div>
//     </div>
//   );
// }

// export default function ProviderGrid({ providers, onBook }) {
//   const [activeProvider, setActiveProvider] = useState(null);
//   const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE);

//   if (!providers || providers.length === 0) return null;

//   // In-network first, then out-of-network
//   const inNetwork = providers.filter(p => p.status === 'in-network');
//   const outOfNetwork = providers.filter(p => p.status === 'out-of-network');
//   const allProviders = [...inNetwork, ...outOfNetwork];

//   const visible = allProviders.slice(0, visibleCount);
//   const hiddenCount = allProviders.length - visibleCount;
//   const showingAll = visibleCount >= allProviders.length;

//   const visibleInNetwork = visible.filter(p => p.status === 'in-network');
//   const visibleOutOfNetwork = visible.filter(p => p.status === 'out-of-network');

//   return (
//     <>
//       <div className="provider-results-wrap">
//         {visibleInNetwork.length > 0 && (
//           <div className="provider-section">
//             <div className="provider-section-label in-network-label">
//               <FaCircleCheck size={12} /> In-Network ({inNetwork.length})
//             </div>
//             <div className="provider-grid">
//               {visibleInNetwork.map((p, i) => (
//                 <ProviderCard key={p.npi || i} provider={p} index={i} onClick={setActiveProvider} />
//               ))}
//             </div>
//           </div>
//         )}

//         {visibleOutOfNetwork.length > 0 && (
//           <div className="provider-section">
//             <div className="provider-section-label out-of-network-label">
//               <FaCircleXmark size={12} /> Out-of-Network ({outOfNetwork.length})
//             </div>
//             <div className="provider-grid">
//               {visibleOutOfNetwork.map((p, i) => (
//                 <ProviderCard key={p.npi || i} provider={p} index={visibleInNetwork.length + i} onClick={setActiveProvider} />
//               ))}
//             </div>
//           </div>
//         )}

//         {!showingAll && (
//           <button className="show-more-btn" onClick={() => setVisibleCount(allProviders.length)}>
//             Show {hiddenCount} more doctor{hiddenCount !== 1 ? 's' : ''} ↓
//           </button>
//         )}

//         {showingAll && allProviders.length > INITIAL_VISIBLE && (
//           <button className="show-more-btn show-less-btn" onClick={() => setVisibleCount(INITIAL_VISIBLE)}>
//             Show less ↑
//           </button>
//         )}
//       </div>

//       {activeProvider && (
//         <ProviderModal
//           provider={activeProvider}
//           onClose={() => setActiveProvider(null)}
//           onBook={(backendMsg, displayMsg) => {
//             if (onBook) onBook(backendMsg, displayMsg);
//           }}
//         />
//       )}
//     </>
//   );
// }





import React, { useState } from 'react';
import { FaPhone, FaIdCard } from 'react-icons/fa';
import { FaLocationDot, FaCircleCheck, FaCircleXmark, FaMars, FaVenus } from 'react-icons/fa6';
import ProviderModal from './ProviderModal';

const INITIAL_VISIBLE = 3;

function StarRating({ rating }) {
  if (!rating) return null;
  const full = Math.floor(rating);
  const half = rating - full >= 0.25 && rating - full < 0.75;
  const empty = 5 - full - (half ? 1 : 0);
  return (
    <span style={{ fontSize: 11, color: '#f59e0b', letterSpacing: 1 }}>
      {'★'.repeat(full)}{half ? '½' : ''}{'☆'.repeat(empty)}
      <span style={{ color: '#64748b', marginLeft: 3, fontWeight: 600 }}>{rating.toFixed(1)}</span>
    </span>
  );
}


function NetworkBadge({ status }) {
  if (status === 'in-network') return (
    <span className="badge badge-in-network"><FaCircleCheck size={11} /> In-Network</span>
  );
  return <span className="badge badge-out-of-network"><FaCircleXmark size={11} /> Out-of-Network</span>;
}

function ProviderCard({ provider, index, onClick, mriState }) {
  const genderIcon = provider.gender === 'F'
    ? <FaVenus size={15} style={{ color: '#db2777' }} />
    : provider.gender === 'M'
    ? <FaMars size={15} style={{ color: '#2563eb' }} />
    : null;

  // Lock booking ONLY for imaging/radiology providers when prior auth is pending/missing.
  // Regular specialists (ortho, cardiology, etc.) should never be locked by mriState.
  const IMAGING_SPECIALTIES = ['radiology', 'diagnostic radiology', 'imaging', 'nuclear medicine', 'mri', 'ct'];
  const provSpecialty = (provider.specialty || '').toLowerCase();
  const provName      = (provider.name || '').toLowerCase();
  const isImagingProvider = IMAGING_SPECIALTIES.some(kw => provSpecialty.includes(kw) || provName.includes(kw));
  const bookingBlocked = isImagingProvider && (mriState === 'prior_auth_pending' || mriState === 'prior_auth_none');
  const blockLabel = mriState === 'prior_auth_pending'
    ? '🔒 Insurance sign-off pending — booking locked until approved'
    : mriState === 'prior_auth_none'
    ? '🔒 Insurance sign-off needed before booking'
    : null;

  return (
    <div className={`provider-card ${provider.status}`}>
      <div className="provider-card-top">
        <div className="provider-index">{index + 1}</div>
        <div className="provider-card-info">
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div className="provider-card-title">{provider.name}</div>
            {genderIcon}
          </div>
          {provider.specialty && <div className="provider-card-specialty">{provider.specialty}</div>}
          {provider.rating && <StarRating rating={provider.rating} />}
        </div>
        <NetworkBadge status={provider.status} />
      </div>
      <div className="provider-card-details">
        {(provider.distance || provider.address) && (
          <div className="provider-detail-row">
            <FaLocationDot size={13} className="detail-icon" />
            <span>{provider.address}{provider.distance ? ` (${provider.distance})` : ''}</span>
          </div>
        )}
        {provider.phone && (
          <div className="provider-detail-row">
            <FaPhone size={12} className="detail-icon" />
            <a href={`tel:${provider.phone}`} className="provider-phone" onClick={e => e.stopPropagation()}>{provider.phone}</a>
          </div>
        )}
        {provider.npi && (
          <div className="provider-detail-row">
            <FaIdCard size={13} className="detail-icon" />
            <span className="provider-npi">NPI: {provider.npi}</span>
          </div>
        )}
        {provider.languages && (
          <div className="provider-detail-row">
            <span style={{ fontSize: 12, flexShrink: 0 }}>🌐</span>
            <span style={{ fontSize: 12, color: '#334155' }}>{provider.languages}</span>
          </div>
        )}
        {provider.consultation && (
          <div className="provider-detail-row">
            <span style={{ fontSize: 12, flexShrink: 0 }}>🏥</span>
            <span style={{ fontSize: 12, color: '#334155' }}>{provider.consultation.replace(/&amp;/g, '&')}</span>
          </div>
        )}
      </div>

      {provider.llm_reasoning && (
        <div style={{
          background: '#f0fdf4', border: '1px solid #86efac',
          borderRadius: 8, padding: '8px 12px', marginTop: 8, fontSize: 12
        }}>
          <strong>🤖 Why chosen:</strong> {provider.llm_reasoning}
        </div>
      )}

      {provider.tradeoff && provider.tradeoff !== 'No significant tradeoff' && (
        <div style={{
          background: '#fef3c7', border: '1px solid #fcd34d',
          borderRadius: 8, padding: '8px 12px', marginTop: 4, fontSize: 11,
          color: '#92400e'
        }}>
          <strong>⚖️ Tradeoff:</strong> {provider.tradeoff}
        </div>
      )}

      {provider.critic_note && (
        <div style={{
          background: '#eff6ff', border: '1px solid #bfdbfe',
          borderRadius: 8, padding: '8px 12px', marginTop: 4, fontSize: 11,
          color: '#1e40af'
        }}>
          <strong>✅ Verified:</strong> {provider.critic_note}
        </div>
      )}

      {provider.rejected_others?.length > 0 && (
        <details style={{ marginTop: 6 }}>
          <summary style={{ fontSize: 11, color: '#64748b', cursor: 'pointer' }}>
            Also considered ({provider.rejected_others.length} others)
          </summary>
          {provider.rejected_others.map((r, i) => (
            <div key={i} style={{ fontSize: 11, color: '#94a3b8', padding: '2px 0' }}>
              ✗ {r.name} — {r.rejection_reason}
            </div>
          ))}
        </details>
      )}

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 10 }}>
        {bookingBlocked ? (
          <div style={{
            padding: '8px 14px',
            borderRadius: 20,
            border: '1.5px solid #f59e0b',
            background: '#fef3c7',
            color: '#92400e',
            fontSize: 12,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            {blockLabel}
          </div>
        ) : (
          <button
            onClick={(e) => { e.stopPropagation(); onClick(provider); }}
            style={{
              padding: '7px 22px',
              borderRadius: 20,
              border: '1.5px solid #2D308D',
              background: '#2D308D',
              color: '#fff',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'background 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#1a1a6e'}
            onMouseLeave={e => e.currentTarget.style.background = '#2D308D'}
          >
            Click to Book
          </button>
        )}
      </div>
    </div>
  );
}

export default function ProviderGrid({ providers, onBook, rankedList, onQuickSelect, priorAuthPending, mriState }) {
  const [activeProvider, setActiveProvider] = useState(null);
  const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE);
  const bookingBlocked = mriState === 'prior_auth_pending' || priorAuthPending;

  if (!providers || providers.length === 0) return null;

  const inNetwork = providers.filter(p => p.status === 'in-network');
  const outOfNetwork = providers.filter(p => p.status === 'out-of-network');
  const allProviders = [...inNetwork, ...outOfNetwork];
  const visible = allProviders.slice(0, visibleCount);
  const hiddenCount = allProviders.length - visibleCount;
  const showingAll = visibleCount >= allProviders.length;
  const visibleInNetwork = visible.filter(p => p.status === 'in-network');
  const visibleOutOfNetwork = visible.filter(p => p.status === 'out-of-network');

  return (
    <>
      <div className="provider-results-wrap">
        {visibleInNetwork.length > 0 && (
          <div className="provider-section">
            <div className="provider-section-label in-network-label">
              <FaCircleCheck size={12} /> In-Network
            </div>
            <div className="provider-grid">
              {visibleInNetwork.map((p, i) => (
                <ProviderCard key={p.npi || i} provider={p} index={i} onClick={setActiveProvider} mriState={mriState} />
              ))}
            </div>
          </div>
        )}
        {visibleOutOfNetwork.length > 0 && (
          <div className="provider-section">
            <div className="provider-section-label out-of-network-label">
              <FaCircleXmark size={12} /> Out-of-Network
            </div>
            <div className="provider-grid">
              {visibleOutOfNetwork.map((p, i) => (
                <ProviderCard key={p.npi || i} provider={p} index={visibleInNetwork.length + i} onClick={setActiveProvider} mriState={mriState} />
              ))}
            </div>
          </div>
        )}
        {!showingAll && (
          <button className="show-more-btn" onClick={() => setVisibleCount(allProviders.length)}>
            Show {hiddenCount} more doctor{hiddenCount !== 1 ? 's' : ''} ↓
          </button>
        )}
        {showingAll && allProviders.length > INITIAL_VISIBLE && (
          <button className="show-more-btn show-less-btn" onClick={() => setVisibleCount(INITIAL_VISIBLE)}>
            Show less ↑
          </button>
        )}

        {rankedList?.length >= 3 && onQuickSelect && (
          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            <button
              onClick={() => onQuickSelect('Show me the best overall option')}
              style={{ padding: '6px 12px', borderRadius: 16, border: '1.5px solid #2D308D', background: '#fff', color: '#2D308D', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
            >⭐ Best Overall</button>
            <button
              onClick={() => onQuickSelect('Show me the fastest available option')}
              style={{ padding: '6px 12px', borderRadius: 16, border: '1.5px solid #7c3aed', background: '#fff', color: '#7c3aed', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
            >⚡ Fastest</button>
            <button
              onClick={() => onQuickSelect('Show me the closest option')}
              style={{ padding: '6px 12px', borderRadius: 16, border: '1.5px solid #0891b2', background: '#fff', color: '#0891b2', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
            >📍 Closest</button>
          </div>
        )}
      </div>

      {!bookingBlocked && activeProvider && (
        <ProviderModal
          provider={activeProvider}
          defaultDate={activeProvider._agentDate || null}
          onClose={() => setActiveProvider(null)}
          onBook={(backendMsg, displayMsg) => { if (onBook) onBook(backendMsg, displayMsg); }}
        />
      )}
    </>
  );
}
