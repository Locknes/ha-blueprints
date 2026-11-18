# Home Assistant Blueprints (`ha-blueprints`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Minimal, readable, zero-spaghetti **Home Assistant** automation blueprints built for modern Home Assistant (`2024.10+`).

---

## Available Blueprints

### 1. Frigate Review Notification (`Frigate 0.14–0.18+`)

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLocknes%2Fha-blueprints%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Ffrigate_review_notifications.yaml)

**Path:** [`blueprints/automation/frigate_review_notifications.yaml`](blueprints/automation/frigate_review_notifications.yaml)

A clean (~340-line), readable replacement for legacy `frigate/events` Gists and 3,000-line Jinja monoliths:

- **Native `frigate/reviews` Clustering:** Groups overlapping detections (e.g., `person` + `dog`) into a single review thread instead of firing separate alerts per bounding box.
- **Stateless In-Place Updates (No Stuck `wait_for_trigger` Event Loops):** Diffs `before` vs. `after` so `new` and `update` frames finish in `<50 ms`—buzzing once on the first matching frame and silently updating in place (`alert_once: true` on Android, `passive` / `sound: none` on iOS) as objects, zones, or `-verified` sub-labels evolve.
- **Smart Media & Button Lifecycle:**
  - **Active (`new` / `update`):** Attaches `snapshot.jpg`, opens live view (`entityId:camera.<name>`) on tap, and shows **`Live Camera`**, **`Snapshot`**, and **`Mute Xm`**.
  - **Ended (`end`):** Upgrades to Frigate's animated **`review_preview.gif`** (optional) and swaps Button 1 to **`View Clip`** (`/api/frigate/notifications/<event_id>/clip.mp4`).
- **Companion-App Relative Media URLs:** Uses relative `/api/frigate/notifications/...` paths so the Home Assistant Companion App fetches media over its authenticated session (works seamlessly behind reverse proxies, mTLS, or Zero-Trust edges without public `base_url` exposure).
- **Anytime Mute + Live Countdown:** Tapping **`Mute`** works at any point (live, during cooldown, or minutes after the event ended), displays a swipeable countdown pill (`chronometer: true`), and includes a 1-tap **`Unsilence Now`** button.

#### Prerequisites
1. **Frigate `0.14+`** publishing to MQTT (`frigate/reviews`).
2. **[Frigate Home Assistant Integration](https://github.com/blakeblackshear/frigate-hass-integration)** (`v5+`) installed for `/api/frigate/notifications/...` media proxying.
3. **Home Assistant Companion App** (Android or iOS).

---

## Local Validation

Every blueprint is schema-checked and simulated across Jinja2 `NativeEnvironment` test cases before merge:

```bash
python3 -m unittest discover -s tests -v
```
