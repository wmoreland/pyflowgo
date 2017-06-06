import pyflowgo.flowgo_logger


class FlowGoIntegrator:

    """ The integrator allows to make the flow front advancing
    It is here that the differential equation of the flow advance is solved
    and here where the limits are fixed"""

    def __init__(self, dx, material_lava, material_air, terrain_condition, heat_budget,
                 crystallization_rate_model):
        """ this function allows to set the initial parameters"""
        self.logger = pyflowgo.flowgo_logger.FlowGoLogger()
        self.dx = dx  # in m
        self._has_finished = False
        self.effusion_rate = 0.
        self.iteration = 0.
        self.crystallization_rate_model = crystallization_rate_model
        self.material_lava = material_lava
        self.material_air = material_air
        self.terrain_condition = terrain_condition
        self.heat_budget = heat_budget

    def single_step(self, current_state):
        """This function makes the flow advancing it takes the velocity that was calculated in material lava and check
        whether it is positif and then calculate the heat budget in order to get the new temperature and new crystal
        content in order to get the new viscosity and therefore with this new viscosity it calculate the new velocity
        as a function of the slope at this current location (that is given by the slope_distance file or by
        interpolation of it)"""

        v_mean = self.material_lava.compute_mean_velocity(current_state, self.terrain_condition)

        if v_mean <= 0.:
            self._has_finished = True
            return
        #print('Vmean=', v_mean)

        # computes the quantities at this current state from the terrain condition
        channel_depth = self.terrain_condition.get_channel_depth(current_state.get_current_position())

        # Here we set the initial condition (iteration = 0) and calculate the effusion rate
        if self.iteration == 0.:
            channel_width = self.terrain_condition.get_channel_width(current_state.get_current_position())
            self.effusion_rate = v_mean * channel_width * channel_depth
            print('effusion_rate =' + str(self.effusion_rate))

        # Here we start the loop
        # Base on mass conservation, the effusion rate and the depth channel are kept fixed, so the width can
        # be calculated at each step :
        channel_width = self.effusion_rate / (v_mean * channel_depth)

        #TODO: Here I add the slope:ASK MIMI TO MOVE IT FROM HERE
        channel_slope = self.terrain_condition.get_channel_slope(current_state.get_current_position())
        #print("slope=",channel_slope)

        # ------------------------------------------------- HEAT BUDGET ------------------------------------------------
        # Here the right hand side (rhs) from Eq. 7b, Harris and Rowland (2001)
        # rhs = dT/dx

        rhs = -self.heat_budget.compute_heat_budget(current_state, channel_width, channel_depth)

        # ------------------------------------------------ COOLING RATE ------------------------------------------------
        # 4) now we calculate the temperature variation
        # first we need the crystallization_rate = dphi_dtemp this will be changed by looking directly into pyMELTS,
        # to get the right amount of crystals at this new temperature.
        # crystallization rate model
        dphi_dtemp = self.crystallization_rate_model.compute_crystallization_rate(current_state) # je rajoute current state 23 dec

        # Cooling per unit of distance is calculated
        # from Eq. 7b HR01 / Eq. 21 HR14 / Eq. 15 Harris et al. 2015 / Eq. 21 HR14
        bulk_density = self.material_lava.get_bulk_density(current_state)
        latent_heat_of_crystallization = self.material_lava.get_latent_heat_of_crystallization()

        # Here we solve the differential equation
        dtemp_dx = (rhs / (self.effusion_rate * bulk_density * latent_heat_of_crystallization * dphi_dtemp))
        #print(dphi_dtemp)
        # ------------------------------------------ CRYSTALLIZATION PER METER -----------------------------------------
        dphi_dx = dtemp_dx * (-dphi_dtemp)

        # ------------------------- NEW CRYSTAL FRACTION AND NEW TEMPERATURE USED FOR NEXT STEP ------------------------
        # the new cristal fraction due to the temperature decrease for the current step is
        # (Euler step for solving differential equation) :

        phi = current_state.get_crystal_fraction()
        new_phi = phi + (dphi_dx * self.dx)
        print('phi=',new_phi)

        # ------------------------------------------ NOW WE JUMP TO THE NEXT STEP --------------------------------------
        # we calculate the new core temperature in K for the the next line, using Euler as well

        temp_core = current_state.get_core_temperature()
        new_temp_core = temp_core + dtemp_dx * self.dx
        print('Tcore=',new_temp_core)
        # ------------------------------------- LOG ALL THE VALUES INTO THE LOGGER -------------------------------------
        self.logger.add_variable("channel_width", current_state.get_current_position(), channel_width)
        self.logger.add_variable("crystal_fraction", current_state.get_current_position(),
                                 current_state.get_crystal_fraction())
        self.logger.add_variable("core_temperature", current_state.get_current_position(),
                                 current_state.get_core_temperature())
        self.logger.add_variable("viscosity", current_state.get_current_position(),
                                 self.material_lava.computes_bulk_viscosity(current_state))
        self.logger.add_variable("mean_velocity", current_state.get_current_position(), v_mean)
        self.logger.add_variable("core_temperature", current_state.get_current_position(),
                                 current_state.get_core_temperature())
        self.logger.add_variable("dphi_dx", current_state.get_current_position(), dphi_dx)
        self.logger.add_variable("dtemp_dx", current_state.get_current_position(), dtemp_dx)
        #self.logger.add_variable("latent_heat_of_crystallization", current_state.get_current_position(),
                                 #latent_heat_of_crystallization)
        self.logger.add_variable("dphi_dtemp", current_state.get_current_position(), dphi_dtemp)
        #TODO : here I added the log of the time in s, the slope, the effusion rate and the channel depth
        self.logger.add_variable("current_time", current_state.get_current_position(),
                                 current_state.get_current_time())
        self.logger.add_variable("slope", current_state.get_current_position(), channel_slope)
        self.logger.add_variable("effusion_rate", current_state.get_current_position(), str(self.effusion_rate))
        self.logger.add_variable("channel_depth", current_state.get_current_position(),channel_depth)





        # -------------------------- UPDATE THE STATE WITH NEW CRYSTAL FRACTION AND NEW TEMPERATURE ----------------
        current_state.set_crystal_fraction(new_phi)
        current_state.set_core_temperature(new_temp_core)

        current_state.set_current_position(current_state.get_current_position() + self.dx)
        current_state.set_current_time(current_state.get_current_time() + self.dx / v_mean)

        self.iteration += 1.

        if (new_temp_core <= self.crystallization_rate_model.get_solid_temperature()) or (new_phi >= 0.52) \
                or (current_state.get_current_position() >= self.terrain_condition.get_max_channel_length()):
            self._has_finished = True
            return
    # ------------------------------------------------ FINISH THE LOOP -------------------------------------------------

    def has_finished(self):
        return self._has_finished

    def read_initial_condition_from_json_file(self, filename):
        # read json parameters file\
        pass
    # ------------------------------------------------ INITIALIZE THE STATE --------------------------------------------

    def initialize_state(self, current_state, filename):

        current_state.read_initial_condition_from_json_file(filename)

        # retrieve other values from external
        initial_temperature = self.material_lava.get_eruption_temperature()
        initial_crystal_fraction = self.crystallization_rate_model.get_crystal_fraction(initial_temperature)

        current_state.set_crystal_fraction(initial_crystal_fraction)
        current_state.set_core_temperature(initial_temperature)