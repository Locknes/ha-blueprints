# Home Assistant Blueprints (`ha-blueprints`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Minimal, readable, zero-spaghetti **Home Assistant** automation blueprints built for modern Home Assistant (`2024.10+`).

---

## Available Blueprints

### 1. Frigate Review Notification (`Frigate 0.14–0.18+`)

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLocknes%2Fha-blueprints%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Ffrigate_review_notifications.yaml)

**Path:** [`blueprints/automation/frigate_review_notifications.yaml`](blueprints/automation/frigate_review_notifications.yaml)

A clean, readable replacement for legacy `frigate/events` Gists and 3,000-line Jinja monoliths:

- **Native `frigate/reviews` Clustering:** Groups overlapping detections (e.g., `person` + `dog`) into a single review thread instead of firing separate alerts per bounding box.
- **In-Place Per-Camera Replacement (`frigate_<camera>`):** Updates and the final `(clip ready)` notification replace the existing camera notification in place (`alert_once: true` on Android, `passive` / `sound: none` on iOS) instead of piling up separate cards per review segment.
- **Zero-Proxy-Hop MQTT RAM Snapshots (`image.<camera>_<object>`):** Serves inline notification previews directly out of Home Assistant's RAM (`/api/image_proxy/image.<camera>_<object>?token=...` populated over MQTT), avoiding reverse-proxy `X-Forwarded-For` `403` blocks on internal Frigate vhosts and gracefully falling back to `/api/frigate/<client_id>/snapshot/<id>?bbox=1`.
- **Fullscreen Views + Direct HTTPS Clip Playback:**
  - **`Fullscreen Camera / Frigate View Path`:** Replaces Home Assistant's small bottom-sheet `entityId:` popup with your full-screen Frigate Ingress panel (`/ccab4aaf_frigate-proxy`) or Lovelace Advanced Camera Card tab (`/lovelace/cameras`).
  - **`External HA URL for Direct Clip Playback`:** Opens `clip.mp4` (`Play Clip`) directly in Android/iOS's fullscreen HTML5 video player via an absolute `https://` URL—working on stock Google Pixel without third-party `intent://` apps and bypassing Android Companion App's `FrontendScreen` `?external_auth=1` WebView bug (`home-assistant/android#7380`) and `UrlUtil.handle` `%2F` path-splitting bug.
- **Anytime Mute + Live Countdown:** Tapping **`Mute`** works at any point, displays a swipeable countdown pill (`chronometer: true`), and includes a 1-tap **`Unsilence Now`** button.

#### Prerequisites
1. **Frigate `0.14+`** publishing to MQTT (`frigate/reviews`).
2. **[Frigate Home Assistant Integration](https://github.com/blakeblackshear/frigate-hass-integration)** (`v5+`).
3. **Home Assistant Companion App** (Android or iOS).

---

## Local Validation

Every blueprint is schema-checked and simulated across Jinja2 `NativeEnvironment` test cases before merge:

```bash
python3 -m unittest discover -s tests -v
```
