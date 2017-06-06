import math
import json

import pyflowgo.base.flowgo_base_relative_viscosity_model


class FlowGoRelativeViscosityModelCosta2(pyflowgo.base.flowgo_base_relative_viscosity_model.
                                         FlowGoBaseRelativeViscosityModel):
    """This methods permits to calculate the effect of crystal cargo on viscosity according to Costa et al []
    This relationship considers the strain rate and allows to evautate the effect of high crystal fraction
    (above maximum packing).
    The input parameters include the variable crystal fraction (phi) and other parameters depending on the aspect ratio
    of the crystals.
    Here the method costa1 corresponds to case where:
        for strain-rate = 1s-1, phi_max = 0.44
    for strain-rate = 10-4 s-1, phi_max= 0.36,

    The inputs parameters correspond to the particles B from Cimarelli et al. [2011]

    References:
    ---------


    """

    _strain_rate = 1.

    def read_initial_condition_from_json_file(self, filename):
        # read json parameters file
        with open(filename) as data_file:
            data = json.load(data_file)
            self._strain_rate = float(data['relative_viscosity_parameters']['strain_rate'])

    def compute_relative_viscosity(self, state):

        phi = state.get_crystal_fraction()
        if self._strain_rate == 1.0:
            # needle-like B particles from Cimarelli et al., 2011
            # self.phi_max_2 = 0.44
            delta_1 = 4.45
            gama_1 = 8.55
            phi_star_1 = 0.28
            epsilon_1 = 0.001

            f = (1. - epsilon_1) * math.erf(min(25., (
                (math.sqrt(math.pi) / (2. * (1. - epsilon_1))) * (phi / phi_star_1) * (
                    1. + (math.pow((phi / phi_star_1), gama_1))))))

            relative_viscosity = (1. + math.pow((phi / phi_star_1), delta_1)) / (
                math.pow((1. - f), (2.5 * phi_star_1)))
            return relative_viscosity

        if self._strain_rate == 0.0001:
            # needle-like, B particles from Cimarelli et al., 2011
            # self.phi_max = 0.36
            delta_1 = 7.5
            gama_1 = 5.5
            phi_star_1 = 0.26
            epsilon_1 = 0.0002

            f = (1. - epsilon_1) * math.erf(min(25., (
                (math.sqrt(math.pi) / (2. * (1. - epsilon_1))) * (phi / phi_star_1) * (
                    1. + (math.pow((phi / phi_star_1), gama_1))))))

            relative_viscosity = (1. + math.pow((phi / phi_star_1), delta_1)) / (
                math.pow((1. - f), (2.5 * phi_star_1)))
            return relative_viscosity

