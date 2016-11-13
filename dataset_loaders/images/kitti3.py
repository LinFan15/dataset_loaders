import os
import numpy as np
from PIL import Image
from getpass import getuser
import time
import shutil

from dataset_loaders.parallel_loader import ThreadedDataset

floatX = 'float32'

class KITTIdataset3(ThreadedDataset):
    name = 'kitti3'
    nclasses = 11
    debug_shape = (375, 500, 3)

    data_shape = (None, None, 3)
    # mean = np.asarray([122.67891434, 116.66876762, 104.00698793]).astype(
    #    'float32')
    std = 1.
    _void_labels = [11] # [255] (TODO: No void class???)
    GTclasses = range(11) + _void_labels

    _cmap = {
        0: (128, 128, 128),    # Sky
        1: (128, 0, 0),        # Building
        2: (128, 64, 128),     # Road
        3: (0, 0, 192),        # Sidewalk
        4: (64, 64, 128),      # Fence
        5: (128, 128, 0),      # Vegetation
        6: (192, 192, 128),    # Pole
        7: (64, 0, 128),       # Car
        8: (192, 128, 128),    # Sign
        9: (64, 64, 0),        # Pedestrian
        10: (0, 128, 192)      # Cyclist
        # 255: (255, 255, 255)   # void
    }

    _mask_labels = {0: 'Sky', 1: 'Building', 2:  'Road', 3:  'Sidewalk',
                    4:  'Fence', 5:  'Vegetation', 6:  'Pole',
                    7:  'Car', 8:  'Sign', 9:  'Pedestrian',10: 'Cyclist'}
                    # 255: 'void'}

    _filenames = None



    @property
    def filenames(self):
        import glob

        if self._filenames is None:
            # Load filenames
            filenames = []

            # Get file names from images folder
            file_pattern = os.path.join(self.image_path, "*.png")
            file_names = glob.glob(file_pattern)
            # print (str(file_names))

            # Get raw filenames from file names list
            for file_name in file_names:
                path, file_name = os.path.split(file_name)
                file_name, ext = os.path.splitext(file_name)
                raw_name = file_name.strip()
                filenames.append(file_name)
                # print (file_name)

            # Save the filenames list
            self._filenames = filenames
        return self._filenames

    def __init__(self,
                 which_set="train",
                 with_filenames=False,
                 norm=False,
                 *args, **kwargs):

        self.which_set = "val" if which_set == "valid" else which_set
        self.with_filenames = with_filenames
        usr = getuser()
        self.path = '/Tmp/'+usr+'/datasets/kitti/'
        self.sharedpath = '/data/lisatmp4/romerosa/datasets/kitti3/'
        # '/data/lisa/exp/vazquezd/datasets/KITTI_SEMANTIC/'
        # self.path = '/home/'+usr+'/datasets/KITTI/'
        # self.sharedpath = '/home/dvazquez/Desktop/KITTI_SEMANTIC/'

        if self.which_set not in ("train", "val",'test', 'trainval'):
            raise ValueError("Unknown argument to which_set %s" %
                             self.which_set)

        if self.which_set == 'train':
            set_folder = 'Training_00/'
        elif self.which_set == 'val':
            set_folder = 'valid/'
        elif self.which_set == 'test':
            set_folder = 'Validation_07/'
        elif self.which_set == 'trainval':
            set_folder = 'trainval/'
        else:
            raise ValueError

        self.image_path = os.path.join(self.path, set_folder, "RGB")
        self.mask_path = os.path.join(self.path, set_folder, "GT_ind")

        self.mu_kitti = [0.35675976, 0.37380189, 0.3764753]
        self.sigma_kitti = [0.32064945, 0.32098866, 0.32325324]

        self.norm = norm
        print self.norm

        super(KITTIdataset3, self).__init__(*args, **kwargs)

    def get_names(self):

        # Limit to the number of videos we want
        sequences = []
        seq_length = self.seq_length
        seq_per_video = self.seq_per_video
        image_names = self.filenames
        video_length = len(image_names)
        max_num_sequences = video_length - seq_length + 1
        if (not self.seq_length or not self.seq_per_video or
                self.seq_length >= video_length):
            # Use all possible frames
            sequences = image_names[:max_num_sequences:
                                    self.seq_length - self.overlap]
        else:
            if max_num_sequences < seq_per_video:
                # If there are not enough frames, cap seq_per_video to
                # the number of available frames
                print("/!\ Warning : you asked {} sequences of {} "
                      "frames each but the dataset only has {} "
                      "frames".format(seq_per_video, seq_length,
                                      video_length))
                seq_per_video = max_num_sequences

            if self.overlap != self.seq_length - 1:
                raise('Overlap other than seq_length - 1 is not '
                      'implemented')
            # pick `seq_per_video` random indexes between 0 and
            # (video length - sequence length)
            first_frame_indexes = self.rng.permutation(range(
                max_num_sequences))[0:seq_per_video]

            for i in first_frame_indexes:
                sequences.append(image_names[i])

        # Return images
        return np.array(sequences)

    def load_sequence(self, img_name):
        from skimage import io
        image_batch = []
        mask_batch = []
        filename_batch = []

        if self.seq_length != 1:
            raise NotImplementedError()

        # Load image
        img = io.imread(os.path.join(self.image_path, img_name + ".png"))
        img = img.astype(floatX) / 255.

        if self.norm:
            img -= self.mu_kitti
            img /= self.sigma_kitti

        # Load mask
        mask = np.array(Image.open(
                os.path.join(self.mask_path, img_name + ".png")))
        mask = mask.astype('int32')

        # cmap2 = {
        #     (128, 128, 128):0,    # Sky
        #     (128, 0, 0):1,        # Building
        #     (128, 64, 128):2,     # Road
        #     (0, 0, 192):3,        # Sidewalk
        #     (64, 64, 128):4,      # Fence
        #     (128, 128, 0):5,      # Vegetation
        #     (192, 192, 128):6,    # Pole
        #     (64, 0, 128):7,       # Car
        #     (192, 128, 128):8,    # Sign
        #     (64, 64, 0):9,        # Pedestrian
        #     (0, 128, 192):10      # Cyclist
        #     # 255: (255, 255, 255)   # void
        # }
        #
        # # Change color by classes
        # # TODO: DO THIS FASTER!!!!
        # mask2 = np.zeros(mask.shape[0:2]).astype('int32')
        # # print (mask2.shape)
        # for key, val in self._cmap.iteritems():
        #     # print ('key: ' + str(key))
        #     # print ('val: ' + str(val))
        #     val = np.asarray(val)
        #     for i in range (mask.shape[0]):
        #         for j in range (mask.shape[1]):
        #             if all(mask[i,j,:] == val):
        #                 mask2[i,j] = key
        # mask = mask2
        # print (np.min(mask))
        # print (np.max(mask))
        #
        # # Save image
        # io.imsave(os.path.join(self.mask_path, 'ind', img_name + ".png"), mask)

        # Add to minibatch
        image_batch.append(img)
        mask_batch.append(mask)
        if self.with_filenames:
            filename_batch.append(img_name)

        image_batch = np.array(image_batch)
        mask_batch = np.array(mask_batch)
        filename_batch = np.array(filename_batch)

        if self.with_filenames:
            return image_batch, mask_batch, filename_batch
        else:
            return image_batch, mask_batch


