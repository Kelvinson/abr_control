import numpy as np
import os
import scipy.special

from .signal import Signal

try:
    import nengo
except ImportError:
    raise Exception('Nengo module needs to be installed to ' +
                    'use adaptive dynamics.')

nengolib = None
try:
    import nengolib
except ImportError:
    print('Nengo lib not installed, encoder placement will be sub-optimal.')


class DynamicsAdaptation(Signal):
    """ An implementation of nonlinear dynamics adaptation using Nengo,
    as described in (DeWolf, Stewart, Slotine, and Eliasmith, 2016)

    The model learns to account for unknown / unmodelled external or
    internal forces, using an efferent copy of the control signal to train.

    Parameters
    ----------
    robot_config : class instance
        contains all relevant information about the arm
        such as: number of joints, number of links, mass information etc.
    n_neurons : int, optional (Default: 1000)
        number of neurons per adaptive population
    n_adapt_pop : int, optional (Default: 1)
        number of adaptive populations
    pes_learning_rate : float, optional (Default: 1e-6)
        controls the speed of neural adaptation
    intercepts list : list of two floats, optional (Default: (0.5, 1.0))
        voltage threshold range for neurons
    spiking : boolean, optional (Default: False)
        use spiking or rate mode neurons
    filter_error : boolean, optional (Default: False)
        apply low pass filter to the error signal or not
    weights_file : string, optional (Default: None)
        path to file where learned weights are saved
    backend : string, optional (Default: nengo)
        {'nengo', 'nengo_ocl', 'nengo_spinnaker'}
    use_dq : boolean, optional (Default: False)
        set True to pass in position and velocity,
        False if only passing in position
    """

    def __init__(self, robot_config,
                 n_neurons=1000,
                 n_adapt_pop=1,
                 pes_learning_rate=1e-6,
                 intercepts=(0.5, 1.0),
                 spiking=False,
                 filter_error=False,
                 weights_file=None,
                 backend='nengo',
                 use_dq=False):
        self.robot_config = robot_config

        self.u_adapt = np.zeros(self.robot_config.N_JOINTS)

        self.use_dq = use_dq

        if self.use_dq is True:
            self.N_INPUTS = 2
        else:
            self.N_INPUTS = 1

        weights_file = (['']*n_adapt_pop if
                        weights_file is None else weights_file)

        dim = self.robot_config.N_JOINTS
        nengo_model = nengo.Network(seed=10)
        with nengo_model:

            # create a Node for passing in the scaled system feedback
            def qdq_input(t):
                """ returns q and dq """

                q = ((self.q + np.pi) % (np.pi*2)) - np.pi

                if self.use_dq is True:
                    output = (np.hstack([
                              self.robot_config.scaledown('q', q),
                              self.robot_config.scaledown('dq', self.dq)]))
                else:
                    output = np.hstack([
                        self.robot_config.scaledown('q', q)])

                return output
            qdq_input = nengo.Node(qdq_input, size_out=dim * self.N_INPUTS)

            # create a Node for passing in the training signal
            def u_input(t):
                """ returns the control signal for training """

                return self.training_signal
            u_input = nengo.Node(u_input, size_out=dim)

            # create a Node for saving the adaptive population output
            def u_adapt_output(t, x):
                """ stores the adaptive output for use in control() """

                self.u_adapt = np.copy(x)
            output = nengo.Node(u_adapt_output, size_in=dim, size_out=0)

            adapt_ens = []
            conn_learn = []
            for ii in range(n_adapt_pop):
                N_DIMS = self.robot_config.N_JOINTS * self.N_INPUTS
                intercepts = AreaIntercepts(
                    dimensions=N_DIMS,
                    base=nengo.dists.Uniform(intercepts[0], intercepts[1]))

                if spiking:
                    neuron_type = nengo.LIF()
                else:
                    neuron_type = nengo.LIFRate()

                # create the adaptive ensembles
                adapt_ens.append(nengo.Ensemble(
                    n_neurons=n_neurons,
                    dimensions=N_DIMS,
                    intercepts=intercepts,
                    neuron_type=neuron_type))

                try:
                    # if the NengoLib is installed, use it
                    # to optimize encoder placement
                    adapt_ens.encoders = (
                        nengolib.stats.ScatteredHypersphere(
                            surface=True))
                except AttributeError:
                    pass

                # proved context signal to adaptive population
                nengo.Connection(
                    qdq_input,
                    adapt_ens[ii][:N_DIMS],
                    synapse=0.005)

                # load weights from file if they exist, otherwise use zeros
                print('%s' % weights_file[ii])
                if os.path.isfile('%s' % weights_file[ii]):
                    transform = np.load(weights_file[ii])['weights'][-1][0]
                    print('Loading transform: \n', transform)
                    print('Transform all zeros: ', np.allclose(transform, 0))
                else:
                    print('Transform is zeros')
                    transform = np.zeros((adapt_ens[ii].n_neurons,
                                          self.robot_config.N_JOINTS)).T
                # set up learning connections
                if backend == 'nengo_spinnaker':
                    conn_learn.append(
                        nengo.Connection(
                            adapt_ens[ii],
                            output,
                            learning_rule_type=nengo.PES(pes_learning_rate),
                            solver=DummySolver(transform.T)))
                else:
                    conn_learn.append(
                        nengo.Connection(
                            adapt_ens[ii].neurons,
                            output,
                            learning_rule_type=nengo.PES(pes_learning_rate),
                            transform=transform))

                # Allow filtering of error signal
                def gate_error(x):
                    """ Filters the error, if filter_error is True """

                    if filter_error:
                        if np.linalg.norm(x) > 2.0:
                            x /= np.linalg.norm(x) * 0.5
                    return x
                nengo.Connection(u_input, conn_learn[ii].learning_rule,
                                 # invert to provide error not reward
                                 transform=-1,
                                 function=gate_error,
                                 synapse=0.01)

        nengo.cache.DecoderCache().invalidate()
        if backend == 'nengo':
            self.sim = nengo.Simulator(nengo_model, dt=.001)
        elif backend == 'nengo_ocl':
            try:
                import nengo_ocl
            except ImportError:
                raise Exception('Nengo OCL not installed, ' +
                                'cannot use this backend.')
            import pyopencl as cl
            # Here, the context would be to use all devices from platform [0]
            ctx = cl.Context(cl.get_platforms()[0].get_devices())
            self.sim = nengo_ocl.Simulator(nengo_model, context=ctx, dt=.001)
        elif backend == 'nengo_spinnaker':
            try:
                import nengo_spinnaker
            except ImportError:
                raise Exception('Nengo SpiNNaker not installed, ' +
                                'cannot use this backend.')
            self.sim = nengo_spinnaker.Simulator(nengo_model)
            self.q = np.zeros(self.robot_config.N_JOINTS)
            self.dq = np.zeros(self.robot_config.N_JOINTS)
            self.training_signal = np.zeros(self.robot_config.N_JOINTS)
            # start running the spinnaker model
            self.sim.async_run_forever()
        else:
            raise Exception('Invalid backend specified')
        self.backend = backend

    def generate(self, q, dq, training_signal):
        """ Generates the control signal

        Parameters
        ----------
        q : numpy.array
            the current joint angles [radians]
        dq : numpy.array
            the current joint velocities [radians/second]
        training_signal : numpy.array
            the learning signal to drive adaptation
        """

        # store local copies to feed in to the adaptive population
        self.q = q
        self.dq = dq
        self.training_signal = training_signal

        # run the simulation t generate the adaptive signal
        if self.backend == 'nengo' or self.backend == 'nengo_ocl':
            self.sim.run(time_in_seconds=.001, progress_bar=False)
        elif self.backend == 'nengo_spinnaker':
            # update spinnaker inputs
            self.sim.async_update()
        else:
            self.sim.run(time_in_seconds=.001)

        return self.u_adapt


