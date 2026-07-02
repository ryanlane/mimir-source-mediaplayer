const BASE_URL = () => window.mimirServerBaseUrl || window.location.origin;
const API = () => `${BASE_URL()}/api/channels/com.mimir.mediaplayer`;
const BACKEND_LABELS = { plex: 'Plex', jellyfin: 'Jellyfin', emby: 'Emby' };

const STYLES = `
  :host { display: block; font-family: var(--font-base, system-ui, sans-serif); color: var(--color-text, #e8e8e8); }
  .panel { max-width: 680px; }
  h2 { font-size: 1.1rem; margin: 0 0 4px; color: var(--color-text, #e8e8e8); }
  .sub { font-size: 0.82rem; color: var(--color-text-secondary, #888); margin: 0 0 20px; }
  .form-group { margin-bottom: 14px; }
  label { display: block; font-size: 0.82rem; margin-bottom: 4px; color: var(--color-text-secondary, #888); }
  input[type=text], input[type=password], input[type=url], select {
    width: 100%; box-sizing: border-box;
    background: var(--color-surface, #1a1a1a); border: 1px solid var(--color-border, #333);
    color: var(--color-text, #e8e8e8); border-radius: var(--radius-sm, 4px);
    padding: 8px 10px; font-size: 0.9rem;
  }
  .checkbox-row { display: flex; align-items: center; gap: 8px; font-size: 0.9rem; }
  .hint { font-size: 0.75rem; color: var(--color-text-tertiary, #666); margin-top: 4px; }
  .actions { display: flex; gap: 10px; align-items: center; margin-top: 18px; flex-wrap: wrap; }
  .btn { padding: 8px 18px; border: none; border-radius: var(--radius-sm, 4px); cursor: pointer; font-size: 0.9rem; }
  .btn-primary { background: light-dark(#036600, #2e7a30); color: #fff; }
  .btn-primary:hover { background: light-dark(#024d00, #3a963c); }
  .btn-primary:disabled { opacity: 0.5; cursor: default; }
  .btn-secondary { background: var(--color-surface, #222); color: var(--color-text, #e8e8e8); border: 1px solid var(--color-border, #333); }
  .btn-secondary:hover { background: var(--color-surface-hover, #2a2a2a); }
  .btn-danger { background: transparent; color: var(--color-error, #f87171); border: 1px solid color-mix(in srgb, var(--color-error, #f87171) 55%, transparent); }
  .btn-danger:disabled { opacity: 0.5; cursor: default; }
  .now-playing { display: flex; gap: 14px; align-items: flex-start; padding: 14px;
    background: var(--color-surface, #1a1a1a); border-radius: var(--radius-md, 8px); margin-bottom: 20px; }
  .poster { width: 80px; height: 120px; border-radius: 4px; object-fit: cover; background: #222; flex-shrink: 0; }
  .poster-placeholder { width: 80px; height: 120px; border-radius: 4px; background: #2a2a2a;
    display: flex; align-items: center; justify-content: center; font-size: 2rem; color: #555; flex-shrink: 0; }
  .meta { flex: 1; min-width: 0; }
  .badge { display: inline-flex; align-items: center; gap: 5px; font-size: 0.72rem;
    padding: 2px 7px; border-radius: 99px; background: var(--color-accent, #00c851); color: #000; margin-bottom: 8px; font-weight: 600; }
  .badge-paused { background: #444; color: #aaa; }
  .badge-idle { background: #333; color: #777; }
  .media-title { font-weight: 600; font-size: 0.95rem; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .media-series { font-size: 0.82rem; color: var(--color-text-secondary, #888); margin-bottom: 2px; }
  .media-year { font-size: 0.78rem; color: var(--color-text-tertiary, #666); }
  .error { color: var(--color-error, #f87171); font-size: 0.82rem; margin-top: 8px; }
  .success-msg { color: var(--color-success, #4ade80); font-size: 0.82rem; margin-top: 8px; }
  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid var(--color-accent, #00c851);
    border-top-color: transparent; border-radius: 50%; animation: spin .7s linear infinite; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .divider { border: none; border-top: 1px solid var(--color-border, #333); margin: 20px 0; }
  .section-title { font-size: 0.78rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--color-text-tertiary, #666); margin-bottom: 12px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .server-layout { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 16px; align-items: start; }
  .server-list { display: flex; flex-direction: column; gap: 8px; }
  .server-item { width: 100%; text-align: left; padding: 10px 12px; border: 1px solid var(--color-border, #333);
    border-radius: var(--radius-sm, 4px); background: var(--color-surface, #1a1a1a); color: var(--color-text, #e8e8e8); cursor: pointer; }
  .server-item.active { border-color: var(--color-accent, #00c851); box-shadow: inset 3px 0 0 var(--color-accent, #00c851); }
  .server-name { display: block; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .server-meta { display: block; margin-top: 2px; font-size: 0.74rem; color: var(--color-text-tertiary, #666); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .server-editor { min-width: 0; }
  .webhook-box { background: var(--color-background-alt, #111); border: 1px solid var(--color-border, #333);
    border-radius: var(--radius-md, 8px); padding: 14px; display: flex; flex-direction: column; gap: 10px; }
  .webhook-url-row { display: flex; gap: 8px; align-items: center; }
  .webhook-url { flex: 1; font-family: monospace; font-size: 0.78rem; background: var(--color-surface, #1a1a1a);
    border: 1px solid var(--color-border, #333); border-radius: var(--radius-sm, 4px);
    padding: 6px 10px; color: var(--color-text, #e8e8e8); white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; user-select: all; cursor: text; }
  .btn-copy { padding: 6px 12px; border: 1px solid var(--color-border, #333); border-radius: var(--radius-sm, 4px);
    background: var(--color-surface, #222); color: var(--color-text, #e8e8e8); cursor: pointer; font-size: 0.82rem;
    white-space: nowrap; flex-shrink: 0; transition: background 100ms; }
  .btn-copy:hover { background: var(--color-surface-hover, #2a2a2a); }
  .btn-copy.copied { color: var(--color-success, #4ade80); border-color: var(--color-success, #4ade80); }
  .webhook-note { font-size: 0.75rem; color: var(--color-text-tertiary, #666); line-height: 1.5; }
  .webhook-note a { color: var(--color-accent, #00c851); }
  .webhook-status { font-size: 0.75rem; color: var(--color-text-tertiary, #666); display: flex; align-items: center; gap: 6px; }
  .webhook-status-dot { width: 7px; height: 7px; border-radius: 50%; background: #444; flex-shrink: 0; }
  .webhook-status-dot--ok { background: var(--color-success, #4ade80); }
  .webhook-status-dot--warn { background: var(--color-warning, #f59e0b); }
  @media (max-width: 640px) { .server-layout, .two-col { grid-template-columns: 1fr; } }
`;

