# mimir-source-mediaplayer

A Mimir channel that displays the **poster of the currently playing video** from one or more Plex, Jellyfin, or Emby servers. Designed to work as a [now-playing interrupt source](../mimir-docs/) — it pre-empts gallery or slideshow content whenever a video is active, then reverts when playback stops.

---

## How it works

The channel detects active playback and fires push events so scenes switch to the poster instantly:

1. Fetches the poster image directly from the server (movie poster, or series poster for TV episodes)
2. Renders it at the display's native resolution — cropped to fill or letterboxed, with an optional title overlay
3. Fires a push event with `is_playing: true` so any scene using this channel as an interrupt source switches immediately
4. When playback stops (or is paused), fires `is_playing: false` and the scene reverts to its base content after the configured resume delay

### Plex — webhooks (recommended)

For Plex, the channel supports [webhooks](https://support.plex.tv/articles/115002267687-webhooks/) for instant response. Configure the webhook URL shown in the settings page under **Settings → Webhooks → Add Webhook** in Plex. When webhooks are active the poll interval backs off to 2 minutes (safety net only).

> **Note:** Plex webhooks require a Plex Pass subscription.

### Polling fallback

Without webhooks (or for Jellyfin/Emby), the channel polls configured servers every 15 seconds. If more than one server has an active session, currently playing sessions are preferred over paused sessions, then the configured server order is used.

---

## Supported backends

| Backend      | Default port | Auth method                 |
| ------------ | ------------ | --------------------------- |
| **Plex**     | `32400`      | Plex token (`X-Plex-Token`) |
| **Jellyfin** | `8096`       | API key (`X-Emby-Token`)    |
| **Emby**     | `8096`       | API key (`X-Emby-Token`)    |

---

## Installation

Install it like any other Mimir plugin — either via the Plugin Registry in the Mimir admin UI, or manually:

```bash
git clone https://github.com/ryanlane/mimir-source-mediaplayer.git
pip install -r mimir-source-mediaplayer/requirements.txt
```

Then point Mimir at the plugin directory in your server configuration.

---

## Configuration

Open the **Media Player** channel page in the Mimir admin UI and add one or more media servers. You can configure a Plex server, a Jellyfin server, an Emby server, or any combination of supported backends.

### Connections

| Setting               | Description                                                                                                |
| --------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Display Name**      | Friendly name shown in status and push metadata                                                            |
| **Media Server Type** | `plex`, `jellyfin`, or `emby`                                                                              |
| **Server URL**        | Full URL with port — e.g. `http://192.168.1.10:32400` (Plex) or `http://192.168.1.10:8096` (Jellyfin/Emby) |
| **API Token / Key**   | See below for how to obtain this per backend                                                               |
| **Username Filter**   | Optional. Leave blank to show any active session; set to a username to only follow that user's playback    |
| **Verify SSL**        | Uncheck for servers with self-signed certificates (common on local networks)                               |
| **Poll this server**  | Disable temporarily without deleting the server                                                            |

### Display

| Setting                | Description                                                                                  |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| **Poster Fit**         | `crop` fills the display (may trim edges); `letterbox` shows the full poster with black bars |
| **Show Title Overlay** | Draws the title, series name, episode number, and year in a bar at the bottom of the poster  |
| **Overlay Theme**      | `dark` (white text on dark bar) or `light` (dark text on light bar)                          |

### Webhooks (Plex only)

When the selected server is Plex, the settings page shows a **Webhooks** section with a server-specific URL to paste into that Plex server. Use the URL shown for that specific server so webhook events are associated with the right configured connection.

Webhook URLs use this shape: `http://<your-mimir-server>:5000/api/channels/com.mimir.mediaplayer/webhook/<server-id>`

The legacy URL `http://<your-mimir-server>:5000/api/channels/com.mimir.mediaplayer/webhook` still works as a fallback for the first configured Plex server.

---

## Getting your API token

### Plex

Plex uses an authentication token rather than an API key. See the official guide for how to find yours:

**[Finding an Authentication Token (X-Plex-Token) — Plex Support](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)**

### Jellyfin

1. Open the Jellyfin dashboard → **Administration** → **API Keys**
2. Click **+** to create a new key, give it a name (e.g. `mimir`)
3. Copy the generated key

### Emby

1. Open the Emby dashboard → **API Keys** (under Advanced)
2. Click **New API Key**, give it a name
3. Copy the generated key

---

## Multi-user servers

If multiple users share a server, the channel shows the first active session it finds for that server. To follow a specific user, set **Username Filter** on that server to their exact username (case-insensitive).

If two users are watching simultaneously on the same server, the channel shows the session it encounters first in the API response — typically the most recently started one on Plex, or the first in the sessions list on Jellyfin/Emby.

---

## TV episodes vs. movies

For **TV episodes**, the channel uses the **series poster** rather than the episode thumbnail — so you see the show's artwork rather than a scene still. For **movies**, it uses the movie poster directly.

The title overlay (when enabled) shows:

- **Movie:** title on the first line, year below
- **Episode:** series name + episode number (e.g. `Breaking Bad · S01E01`) on the first line, episode title below

---

## Using as a now-playing interrupt

After configuring the channel, add it as a **Now Playing** source on a scene in the Program Editor:

1. Open the scene you want to configure in the Mimir admin UI
2. In the **NOW PLAYING** section, click **+ Add Source** and select **Media Player Now Playing**
3. Set a **Priority** (1–100; higher values win when multiple now-playing sources are active)
4. Set a **Resume Delay** — how many seconds to wait after playback stops before reverting to the scene's base content (prevents flicker between consecutive videos)

The scene will show its normal content (gallery, slideshow, etc.) when nothing is playing, and switch to the media poster the moment playback starts.

---

## Requirements

- Python 3.8+
- `pillow` — poster rendering
- `requests` — HTTP client
- `fastapi` — plugin API

No Playwright or external renderer required — rendering is done entirely with Pillow.

---

## Settings reference

| Key                    | Type    | Default      | Description                                       |
| ---------------------- | ------- | ------------ | ------------------------------------------------- |
| `servers`              | array   | `[]`         | Configured media server connections               |
| `servers[].id`         | string  | generated    | Stable server id used for cache keys and webhooks |
| `servers[].name`       | string  | backend name | Friendly display name                             |
| `servers[].backend`    | string  | `plex`       | `plex` \| `jellyfin` \| `emby`                    |
| `servers[].server_url` | string  | `""`         | Full server URL including port                    |
| `servers[].api_token`  | string  | `""`         | Plex token or Jellyfin/Emby API key               |
| `servers[].username`   | string  | `""`         | Filter sessions by username (blank = any)         |
| `servers[].verify_ssl` | boolean | `false`      | Verify SSL certificate                            |
| `servers[].enabled`    | boolean | `true`       | Poll this server                                  |
| `fit_mode`             | string  | `crop`       | `crop` \| `letterbox`                             |
| `show_info`            | boolean | `true`       | Show title overlay bar                            |
| `theme`                | string  | `dark`       | `dark` \| `light` overlay                         |

Settings written by older versions with top-level `backend`, `server_url`, `api_token`, `username`, and `verify_ssl` are migrated into the first `servers[]` entry automatically.