def test():
    trainiter = KITTIdataset(
        which_set='train',
        batch_size=10,
        seq_per_video=0,
        seq_length=0,
        crop_size=(224, 224),
        get_one_hot=True,
        get_01c=True,
        use_threads=True)

    validiter = KITTIdataset(
        which_set='valid',
        batch_size=5,
        seq_per_video=0,
        seq_length=0,
        crop_size=(224, 224),
        get_one_hot=True,
        get_01c=True,
        use_threads=False)

    train_nsamples = trainiter.nsamples
    nclasses = trainiter.get_n_classes()
    nbatches = trainiter.get_n_batches()
    train_batch_size = trainiter.get_batch_size()
    print("Train %d" % (train_nsamples))

    valid_nsamples = validiter.nsamples
    print("Valid %d" % (valid_nsamples))

    # Simulate training
    max_epochs = 2
    start_training = time.time()
    for epoch in range(max_epochs):
        start_epoch = time.time()
        for mb in range(nbatches):
            start_batch = time.time()
            train_group = trainiter.next()

            # time.sleep approximates running some model
            # time.sleep(0.1)
            print("Minibatch {}: {} seg".format(mb, (time.time() - start_batch)))
        print("Epoch time: %s" % str(time.time() - start_epoch))
    print("Training time: %s" % str(time.time() - start_training))


if __name__ == '__main__':
    test()
