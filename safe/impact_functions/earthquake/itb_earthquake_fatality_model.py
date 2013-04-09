from safe.impact_functions.core import (FunctionProvider,
                                        get_hazard_layer,
                                        get_exposure_layer,
                                        get_question)
from safe.storage.raster import Raster
from safe.common.utilities import (ugettext as tr,
                                   get_defaults,
                                   format_int)
from safe.common.tables import Table, TableRow
from safe.common.exceptions import InaSAFEError
from third_party.odict import OrderedDict

import numpy


class ITBFatalityFunction(FunctionProvider):
    """Indonesian Earthquake Fatality Model

    This model was developed by Institut Tecknologi Bandung (ITB) and
    implemented by Dr Hadi Ghasemi, Geoscience Australia


    Reference:

    Indonesian Earthquake Building-Damage and Fatality Models and
    Post Disaster Survey Guidelines Development,
    Bali, 27-28 February 2012, 54pp.


    Algorithm:

    In this study, the same functional form as Allen (2009) is adopted
    to express fatality rate as a function of intensity (see Eq. 10 in the
    report). The Matlab built-in function (fminsearch) for  Nelder-Mead
    algorithm was used to estimate the model parameters. The objective
    function (L2G norm) that is minimised during the optimisation is the
    same as the one used by Jaiswal et al. (2010).

    The coefficients used in the indonesian model are
    x=0.62275231, y=8.03314466, zeta=2.15

    Allen, T. I., Wald, D. J., Earle, P. S., Marano, K. D., Hotovec, A. J.,
    Lin, K., and Hearne, M., 2009. An Atlas of ShakeMaps and population
    exposure catalog for earthquake loss modeling, Bull. Earthq. Eng. 7,
    701-718.

    Jaiswal, K., and Wald, D., 2010. An empirical model for global earthquake
    fatality estimation, Earthq. Spectra 26, 1017-1037.


    Caveats and limitations:

    The current model is the result of the above mentioned workshop and
    reflects the best available information. However, the current model
    has a number of issues listed below and is expected to evolve further
    over time.

    1 - The model is based on limited number of observed fatality
        rates during 4 past fatal events.
    2 - The model clearly over-predicts the fatality rates at
        intensities higher than VIII.
    3 - The model only estimates the expected fatality rate for a given
        intensity level; however the associated uncertainty for the proposed
        model is not addressed.
    4 - There are few known mistakes in developing the current model:
        - rounding MMI values to the nearest 0.5,
        - Implementing Finite-Fault models of candidate events, and
        - consistency between selected GMPEs with those in use by BMKG.
          These issues will be addressed by ITB team in the final report.

    Note: Because of these caveats, decisions should not be made solely on
    the information presented here and should always be verified by ground
    truthing and other reliable information sources.

    :author Hadi Ghasemi
    :rating 3

    :param requires category=='hazard' and \
                    subcategory=='earthquake' and \
                    layertype=='raster' and \
                    unit=='MMI'

    :param requires category=='exposure' and \
                    subcategory=='population' and \
                    layertype=='raster'

    """

    title = tr('Die or be displaced')
    synopsis = tr('To asses the impact of earthquake on population based on '
                  'earthquake model developed by ITB')
    citations = \
        tr(' * Indonesian Earthquake Building-Damage and Fatality Models and '
           '   Post Disaster Survey Guidelines Development Bali, 27-28 '
           '   February 2012, 54pp.\n'
           ' * Allen, T. I., Wald, D. J., Earle, P. S., Marano, K. D., '
           '   Hotovec, A. J., Lin, K., and Hearne, M., 2009. An Atlas '
           '   of ShakeMaps and population exposure catalog for '
           '   earthquake loss modeling, Bull. Earthq. Eng. 7, 701-718.\n'
           ' * Jaiswal, K., and Wald, D., 2010. An empirical model for '
           '   global earthquake fatality estimation, Earthq. Spectra '
           '   26, 1017-1037.\n')
    limitation = \
        tr(' - The model is based on limited number of observed fatality '
           '   rates during 4 past fatal events. \n'
           ' - The model clearly over-predicts the fatality rates at '
           '   intensities higher than VIII.\n'
           ' - The model only estimates the expected fatality rate '
           '   for a given intensity level; however the associated '
           '   uncertainty for the proposed model is not addressed.\n'
           ' - There are few known mistakes in developing the current '
           '   model:\n\n'
           '   * rounding MMI values to the nearest 0.5,\n'
           '   * Implementing Finite-Fault models of candidate events, and\n'
           '   * consistency between selected GMPEs with those in use by '
           '     BMKG.\n')
    actions = tr('Provide details about the population will be die or '
                 'displaced')
    detailed_description = \
        tr('This model was developed by Institut Tecknologi Bandung (ITB) '
           'and implemented by Dr Hadi Ghasemi, Geoscience Australia\n'
           'Algorithm:\n'
           'In this study, the same functional form as Allen (2009) is '
           'adopted o express fatality rate as a function of intensity '
           '(see Eq. 10 in the report). The Matlab built-in function '
           '(fminsearch) for  Nelder-Mead algorithm was used to estimate '
           'the model parameters. The objective function (L2G norm) that '
           'is minimized during the optimisation is the same as the one '
           'used by Jaiswal et al. (2010).\n'
           'The coefficients used in the indonesian model are x=0.62275231, '
           'y=8.03314466, zeta=2.15')
    defaults = get_defaults()
    parameters = OrderedDict([
        ('x', 0.62275231), ('y', 8.03314466),  # Model coefficients
        # Rates of people displaced for each MMI level
        ('displacement_rate', {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1.0,
                               7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0}),
        ('mmi_range', range(2, 10)),
        ('step', 0.5),
        # Threshold below which layer should be transparent
        ('tolerance', 0.01),
        ('calculate_displaced_people', True),
        ('postprocessors', OrderedDict([
            ('Gender', {'on': True}),
            ('Age', {
                'on': True,
                'params': OrderedDict([
                    ('youth_ratio', defaults['YOUTH_RATIO']),
                    ('adult_ratio', defaults['ADULT_RATIO']),
                    ('elder_ratio', defaults['ELDER_RATIO'])])})]))])

    def fatality_rate(self, mmi):
        """
        ITB method to compute fatality rate
        :param x: model coefficient.
        :param y: model coefficient.
        """
        # As per email discussion with Ole, Trevor, Hadi, mmi < 4 will have
        # a fatality rate of 0 - Tim
        if mmi < 4:
            return 0

        x = self.parameters['x']
        y = self.parameters['y']
        return numpy.power(10.0, x * mmi - y)

    def run(self, layers):
        """Indonesian Earthquake Fatality Model

        Input
          layers: List of layers expected to contain
              H: Raster layer of MMI ground shaking
              P: Raster layer of population density

        """

        # Define percentages of people being displaced at each mmi level
        displacement_rate = self.parameters['displacement_rate']

        # Tolerance for transparency
        tolerance = self.parameters['tolerance']

        # Extract input layers
        intensity = get_hazard_layer(layers)
        population = get_exposure_layer(layers)

        question = get_question(intensity.get_name(),
                                population.get_name(),
                                self)

        # Extract data grids
        H = intensity.get_data()   # Ground Shaking
        P = population.get_data(scaling=True)  # Population Density

        # Calculate population affected by each MMI level
        # FIXME (Ole): this range is 2-9. Should 10 be included?

        mmi_range = self.parameters['mmi_range']
        number_of_exposed = {}
        number_of_displaced = {}
        number_of_fatalities = {}

        # Calculate fatality rates for observed Intensity values (H
        # based on ITB power model
        R = numpy.zeros(H.shape)
        for mmi in mmi_range:

            # Identify cells where MMI is in class i and
            # count population affected by this shake level
            I = numpy.where(
                (H > mmi - self.parameters['step']) * (
                    H <= mmi + self.parameters['step']), P, 0)

            # Calculate expected number of fatalities per level
            fatality_rate = self.fatality_rate(mmi)

            F = fatality_rate * I

            # Calculate expected number of displaced people per level
            try:
                D = displacement_rate[mmi] * I
            except KeyError, e:
                msg = 'mmi = %i, I = %s, Error msg: %s' % (mmi, str(I), str(e))
                raise InaSAFEError(msg)

            # Adjust displaced people to disregard fatalities.
            # Set to zero if there are more fatalities than displaced.
            D = numpy.where(D > F, D - F, 0)

            # Sum up numbers for map
            R += D   # Displaced

            # Generate text with result for this study
            # This is what is used in the real time system exposure table
            number_of_exposed[mmi] = numpy.nansum(I.flat)
            number_of_displaced[mmi] = numpy.nansum(D.flat)
            number_of_fatalities[mmi] = numpy.nansum(F.flat)

        # Set resulting layer to NaN when less than a threshold. This is to
        # achieve transparency (see issue #126).
        R[R < tolerance] = numpy.nan

        # Total statistics
        total = int(round(numpy.nansum(P.flat) / 1000) * 1000)

        # Compute number of fatalities
        fatalities = int(round(numpy.nansum(number_of_fatalities.values())
                               / 1000)) * 1000
        # As per email discussion with Ole, Trevor, Hadi, total fatalities < 50
        # will be rounded down to 0 - Tim
        if fatalities < 50:
            fatalities = 0

        # Compute number of people displaced due to building collapse
        displaced = int(round(numpy.nansum(number_of_displaced.values())
                              / 1000)) * 1000

        # Generate impact report
        table_body = [question]

        # Add total fatality estimate
        #s = str(int(fatalities)).rjust(10)
        s = format_int(fatalities)
        table_body.append(TableRow([tr('Number of fatalities'), s],
                                   header=True))

        if self.parameters['calculate_displaced_people']:
            # Add total estimate of people displaced
            #s = str(int(displaced)).rjust(10)
            s = format_int(displaced)
            table_body.append(TableRow([tr('Number of people displaced'), s],
                                       header=True))
        else:
            displaced = 0

        # Add estimate of total population in area
        #s = str(int(total)).rjust(10)
        s = format_int(int(total))
        table_body.append(TableRow([tr('Total number of people'), s],
                                   header=True))

        # Calculate estimated needs based on BNPB Perka 7/2008 minimum bantuan
        # FIXME: Refactor and share
        rice = int(displaced * 2.8)
        drinking_water = int(displaced * 17.5)
        water = int(displaced * 67)
        family_kits = int(displaced / 5)
        toilets = int(displaced / 20)

        # Generate impact report for the pdf map
        table_body = [question,
                      TableRow([tr('Fatalities'),
                                '%s' % format_int(fatalities)],
                               header=True),
                      TableRow([tr('People displaced'),
                                '%s' % format_int(displaced)],
                               header=True),
                      TableRow(tr('Map shows density estimate of '
                                  'displaced population')),
                      TableRow([tr('Needs per week'), tr('Total')],
                               header=True),
                      [tr('Rice [kg]'), format_int(rice)],
                      [tr('Drinking Water [l]'), format_int(drinking_water)],
                      [tr('Clean Water [l]'), format_int(water)],
                      [tr('Family Kits'), format_int(family_kits)],
                      [tr('Toilets'), format_int(toilets)]]
        impact_table = Table(table_body).toNewlineFreeString()

        table_body.append(TableRow(tr('Action Checklist:'), header=True))
        if fatalities > 0:
            table_body.append(tr('Are there enough victim identification '
                                 'units available for %s people?') %
                              format_int(fatalities))
        if displaced > 0:
            table_body.append(tr('Are there enough shelters and relief items '
                                 'available for %s people?')
                              % format_int(displaced))
            table_body.append(TableRow(tr('If yes, where are they located and '
                                          'how will we distribute them?')))
            table_body.append(TableRow(tr('If no, where can we obtain '
                                          'additional relief items from and '
                                          'how will we transport them?')))

        # Extend impact report for on-screen display
        table_body.extend([TableRow(tr('Notes'), header=True),
                           tr('Total population: %s') % format_int(total),
                           tr('People are considered to be displaced if '
                              'they experience and survive a shake level'
                              'of more than 5 on the MMI scale '),
                           tr('Minimum needs are defined in BNPB '
                              'regulation 7/2008'),
                           tr('The fatality calculation assumes that '
                              'no fatalities occur for shake levels below 4 '
                              'and fatality counts of less than 50 are '
                              'disregarded.'),
                           tr('All values are rounded up to the nearest '
                              'integer in order to avoid representing human '
                              'lives as fractionals.')])

        # impact_summary = Table(table_body).toNewlineFreeString()
        # map_title = tr('People in need of evacuation')

        table_body.append(TableRow(tr('Notes'), header=True))
        table_body.append(tr('Fatality model is from '
                             'Institute of Teknologi Bandung 2012.'))
        table_body.append(tr('Population numbers rounded to nearest 1000.'))

        impact_summary = Table(table_body).toNewlineFreeString()
        impact_table = impact_summary
        map_title = tr('Earthquake impact to population')

        # Create style info dynamically
        classes = numpy.linspace(numpy.nanmin(R.flat[:]),
                                 numpy.nanmax(R.flat[:]), 5)

        # int & round Added by Tim in 1.2 - class is rounded to the
        # nearest int because we prefer to not categorise people as being
        # e.g. '0.4 people'. Fixes #542

        # This should not be needed as numpynanmin should automatically
        # exlude nans.
        #nanfree_classes = []
        #for c in classes:
        #    if numpy.isnan(c):
        #        nanfree_classes.append(0)
        #    else:
        #        nanfree_classes.append(c)
        #classes = nanfree_classes

        style_classes = [
            dict(colour='#EEFFEE',
                 quantity=int(round(classes[0])),
                 transparency=100,
                 label=tr('%i people/cell') % int(round(classes[0]))),
            dict(colour='#FFFF7F',
                 quantity=int(round(classes[1])),
                 transparency=30),
            dict(colour='#E15500',
                 quantity=int(round(classes[2])),
                 transparency=30,
                 label=tr('%i people/cell') % int(round(classes[2]))),
            dict(colour='#E4001B',
                 quantity=int(round(classes[3])),
                 transparency=30),
            dict(colour='#730000',
                 quantity=int(round(classes[4])),
                 transparency=30,
                 label=tr('%i people/cell') % int(round(classes[4])))]
        style_info = dict(target_field=None, style_classes=style_classes)

        # Create new layer and return
        L = Raster(R,
                   projection=population.get_projection(),
                   geotransform=population.get_geotransform(),
                   keywords={'impact_summary': impact_summary,
                             'total_population': total,
                             'total_fatalities': fatalities,
                             'fatalites_per_mmi': number_of_fatalities,
                             'exposed_per_mmi': number_of_exposed,
                             'displaced_per_mmi': number_of_displaced,
                             'impact_table': impact_table,
                             'map_title': map_title},
                   name=tr('Estimated displaced population'),
                   style_info=style_info)

        # Maybe return a shape file with contours instead
        return L
