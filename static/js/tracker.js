function logEvent(eventType, details) {
  fetch('/api/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_type: eventType,
      event_details: details,
      timestamp: new Date().toISOString()
    })
  }).catch(err => console.warn('log failed', err));
}

// Page view — fires once per page load
window.addEventListener('load', () => {
  logEvent('page_view', { page_id: document.body.dataset.pageId || window.location.pathname });
});

// Click tracking — any element with data-track
document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-track]');
  if (el) {
    logEvent('click', { element_id: el.id || el.dataset.track, element_type: el.tagName });
  }
});

// YouTube video tracking is handled via the IFrame API in lesson.html.
