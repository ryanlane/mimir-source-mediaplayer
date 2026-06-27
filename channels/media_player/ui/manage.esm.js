const BASE_URL = () => window.mimirServerBaseUrl || window.location.origin;
const API = () => `${BASE_URL()}/api/channels/com.mimir.mediaplayer`;

const STYLES = `
  :host { display: block; font-family: var(--font-base, system-ui, sans-serif); color: var(--color-text, #e8e8e8); }
  .panel { max-width: 560px; }
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
  .actions { display: flex; gap: 10px; align-items: center; margin-top: 18px; }
  .btn { padding: 8px 18px; border: none; border-radius: var(--radius-sm, 4px); cursor: pointer; font-size: 0.9rem; }
  .btn-primary { background: var(--color-primary, #036600); color: #fff; }
  .btn-primary:hover { background: var(--color-primary-hover, #02550b); }
  .btn-primary:disabled { opacity: 0.5; cursor: default; }
  .btn-secondary { background: var(--color-surface, #222); color: var(--color-text, #e8e8e8); border: 1px solid var(--color-border, #333); }
  .btn-secondary:hover { background: var(--color-surface-hover, #2a2a2a); }
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
`;

class MediaPlayerManager extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._state = {
      loading: true, saving: false, testing: false,
      error: null, successMsg: null,
      // connection
      backend: 'plex', serverUrl: '', apiToken: '', username: '', verifySsl: false,
      // display
      fitMode: 'crop', showInfo: true, theme: 'dark',
      // status
      configured: false, session: null, sessionStatus: null,
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

  async _load() {
    try {
      const resp = await fetch(`${API()}/settings`);
      const data = await resp.json();
      if (data.success) {
        const s = data.settings || {};
        this._set({
          loading: false,
          backend:    s.backend || 'plex',
          serverUrl:  s.server_url || '',
          apiToken:   '',   // never pre-fill masked token
          username:   s.username || '',
          verifySsl:  s.verify_ssl || false,
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
    const s = this._state;
    const body = {
      backend:    s.backend,
      server_url: s.serverUrl.trim(),
      username:   s.username.trim(),
      verify_ssl: s.verifySsl,
      fit_mode:   s.fitMode,
      show_info:  s.showInfo,
      theme:      s.theme,
    };
    if (s.apiToken.trim()) body.api_token = s.apiToken.trim();

    this._set({ saving: true, error: null, successMsg: null });
    try {
      const resp = await fetch(`${API()}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (data.success) {
        this._set({ saving: false, apiToken: '', configured: data.settings?.configured || false, successMsg: 'Settings saved.' });
        if (this._state.configured) this._startPolling();
      } else {
        this._set({ saving: false, error: 'Save failed.' });
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
        this._set({ session: data.session || null, sessionStatus: data.status || null });
      } catch (_) {}
    };
    poll();
    this._pollTimer = setInterval(poll, 15000);
  }

  _render() {
    const s = this._state;
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
          <div class="section-title">Connection</div>

          <div class="form-group">
            <label>Media Server</label>
            <select id="backend">
              <option value="plex"     ${s.backend === 'plex'     ? 'selected' : ''}>Plex</option>
              <option value="jellyfin" ${s.backend === 'jellyfin' ? 'selected' : ''}>Jellyfin</option>
              <option value="emby"     ${s.backend === 'emby'     ? 'selected' : ''}>Emby</option>
            </select>
          </div>
          <div class="form-group">
            <label>Server URL</label>
            <input id="serverUrl" type="url" value="${s.serverUrl}" placeholder="${s.backend === 'plex' ? 'http://192.168.1.10:32400' : 'http://192.168.1.10:8096'}" autocomplete="off">
            <div class="hint">Include http:// or https:// and the port number.</div>
          </div>
          <div class="form-group">
            <label>API Token / Key ${s.configured ? '<span style="color:var(--color-text-tertiary,#666)">(leave blank to keep existing)</span>' : ''}</label>
            <input id="apiToken" type="password" value="${s.apiToken}" placeholder="${s.configured ? '••••••••' : (s.backend === 'plex' ? 'Plex token' : 'API key')}" autocomplete="off">
            ${s.backend === 'plex' ? '<div class="hint">Found in Plex Web → Account → Authorized Devices, or see plex.tv/claim.</div>' : ''}
            ${s.backend !== 'plex' ? '<div class="hint">Create an API key in the server dashboard under API Keys.</div>' : ''}
          </div>
          <div class="form-group">
            <label>Username Filter <span style="color:var(--color-text-tertiary,#666)">(optional)</span></label>
            <input id="username" type="text" value="${s.username}" placeholder="Leave blank to show any active session" autocomplete="off">
          </div>
          <div class="form-group">
            <div class="checkbox-row">
              <input id="verifySsl" type="checkbox" ${s.verifySsl ? 'checked' : ''}>
              <label for="verifySsl" style="margin:0">Verify SSL certificate</label>
            </div>
            <div class="hint" style="margin-left:22px">Uncheck for servers with self-signed certificates.</div>
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

          <div class="actions">
            <button class="btn btn-primary" id="save" ${s.saving ? 'disabled' : ''}>
              ${s.saving ? '<span class="spinner"></span> Saving…' : 'Save Settings'}
            </button>
          </div>
          ${s.error      ? `<div class="error">${s.error}</div>`           : ''}
          ${s.successMsg ? `<div class="success-msg">${s.successMsg}</div>` : ''}
        ` : ''}
      </div>
    `;

    const $ = id => this.shadowRoot.getElementById(id);
    $('save')?.addEventListener('click', () => this._save());
    $('backend')?.addEventListener('change',   e => { this._state.backend    = e.target.value;   this._render(); });
    $('serverUrl')?.addEventListener('input',  e => { this._state.serverUrl  = e.target.value; });
    $('apiToken')?.addEventListener('input',   e => { this._state.apiToken   = e.target.value; });
    $('username')?.addEventListener('input',   e => { this._state.username   = e.target.value; });
    $('verifySsl')?.addEventListener('change', e => { this._state.verifySsl  = e.target.checked; });
    $('fitMode')?.addEventListener('change',   e => { this._state.fitMode    = e.target.value; });
    $('theme')?.addEventListener('change',     e => { this._state.theme      = e.target.value; });
    $('showInfo')?.addEventListener('change',  e => { this._state.showInfo   = e.target.checked; });
  }

  _sessionHtml(session) {
    const playing = session?.is_playing;
    const paused  = session && !playing;
    const badgeCls = playing ? '' : 'badge-paused';
    const badgeLabel = playing ? '▶ NOW PLAYING' : '⏸ PAUSED';

    const isEpisode = session?.media_type === 'episode';
    const title = session?.title || '—';
    const series = session?.series_title;
    const year  = session?.year;
    const s_num = session?.season_num;
    const e_num = session?.episode_num;
    const epLabel = (s_num && e_num) ? `S${String(s_num).padStart(2,'0')}E${String(e_num).padStart(2,'0')}` : '';

    return `
      <div class="now-playing">
        <div class="poster-placeholder">🎬</div>
        <div class="meta">
          <div class="badge ${badgeCls}">${badgeLabel}</div>
          ${isEpisode && series ? `<div class="media-series">${series}${epLabel ? ' · ' + epLabel : ''}</div>` : ''}
          <div class="media-title">${title}</div>
          ${year ? `<div class="media-year">${year}</div>` : ''}
        </div>
      </div>
    `;
  }
}

customElements.define('x-mediaplayer-manager', MediaPlayerManager);