class DummySolver(nengo.solvers.Solver):
    """ A Nengo weights solver that returns a provided set of weights.
    """


    def __init__(self, fixed):
        self.fixed = fixed
        self.weights = False

    def __call__(self, A, Y, rng=None, E=None):
        return self.fixed, {}


class AreaIntercepts(nengo.dists.Distribution):
    """ Generate an optimally distributed set of intercepts in
    high-dimensional space.
    """
    dimensions = nengo.params.NumberParam('dimensions')
    base = nengo.dists.DistributionParam('base')

    def __init__(self, dimensions, base=nengo.dists.Uniform(-1, 1)):
        super(AreaIntercepts, self).__init__()
        self.dimensions = dimensions
        self.base = base

    def __repr(self):
        return ("AreaIntercepts(dimensions=%r, base=%r)" %
                (self.dimensions, self.base))

    def transform(self, x):
        sign = 1
        if x > 0:
            x = -x
            sign = -1
        return sign * np.sqrt(1 - scipy.special.betaincinv(
            (self.dimensions + 1) / 2.0, 0.5, x + 1))

    def sample(self, n, d=None, rng=np.random):
        s = self.base.sample(n=n, d=d, rng=rng)
        for i in range(len(s)):
            s[i] = self.transform(s[i])
        return s
