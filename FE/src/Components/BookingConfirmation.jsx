import React from 'react';
import { FaCircleCheck } from 'react-icons/fa6';
import { FaEnvelope, FaUser, FaCalendarDay, FaClock, FaVideo, FaMapMarkerAlt, FaStickyNote } from 'react-icons/fa';
import { MdLocalHospital } from 'react-icons/md';

export default function BookingConfirmation({ booking }) {
  if (!booking) return null;

  return (
    <div className="booking-card">
      <div className="booking-card-header">
        <FaCircleCheck size={18} style={{ color: '#16a34a', flexShrink: 0 }} />
        <span>Appointment Confirmed!</span>
      </div>
      <div className="booking-card-body">
        {booking.provider && (
          <div className="booking-row">
            <FaUser size={12} style={{ color: '#64748b', flexShrink: 0 }} />
            <span className="booking-label">Provider</span>
            <span className="booking-value">{booking.provider}</span>
          </div>
        )}
        {booking.date && (
          <div className="booking-row">
            <FaCalendarDay size={12} style={{ color: '#64748b', flexShrink: 0 }} />
            <span className="booking-label">Date</span>
            <span className="booking-value">{booking.date}</span>
          </div>
        )}
        {booking.time && (
          <div className="booking-row">
            <FaClock size={12} style={{ color: '#64748b', flexShrink: 0 }} />
            <span className="booking-label">Time</span>
            <span className="booking-value">{booking.time}</span>
          </div>
        )}
        {booking.consultation_type && (
          <div className="booking-row">
            {booking.consultation_type === 'Telehealth'
              ? <FaVideo size={12} style={{ color: '#64748b', flexShrink: 0 }} />
              : <MdLocalHospital size={13} style={{ color: '#64748b', flexShrink: 0 }} />}
            <span className="booking-label">Mode</span>
            <span className="booking-value">{booking.consultation_type}</span>
          </div>
        )}
        {booking.address && (
          <div className="booking-row">
            <FaMapMarkerAlt size={12} style={{ color: '#64748b', flexShrink: 0 }} />
            <span className="booking-label">Address</span>
            <span className="booking-value">{booking.address}</span>
          </div>
        )}
        {booking.telehealth_link && (
          <div className="booking-row">
            <FaVideo size={12} style={{ color: '#64748b', flexShrink: 0 }} />
            <span className="booking-label">Meeting Link</span>
            <span className="booking-value">
              <a href={booking.telehealth_link} target="_blank" rel="noreferrer"
                style={{ color: '#2D308D', fontWeight: 600, wordBreak: 'break-all' }}>
                {booking.telehealth_link}
              </a>
            </span>
          </div>
        )}
        {booking.timezone_note && (
          <div className="booking-row">
            <FaStickyNote size={12} style={{ color: '#64748b', flexShrink: 0 }} />
            <span className="booking-label">Note</span>
            <span className="booking-value" style={{ color: '#64748b', fontSize: 12 }}>{booking.timezone_note}</span>
          </div>
        )}
      </div>
      <div className="booking-card-footer">
        <FaEnvelope size={12} style={{ marginRight: 6, verticalAlign: 'middle', flexShrink: 0 }} />
        {booking.telehealth_link
          ? 'Confirmation noted. Join via the meeting link above.'
          : 'Confirmation noted. Please arrive 15 minutes early.'}
      </div>
    </div>
  );
}
