import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from guided_experience import (
    GUIDED_ACTIONS,
    build_welcome_activity,
    command_from_text,
    guided_action_from_activity,
    guided_prompt,
    topic_hint,
)


class GuidedExperienceTests(unittest.TestCase):
    def test_welcome_card_contains_all_closed_actions(self):
        activity = build_welcome_activity()
        card = activity.attachments[0].content
        submitted_actions = {
            action["data"]["libras_action"] for action in card["actions"]
        }

        self.assertEqual(set(GUIDED_ACTIONS), submitted_actions)
        self.assertIn("¿Qué deseas hacer hoy?", activity.text)

    def test_only_whitelisted_submit_payloads_are_accepted(self):
        activity = build_welcome_activity()
        activity.value = {"libras_action": "version"}
        self.assertEqual("version", guided_action_from_activity(activity))

        activity.value = {"libras_action": "delete_all"}
        self.assertIsNone(guided_action_from_activity(activity))

    def test_action_has_prompt_and_topic_hint(self):
        self.assertIn("versión", guided_prompt("version"))
        self.assertEqual("consulta de versión", topic_hint("version"))

    def test_slash_commands_are_deterministic_and_keep_optional_text(self):
        self.assertEqual(("version", ""), command_from_text("/version"))
        self.assertEqual(
            ("procedure", "Evolution 1.19.1.10"),
            command_from_text("/procedimiento Evolution 1.19.1.10"),
        )
        self.assertEqual(("new", ""), command_from_text("/nuevo"))
        self.assertIsNone(command_from_text("/borrar_todo"))
        self.assertIsNone(command_from_text("version"))


if __name__ == "__main__":
    unittest.main()
