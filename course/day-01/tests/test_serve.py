import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "config" / "serve.sh"


class ServeTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        cli = self.root / "vllm"
        cli.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
        cli.chmod(0o755)
        self.target = self.directory("local target", {"architectures": ["Qwen3_5ForConditionalGeneration"]})
        self.draft = self.directory(
            "local draft", {"architectures": ["DSparkDraftModel"], "model_type": "qwen3", "block_size": 7}
        )

    def directory(self, name, config):
        path = self.root / name
        path.mkdir()
        (path / "config.json").write_text(json.dumps(config))
        return path

    def launch(self, *args, check=True):
        return subprocess.run(
            ["bash", SCRIPT, *args],
            text=True,
            capture_output=True,
            check=check,
            env={**os.environ, "PATH": f"{self.root}:{os.environ['PATH']}"},
        )

    def test_local_target_and_optional_dspark(self):
        for paths in [(self.target,), (self.target, self.draft)]:
            with self.subTest(paths=paths):
                argv = self.launch(*paths).stdout.splitlines()
                self.assertEqual(argv[:2], ["serve", str(self.target)])
                self.assertEqual(argv[argv.index("--served-model-name") + 1], "day01-local")
                self.assertNotIn("--revision", argv)
                if len(paths) == 2:
                    self.assertEqual(
                        json.loads(argv[argv.index("--speculative-config") + 1]),
                        {"method": "dspark", "model": str(self.draft), "num_speculative_tokens": 7},
                    )
                else:
                    self.assertNotIn("--speculative-config", argv)

    def test_refuses_draft_as_target_missing_directory_and_wrong_second_model(self):
        for paths in [(self.draft,), (self.root / "missing",), (self.target, self.target)]:
            with self.subTest(paths=paths):
                result = self.launch(*paths, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_course_models_keep_pinned_revisions(self):
        revisions = json.loads(SCRIPT.with_name("revisions.json").read_text())
        for size in ["0.6B", "4B"]:
            argv = self.launch(size).stdout.splitlines()
            model = f"Qwen/Qwen3-{size}"
            self.assertEqual(argv[:2], ["serve", model])
            for flag in ["--revision", "--tokenizer-revision"]:
                self.assertEqual(argv[argv.index(flag) + 1], revisions[model])
