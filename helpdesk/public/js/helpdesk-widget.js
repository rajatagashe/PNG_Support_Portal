/**
 * Frappe Helpdesk Embeddable Customer Support Widget
 * Lightweight vanilla JavaScript launcher & interactive modal
 */
(function () {
  'use strict';

  var config = window.HelpdeskWidgetConfig || {};
  var apiHost = config.apiHost || window.location.origin;
  var primaryColor = config.primaryColor || '#ea580c';
  var secondaryColor = config.secondaryColor || '#fed7aa';
  var title = config.title || 'Support Helpdesk';

  // Inject Widget Styles
  var style = document.createElement('style');
  style.innerHTML = `
    #hd-widget-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background-color: ${primaryColor};
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(234, 88, 12, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 999999;
      transition: transform 0.2s, background-color 0.2s;
    }
    #hd-widget-launcher:hover {
      transform: scale(1.08);
      background-color: #c2410c;
    }
    #hd-widget-container {
      position: fixed;
      bottom: 92px;
      right: 24px;
      width: 360px;
      max-width: calc(100vw - 32px);
      height: 520px;
      max-height: calc(100vh - 120px);
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.16);
      display: none;
      flex-direction: column;
      overflow: hidden;
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      border: 1px solid #fed7aa;
    }
    #hd-widget-header {
      background-color: ${primaryColor};
      color: #ffffff;
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    #hd-widget-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }
    #hd-widget-close {
      cursor: pointer;
      font-size: 20px;
      line-height: 1;
    }
    #hd-widget-tabs {
      display: flex;
      background: #fffaf5;
      border-bottom: 1px solid #fed7aa;
    }
    .hd-widget-tab {
      flex: 1;
      padding: 10px;
      text-align: center;
      font-size: 13px;
      font-weight: 500;
      color: #7c2d12;
      cursor: pointer;
      border-bottom: 2px solid transparent;
    }
    .hd-widget-tab.active {
      color: ${primaryColor};
      border-bottom-color: ${primaryColor};
      background: #ffffff;
    }
    #hd-widget-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }
    .hd-form-group {
      margin-bottom: 12px;
    }
    .hd-form-group label {
      display: block;
      font-size: 12px;
      color: #4b5563;
      margin-bottom: 4px;
      font-weight: 500;
    }
    .hd-form-control {
      width: 100%;
      box-sizing: border-box;
      padding: 8px 10px;
      border: 1px solid #fed7aa;
      border-radius: 6px;
      font-size: 13px;
      outline: none;
    }
    .hd-form-control:focus {
      border-color: ${primaryColor};
      box-shadow: 0 0 0 2px ${secondaryColor};
    }
    .hd-btn-submit {
      width: 100%;
      background-color: ${primaryColor};
      color: #ffffff;
      border: none;
      padding: 10px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 14px;
      cursor: pointer;
      transition: background-color 0.2s;
    }
    .hd-btn-submit:hover {
      background-color: #c2410c;
    }
    .hd-search-item {
      padding: 10px;
      border-bottom: 1px solid #f3f4f6;
      cursor: pointer;
    }
    .hd-search-item:hover {
      background: #fffaf5;
    }
    .hd-search-title {
      font-size: 13px;
      font-weight: 600;
      color: #1f2937;
    }
    .hd-search-excerpt {
      font-size: 12px;
      color: #6b7280;
      margin-top: 2px;
    }
  `;
  document.head.appendChild(style);

  // Build DOM Structure
  var launcher = document.createElement('div');
  launcher.id = 'hd-widget-launcher';
  launcher.innerHTML = `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
  `;

  var container = document.createElement('div');
  container.id = 'hd-widget-container';
  container.innerHTML = `
    <div id="hd-widget-header">
      <h3 id="hd-widget-title">${title}</h3>
      <span id="hd-widget-close">&times;</span>
    </div>
    <div id="hd-widget-tabs">
      <div class="hd-widget-tab active" data-tab="help">Search Help</div>
      <div class="hd-widget-tab" data-tab="ticket">New Ticket</div>
    </div>
    <div id="hd-widget-body">
      <!-- Search Help Panel -->
      <div id="hd-panel-help">
        <input type="text" id="hd-search-input" class="hd-form-control" placeholder="Search knowledge base articles..." style="margin-bottom: 12px;" />
        <div id="hd-search-results">
          <p style="font-size: 13px; color: #6b7280; text-align: center; margin-top: 32px;">Type a keyword above to find instant answers.</p>
        </div>
      </div>

      <!-- Ticket Panel -->
      <div id="hd-panel-ticket" style="display: none;">
        <form id="hd-ticket-form">
          <div class="hd-form-group">
            <label>Your Email *</label>
            <input type="email" id="hd-input-email" class="hd-form-control" required placeholder="you@company.com" />
          </div>
          <div class="hd-form-group">
            <label>Your Name</label>
            <input type="text" id="hd-input-name" class="hd-form-control" placeholder="Full Name" />
          </div>
          <div class="hd-form-group">
            <label>Subject *</label>
            <input type="text" id="hd-input-subject" class="hd-form-control" required placeholder="Brief summary of query" />
          </div>
          <div class="hd-form-group">
            <label>Description *</label>
            <textarea id="hd-input-desc" class="hd-form-control" rows="4" required placeholder="Provide details..."></textarea>
          </div>
          <button type="submit" class="hd-btn-submit" id="hd-submit-btn">Send Query</button>
          <div id="hd-form-status" style="margin-top: 10px; font-size: 13px; text-align: center;"></div>
        </form>
      </div>
    </div>
  `;

  document.body.appendChild(launcher);
  document.body.appendChild(container);

  // Interactive Handlers
  launcher.addEventListener('click', function () {
    container.style.display = container.style.display === 'flex' ? 'none' : 'flex';
  });

  document.getElementById('hd-widget-close').addEventListener('click', function () {
    container.style.display = 'none';
  });

  // Tab Switching
  var tabs = container.querySelectorAll('.hd-widget-tab');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');
      var target = tab.getAttribute('data-tab');
      document.getElementById('hd-panel-help').style.display = target === 'help' ? 'block' : 'none';
      document.getElementById('hd-panel-ticket').style.display = target === 'ticket' ? 'block' : 'none';
    });
  });

  // Live Article Search
  var searchInput = document.getElementById('hd-search-input');
  var searchTimeout = null;
  searchInput.addEventListener('input', function () {
    clearTimeout(searchTimeout);
    var query = searchInput.value.trim();
    if (query.length < 2) {
      document.getElementById('hd-search-results').innerHTML = '<p style="font-size: 13px; color: #6b7280; text-align: center; margin-top: 32px;">Type a keyword above to find instant answers.</p>';
      return;
    }

    searchTimeout = setTimeout(function () {
      fetch(`${apiHost}/api/method/helpdesk.api.widget.search_widget_articles?query=${encodeURIComponent(query)}`)
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var articles = data.message || [];
          var container = document.getElementById('hd-search-results');
          if (articles.length === 0) {
            container.innerHTML = '<p style="font-size: 13px; color: #6b7280; text-align: center; margin-top: 32px;">No matching articles found.</p>';
            return;
          }
          container.innerHTML = articles.map(function (a) {
            return `<div class="hd-search-item">
              <div class="hd-search-title">${a.title}</div>
              <div class="hd-search-excerpt">${a.excerpt || ''}</div>
            </div>`;
          }).join('');
        })
        .catch(function () {
          document.getElementById('hd-search-results').innerHTML = '<p style="font-size: 13px; color: #ef4444; text-align: center;">Error loading articles.</p>';
        });
    }, 250);
  });

  // Form Submission
  var form = document.getElementById('hd-ticket-form');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var submitBtn = document.getElementById('hd-submit-btn');
    var statusDiv = document.getElementById('hd-form-status');
    submitBtn.disabled = true;
    submitBtn.innerText = 'Submitting...';
    statusDiv.innerText = '';

    var payload = {
      email: document.getElementById('hd-input-email').value,
      name: document.getElementById('hd-input-name').value,
      subject: document.getElementById('hd-input-subject').value,
      description: document.getElementById('hd-input-desc').value,
    };

    fetch(`${apiHost}/api/method/helpdesk.api.widget.submit_widget_ticket`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (res) { return res.json(); })
      .then(function (res) {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Send Query';
        if (res.message && res.message.ticket_name) {
          statusDiv.style.color = '#16a34a';
          statusDiv.innerText = `Ticket #${res.message.ticket_name} created successfully!`;
          form.reset();
        } else {
          statusDiv.style.color = '#ef4444';
          statusDiv.innerText = res.exc_type || 'Failed to submit ticket.';
        }
      })
      .catch(function (err) {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Send Query';
        statusDiv.style.color = '#ef4444';
        statusDiv.innerText = 'Network error submitting ticket.';
      });
  });
})();
