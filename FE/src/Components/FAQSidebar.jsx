import React from 'react';

const FAQSidebar = ({ faqs, onClose }) => {
  return (
    <div style={{ position: 'fixed', right: 0, top: 0, width: '300px', height: '100%', background: 'white', borderLeft: '1px solid #ccc', padding: '20px' }}>
      <button onClick={onClose}>Close</button>
      <h3>FAQs</h3>
      <ul>
        {faqs.map((faq, index) => (
          <li key={index}>
            <strong>{faq.question}</strong>
            <p>{faq.answer}</p>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FAQSidebar;