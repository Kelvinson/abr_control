from abr_control.utils import DataHandler, make_gif, ProcessData
import numpy as np
import matplotlib
matplotlib.use("TKAgg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d
import subprocess
import os

class DataVisualizer
    def __init__(traj_colors=None, link_colors, joint_colors, segment_colors):
        #TODO: decide how to go about automating the colours for this
        # keep reading below
        """
        a few cases that need to be determined, plotting data over time, 3D
        positional data, and N_JOINT data over time
        """
        if colors is None:
            #TODO: generate a long list of colours that will actually
            # look good and won't be too similar
            self.colors = []
        else:
            self.colors = colors
        self.test_list = []
        # marker_size = [2**5, 2**5, 2**5, 2**5, 2**5, 2**5, 2**5]
        # marker = ['o', 'o', 'o', 'o', 'o', 'o', 'o']

    def align_yaxis(ax1, v1, ax2, v2):
        """adjust ax2 ylimit so that v2 in ax2 is aligned to v1 in ax1"""
        _, y1 = ax1.transData.transform((0, v1))
        _, y2 = ax2.transData.transform((0, v2))
        inv = ax2.transData.inverted()
        _, dy = inv.transform((0, 0)) - inv.transform((0, y1-y2))
        miny, maxy = ax2.get_ylim()
        ax2.set_ylim(miny+dy, maxy+dy)

    def add_to_plot(self, show_trajectory=False):
        """
        Add provided data to plot
        Can keep adding trajectory of tests, select which to create the arm
        for, add path planners, targets etc

        PARAMETERS
        ----------
        show_trajectory: boolean, Optional (Default: False)
            True: show trace of trajectory as the figure progresses
            False: no trajectory shown
        """

    def add_joints(ax, data, label):
        """
        Plots the joint positions and joins them to form the arm segments
        """
        #TODO: decide how to set marker and size
        c = 'k'
        for xyz in data:
            # plot target location
            ax.scatter(xyz[0], xyz[1], xyz[2], c=c, marker=marker, s=s,
                    label='Joints')
        ax.plot(data.T[0], data.T[1], data.T[2], c=c)
        return ax

    def add_links(ax, data, label):
        """
        Plots the link centers of mass
        """
        #TODO: decide how to set marker and size
        c = 'tab:grey'
        for xyz in data:
            # plot target location
            ax.scatter(xyz[0], xyz[1], xyz[2], c=c, marker=marker, s=s,
                    label='Link COM')
        return ax


    def add_trajectory(ax, data, label):
        """
        Plots a 3D trajectory from the 3 x n data provided
        The label is only used to keep track of what color corresponds to which
        dataset
        """
        if label not in self.test_list:
            self.test_list.append(label)
        # set the color of this test to correspond to the color at the same
        # index in self.color
        # i.e. if label is the ith entry in self.test_list, then it will be
        # assigned the ith color in self.colors

        c = self.colors[self.test_list.index(label)]
        ax.plot(data[:, 0], data[:,1], data[:,2],
                color=c, label=tests[0])

    def add_3D_text(ax, text):
        ax.text(-0.5, -0.5, 0.9, 'Avg: %.3f m'%np.mean(error_t[jj]), color='b')
        ax.text(-0.5, -0.5, 1.0, 'Final: %.3f m'%(error_t[jj][-1]), color='b')
        ax.text(-0.5, -0.5, 1.1, 'Error: %.3f m'%(error), color='b')
        ax.text(-0.5, -0.5, 1.2, tests[0], color='b')


        ax.text(-0.5, -0.5, 0.5, 'Avg: %.3f m'%np.mean(error_0[jj]),
                color='tab:purple')
        ax.text(-0.5, -0.5, 0.6, 'Final: %.3f m'%(error_0[jj][-1]),
                color='tab:purple')
        if ii >= len(error_0[jj]):
            iii = len(error_0[jj])-1
        else:
            iii = ii
        ax.text(-0.5, -0.5, 0.7, 'Error: %.3f m'%(error_0[jj][iii]),
                color='tab:purple')
        ax.text(-0.5, -0.5, 0.8, tests[1], color='tab:purple')
        if jj == len(runs)-1:
            ax.legend(bbox_to_anchor=[1.15, 0.5], loc='center left')
