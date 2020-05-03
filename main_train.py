from config import get_arguments
##Andreas edited
from SinGAN.manipulate import *
from SinGAN.training import *
##
import SinGAN.functions as functions

##NOTES: function changed (old below)
# torch2uint8(x):
#now with 4 dimensions
#x = x[:,:,:,:]
#x = x.permute((0,2,3,1))

if __name__ == '__main__':
    parser = get_arguments()
    #Andreas Changed to videos
    parser.add_argument('--quickselect', help='1,2,3,4,5,6', default='0')

    parser.add_argument('--input_dir', help='input image dir', default='Input/Videos')

    parser.add_argument('--input_name', help='input image name', required=False, default='Falls10')

    parser.add_argument('--mode', help='task to be done', default='train')

    parser.add_argument('--dimensions', help='number of dimensions', default=4)

    parser.add_argument('--frame_cap', help='limit frames', default=15)

    parser.add_argument('--on_server', help='on HPC Cluster', default=1)

    opt = parser.parse_args()
    opt = functions.post_config(opt)
    if(opt.quickselect == '1'):
        opt.input_name = 'Pond'
    elif(opt.quickselect == '2'):
        opt.input_name = 'Ripples'
    elif(opt.quickselect == '3'):
        opt.input_name = 'Trees'
    elif(opt.quickselect == '4'):
        opt.input_name = 'Snowboard'
    elif(opt.quickselect == '5'):
        opt.input_name = 'Beer'

    Gs = []
    Zs = []
    reals = []
    NoiseAmp = []
    dir2save = functions.generate_dir2save(opt)

    #ANDREAS CHANGEd
    if (os.path.exists(dir2save) and False):
        print('trained model already exist')
    else:
        try:
            os.makedirs(dir2save)
        except OSError:
            pass

        #Andreas convert image also this does nothing since other than check if format correct
        if (opt.dimensions == 4) :
            size = functions.VideotoImage(opt)
            opt.path = opt.input_dir + "/" + opt.input_name
            print(opt.path)
        real = functions.read_image(opt)
        functions.adjust_scales2image(real, opt) #make 250 max dimension




##Andreas initially all are [] lists
        train(opt, Gs, Zs, reals, NoiseAmp)
#    manipulate.SinGAN_generate(Gs,Zs,reals,NoiseAmp,opt)
        ##
