from django.test import TestCase

from meshapi.widgets import PanoramaViewer


class TestPanoramaViewer(TestCase):
    def setUp(self):
        pass

    def test_pano_get_context(self):
        PanoramaViewer.pano_get_context("test", "[\"blah\", \"blah2\"]")

    def test_pano_get_context_bad_value(self):
        PanoramaViewer.pano_get_context("test", 100) # type: ignore
        PanoramaViewer.pano_get_context("test", None) # type: ignore
