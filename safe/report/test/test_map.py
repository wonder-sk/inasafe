# coding=utf-8
"""**Tests for map creation in QGIS plugin.**

"""
__author__ = 'Tim Sutton <tim@kartoza.com>'
__revision__ = '$Format:%H$'
__date__ = '01/11/2010'
__license__ = "GPL"
__copyright__ = 'Copyright 2012, Australia Indonesia Facility for '
__copyright__ += 'Disaster Reduction'

# this import required to enable PyQt API v2 - DO NOT REMOVE!
# noinspection PyUnresolvedReferences
import qgis  # pylint: disable=W0611

import unittest
import os
import logging

# Add PARENT directory to path to make test aware of other modules
# pardir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# sys.path.append(pardir)

from qgis.core import (
    QgsMapLayerRegistry,
    QgsRectangle)
from qgis.gui import QgsMapCanvasLayer

from safe.common.testing import get_qgis_app
# In our tests, we need to have this line below before importing any other
# safe_qgis.__init__ to load all the configurations that we make for testing
QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()

from safe.common.utilities import temp_dir, unique_filename
from safe.utilities.resources import resources_path
from safe.utilities.utilities_for_testing import load_layer
from safe.utilities.gis import qgis_version
from safe.report.map import Map

LOGGER = logging.getLogger('InaSAFE')


class MapTest(unittest.TestCase):
    """Test the InaSAFE Map generator"""

    def setUp(self):
        """Setup fixture run before each tests"""
        # noinspection PyArgumentList
        layer_registry = QgsMapLayerRegistry.instance()
        layer_registry.removeAllMapLayers()

    def test_get_map_title(self):
        """Getting the map title from the keywords"""
        layer, _ = load_layer('test_floodimpact.tif')
        report = Map(IFACE)
        report.set_impact_layer(layer)
        title = report.map_title()
        expected_title = 'Penduduk yang Mungkin dievakuasi'
        message = 'Expected: %s\nGot:\n %s' % (expected_title, title)
        assert title == expected_title, message

    def test_handle_missing_map_title(self):
        """Missing map title from the keywords fails gracefully"""
        # TODO running OSM Buildngs with Pendudk Jakarta
        # wasthrowing an error when requesting map title
        # that this test wasnt replicating well
        layer, _ = load_layer('population_padang_1.asc')
        report = Map(IFACE)
        report.set_impact_layer(layer)
        title = report.map_title()
        expected_title = None
        message = 'Expected: %s\nGot:\n %s' % (expected_title, title)
        assert title == expected_title, message

    def test_default_template(self):
        """Test that loading default template works"""
        LOGGER.info('Testing default_template')
        layer, _ = load_layer('test_shakeimpact.shp')
        canvas_layer = QgsMapCanvasLayer(layer)
        CANVAS.setLayerSet([canvas_layer])
        rect = QgsRectangle(106.7894, -6.2308, 106.8004, -6.2264)
        CANVAS.setExtent(rect)
        CANVAS.refresh()
        report = Map(IFACE)
        report.set_impact_layer(layer)
        out_path = unique_filename(
            prefix='map_default_template_test',
            suffix='.pdf',
            dir=temp_dir('test'))
        report.make_pdf(out_path)

        # Check the file exists
        message = 'Rendered output does not exist: %s' % out_path
        self.assertTrue(os.path.exists(out_path), message)

        # Check the file is not corrupt
        message = 'The output file %s is corrupt' % out_path
        out_size = os.stat(out_path).st_size
        self.assertTrue(out_size > 0, message)

        # Check the components in composition are default components
        if qgis_version() < 20500:
            safe_logo = report.composition.getComposerItemById(
                'safe-logo').pictureFile()
            north_arrow = report.composition.getComposerItemById(
                'north-arrow').pictureFile()
            org_logo = report.composition.getComposerItemById(
                'organisation-logo').pictureFile()
        else:
            safe_logo = report.composition.getComposerItemById(
                'safe-logo').picturePath()
            north_arrow = report.composition.getComposerItemById(
                'north-arrow').picturePath()
            org_logo = report.composition.getComposerItemById(
                'organisation-logo').picturePath()

        expected_safe_logo = resources_path(
            'img', 'logos', 'inasafe-logo-url.svg')
        expected_north_arrow = resources_path(
            'img', 'north_arrows', 'simple_north_arrow.png')
        expected_org_logo = resources_path('img', 'logos', 'supporters.png')

        message = 'The safe logo path is not the default one'
        self.assertEqual(expected_safe_logo, safe_logo, message)

        message = 'The north arrow path is not the default one'
        self.assertEqual(expected_north_arrow, north_arrow, message)

        message = 'The organisation logo path is not the default one'
        self.assertEqual(expected_org_logo, org_logo, message)

    def test_custom_logo(self):
        """Test that setting user-defined logo works."""
        LOGGER.info('Testing custom_logo')
        layer, _ = load_layer('test_shakeimpact.shp')
        canvas_layer = QgsMapCanvasLayer(layer)
        CANVAS.setLayerSet([canvas_layer])
        rect = QgsRectangle(106.7894, -6.2308, 106.8004, -6.2264)
        CANVAS.setExtent(rect)
        CANVAS.refresh()
        report = Map(IFACE)
        report.set_impact_layer(layer)

        custom_logo_path = resources_path('img', 'logos', 'logo-flower.png')
        report.set_organisation_logo(custom_logo_path)
        out_path = unique_filename(
            prefix='map_custom_logo_test', suffix='.pdf', dir=temp_dir('test'))
        report.make_pdf(out_path)

        # Check the file exists
        message = 'Rendered output does not exist: %s' % out_path
        self.assertTrue(os.path.exists(out_path), message)

        # Check the file is not corrupt
        message = 'The output file %s is corrupt' % out_path
        out_size = os.stat(out_path).st_size
        self.assertTrue(out_size > 0, message)

        # Check the organisation logo in composition sets correctly to
        # logo-flower
        if qgis_version() < 20500:
            custom_img_path = report.composition.getComposerItemById(
                'organisation-logo').pictureFile()
        else:
            custom_img_path = report.composition.getComposerItemById(
                'organisation-logo').picturePath()

        message = 'The custom logo path is not set correctly'
        self.assertEqual(custom_logo_path, custom_img_path, message)


if __name__ == '__main__':
    suite = unittest.makeSuite(MapTest, 'test')
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
