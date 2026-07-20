import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KEYMAP = ROOT / "config" / "charybdis.keymap"
LAYOUTS = ROOT / "config" / "charybdis-layouts.dtsi"
METADATA = ROOT / "config" / "charybdis.json"


class NanoLayoutTest(unittest.TestCase):
    def test_keymap_layers_have_35_bindings(self):
        source = KEYMAP.read_text(encoding="utf-8")
        for layer in ("BASE", "NUM", "NAV", "ETC", "SET", "VOU"):
            match = re.search(
                rf"\b{layer}\s*\{{.*?bindings\s*=\s*<(.*?)>;",
                source,
                re.DOTALL,
            )
            self.assertIsNotNone(match, f"missing {layer} layer")
            bindings = re.findall(r"&[A-Za-z][A-Za-z0-9_]*", match.group(1))
            self.assertEqual(35, len(bindings), f"{layer} has {len(bindings)} bindings")

    def test_position_groups_match_3x5_plus_five_thumbs(self):
        source = KEYMAP.read_text(encoding="utf-8")
        expected = {
            "KEYS_L": list(range(0, 5)) + list(range(10, 15)) + list(range(20, 25)),
            "KEYS_R": list(range(5, 10)) + list(range(15, 20)) + list(range(25, 30)),
            "THUMBS": list(range(30, 35)),
        }
        for name, positions in expected.items():
            match = re.search(rf"^\s*#define {name} ([0-9 ]+)\r?$", source, re.MULTILINE)
            self.assertIsNotNone(match, f"missing {name}")
            self.assertEqual(positions, [int(value) for value in match.group(1).split()])

        for values in re.findall(r"key-positions\s*=\s*<([0-9 ]+)>;", source):
            self.assertTrue(all(int(value) < 35 for value in values.split()))

    def test_timeless_home_row_mods_keep_positional_guards(self):
        source = KEYMAP.read_text(encoding="utf-8")
        expected = {
            "hml": ("KEYS_R", 280, 150),
            "hmr": ("KEYS_L", 280, 150),
            "hsl": ("KEYS_R", 200, 0),
            "hsr": ("KEYS_L", 200, 0),
        }
        for behavior, (opposite_hand, tapping_term, prior_idle) in expected.items():
            match = re.search(rf"\b{behavior}:.*?\{{(.*?)\n\s*\}};", source, re.DOTALL)
            self.assertIsNotNone(match, f"missing {behavior}")
            body = match.group(1)
            self.assertIn('flavor = "balanced";', body)
            self.assertIn(f"tapping-term-ms = <{tapping_term}>;", body)
            self.assertIn("quick-tap-ms = <175>;", body)
            self.assertIn(f"require-prior-idle-ms = <{prior_idle}>;", body)
            self.assertIn(f"hold-trigger-key-positions = <{opposite_hand} THUMBS>;", body)
            self.assertIn("hold-trigger-on-release;", body)

    def test_num_row_uses_timeless_home_row_mods(self):
        source = KEYMAP.read_text(encoding="utf-8")
        layer = re.search(r"\bNUM\s*\{.*?bindings\s*=\s*<(.*?)>;", source, re.DOTALL)
        self.assertIsNotNone(layer)
        bindings = " ".join(layer.group(1).split())
        expected = (
            "&hml LEFT_GUI NUMBER_1 &hml LEFT_ALT NUMBER_2 &hml LCTRL NUMBER_3 "
            "&hsl LEFT_SHIFT NUMBER_4 &kp N5 &kp NUMBER_6 "
            "&hsr RIGHT_SHIFT N7 &hmr RCTRL N8 &hmr RIGHT_ALT N9 &hmr RIGHT_GUI N0"
        )
        self.assertIn(expected, bindings)

    def test_etc_uses_precision_cursor_listener(self):
        source = KEYMAP.read_text(encoding="utf-8")
        listener = re.search(r"trackball_listener\s*\{(.*?)\n\s*\};", source, re.DOTALL)
        self.assertIsNotNone(listener)
        self.assertIn("layers = <0 5>;", listener.group(1))
        self.assertIn("scale-divisor = <6>;", listener.group(1))

        precision = re.search(r"trackball_snipe_listener\s*\{(.*?)\n\s*\};", source, re.DOTALL)
        self.assertIsNotNone(precision)
        self.assertIn("layers = <3>;", precision.group(1))
        self.assertIn("scale-divisor = <18>;", precision.group(1))
        self.assertNotIn("trackball_gesture_listener", source)
        self.assertNotIn("ib_gesture_nav:", source)

    def test_physical_layout_uses_five_column_transform(self):
        source = LAYOUTS.read_text(encoding="utf-8")
        self.assertIn('display-name = "Charybdis Nano 3x5";', source)
        self.assertIn("transform = <&five_column_transform>;", source)
        self.assertEqual(35, source.count("<&key_physical_attrs"))

    def test_keymap_editor_metadata_exposes_only_nano_layout(self):
        metadata = json.loads(METADATA.read_text(encoding="utf-8"))
        self.assertEqual("Charybdis Nano", metadata["name"])
        layouts = metadata["layouts"]
        self.assertEqual(["five_column_transform"], list(layouts))
        layout = layouts["five_column_transform"]["layout"]
        self.assertEqual(35, len(layout))
        self.assertEqual([10, 10, 10, 5], [sum(key["row"] == row for key in layout) for row in range(4)])

    def test_dongle_selects_five_column_transform(self):
        source = (ROOT / "boards" / "shields" / "charybdis-dongle" / "charybdis.dtsi").read_text(
            encoding="utf-8"
        )
        chosen = re.search(r"chosen\s*\{(.*?)\};", source, re.DOTALL)
        self.assertIsNotNone(chosen)
        self.assertIn("zmk,matrix_transform = &five_column_transform;", chosen.group(1))

    def test_custom_shields_are_exposed_as_a_zephyr_module(self):
        module = (ROOT / "zephyr" / "module.yml").read_text(encoding="utf-8")
        self.assertRegex(module, r"settings:\s+board_root: \.\s*$")


if __name__ == "__main__":
    unittest.main()
