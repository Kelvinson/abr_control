from abr_control.utils import DataHandler
import matplotlib.pyplot as plt
import numpy as np

dat = DataHandler(use_cache=True, db_name='parameter_tuning')

test_group = 'friction_post_tuning'
test_name = 'nengo_loihi_friction_10_0'
save_name = '%s/%s/neuron_tuning_spherical'%(test_group, test_name)
keys = dat.get_keys(save_name)

sum_diff = []
neurons_active = []
prop_time = []
intercepts_load = []
modes = []
num_active = []
num_inactive = []


for ii in keys :
    data = dat.load(params=['intercepts_bounds', 'intercepts_mode', 'diff_active',
            'neurons_active', 'prop_time', 'sum_diff', 'num_active', 'num_inactive'],
            save_location='%s_3/%s'%(save_name,ii))

    sum_diff0 = data['sum_diff']
    sum_diff.append(sum_diff0[0])

    prop_time0 = data['prop_time']
    prop_time.append(prop_time0)

    neurons_active0 = data['neurons_active']
    neurons_active.append(neurons_active0)

    intercepts_bounds0 = data['intercepts_bounds']
    intercepts_load.append(intercepts_bounds0)

    modes0 = data['intercepts_mode']
    modes.append(modes0)

    num_active.append(data['num_active'])
    num_inactive.append(data['num_inactive'])

for ind in range(0, len(keys)):
    print('active')
    print(np.array(neurons_active[ind]))
    print('time')
    print(np.array(prop_time[ind]))
    plt.figure()
    plt.title('Active: %i | Inactive: %i'%(num_active[ind], num_inactive[ind]))
    plt.plot(np.squeeze(prop_time[0]), np.squeeze(neurons_active[ind]),
            label='%i: %f \n%s: %s'%
            (ind, sum_diff[ind], intercepts_load[ind], modes[ind]))

    plt.legend()
    plt.show()

