"""
using the input from a provided test and the desired upper and lower limits of
a triangular distribution, the script will run through every possible set of
intercepts and modes. The sets that provide activity that matches the ideal the
closest will be plotted along with their intercept values.
"""
from abr_control.utils import DataHandler, LearningProfile
from abr_control.controllers import signals
import numpy as np
import time as t
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

class IdealIntercepts():
    def generate_possible_intercepts(self):
        # Create list of all possible intercepts
        # the stop value does not get included, so we use 1.0 instead of 0.9
        intercept_range = np.arange(-.9, 1.0, .1)
        mode_range = np.arange(-.9, 1.0, .2)

        intercepts = np.array(np.meshgrid(intercept_range, intercept_range)).T.reshape(-1, 2)

        # get a list of all valid intercepts
        valid = []
        rej = []
        use_spherical=True
        for vals in intercepts:
            vals[0] = round(vals[0], 1)
            vals[1] = round(vals[1], 1)
            if vals[0] < vals[1]:
                for mode in mode_range:
                    mode = round(mode, 1)
                    if vals[0] <= mode and mode <= vals[1]:
                        if use_spherical:
                            valid.append(np.array([vals[0],vals[1], mode]))
                        else:
                            if vals[0] < 0 and vals[1] > 0:
                                valid.append(np.array([vals[0], vals[1], mode]))

        intercepts = np.array(valid)
        print('There are %i valid combinations of intercepts and modes'%len(intercepts))
        return intercepts

    def ideal_profile(self, n_neurons, n_bins):
        # the following are two points on a line that will be used to create the ideal
        # distribution that will be compared against to find the closest match
        # [proportion_neurons_active, proportion_of_time_active]
        max_activity = [0.1, 0]
        min_activity = [0, 0.6]
        # Create the ideal distribution
        n_line_points = int(min_activity[1] * n_bins)
        n_zero_points = n_bins-n_line_points-1

        # want 10% activity at 0 prop time and <5% at 0.6 prop time
        ideal_dist = np.hstack((np.linspace(max_activity[0]*n_neurons,
            min_activity[0]*n_neurons, n_line_points),
                            np.zeros(n_zero_points)))
        return ideal_dist

    def run_intercept_scan(
            self, n_input, n_output, n_neurons, n_ensembles, pes_learning_rate,
            backend, seed, neuron_type, encoders, input_signal, save_name='test1'):

        min_to_plot = 10
        learning = LearningProfile()
        self.dat = DataHandler(db_name='ideal_intercepts')

        intercepts = self.generate_possible_intercepts()
        length = len(intercepts)

        n_bins = 100
        bins = np.linspace(0,1,n_bins)
        ideal = self.ideal_profile(n_neurons, n_bins)
        self.dat.save(
                data={'ideal': ideal},
                save_location='%s'%save_name,
                overwrite=True)

        for ii ,intercept in enumerate(intercepts) :
            if ii == min_to_plot:
                break
            print('%.2f%% complete'%(ii/length*100), end='\r')

            intercept_list = signals.AreaIntercepts(
                dimensions=n_input,
                base=signals.Triangular(intercept[0], intercept[2], intercept[1]))

            rng = np.random.RandomState(seed)
            intercept_list = intercept_list.sample(n_neurons, rng=rng)
            intercept_list = np.array(intercept_list)

            network = signals.DynamicsAdaptation(
                n_input=n_input,
                n_output=n_output,
                n_neurons=n_neurons,
                n_ensembles=n_ensembles,
                pes_learning_rate=1e-6,
                intercepts=intercept_list,
                backend=backend,
                probe_weights=True,
                seed=seed,
                neuron_type=neuron_type,
                encoders=encoders)

            [time_active, activity] = learning.prop_time_neurons_active(
                                            network=network,
                                            input_signal=input_signal)

            # check how many neurons are never active
            num_inactive = 0
            num_active = 0
            for ens in activity:
                ens = ens.T
                for nn, neuron in enumerate(ens):
                    if np.sum(ens[nn]) == 0:
                        num_inactive += 1
                    else:
                        num_active += 1

            print(np.array(activity).shape)
            # save the data for the line plot of the histogram
            y, bins_out = np.histogram(np.squeeze(time_active), bins=bins)
            centers = 0.5*(bins_out[1:]+bins_out[:-1])
            prop_time = centers
            neurons_active = y
            diff_to_ideal = ideal-neurons_active

            data = {'activity': activity, 'intercept_bounds': intercept[:2],
                    'intercept_mode': intercept[2], 'diff_to_ideal': diff_to_ideal,
                    'prop_time': prop_time, 'neurons_active': neurons_active,
                    'num_active': num_active, 'num_inactive': num_inactive,
                    'error': np.sum(np.abs(diff_to_ideal))}
            self.dat.save(data=data, save_location='%s/%05d'%(save_name, ii), overwrite=True)

        self.review(save_name=save_name, min_to_plot=min_to_plot)

    def review(self, save_name, min_to_plot=10):
        # Plot the activity for the 5 sets of intercepts with the least deviation from
        # the ideal
        run_data = []
        errors = []

        for ii in range(0,min_to_plot) :
            data = self.dat.load(
                    params=['intercept_bounds', 'intercept_mode', 'diff_to_ideal',
                    'neurons_active', 'prop_time', 'error', 'num_active', 'num_inactive'],
                    save_location='%s/%05d'%(save_name,ii))
            run_data.append(data)
            errors.append(data['error'])
        ideal = self.dat.load(params=['ideal'], save_location='%s'%save_name)['ideal']

        indices = np.array(errors).argsort()[:min_to_plot]
        print('Plotting...')
        plt.figure()
        for ii in range(0, min_to_plot):
            ind = indices[ii]
            data = run_data[ind]
            #plt.title('Active: %i | Inactive: %i'%(data['num_active'], data['num_inactive']))
            plt.plot(np.squeeze(data['prop_time']), np.squeeze(data['neurons_active']),
                    label='%i: err:%.2f \n%s: %s'%
                    (ind, data['error'], data['intercept_bounds'], data['intercept_mode']))

        plt.plot(np.squeeze(data['prop_time']), ideal, label='ideal')
        plt.legend()
        plt.show()
