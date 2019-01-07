from abr_control.utils import DataHandler, make_gif, DataProcessor, DataVisualizer
import numpy as np
import matplotlib
matplotlib.use("TKAgg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d
import subprocess
import os

class VirtualArm():
    """
    Loads the data from the specified run for the provided list of tests and
    plots the desired frame from those tests
    """
    def __init__(self, use_cache=True, db_name=None):
        """
        Sets up save location and clears old figures

        PARAMETERS
        ----------
        use_cache: boolean, Optional (Default:True)
            True to prepend the abr_control cache folder to the directory
            provided. This location is specified in abr_control/utils/paths.py
            False to use the directory pass in as is
        db_name: string
            name of the hdf5 database to load data from
        """
        # set up save location for figures
        if use_cache:
            from abr_control.utils.paths import cache_dir
            save_loc = '%s/figures'%cache_dir
        else:
            save_loc = 'figures'
        # create save location if it does not exist
        if not os.path.exists(save_loc):
            os.makedirs(save_loc)

        if not os.path.exists('%s/gif_fig_cache'%save_loc):
            os.makedirs('%s/gif_fig_cache'%save_loc)

        # delete old files if they exist in the figure cache. These are used to
        # create a gif and need to be deleted to avoid the issue where the
        # current test has fewer images than what is already in the cache, this
        # would lead to the old images being appended to the end of the gif
        files = [f for f in os.listdir('%s/gif_fig_cache'%save_loc) if f.endswith(".png") ]
        for ii, f in enumerate(files):
            if ii == 0:
                print('Deleting old temporary figures for gif creation...')
            os.remove(os.path.join('%s/gif_fig_cache'%save_loc, f))

        # instantiate our data processor
        self.proc = DataProcessor()
        # instantiate our database object
        self.dat = DataHandler(use_cache=use_cache, db_name=db_name)
        # instantiate our data visualizer
        self.vis = DataVisualizer()

    def create_dict(self, test_groups, test_names, session, run,
            show_arm, final_frame, interp_steps=100):
        """
        Loads the required data from the test_names provided and adds them to
        a dictionary, linked to the relevant data to the testgroup-testname

        Returns a dictionary of recorded data

        PARAMETERS
        ----------
        test_groups: list of strings
            list of test groups
        test_names: list of strings
            list of test names
        session: int
            the session number of interest
        run: int
            the run number of interst
        show_arm: list of booleans
            a list True or False whether to show the arm in the plot, or just
            the EE
        interp_steps: int, Optional (Default=100)
            the number of steps to interpolate from the data to align results.
            NOTE: this assumes that the tests passed in are of the same length
            wrt to run time
        final_frame: boolean, Optional (Default=False)
            True to only show the final frame of the run, this greatly shortens
            the processing time
        """
        def load_data(self, save_location, show_arm):
            """
            Loads data from hdf5 database

            This is only run once to load in recorded data and interpolate it
            for even sampling. Afterwards the plot_frame() function can be
            called to plot the specified frame of the movement.

            PARAMETERS
            ----------
            save_location: string
                points to the location in the hdf5 database to read from
            show_arm: bolean
                changes what parameters are loaded, as more are required if
                a virtual arm is to be plotted
            """
            #NOTE: is it worth adding a check to make sure that different tests
            # are of the same length (time)
            # set params depending on whether a virtual arm will be shown
            if show_arm:
                params = ['q', 'error', 'target', 'ee_xyz', 'filter', 'time']
                self.test_data[save_location][show_arm] = True
            else:
                params = ['error', 'ee_xyz', 'time']
                self.test_data[save_location][show_arm] = False
            # load data from hdf5 database
            data = dat.load(params=params,
                    save_location=save_location)
            # interpolate for even sampling and save to our dictionary
            for param in params:
                # looking at entire movement
                if not self.final_frame:
                    data[param] = self.proc.interpolate_data(data=data[param],
                            time_intervals=data['time']), n_points=interp_steps)
                # only interested in final position
                else:
                    data[param] = data[param][-1]
                self.test_data[save_location][param] = data[param]

        self.final_frame = final_frame
        self.show_arm = show_arm
        # in case a single test is passed in, turn it into a list with one
        # entry so we do not run into errors when we try to loop through them
        if not isinstance(test_groups, list):
            test_groups = [test_groups]
        if not isinstance(test_names, list):
            test_names = [test_names]
        if not isinstance(self.show_arm, list):
            self.show_arm = [self.show_arm]

        # instantiate our dictionary to store test data
        self.test_data = {}
        # loop through the list of test names and store the run data to a dict
        for ii in range(0, len(test_names)):
            save_location=('%s/%s/session%03d/run%03d'%
                (test_groups[ii], test_names[ii], session, run))
            # create a dictionary entry for each test based on the group,
            # testname, session, and run
            self.test_data[save_location] = {}
            load_data(save_location=save_location, show_arm=show_arm[ii])

    def get_cartesian_location(self, robot_config, test_key):
        """
        Gets the cartesian coordinates of joints and links

        PARAMETERS
        ----------
        robot_config: instantiated abr_control robot config
            This is required to transform joint angles to cartesian coordinates
        test_key: string
            the key to point to the tests save location in the dictionary
        """

        joint_angles = self.test_data[test_key]['q']
        self.test_data[test_key]['joints_xyz'] = []
        self.test_data[test_key]['links_xyz'] = []
        for q in joint_angles:
            joints_xyz= []
            links_xyz = []
            for ii in range(0, robot_config.N_JOINTS):
                joints_xyz.append(robot_config.Tx('joint%i'%ii, q=q,
                        offset=robot_config.OFFSET))
                # NOTE: do we need to np.copy() this?
            for ii in range(0, robot_config.N_LINKS):
                links_xyz.append(robot_config.Tx('link%i'%ii, q=q,
                        offset=robot_config.OFFSET))
            # NOTE: do we need to np.copy() this?
            self.test_data[test_key]['joints_xyz'].append(joints_xyz)
            self.test_data[test_key]['links_xyz'].append(links_xyz)

    def check_limits(self):
        """
        Checks limits to note collisions with floor

        PARAMETERS
        ----------
        """
        raise Exception ("""The check_limits feature is currently not supported""")
        # if any joint drops below the origin, change its color to red
        for kk, j in enumerate(joints):
            # 0.04m == radius of elbow joint
            if j[2] < 0.04:
                colors[kk] = 'r'
                marker_size[kk] = 2**9
                marker[kk] = '*'
            else:
                colors[kk] = 'k'
                marker_size[kk] = 2**5
                marker[kk] = 'o'

    def generate(self, robot_config=None,
            run, session, test_groups, test_names, show_arm,
            final_frame=False, interp_steps=100):
        #NOTE: should robot_config be a list or do we assume that we will not
        # be comparing different arms?
        """
        Loads the relevant test data and calculates the required information
        for plotting a virtual arm, saving all to a dictionary of interpolated
        data for even sampling between tests.

        PARAMETERS
        ----------
        robot_config: instantiated abr_control robot config
            This is required to transform joint angles to cartesian coordinates
        session: int
            the session number of interest
        run: int
            the run number of interst
        test_groups: list of strings
            the group names corresponding to the list of tests
        test_names: list of strings
            the list of test names to plot
        show_arm: list of booleans
            corresponding list to test_names
            True: plot a virtual arm
            False: plot EE data
        interp_steps: int, Optional (Default=100)
            the number of steps to interpolate from the data to align results.
            NOTE: this assumes that the tests passed in are of the same length
            wrt to run time
        final_frame: boolean, Optional (Default=False)
            True to only show the final frame of the run, this greatly shortens
            the processing time
        """
        #NOTE: would it be better to specify frames_per_sec instead of
        # interp_steps?

        if len(test_names) != len(test_groups):
            raise Exception("""You must pass in a test group for each
                    testname\n
                    len()test_groups) %i: len(test_names) %i"""
                    %(len(test_groups), len(test_names)))

        if len(test_names) != len(show_arm):
            raise Exception("""You must specify whether to plot a virtual arm
            (True) or just the end-effector (False) for each test\n
                    len(show_arm) %i: len(test_names) %i"""
                    %(len(show_arm),len(test_names)))
        if robot_config is None and np.any(show_arm):
            raise Exception("""To get information to plot a virtual arm an arm
                    config is required""")
        if robot_config is not None:
            robot_config.init_all()

        self.final_frame = final_frame
        self.show_arm = show_arm
        # create a dictionary with our test data interpolated to the same
        # number of steps
        self.create_dict(test_groups=test_groups, test_names=test_names,
                sessions=sessions, runs=runs, interp_steps=interp_steps,
                final_frame=self.final_frame, show_arm=self.show_arm)

        for ii in range(0, len(test_names)):
            if show_arm[ii]:
                # get the cartesian coordinates of the virtual arm joints and links
                test_key=('%s/%s/session%03d/run%03d'%
                    (test_groups[ii], test_names[ii], session, run))
                self.get_cartesian_location(robot_config=robot_config,
                        test_key=test_key)
                #TODO: need to implement limit checking - basic will be checking
                # collision with ground
                # # check if any of the cartesian points fall passed our working limit
                # self.check_limits()

    def plot_frame(self, ax=None, show_plot=False, save_fig=False,
            return_ax=True, frame=None):
        """
        Plots a single frame in time of the interpolated data from generate()

        if final_frame was set to True only the last frame in the reach will be
        plotted. If multiple frames are desired, the user has two methods to
        display the data.
        1: pass in an ax object to handle the plotting in whatever way the user
           see's fit
        2: leave ax=None in which case a figure and axis will be created to
           plot on

        in both cases the user can select whether to return the ax object or
        not. If return_ax=False then the figure will be saved as a png and
        displayed depending on the settings of show_plot and save_fig

        ax: ax object of figure, Optional (Default: None)
            if None is provided, one will be created. However, if the user
            desires to have multiple function calls, plotting to the same ax
            object, the none can be passed in and the data will be plotted onto
            it
        show_plot: boolean, Optional (Default=False)
            True to display plot
        save_fig: boolean, Optional (Default=False)
            True to save a pdf and png of the figure
        return_ax: Boolean, Optional (Default=True)
            True to return the ax object
        frame: int, Optional (Default=None)
            the list entry to plot from the interpolated data
            if None the final frame will be plotted
        """

        try:
            self.test_data
        except NameError:
            print("""Please run the generate() function before trying to plot
                    a frame to obtain the required data""")

        # if the user set final_frame to True while generating and tries to
        # specify a frame for plotting we will not have the data since only the
        # final frame was saved during the generate() call
        if self.final_frame is True and frame is not None:
            raise Exception ("""final_frame was set to True while generating
                    the required data, but %i was passed in for frame. \n To
                    plot a frame other than the last frame the generate()
                    function will have to be called with final_frame=False to
                    collect data throughout the entire dataset"""%frame)

        if ax is None:
            # user did not pass in an axis object so plot onto a new figure and
            # axis
            fig = plt.figure()
            ax = fig.add_subplot(111)

        # plot the trajectories up the the desired frame for each test
        for test in test_data.keys():
            # plot the EE trajectory
            ax = vis.add_trajectory(ax=ax, data=test['ee_xyz'][:, 0:frame],
                    label=test)
            if test['show_arm']:
                # plot the joint positions and joint them with links
                ax = vis.add_joints(ax=ax, data=test['joints_xyz'][frame],
                        label=test)
                # plot the links' centers of mass
                ax = vis.add_links(ax=ax, data=test['links_xyz'][frame],
                        label=test)

                # plot the target trajectory
                ax = vis.add_trajectory(ax=ax, data=test['filter'][:,0:frame],
                        label='filter')

        if return_ax:
            return ax

        # show plot if not return? what if show_plot false? same goes for
        # saving

    def save_figure(self):
        plt.tight_layout()
        plt.savefig('%s/gif_fig_cache/%05d.png'%(save_loc,ii))
        plt.close()