class MediaPlayerManager extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._state = {
      loading: true, saving: false,
      error: null, successMsg: null,
      servers: [], selectedServerId: null,
      // display
      fitMode: 'crop', showInfo: true, theme: 'dark',
      // status
      configured: false, session: null, sessionStatus: null, webhook: null,
    };
    this._pollTimer = null;
  }

  connectedCallback() {
    this._load();
  }

  disconnectedCallback() {
    clearInterval(this._pollTimer);
  }

  _set(updates) {
    Object.assign(this._state, updates);
    this._render();
  }

  _defaultServer() {
    const id = `server-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return { id, name: 'Plex', backend: 'plex', server_url: '', api_token: '', api_token_masked: '', username: '', verify_ssl: false, enabled: true };
  }

  _selectedServer() {
    return this._state.servers.find(server => server.id === this._state.selectedServerId) || this._state.servers[0] || null;
  }

  _escape(value) {
    return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  }

  _normalizeServers(rawServers, legacySettings = {}) {
    const servers = Array.isArray(rawServers) ? rawServers : [];
    if (servers.length) {
      return servers.map(server => ({
        id: server.id || `server-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        name: server.name || BACKEND_LABELS[server.backend] || 'Media Server',
        backend: server.backend || 'plex',
        server_url: server.server_url || '',
        api_token: '',
        api_token_masked: server.api_token || '',
        username: server.username || '',
        verify_ssl: server.verify_ssl || false,
        enabled: server.enabled !== false,
      }));
    }
    return [{
      ...this._defaultServer(),
      backend: legacySettings.backend || 'plex',
      name: BACKEND_LABELS[legacySettings.backend] || 'Plex',
      server_url: legacySettings.server_url || '',
      api_token_masked: legacySettings.api_token || '',
      username: legacySettings.username || '',
      verify_ssl: legacySettings.verify_ssl || false,
    }];
  }

  _updateSelectedServer(updates, rerender = false) {
    const selected = this._selectedServer();
    if (!selected) return;
    this._state.servers = this._state.servers.map(server => server.id === selected.id ? { ...server, ...updates } : server);
    if (rerender) this._render();
  }

  async _load() {
    try {
      const resp = await fetch(`${API()}/settings`);
      const data = await resp.json();
      if (data.success) {
        const s = data.settings || {};
        const servers = this._normalizeServers(s.servers, s);
        this._set({
          loading: false,
          servers,
          selectedServerId: servers[0]?.id || null,
          fitMode:    s.fit_mode || 'crop',
          showInfo:   s.show_info !== false,
          theme:      s.theme || 'dark',
          configured: s.configured || false,
        });
        if (s.configured) this._startPolling();
      }
    } catch (e) {
      this._set({ loading: false, error: 'Could not load settings.' });
    }
  }

  async _save() {
    const servers = this._state.servers.map(server => {
      const body = {
        id: server.id,
        name: (server.name || '').trim() || BACKEND_LABELS[server.backend] || 'Media Server',
        backend: server.backend,
        server_url: (server.server_url || '').trim(),
        username: (server.username || '').trim(),
        verify_ssl: Boolean(server.verify_ssl),
        enabled: server.enabled !== false,
      };
      if ((server.api_token || '').trim()) body.api_token = server.api_token.trim();
      return body;
    });

    this._set({ saving: true, error: null, successMsg: null });
    try {
      const resp = await fetch(`${API()}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          servers,
          fit_mode: this._state.fitMode,
          show_info: this._state.showInfo,
          theme: this._state.theme,
        }),
      });
      const data = await resp.json();
      if (data.success) {
        const savedServers = this._normalizeServers(data.settings?.servers || []);
        const selectedStillExists = savedServers.some(server => server.id === this._state.selectedServerId);
        this._set({
          saving: false,
          servers: savedServers,
          selectedServerId: selectedStillExists ? this._state.selectedServerId : savedServers[0]?.id || null,
          configured: data.settings?.configured || false,
          successMsg: 'Settings saved.',
        });
        if (this._state.configured) this._startPolling();
      } else {
        this._set({ saving: false, error: data.error || 'Save failed.' });
      }
    } catch (e) {
      this._set({ saving: false, error: String(e) });
    }
  }

  _startPolling() {
    clearInterval(this._pollTimer);
    const poll = async () => {
      try {
        const resp = await fetch(`${API()}/status`);
        const data = await resp.json();
        this._set({ session: data.session || null, sessionStatus: data.status || null, webhook: data.webhook || null });
      } catch (_) {}
    };
    poll();
    this._pollTimer = setInterval(poll, 15000);
  }

  _render() {
    const s = this._state;
    const selected = this._selectedServer();
    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <div class="panel">
        <h2>Media Player Now Playing</h2>
        <p class="sub">Shows the poster of the currently playing video from Plex, Jellyfin, or Emby.
          Add this channel as a <strong>Now Playing</strong> interrupt source on any program.</p>

        ${s.loading ? '<div><span class="spinner"></span> Loading…</div>' : ''}

        ${!s.loading && s.configured && s.session ? this._sessionHtml(s.session) : ''}
        ${!s.loading && s.configured && !s.session ? '<div style="font-size:0.85rem;color:var(--color-text-tertiary,#666);margin-bottom:16px;">No active session — nothing is playing right now.</div>' : ''}

        ${!s.loading ? `
          <hr class="divider">
          <div class="section-title">Connections</div>

          <div class="server-layout">
            <div>
              <div class="server-list">
                ${s.servers.map(server => this._serverButtonHtml(server, selected)).join('')}
              </div>
              <div class="actions">
                <button class="btn btn-secondary" id="addServer">Add Server</button>
              </div>
            </div>
            <div class="server-editor">
              ${selected ? this._serverEditorHtml(selected) : ''}
            </div>
          </div>

          <hr class="divider">
          <div class="section-title">Display</div>

          <div class="two-col">
            <div class="form-group">
              <label>Poster Fit</label>
              <select id="fitMode">
                <option value="crop"       ${s.fitMode === 'crop'      ? 'selected' : ''}>Crop (fill display)</option>
                <option value="letterbox"  ${s.fitMode === 'letterbox' ? 'selected' : ''}>Letterbox (show full poster)</option>
              </select>
            </div>
            <div class="form-group">
              <label>Overlay Theme</label>
              <select id="theme">
                <option value="dark"  ${s.theme === 'dark'  ? 'selected' : ''}>Dark</option>
                <option value="light" ${s.theme === 'light' ? 'selected' : ''}>Light</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <div class="checkbox-row">
              <input id="showInfo" type="checkbox" ${s.showInfo ? 'checked' : ''}>
              <label for="showInfo" style="margin:0">Show title overlay on poster</label>
            </div>
          </div>

          ${selected?.backend === 'plex' ? this._webhookHtml(selected, s.webhook) : ''}

          <div class="actions">
            <button class="btn btn-primary" id="save" ${s.saving ? 'disabled' : ''}>
              ${s.saving ? '<span class="spinner"></span> Saving…' : 'Save Settings'}
            </button>
          </div>
          ${s.error      ? `<div class="error">${this._escape(s.error)}</div>`           : ''}
          ${s.successMsg ? `<div class="success-msg">${this._escape(s.successMsg)}</div>` : ''}
        ` : ''}
      </div>
    `;

    const $ = id => this.shadowRoot.getElementById(id);
    $('save')?.addEventListener('click', () => this._save());
    $('addServer')?.addEventListener('click', () => this._addServer());
    $('removeServer')?.addEventListener('click', () => this._removeSelectedServer());
    $('serverName')?.addEventListener('input', e => this._updateSelectedServer({ name: e.target.value }));
    $('backend')?.addEventListener('change', e => {
      const backend = e.target.value;
      const selected = this._selectedServer();
      this._updateSelectedServer({ backend, name: selected?.name || BACKEND_LABELS[backend] }, true);
    });
    $('serverUrl')?.addEventListener('input', e => this._updateSelectedServer({ server_url: e.target.value }));
    $('apiToken')?.addEventListener('input', e => this._updateSelectedServer({ api_token: e.target.value }));
    $('username')?.addEventListener('input', e => this._updateSelectedServer({ username: e.target.value }));
    $('verifySsl')?.addEventListener('change', e => this._updateSelectedServer({ verify_ssl: e.target.checked }));
    $('enabled')?.addEventListener('change', e => this._updateSelectedServer({ enabled: e.target.checked }, true));
    $('fitMode')?.addEventListener('change',   e => { this._state.fitMode    = e.target.value; });
    $('theme')?.addEventListener('change',     e => { this._state.theme      = e.target.value; });
    $('showInfo')?.addEventListener('change',  e => { this._state.showInfo   = e.target.checked; });
    this.shadowRoot.querySelectorAll('[data-server-id]').forEach(button => {
      button.addEventListener('click', () => this._set({ selectedServerId: button.dataset.serverId, successMsg: null, error: null }));
    });
    $('copyWebhook')?.addEventListener('click', () => {
      const selected = this._selectedServer();
      const url = selected ? this._webhookUrl(selected) : `${BASE_URL()}/api/channels/com.mimir.mediaplayer/webhook`;
      navigator.clipboard?.writeText(url).then(() => {
        const btn = $('copyWebhook');
        if (btn) { btn.textContent = 'Copied!'; btn.classList.add('copied'); setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000); }
      });
    });
  }

  _addServer() {
    const server = this._defaultServer();
    this._set({ servers: [...this._state.servers, server], selectedServerId: server.id, successMsg: null, error: null });
  }

  _removeSelectedServer() {
    const selected = this._selectedServer();
    if (!selected || this._state.servers.length <= 1) return;
    const servers = this._state.servers.filter(server => server.id !== selected.id);
    this._set({ servers, selectedServerId: servers[0]?.id || null, successMsg: null, error: null });
  }

  _serverButtonHtml(server, selected) {
    const active = selected?.id === server.id ? 'active' : '';
    const configured = server.enabled !== false && server.server_url && (server.api_token || server.api_token_masked) ? 'Configured' : 'Needs setup';
    return `<button class="server-item ${active}" data-server-id="${this._escape(server.id)}">
      <span class="server-name">${this._escape(server.name || BACKEND_LABELS[server.backend] || 'Media Server')}</span>
      <span class="server-meta">${this._escape(BACKEND_LABELS[server.backend] || server.backend)} &middot; ${configured}${server.enabled === false ? ' &middot; Disabled' : ''}</span>
    </button>`;
  }

  _serverEditorHtml(server) {
    return `
      <div class="form-group">
        <label>Display Name</label>
        <input id="serverName" type="text" value="${this._escape(server.name)}" placeholder="Living Room Plex" autocomplete="off">
      </div>
      <div class="form-group">
        <label>Media Server Type</label>
        <select id="backend">
          <option value="plex" ${server.backend === 'plex' ? 'selected' : ''}>Plex</option>
          <option value="jellyfin" ${server.backend === 'jellyfin' ? 'selected' : ''}>Jellyfin</option>
          <option value="emby" ${server.backend === 'emby' ? 'selected' : ''}>Emby</option>
        </select>
      </div>
      <div class="form-group">
        <label>Server URL</label>
        <input id="serverUrl" type="url" value="${this._escape(server.server_url)}" placeholder="${server.backend === 'plex' ? 'http://192.168.1.10:32400' : 'http://192.168.1.10:8096'}" autocomplete="off">
        <div class="hint">Include http:// or https:// and the port number.</div>
      </div>
      <div class="form-group">
        <label>API Token / Key ${server.api_token_masked ? '<span style="color:var(--color-text-tertiary,#666)">(leave blank to keep existing)</span>' : ''}</label>
        <input id="apiToken" type="password" value="${this._escape(server.api_token || '')}" placeholder="${server.api_token_masked ? '********' : (server.backend === 'plex' ? 'Plex token' : 'API key')}" autocomplete="off">
        ${server.backend === 'plex' ? '<div class="hint">See <a href="https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/" target="_blank" rel="noopener noreferrer">Finding your Plex token</a> for instructions.</div>' : ''}
        ${server.backend !== 'plex' ? '<div class="hint">Create an API key in the server dashboard under API Keys.</div>' : ''}
      </div>
      <div class="form-group">
        <label>Username Filter <span style="color:var(--color-text-tertiary,#666)">(optional)</span></label>
        <input id="username" type="text" value="${this._escape(server.username)}" placeholder="Leave blank to show any active session" autocomplete="off">
      </div>
      <div class="form-group">
        <div class="checkbox-row">
          <input id="verifySsl" type="checkbox" ${server.verify_ssl ? 'checked' : ''}>
          <label for="verifySsl" style="margin:0">Verify SSL certificate</label>
        </div>
        <div class="hint" style="margin-left:22px">Uncheck for servers with self-signed certificates.</div>
      </div>
      <div class="form-group">
        <div class="checkbox-row">
          <input id="enabled" type="checkbox" ${server.enabled !== false ? 'checked' : ''}>
          <label for="enabled" style="margin:0">Poll this server</label>
        </div>
      </div>
      <div class="actions">
        <button class="btn btn-danger" id="removeServer" ${this._state.servers.length <= 1 ? 'disabled' : ''}>Remove Server</button>
      </div>
    `;
  }

  _webhookUrl(server) {
    return `${BASE_URL()}/api/channels/com.mimir.mediaplayer/webhook/${encodeURIComponent(server.id)}`;
  }

  _webhookHtml(server, webhook) {
    return `
      <hr class="divider">
      <div class="section-title">Webhooks <span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--color-accent,#00c851);font-size:0.7rem;">Plex Pass required</span></div>
      <div class="webhook-box">
        <div class="webhook-url-row">
          <div class="webhook-url" id="webhookUrl">${this._escape(this._webhookUrl(server))}</div>
          <button class="btn-copy" id="copyWebhook">Copy</button>
        </div>
        <p class="webhook-note">
          Add this URL in Plex: <strong>Settings &gt; Webhooks &gt; Add Webhook</strong>.<br>
          Use the server-specific URL so webhook events update the matching Plex connection.
          <a href="https://support.plex.tv/articles/115002267687-webhooks/" target="_blank" rel="noopener noreferrer">Webhook setup guide</a>
        </p>
        ${this._webhookStatusHtml(webhook)}
      </div>
    `;
  }

  _relativeTime(epochSeconds) {
    if (!epochSeconds) return null;
    const ago = Math.floor(Date.now() / 1000 - epochSeconds);
    if (ago < 5)   return 'just now';
    if (ago < 60)  return `${ago}s ago`;
    if (ago < 3600) return `${Math.floor(ago / 60)}m ago`;
    return `${Math.floor(ago / 3600)}h ago`;
  }

  _webhookStatusHtml(webhook) {
    if (!webhook?.last_event_at) {
      return `<div class="webhook-status">
        <div class="webhook-status-dot"></div>
        No events received yet — check the URL is correct and Plex can reach this server.
      </div>`;
    }
    const age = Math.floor(Date.now() / 1000 - webhook.last_event_at);
    const dotClass = age < 300 ? 'webhook-status-dot--ok' : 'webhook-status-dot--warn';
    return `<div class="webhook-status">
      <div class="webhook-status-dot ${dotClass}"></div>
      Last event: <strong>${this._escape(webhook.last_event_type || 'unknown')}</strong> — ${this._relativeTime(webhook.last_event_at)}
    </div>`;
  }

  _sessionHtml(session) {
    const playing = session?.is_playing;
    const badgeCls = playing ? '' : 'badge-paused';
    const badgeLabel = playing ? '▶ NOW PLAYING' : '⏸ PAUSED';

    const isEpisode = session?.media_type === 'episode';
    const title = session?.title || '—';
    const series = session?.series_title;
    const year  = session?.year;
    const s_num = session?.season_num;
    const e_num = session?.episode_num;
    const epLabel = (s_num && e_num) ? `S${String(s_num).padStart(2,'0')}E${String(e_num).padStart(2,'0')}` : '';
    const serverLabel = session?.server_name ? `${session.server_name} · ${BACKEND_LABELS[session.backend] || session.backend}` : '';

    return `
      <div class="now-playing">
        <div class="poster-placeholder">🎬</div>
        <div class="meta">
          <div class="badge ${badgeCls}">${badgeLabel}</div>
          ${serverLabel ? `<div class="media-year">${this._escape(serverLabel)}</div>` : ''}
          ${isEpisode && series ? `<div class="media-series">${this._escape(series)}${epLabel ? ' · ' + epLabel : ''}</div>` : ''}
          <div class="media-title">${this._escape(title)}</div>
          ${year ? `<div class="media-year">${this._escape(year)}</div>` : ''}
        </div>
      </div>
    `;
  }
}

customElements.define('x-mediaplayer-manager', MediaPlayerManager);
