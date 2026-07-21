import json
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class CliTests(unittest.TestCase):
    def test_demo_create_outputs_committed_json_dossier(self):
        with TemporaryDirectory() as workspace:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "research_mvp",
                    "--workspace",
                    workspace,
                    "create",
                    "demo:video-1",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["source"]["platform"], "demo")
            self.assertIn(
                payload["status"], {"complete", "complete_with_gaps"}
            )
            self.assertNotIn("secret", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
