import email
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "checker.py"
spec = importlib.util.spec_from_file_location("checker", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CheckerTests(unittest.TestCase):
    def test_filter_new_uids_skips_processed_and_old(self):
        state = {"processed_uids": ["10", "12"], "last_uid": 11}
        out = mod.filter_new_uids([b"10", b"11", b"12", b"13", b"14"], state)
        self.assertEqual(out, [b"13", b"14"])

    def test_update_state_after_run_keeps_recent_processed(self):
        state = {"processed_uids": [str(i) for i in range(600)], "last_uid": 500}
        new_state = mod.update_state_after_run(state, [b"601", b"602"])
        self.assertEqual(new_state["last_uid"], 602)
        self.assertLessEqual(len(new_state["processed_uids"]), 500)
        self.assertIn("602", new_state["processed_uids"])

    def test_build_fallback_summary_uses_subject_sender_and_preview(self):
        summary = mod.build_fallback_summary([
            {"subject": "Invoice", "from": "billing@example.com", "body": "Payment due tomorrow"}
        ])
        self.assertIn("Invoice", summary)
        self.assertIn("billing@example.com", summary)
        self.assertIn("Payment due tomorrow", summary)

    def test_format_digest_marks_fallback(self):
        text = mod.format_digest("me@gmail.com", [{"uid": "1"}], "- test", used_fallback=True)
        self.assertIn("AI summary unavailable", text)
        self.assertIn("1 новых писем", text)

    def test_load_and_save_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            original = mod.STATE_FILE
            mod.STATE_FILE = str(path)
            try:
                payload = {"processed_uids": ["1"], "last_uid": 1}
                mod.save_state(payload)
                self.assertEqual(mod.load_state(), payload)
            finally:
                mod.STATE_FILE = original

    def test_get_text_from_msg_extracts_text_attachment_preview(self):
        msg = email.message.EmailMessage()
        msg.set_content("Hello from body")
        msg.add_attachment("col1,col2\n1,2", filename="data.csv")
        body, attachments = mod.get_text_from_msg(msg)
        self.assertIn("Hello from body", body)
        self.assertTrue(any("data.csv" in item for item in attachments))


if __name__ == "__main__":
    unittest.main()
