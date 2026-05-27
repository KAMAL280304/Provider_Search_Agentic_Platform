import React, { useState } from 'react';
import { FaRegCalendarAlt, FaVideo } from 'react-icons/fa';
import { FaCircleCheck } from 'react-icons/fa6';
import { MdLocalHospital } from 'react-icons/md';

export default function AppointmentSlots({ slots, onSelect, preferredMode, providerName }) {
  // selected stores { time, groupLabel } so each group tracks selection independently
  const [selected, setSelected] = useState(null);

  if (!slots || slots.length === 0) return null;

  const handleSelect = (slot, groupLabel) => {
    const time = typeof slot === 'string' ? slot : slot.time;
    setSelected({ time, groupLabel });
    // Send time with consultation type so backend knows which was chosen
    onSelect(`${time} ${groupLabel}`);
  };

  // Normalise: slots may be plain strings (legacy) or { time, type, booked } objects
  const normalised = slots.map(s =>
    typeof s === 'string' ? { time: s, type: null, booked: false } : s
  );

  const inPerson   = normalised.filter(s => s.type === 'In-Person' || s.type === 'Both');
  const telehealth = normalised.filter(s => s.type === 'Telehealth' || s.type === 'Both');
  const untyped    = normalised.filter(s => !s.type);

  // Decide which groups to show based on preferredMode from agent context
  // preferredMode: 'In-Person' | 'Telehealth' | 'Both' | null
  const showInPerson   = preferredMode === 'Telehealth' ? false : inPerson.length > 0;
  const showTelehealth = preferredMode === 'In-Person'  ? false : telehealth.length > 0;
  const hasGroups = inPerson.length > 0 || telehealth.length > 0;

  const renderGroup = (groupSlots, label, icon, color) => {
    if (!groupSlots.length) return null;
    const groupSelected = selected?.groupLabel === label ? selected.time : null;
    return (
      <div style={{ marginBottom: 10 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color, marginBottom: 5, display: 'flex', alignItems: 'center', gap: 5 }}>
          {icon} {label}
        </div>
        <div className="slots-grid">
          {groupSlots.map((s, i) => (
            <button
              key={i}
              className={`slot-btn ${groupSelected === s.time ? 'slot-selected' : ''}`}
              onClick={() => !s.booked && !selected && handleSelect(s, label)}
              disabled={s.booked || !!selected}
              style={s.booked ? { opacity: 0.4, cursor: 'not-allowed', textDecoration: 'line-through' } : {}}
            >
              {s.time}
            </button>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="slots-wrap">
      <div className="slots-header">
        <FaRegCalendarAlt size={14} style={{ marginRight: '7px', verticalAlign: 'middle' }} />
        Available Appointment Slots
      </div>
      {providerName && (
        <div style={{ fontSize: 13, fontWeight: 600, color: '#1a2f5a', marginBottom: 8, paddingLeft: 2 }}>
          🏥 {providerName}
        </div>
      )}

      {hasGroups ? (
        <>
          {showInPerson   && renderGroup(inPerson,   'In-Person',  <MdLocalHospital size={13} />, '#1d4ed8')}
          {showTelehealth && renderGroup(telehealth, 'Telehealth', <FaVideo size={12} />,         '#0891b2')}
          {/* Fallback: if preferredMode filtered out everything, show both */}
          {!showInPerson && !showTelehealth && (
            <>
              {renderGroup(inPerson,   'In-Person',  <MdLocalHospital size={13} />, '#1d4ed8')}
              {renderGroup(telehealth, 'Telehealth', <FaVideo size={12} />,         '#0891b2')}
            </>
          )}
        </>
      ) : (
        <div className="slots-grid">
          {untyped.map((s, i) => (
            <button
              key={i}
              className={`slot-btn ${selected?.time === s.time && !selected?.groupLabel ? 'slot-selected' : ''}`}
              onClick={() => !selected && handleSelect(s, '')}
              disabled={!!selected}
            >
              {s.time}
            </button>
          ))}
        </div>
      )}

      {selected && (
        <div className="slot-confirm-note">
          <FaCircleCheck size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
          You selected <strong>{selected.time}</strong>{selected.groupLabel ? ` (${selected.groupLabel})` : ''} — confirming…
        </div>
      )}
    </div>
  );
}
