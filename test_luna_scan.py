import string
import sys
import lasagne as nn
import numpy as np
import theano
import pathfinder
import utils
from configuration import config, set_configuration
from utils_plots import plot_slice_3d_3, plot_slice_3d_3_patch
import theano.tensor as T
import utils_lung

theano.config.warn_float64 = 'raise'

if len(sys.argv) < 2:
    sys.exit("Usage: test_luna_scan.py <configuration_name>")

config_name = sys.argv[1]
set_configuration('configs_luna_scan', config_name)

# predictions path
predictions_dir = utils.get_dir_path('model-predictions', pathfinder.METADATA_PATH)
outputs_path = predictions_dir + '/%s' % config_name
utils.auto_make_dir(outputs_path)

# builds model and sets its parameters
model = config().build_model()

x_shared = nn.utils.shared_empty(dim=len(model.l_in.shape))
idx_z = T.lscalar('idx_z')
idx_y = T.lscalar('idx_y')
idx_x = T.lscalar('idx_x')

fs = config().filter_size
stride = config().stride
pad = config().pad
n_windows = (config().p_transform['patch_size'][0] - fs + 2 * pad) / stride + 1

givens_valid = {}
givens_valid[model.l_in.input_var] = x_shared[:, :,
                                     idx_z * stride:(idx_z * stride) + fs,
                                     idx_y * stride:(idx_y * stride) + fs,
                                     idx_x * stride:(idx_x * stride) + fs]

get_predictions_patch = theano.function([idx_z, idx_y, idx_x],
                                        nn.layers.get_output(model.l_out),
                                        givens=givens_valid,
                                        on_unused_input='ignore')

valid_data_iterator = config().valid_data_iterator

print
print 'Data'
print 'n validation: %d' % valid_data_iterator.nsamples

valid_losses_dice = []
for n, (x, y, id, annotations) in enumerate(valid_data_iterator.generate()):

    pid = id[0]
    annotations = annotations[0]
    predictions_scan = np.zeros_like(x)

    if pad > 0:
        x = np.pad(x[0, 0], pad_width=pad, mode='constant', constant_values=0)
        x = x[None, None, :, :, :]

    x_shared.set_value(x)

    for iz in xrange(n_windows):
        for iy in xrange(n_windows):
            for ix in xrange(n_windows):
                # print iz, iy, ix
                predictions_patch = get_predictions_patch(iz, iy, ix)
                predictions_scan[0, 0,
                iz * stride:(iz + 1) * stride,
                iy * stride:(iy + 1) * stride,
                ix * stride:(ix + 1) * stride] = predictions_patch[0, 0,
                                                 stride / 2:stride * 3 / 2,
                                                 stride / 2:stride * 3 / 2,
                                                 stride / 2:stride * 3 / 2, ]

    predictions_scan = np.clip(predictions_scan, 0, 1)

    d = utils_lung.dice_index(predictions_scan, y)
    print n, d
    valid_losses_dice.append(d)

    for nodule_n, zyxd in enumerate(annotations):
        print zyxd
        plot_slice_3d_3(input=x[0, 0], mask=y[0, 0], prediction=predictions_scan[0, 0],
                        axis=0, pid='-'.join([str(n), str(nodule_n), str(id[0])]),
                        img_dir=outputs_path, idx=zyxd)
    print n, 'Saved plot'

    utils.save_np(predictions_scan[0, 0], outputs_path + '/pred_' + pid)
    utils.save_np(x[0, 0], outputs_path + '/in_' + pid)
    utils.save_np(annotations, outputs_path + '/tgt_' + pid)

    print n, 'Saved pkl', id[0]

print 'Dice index validation loss', np.mean(valid_losses_dice)