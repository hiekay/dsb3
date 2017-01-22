import matplotlib.pyplot as plt
import numpy as np  # linear algebra
import pathfinder
import utils
import utils_lung
import os
import data_transforms
import skimage.draw
import scipy
import collections


def make_circular_mask(img_shape, roi_center, roi_radii):
    mask = np.ones(img_shape) * 0.1
    rr, cc = skimage.draw.ellipse(roi_center[0], roi_center[1], roi_radii[0], roi_radii[1], img_shape)
    mask[rr, cc] = 1.
    return mask


def resample(image, spacing, new_spacing=[1, 1]):
    # Determine current pixel spacing
    spacing = np.array(spacing)
    resize_factor = spacing / new_spacing
    new_real_shape = image.shape * resize_factor
    new_shape = np.round(new_real_shape)
    real_resize_factor = new_shape / image.shape
    new_spacing = spacing / real_resize_factor
    image = scipy.ndimage.interpolation.zoom(image, real_resize_factor)
    return image, new_spacing


def plot_2d(img, mask, pid, img_dir):
    # fig = plt.figure()
    fig, ax = plt.subplots(2, 2, figsize=[8, 8])
    fig.canvas.set_window_title(pid)
    ax[0, 0].imshow(img, cmap='gray')
    ax[0, 1].imshow(mask, cmap='gray')
    ax[1, 0].imshow(img * mask, cmap='gray')
    plt.show()
    fig.savefig(img_dir + '/%s.png' % pid, bbox_inches='tight')
    fig.clf()
    plt.close('all')


def test1():
    image_dir = utils.get_dir_path('analysis', pathfinder.METADATA_PATH)
    image_dir = image_dir + '/test_luna/'
    utils.automakedir(image_dir)

    # sys.stdout = logger.Logger(image_dir + '/test_luna.log')
    # sys.stderr = sys.stdout

    id2zyxd = utils_lung.read_luna_labels(pathfinder.LUNA_LABELS_PATH)

    luna_data_paths = utils_lung.get_patient_data_paths(pathfinder.LUNA_DATA_PATH)
    luna_data_paths = [p for p in luna_data_paths if '.mhd' in p]
    print len(luna_data_paths)
    print id2zyxd.keys()

    for k, p in enumerate(luna_data_paths):
        img, origin, spacing = utils_lung.read_mhd(p)
        img = data_transforms.hu2normHU(img)
        id = os.path.basename(p).replace('.mhd', '')
        for roi in id2zyxd[id]:
            zyx = np.array(roi[:3])
            voxel_coords = utils_lung.world2voxel(zyx, origin, spacing)
            print spacing
            radius_mm = roi[-1] / 2.
            radius_px = radius_mm / spacing[1]
            print 'r in pixels =', radius_px
            # roi_radius = (32.5, 32.5)
            roi_radius = (radius_px, radius_px)
            slice = img[voxel_coords[0], :, :]
            roi_center_yx = (voxel_coords[1], voxel_coords[2])
            # print slice.shape, slice_resample.shape
            mask = make_circular_mask(slice.shape, roi_center_yx, roi_radius)
            plot_2d(slice, mask, id, image_dir)

            slice_mm, _ = resample(slice, spacing[1:])
            roi_center_mm = tuple(int(r * ps) for r, ps in zip(roi_center_yx, spacing[1:]))
            mask_mm = make_circular_mask(slice_mm.shape, roi_center_mm, (radius_mm, radius_mm))
            plot_2d(slice_mm, mask_mm, id, image_dir)


def test2():
    luna_data_paths = utils_lung.get_patient_data_paths(pathfinder.LUNA_DATA_PATH)
    luna_data_paths = [p for p in luna_data_paths if '.mhd' in p]
    print len(luna_data_paths)
    pixel_spacings_xy = []
    n_slices = []

    for k, p in enumerate(luna_data_paths):
        img, origin, spacing = utils_lung.read_mhd(p)
        id = os.path.basename(p).replace('.mhd', '')
        assert spacing[1] == spacing[2]
        pixel_spacings_xy.append(spacing[1])
        n_slices.append(img.shape[0])
        print id, pixel_spacings_xy[-1], n_slices[-1]

    print 'nslices', np.max(n_slices), np.min(n_slices), np.mean(n_slices)
    counts = collections.Counter(pixel_spacings_xy)
    new_list = sorted(pixel_spacings_xy, key=counts.get, reverse=True)
    print 'spacing', new_list


if __name__ == '__main__':
    test1()