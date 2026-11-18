from __future__ import annotations

import pathlib
from types import SimpleNamespace
import unittest

from jinja2.nativetypes import NativeEnvironment
import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FRIGATE_BP = REPO_ROOT / "blueprints" / "automation" / "frigate_review_notifications.yaml"


class InputRef(str):
    pass


class HALoader(yaml.SafeLoader):
    pass


HALoader.add_constructor("!input", lambda loader, node: InputRef(loader.construct_scalar(node)))


class TestFrigateReviewBlueprint(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_text = FRIGATE_BP.read_text(encoding="utf-8")
        cls.doc = yaml.load(cls.raw_text, Loader=HALoader)
        cls.bp = cls.doc["blueprint"]

        cls.defined_inputs = {}
        for k, v in cls.bp["input"].items():
            if isinstance(v, dict) and "input" in v and "selector" not in v:
                collapsed = v.get("collapsed", False)
                for sk, sv in v["input"].items():
                    if collapsed and "default" not in sv:
                        raise AssertionError(f"Input '{sk}' in collapsed section '{k}' missing default")
                    cls.defined_inputs[sk] = sv
            else:
                cls.defined_inputs[k] = v

        cls.env = NativeEnvironment()
        cls.env.filters["unique"] = lambda seq: list(dict.fromkeys(seq))

    def _eval(self, val, ctx: dict, states: dict, allow_states: bool = True):
        if isinstance(val, InputRef):
            return ctx[str(val)]
        if isinstance(val, dict):
            return {k: self._eval(v, ctx, states, allow_states) for k, v in val.items()}
        if isinstance(val, list):
            return [self._eval(v, ctx, states, allow_states) for v in val]
        if isinstance(val, str) and ("{{" in val or "{%" in val):
            local_ctx = dict(ctx)
            if allow_states:
                local_ctx["states"] = lambda eid: states.get(eid, ("unknown", {}))[0]
                local_ctx["state_attr"] = lambda eid, attr: states.get(eid, (None, {}))[1].get(attr)
                local_ctx["expand"] = lambda ents: [
                    SimpleNamespace(entity_id=e, state=states.get(e, ("unknown", {}))[0])
                    for e in (ents if isinstance(ents, list) else ([ents] if ents else []))
                ]
            res = self.env.from_string(val).render(**local_ctx)
            return res.strip() if isinstance(res, str) else res
        return val

    def _simulate(self, trigger_obj: dict, user_inputs: dict | None = None, states: dict | None = None) -> dict:
        mock_states = {
            "camera.backyard": (
                "recording",
                {
                    "friendly_name": "Backyard Cam",
                    "camera_name": "backyard",
                    "client_id": "frigate",
                    "entity_picture": "/api/camera_proxy/camera.backyard?token=camtok123",
                },
            ),
            "image.backyard_person": (
                "2026-11-18T16:38:37.339090",
                {"entity_picture": "/api/image_proxy/image.backyard_person?token=imgtok456"},
            ),
            "image.backyard_cow": (
                "unknown",
                {"entity_picture": "/api/image_proxy/image.backyard_cow?token=empty789"},
            ),
            "person.alice": ("not_home", {"friendly_name": "Alice"}),
        }
        if states:
            mock_states.update(states)

        ctx = {k: spec.get("default") for k, spec in self.defined_inputs.items()}
        ctx["camera"] = "camera.backyard"
        ctx["notify_service"] = "notify.mobile_app_pixel"
        if user_inputs:
            ctx.update(user_inputs)

        # Simulate Home Assistant's `mqtt/trigger.py` strictly: `value_template` ONLY sees `value_json`!
        mqtt_trig = self.doc["triggers"][0]
        wanted_payload = self._eval(mqtt_trig["payload"], ctx, mock_states, allow_states=False)
        if trigger_obj.get("id") == "review":
            rendered_vt = self._eval(
                mqtt_trig["value_template"],
                {"value_json": trigger_obj["payload_json"]},
                mock_states,
                allow_states=False,
            )
            ctx["_mqtt_matched"] = rendered_vt == wanted_payload

        ctx["trigger"] = trigger_obj
        for k, expr in self.doc["variables"].items():
            ctx[k] = self._eval(expr, ctx, mock_states, allow_states=True)

        or_branches = self.doc["conditions"][0]["conditions"]
        mute_cond = trigger_obj.get("id") == "mute" and bool(
            self._eval(or_branches[0]["conditions"][1]["value_template"], ctx, mock_states)
        )
        review_cond = trigger_obj.get("id") == "review" and bool(
            self._eval(or_branches[1]["conditions"][1]["value_template"], ctx, mock_states)
        )
        ctx["_cond_passed"] = mute_cond or review_cond
        ctx["_manual_test_runs"] = bool(
            self._eval(self.doc["actions"][0]["if"][0]["value_template"], ctx, mock_states)
        )
        if ctx["_manual_test_runs"]:
            test_then = self.doc["actions"][0]["then"]
            for k, expr in test_then[0]["variables"].items():
                ctx[k] = self._eval(expr, ctx, mock_states, allow_states=True)
            ctx["_rendered_test_notify"] = self._eval(test_then[1]["data"], ctx, mock_states)
        if review_cond:
            review_then = self.doc["actions"][1]["then"]
            ctx["_first_alert_settle_runs"] = bool(
                self._eval(review_then[0]["if"][0]["value_template"], ctx, mock_states)
            )
            ctx["_gif_delay_runs"] = bool(self._eval(review_then[1]["if"][0]["value_template"], ctx, mock_states))
            for k, expr in review_then[2]["variables"].items():
                ctx[k] = self._eval(expr, ctx, mock_states, allow_states=True)
            ctx["_rendered_notify"] = self._eval(review_then[3]["data"], ctx, mock_states)
        ctx["_mute_runs"] = bool(self._eval(self.doc["actions"][2]["if"][0]["value_template"], ctx, mock_states))
        return ctx

    def test_schema_and_readability_invariants(self) -> None:
        used_inputs: set[str] = set()

        def walk(obj) -> None:
            if isinstance(obj, InputRef):
                used_inputs.add(str(obj))
            elif isinstance(obj, dict):
                for val in obj.values():
                    walk(val)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(self.doc)
        self.assertEqual(used_inputs, set(self.defined_inputs.keys()))
        self.assertRegex(self.bp["homeassistant"]["min_version"], r"^\d+\.\d+\.\d+$")
        self.assertNotIn("namespace(", self.raw_text)
        # Never embed %2F in FrontendTarget paths (Android UrlUtil.handle decodes %2F and splits segments)
        self.assertNotIn("%2F", self.raw_text)

        for name, spec in self.defined_inputs.items():
            sel = spec.get("selector", {})
            if "select" in sel:
                for opt in sel["select"].get("options", []):
                    if isinstance(opt, dict):
                        self.assertIn("label", opt, f"Missing label in {name}")
                        self.assertIn("value", opt, f"Missing value in {name}")

    def test_new_alert_uses_mqtt_ram_image_proxy_with_token(self) -> None:
        res = self._simulate(
            {
                "id": "review",
                "platform": "mqtt",
                "payload_json": {
                    "type": "new",
                    "before": None,
                    "after": {
                        "id": "rev-1",
                        "camera": "backyard",
                        "severity": "alert",
                        "data": {
                            "detections": ["det-1", "det-2"],
                            "objects": ["person", "person-verified"],
                            "sub_labels": ["Courier"],
                            "zones": ["patio"],
                        },
                    },
                },
            }
        )
        self.assertTrue(res["_mqtt_matched"])
        self.assertTrue(res["_cond_passed"])
        self.assertTrue(res["_first_alert_settle_runs"])
        self.assertEqual(res["_rendered_notify"]["title"], "Person (Courier) • Backyard Cam")
        self.assertEqual(
            res["_rendered_notify"]["data"]["image"],
            "/api/image_proxy/image.backyard_person?token=imgtok456",
        )

    def test_unknown_mqtt_image_entity_falls_back_to_frigate_snapshot(self) -> None:
        res = self._simulate(
            {
                "id": "review",
                "platform": "mqtt",
                "payload_json": {
                    "type": "new",
                    "before": None,
                    "after": {
                        "id": "rev-1",
                        "camera": "backyard",
                        "severity": "alert",
                        "data": {"detections": ["det-1"], "objects": ["cow"], "sub_labels": [], "zones": []},
                    },
                },
            }
        )
        self.assertEqual(
            res["_rendered_notify"]["data"]["image"],
            "/api/frigate/frigate/snapshot/det-1?bbox=1",
        )

    def test_fullscreen_dashboard_path_replaces_small_bottom_sheet(self) -> None:
        res = self._simulate(
            {
                "id": "review",
                "platform": "mqtt",
                "payload_json": {
                    "type": "new",
                    "before": None,
                    "after": {
                        "id": "rev-1",
                        "camera": "backyard",
                        "severity": "alert",
                        "data": {"detections": ["det-1"], "objects": ["person"], "sub_labels": [], "zones": []},
                    },
                },
            },
            user_inputs={"camera_dashboard_url": "/ccab4aaf_frigate-proxy"},
        )
        self.assertEqual(res["_rendered_notify"]["data"]["clickAction"], "/ccab4aaf_frigate-proxy")
        self.assertEqual(res["_rendered_notify"]["data"]["actions"][0]["uri"], "/ccab4aaf_frigate-proxy")

    def test_manual_ui_run_button_uses_ram_image_proxy(self) -> None:
        res = self._simulate({"platform": None, "id": None})
        self.assertTrue(res["_manual_test_runs"])
        self.assertEqual(res["_rendered_test_notify"]["title"], "🧪 Test Alert • Backyard Cam")
        self.assertEqual(
            res["_rendered_test_notify"]["data"]["image"],
            "/api/image_proxy/image.backyard_person?token=imgtok456",
        )
        self.assertEqual(res["_rendered_test_notify"]["data"]["actions"][1]["uri"], "/media-browser/browser")

    def test_noop_update_is_skipped_at_trigger(self) -> None:
        state = {
            "id": "rev-1",
            "camera": "backyard",
            "severity": "alert",
            "data": {"detections": ["det-1"], "objects": ["person"], "sub_labels": [], "zones": ["patio"]},
        }
        res = self._simulate(
            {"id": "review", "platform": "mqtt", "payload_json": {"type": "update", "before": state, "after": state}}
        )
        self.assertFalse(res["_mqtt_matched"])

    def test_optional_direct_native_player_intent_and_animated_gif(self) -> None:
        state = {
            "id": "rev-1",
            "camera": "backyard",
            "severity": "alert",
            "data": {"detections": ["det-1"], "objects": ["person"], "sub_labels": [], "zones": []},
        }
        end = self._simulate(
            {"id": "review", "platform": "mqtt", "payload_json": {"type": "end", "before": state, "after": state}},
            user_inputs={"direct_clip_base_url": "https://ha.example.com/", "end_animated_preview": True},
        )
        self.assertTrue(end["_gif_delay_runs"])
        self.assertEqual(
            end["_rendered_notify"]["data"]["image"],
            "/api/frigate/frigate/notifications/rev-1/review_preview.gif",
        )
        self.assertEqual(
            end["_rendered_notify"]["data"]["clickAction"],
            "https://ha.example.com/api/frigate/frigate/notifications/det-1/clip.mp4",
        )
        self.assertEqual(
            end["_rendered_notify"]["data"]["url"],
            "https://ha.example.com/api/frigate/frigate/notifications/det-1/clip.mp4",
        )
        self.assertEqual(end["_rendered_notify"]["data"]["actions"][0]["title"], "Play Clip")

    def test_presence_suppression_still_allows_matching_mute_button_only(self) -> None:
        state = {
            "id": "rev-1",
            "camera": "backyard",
            "severity": "alert",
            "data": {"detections": ["det-1"], "objects": ["person"], "sub_labels": [], "zones": ["patio"]},
        }
        rev = self._simulate(
            {"id": "review", "platform": "mqtt", "payload_json": {"type": "new", "before": None, "after": state}},
            user_inputs={"presence_filter": ["person.alice"]},
            states={"person.alice": ("home", {})},
        )
        self.assertFalse(rev["_cond_passed"])

        other = self._simulate(
            {"id": "mute", "platform": "event", "event": {"data": {"action": "APPROVE_OOB_123"}}},
        )
        self.assertFalse(other["_cond_passed"])

        mute = self._simulate(
            {"id": "mute", "platform": "event", "event": {"data": {"action": "FRIGATE_MUTE_backyard"}}},
            user_inputs={"presence_filter": ["person.alice"]},
            states={"person.alice": ("home", {})},
        )
        self.assertTrue(mute["_cond_passed"])
        self.assertTrue(mute["_mute_runs"])


if __name__ == "__main__":
    unittest.main()
