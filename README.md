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
- **Stateless In-Place Updates (No Stuck `wait_for_trigger` Event Loops):** Diffs `before` vs. `after` so `new` and `update` frames finish in `<50 ms`—buzzing once on the first matching frame and silently updating in place (`alert_once: true` on Android, `passive` / `sound: none` on iOS) as objects, zones, or `-verified` sub-labels evolve.
- **Authenticated `client_id`-Scoped `?bbox=1` Snapshots:** Automatically reads `client_id` off the camera entity and routes inline images through `/api/frigate/<client_id>/snapshot/<id>?bbox=1` (`SnapshotsProxyView`), so Companion Apps authenticate via their existing Bearer token—working reliably even with multiple/disabled Frigate config entries or with Frigate's unauthenticated notification proxy turned **off**.
- **Immune to Android Companion `?external_auth=1` WebView Timeouts (`home-assistant/android#7380`):**
  - **Default (Zero Config):** **`View Clips`** opens Home Assistant's authenticated Frigate Clips Media Browser SPA (`/media-browser/browser/...`) filtered to that camera right inside the Companion App—never hitting `ExternalBusTimeout` on raw `/api/...` files.
  - **Optional Native Fullscreen Player:** Set **`Direct Native Player Base URL`** (e.g., `https://ha.example.com`) with Frigate's notification proxy enabled to launch `clip.mp4` directly in Android's native fullscreen video player (`intent://`).
- **Anytime Mute + Live Countdown:** Tapping **`Mute`** works at any point (live, during cooldown, or minutes after the event ended), displays a swipeable countdown pill (`chronometer: true`), and includes a 1-tap **`Unsilence Now`** button.

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
