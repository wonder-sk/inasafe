"""
InaSAFE Disaster risk assessment tool developed by AusAid -
**SAFE Interface test suite.**

Contact : ole.moller.nielsen@gmail.com

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'tim@linfiniti.com'
__version__ = '0.5.0'
__date__ = '04/04/2012'
__copyright__ = ('Copyright 2012, Australia Indonesia Facility for '
                 'Disaster Reduction')

import os
import numpy
import unittest
from safe_qgis.safe_interface import (getOptimalExtent,
                                   availableFunctions,
                                   readKeywordsFromFile,
                                   readSafeLayer)
from safe_qgis.exceptions import (KeywordNotFoundException,
                               InsufficientOverlapException,
                               InvalidBoundingBoxException)
from common.testing import TESTDATA, HAZDATA, EXPDATA


class ISSafeInterfaceTest(unittest.TestCase):
    """Test the SAFE API Wrapper"""

    def setUp(self):
        """Setup test before each unit"""
        self.vectorPath = os.path.join(TESTDATA, 'Padang_WGS84.shp')
        self.rasterShakePath = os.path.join(HAZDATA,
                                            'Shakemap_Padang_2009.asc')
        self.rasterTsunamiPath = os.path.join(TESTDATA,
                                'tsunami_max_inundation_depth_utm56s.tif')
        self.rasterExposurePath = os.path.join(TESTDATA,
                                             'tsunami_building_exposure.shp')

        self.rasterPopulationPath = os.path.join(EXPDATA, 'glp10ag.asc')

    def test_getOptimalExtent(self):
        """Optimal extent is calculated correctly
        """

        exposure_path = os.path.join(TESTDATA, 'Population_2010.asc')
        hazard_path = os.path.join(HAZDATA,
                                   'Lembang_Earthquake_Scenario.asc')

        # Expected data
        haz_metadata = {'bounding_box': (105.3000035,
                                         -8.3749994999999995,
                                         110.2914705,
                                         -5.5667784999999999),
                        'resolution': (0.0083330000000000001,
                                       0.0083330000000000001)}

        exp_metadata = {'bounding_box': (94.972335000000001,
                                         -11.009721000000001,
                                         141.0140016666665,
                                         6.0736123333332639),
                        'resolution': (0.0083333333333333003,
                                       0.0083333333333333003)}

        # Verify relevant metada is ok
        H = readSafeLayer(hazard_path)
        E = readSafeLayer(exposure_path)

        hazard_bbox = H.get_bounding_box()
        assert numpy.allclose(hazard_bbox, haz_metadata['bounding_box'],
                              rtol=1.0e-12, atol=1.0e-12)

        exposure_bbox = E.get_bounding_box()
        assert numpy.allclose(exposure_bbox, exp_metadata['bounding_box'],
                              rtol=1.0e-12, atol=1.0e-12)

        hazard_res = H.get_resolution()
        assert numpy.allclose(hazard_res, haz_metadata['resolution'],
                              rtol=1.0e-12, atol=1.0e-12)

        exposure_res = E.get_resolution()
        assert numpy.allclose(exposure_res, exp_metadata['resolution'],
                              rtol=1.0e-12, atol=1.0e-12)

        # First, do some examples that produce valid results
        ref_res = [105.3000035, -8.3749995, 110.2914705, -5.5667785]
        view_port = [94.972335, -11.009721, 141.014002, 6.073612]

        bbox = getOptimalExtent(hazard_bbox, exposure_bbox, view_port)
        assert numpy.allclose(bbox, ref_res, rtol=1.0e-12, atol=1.0e-12)

        bbox = getOptimalExtent(hazard_bbox, exposure_bbox, view_port)
        assert numpy.allclose(bbox, ref_res, rtol=1.0e-12, atol=1.0e-12)

        view_port = [105.3000035,
                     -8.3749994999999995,
                     110.2914705,
                     -5.5667784999999999]
        bbox = getOptimalExtent(hazard_bbox, exposure_bbox, view_port)
        assert numpy.allclose(bbox, ref_res,
                              rtol=1.0e-12, atol=1.0e-12)

        # Then one where boxes don't overlap
        view_port = [105.3, -4.3, 110.29, -2.5]
        try:
            getOptimalExtent(hazard_bbox, exposure_bbox, view_port)
        except InsufficientOverlapException, e:
            myMessage = 'Did not find expected error message in %s' % str(e)
            assert 'did not overlap' in str(e), myMessage
        else:
            myMessage = ('Non ovelapping bounding boxes should have raised '
                   'an exception')
            raise Exception(myMessage)

        # Try with wrong input data
        try:
            getOptimalExtent(haz_metadata, exp_metadata, view_port)
        except InvalidBoundingBoxException:
            #good this was expected
            pass
        except InsufficientOverlapException, e:
            myMessage = 'Did not find expected error message in %s' % str(e)
            assert 'Invalid' in str(e), myMessage
        else:
            myMessage = ('Wrong input data should have raised an exception')
            raise Exception(myMessage)

        try:
            getOptimalExtent(None, None, view_port)
        except InvalidBoundingBoxException, e:
            myMessage = 'Did not find expected error message in %s' % str(e)
            assert 'Invalid' in str(e), myMessage
        else:
            myMessage = ('Wrong input data should have raised an exception')
            raise Exception(myMessage)

        try:
            getOptimalExtent('aoeush', 'oeuuoe', view_port)
        except InvalidBoundingBoxException, e:
            myMessage = 'Did not find expected error message in %s' % str(e)
            assert 'Invalid' in str(e), myMessage
        else:
            myMessage = ('Wrong input data should have raised an exception')
            raise Exception(myMessage)

    def test_availableFunctions(self):
        """Check we can get the available functions from the impact calculator.
        """
        myList = availableFunctions()
        assert myList > 1

        # Also test if it works when we give it two layers
        # to see if we can determine which functions will
        # work for them.
        myKeywords1 = readKeywordsFromFile(self.rasterShakePath)
        myKeywords2 = readKeywordsFromFile(self.vectorPath)
        myList = [myKeywords1, myKeywords2]
        myList = availableFunctions(myList)
        assert myList > 1

    def test_getKeywordFromFile(self):
        """Get keyword from a filesystem file's .keyword file."""

        myKeyword = readKeywordsFromFile(
                                    self.rasterShakePath, 'category')
        myExpectedKeyword = 'hazard'
        myMessage = 'Got: %s\n\nExpected %s\n\nDB: %s' % (
                    myKeyword, myExpectedKeyword, self.rasterShakePath)
        assert myKeyword == 'hazard', myMessage

        # Test we get an exception if keyword is not found
        try:
            myKeyword = readKeywordsFromFile(
                            self.rasterShakePath, 'boguskeyword')
        except KeywordNotFoundException:
            pass  # this is good
        except Exception, e:
            myMessage = ('Request for bogus keyword raised incorrect '
                         'exception type: \n %s') % str(e)
            assert(), myMessage

        myKeywords = readKeywordsFromFile(self.rasterShakePath)

        myExpectedKeywords = {'category': 'hazard',
                              'subcategory': 'earthquake',
                              'unit': 'MMI',
                              'title': 'An earthquake in Padang like in 2009'}
        myMessage = 'Expected:\n%s\nGot:\n%s' % (myKeywords,
                                                 myExpectedKeywords)
        assert myKeywords == myExpectedKeywords, myMessage

        myKeywords = readKeywordsFromFile(self.rasterPopulationPath)
        assert myKeywords == {'category': 'exposure',
                              'subcategory': 'population',
                              'datatype': 'density',
                              'title': 'People'}

        myKeywords = readKeywordsFromFile(self.vectorPath)
        assert myKeywords == {'category': 'exposure',
                              'datatype': 'itb',
                              'subcategory': 'building'}

        #  tsunami example (one layer is UTM)
        myKeywords = readKeywordsFromFile(self.rasterTsunamiPath)
        assert myKeywords == {'title': 'Tsunami Max Inundation',
                               'category': 'hazard',
                              'subcategory': 'tsunami',
                              'unit': 'm'}
        myKeywords = readKeywordsFromFile(self.rasterExposurePath)
        print myKeywords == {'category': 'exposure',
                             'subcategory': 'building'}


if __name__ == '__main__':
    suite = unittest.makeSuite(ISSafeInterfaceTest, 'test')
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
