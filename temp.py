from config import get_arguments
#from SinGAN.manipulate import *
#from SinGAN.training import *
import SinGAN.functions as functions
import numpy
from skimage import io as img


if __name__ == '__main__':
#    parser = get_arguments()
#    parser.add_argument('--input_dir', help='input image dir', default='Input/Images')
#    parser.add_argument('--input_name', help='input image name', required=True)
#    parser.add_argument('--mode', help='task to be done', default='train')
#    opt = parser.parse_args()
#    opt = functions.post_config(opt)

#    print(opt)
    x = img.imread('%s/%s' % (opt.input_dir,opt.input_name))
#    x = numpy.array([[1,2,3],[4,5,6]])
    print(x)
#    x = x[:,:,None]
#    print(x)
#    print(x.shape)
    x = x.transpose(0, 2,1)
    print(x)















#    real_ = functions.read_image(opt)
#    print([real_.shape[0],real_.shape[1]])
#    print(min(250/max([real_.shape[0],real_.shape[1]]),1))
#    print(x.transpose((3, 2, 0, 1))/255)
#    x = numpy.array([[[1,2,3],[5,6,7]],[[1,2,3],[5,6,7]]])
#    x = x[0,:,:]
#    print(x)
#    print(x.shape)
#    print(functions.np2torch(x,opt))
#    print(real_)
