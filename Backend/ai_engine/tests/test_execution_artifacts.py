from django.test import SimpleTestCase

from ai_engine.execution_artifacts import (
    collect_media_artifacts,
    extract_primary_article_text,
)


class ExecutionArtifactsTests(SimpleTestCase):
    def test_extract_canvas_outputs_joins_text(self):
        od = {"outputs": {"n1": {"text": "A"}, "n2": {"text": "B"}}}
        t = extract_primary_article_text(od)
        self.assertIn("A", t)
        self.assertIn("B", t)

    def test_collect_media(self):
        od = {
            "outputs": {
                "a": {"text": "x", "image_url": "https://ex.com/a.png"},
                "b": {"audio_url": "https://ex.com/s.mp3"},
                "c": {"video_url": "https://ex.com/v.mp4"},
            }
        }
        m = collect_media_artifacts(od)
        self.assertEqual(len(m["images"]), 1)
        self.assertEqual(len(m["audios"]), 1)
        self.assertEqual(len(m["videos"]), 1)
