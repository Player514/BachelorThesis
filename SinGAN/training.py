import SinGAN.functions as functions
import SinGAN.models as models
import os
import torch.nn as nn
import torch.optim as optim
import torch.utils.data
import torch.nn.functional as F
import math
import matplotlib.pyplot as plt
from SinGAN.imresize import imresize,videoresize, imresize4d
from SinGAN.padding import padding
import numpy as np
import sys

def train(opt,Gs,Zs,reals,NoiseAmp):
    real_ = functions.read_image(opt)
    in_s = 0
    scale_num = 0
    real = videoresize(real_,opt.scale1,opt)
#    print(real.shape)
    #doneish?

    #reals[0] should be [4,x,x,x] len reals = 8
    reals = functions.creat_reals_pyramid(real,reals,opt)
    nfc_prev = 0
    print('r0',reals[0].shape)
    print('r1',reals[1].shape)
    print('r2',reals[2].shape)
#    print(reals[3].shape)
#    print(reals[4].shape)

    while scale_num<opt.stop_scale+1:
        #32
        opt.nfc = min(opt.nfc_init * pow(2, math.floor(scale_num / 4)), 128)
        #32
        opt.min_nfc = min(opt.min_nfc_init * pow(2, math.floor(scale_num / 4)), 128)

        opt.out_ = functions.generate_dir2save(opt)

        opt.outf = '%s/%d' % (opt.out_,scale_num)
        try:
            os.makedirs(opt.outf)
        except OSError:
                pass

        #plt.imsave('%s/in.png' %  (opt.out_), functions.convert_image_np(real), vmin=0, vmax=1)
        #plt.imsave('%s/original.png' %  (opt.out_), functions.convert_image_np(real_), vmin=0, vmax=1)

#        plt.imsave('%s/real_scale.png' %  (opt.outf), functions.convert_image_np(reals[scale_num]), vmin=0, vmax=1)
        #change to 4D
#        functions.VideoSave(opt.out_,'in',real)
#        functions.VideoSave(opt.out_,'original',real_)
#        functions.VideoSave(opt.outf,'real_scale',reals[scale_num])

        D_curr,G_curr = init_models(opt)

        if (nfc_prev==opt.nfc):
            print("gather previous pth")
            G_curr.load_state_dict(torch.load('%s/%d/netG.pth' % (opt.out_,scale_num-1)))
            D_curr.load_state_dict(torch.load('%s/%d/netD.pth' % (opt.out_,scale_num-1)))

        z_curr,in_s,G_curr = train_single_scale(D_curr,G_curr,reals,Gs,Zs,in_s,NoiseAmp,opt)

        G_curr = functions.reset_grads(G_curr,False)
        G_curr.eval()
        D_curr = functions.reset_grads(D_curr,False)
        D_curr.eval()

        Gs.append(G_curr)
        Zs.append(z_curr)
        NoiseAmp.append(opt.noise_amp)

        torch.save(Zs, '%s/Zs.pth' % (opt.out_))
        torch.save(Gs, '%s/Gs.pth' % (opt.out_))
        torch.save(reals, '%s/reals.pth' % (opt.out_))
        torch.save(NoiseAmp, '%s/NoiseAmp.pth' % (opt.out_))

        scale_num+=1
        nfc_prev = opt.nfc
        del D_curr,G_curr
    return



def train_single_scale(netD,netG,reals,Gs,Zs,in_s,NoiseAmp,opt,centers=None):

    #Real starts at 0 goes to 8, is what level we are on pyramid
    real = reals[len(Gs)]
    real = real[None,:,:,:]

    #1,4,3,W,H to 1,3,4,W,H
    #np.transpose(real,(0,2,1,3,4)) added to functions.py while image is in cpu memory

    #add one for line above
    opt.nzz = real.shape[1+1]#+(opt.ker_size-1)*(opt.num_layer)
    opt.nzx = real.shape[2+1]#+(opt.ker_size-1)*(opt.num_layer)
    opt.nzy = real.shape[3+1]#+(opt.ker_size-1)*(opt.num_layer)
#    print(opt.nzz,opt.nzx,opt.nzy)
    #11: 3 + ((3-1)*(5-1))*1
    opt.receptive_field = opt.ker_size + ((opt.ker_size-1)*(opt.num_layer-1))*opt.stride

    #5
    pad_noise = int(((opt.ker_size - 1) * opt.num_layer) / 2)
    #5
    pad_image = int(((opt.ker_size - 1) * opt.num_layer) / 2)

#    print(pad_image)
#    print(pad_image)


    if opt.mode == 'animation_train':
        opt.nzx = real.shape[2]+(opt.ker_size-1)*(opt.num_layer)
        opt.nzy = real.shape[3]+(opt.ker_size-1)*(opt.num_layer)
        pad_noise = 0

#    m_noise = nn.ZeroPad2d(pad_noise) #removed recast to int, basically used to add padding
#    m_image = nn.ZeroPad2d(pad_image) #removed recast to int, basically used to add padding
    m_noise = padding(pad_noise)
    m_image = padding(pad_image)
    #pad 3 d

    #10
    alpha = opt.alpha

    #added dimension nzz dimension
#    print('optnzz,ncz,nzx,nzy',[opt.nzz,opt.nc_z,opt.nzx,opt.nzy])
    #[1,opt.nzz,opt.nzx,opt.nzy]
    fixed_noise = functions.generate_noise([opt.nc_z,opt.nzz,opt.nzx,opt.nzy],device=opt.device)
#    print('fixed_noise',fixed_noise.shape)
    z_opt = torch.full(fixed_noise.shape, 0, device=opt.device)
#    print('z_opt4',z_opt.shape)
    z_opt = m_noise(z_opt)
#    print('z_opt5',z_opt.shape)

    # setup optimizer
    optimizerD = optim.Adam(netD.parameters(), lr=opt.lr_d, betas=(opt.beta1, 0.999))
    optimizerG = optim.Adam(netG.parameters(), lr=opt.lr_g, betas=(opt.beta1, 0.999))
    schedulerD = torch.optim.lr_scheduler.MultiStepLR(optimizer=optimizerD,milestones=[1600],gamma=opt.gamma)
    schedulerG = torch.optim.lr_scheduler.MultiStepLR(optimizer=optimizerG,milestones=[1600],gamma=opt.gamma)

    errD2plot = []
    errG2plot = []
    D_real2plot = []
    D_fake2plot = []
    z_opt2plot = []

    for epoch in range(opt.niter):
        if (Gs == []) & (opt.mode != 'SR_train'): #True
            #modified to 1s to opt.nzz(ie. 4)
            #WARNING 4.25 added opt.nzz
            z_opt = functions.generate_noise([1,opt.nzz,opt.nzx,opt.nzy], device=opt.device, num_samp = 1)
            #single frame image across 1 channel

            z_opt = m_noise(z_opt.expand(1,3,opt.nzz,opt.nzx,opt.nzy))
            noise_ = functions.generate_noise([1,opt.nzz,opt.nzx,opt.nzy], device=opt.device,num_samp = 1)
            noise_ = m_noise(noise_.expand(1,3,opt.nzz,opt.nzx,opt.nzy))
#            print(opt.nzz,opt.nzx,opt.nzy)
#            print("NOISE",noise_.shape)
            #TODO: warning all frame are intialized to same noise map, this is ok for color channel but may be wrong for frames

#old
#            z_opt = functions.generate_noise([1,opt.nzx,opt.nzy], device=opt.device, num_samp = opt.nzz)
#            z_opt = m_noise(z_opt.expand(opt.nzz,3,opt.nzx,opt.nzy))
#            noise_ = functions.generate_noise([1,opt.nzx,opt.nzy], device=opt.device,num_samp = opt.nzz)
#            noise_ = m_noise(noise_.expand(opt.nzz,3,opt.nzx,opt.nzy))
        else:

            noise_ = functions.generate_noise([opt.nc_z,opt.nzz,opt.nzx,opt.nzy], device=opt.device)
#            print('noise__',noise_.shape)
#            noise_ = functions.generate_noise([opt.nc_z,opt.nzx,opt.nzy], device=opt.device)
            noise_ = m_noise(noise_)

        ############################
        # (1) Update D network: maximize D(x) + D(G(z))
        ###########################
#        print('z_opt8',z_opt.shape)
        for j in range(opt.Dsteps): #Dsteps = 3
#            print(j)
            # train with real
            netD.zero_grad()

#            print(type(netD))
#            print("158", real.shape)

            output = netD(real).to(opt.device)
            #D_real_map = output.detach()
            errD_real = -output.mean()#-a
            errD_real.backward(retain_graph=True)
            D_x = -errD_real.item()

            # train with fake
            if (j==0) & (epoch == 0):
                if (Gs == []) & (opt.mode != 'SR_train'): #True

                    #changed from 1 to opt.nzz
                    prev = torch.full([1,opt.nc_z,opt.nzz,opt.nzx,opt.nzy], 0, device=opt.device)
                    in_s = prev
                    prev = m_image(prev) #add padding (5)
                    z_prev = torch.full([1,opt.nc_z,opt.nzz,opt.nzx,opt.nzy], 0, device=opt.device)
                    z_prev = m_noise(z_prev)
                    opt.noise_amp = 1
                elif opt.mode == 'SR_train': #False
                    z_prev = in_s
                    criterion = nn.MSELoss()
                    RMSE = torch.sqrt(criterion(real, z_prev))
                    opt.noise_amp = opt.noise_amp_init * RMSE
                    z_prev = m_image(z_prev)
                    prev = z_prev
                else:#False for first
                    prev = draw_concat(Gs,Zs,reals,NoiseAmp,in_s,'rand',m_noise,m_image,opt)
                    prev = m_image(prev)
                    z_prev = draw_concat(Gs,Zs,reals,NoiseAmp,in_s,'rec',m_noise,m_image,opt)
                    criterion = nn.MSELoss()
                    RMSE = torch.sqrt(criterion(real, z_prev))
                    opt.noise_amp = opt.noise_amp_init*RMSE
                    z_prev = m_image(z_prev)
            else:
                prev = draw_concat(Gs,Zs,reals,NoiseAmp,in_s,'rand',m_noise,m_image,opt)
                prev = m_image(prev)

            if opt.mode == 'paint_train':
                prev = functions.quant2centers(prev,centers)
                plt.imsave('%s/prev.png' % (opt.outf), functions.convert_image_np(prev), vmin=0, vmax=1)

#            sys.exit(1)

            if (Gs == []) & (opt.mode != 'SR_train'):
                noise = noise_
            else:
                noise = opt.noise_amp*noise_+prev

#            print("220 noise",noise.shape)
#            print("221 prev",prev.shape)
            fake = netG(noise.detach(),prev)
#            print(fake)
###
            output = netD(fake.detach())
            errD_fake = output.mean()
            errD_fake.backward(retain_graph=True)
            D_G_z = output.mean().item()

#            print('fake', fake.shape)
            gradient_penalty = functions.calc_gradient_penalty(netD, real, fake, opt.lambda_grad, opt.device)
            gradient_penalty.backward()

            errD = errD_real + errD_fake + gradient_penalty
            optimizerD.step()

        errD2plot.append(errD.detach())

        ############################
        # (2) Update G network: maximize D(G(z))
        ###########################
#        print('z_opt9',z_opt.shape)

        for j in range(opt.Gsteps):
            netG.zero_grad()
            output = netD(fake)
            #D_fake_map = output.detach()
            errG = -output.mean()
            errG.backward(retain_graph=True)
            if alpha!=0:
                loss = nn.MSELoss()
                if opt.mode == 'paint_train':
                    z_prev = functions.quant2centers(z_prev, centers)
                    plt.imsave('%s/z_prev.png' % (opt.outf), functions.convert_image_np(z_prev), vmin=0, vmax=1)
#
#                print('z_opt',z_opt.shape)
#                print('z_prev',z_prev.shape)
                Z_opt = opt.noise_amp*z_opt+z_prev
                rec_loss = alpha*loss(netG(Z_opt.detach(),z_prev),real)
                rec_loss.backward(retain_graph=True)
                rec_loss = rec_loss.detach()
            else:
                Z_opt = z_opt
                rec_loss = 0

            optimizerG.step()

        errG2plot.append(errG.detach()+rec_loss)
        D_real2plot.append(D_x)
        D_fake2plot.append(D_G_z)
        z_opt2plot.append(rec_loss)

        if epoch % 25 == 0 or epoch == (opt.niter-1):
            print('scale %d:[%d/%d]' % (len(Gs), epoch, opt.niter))

        #changed from 500 to 100
        if epoch % 100 == 0 or epoch == (opt.niter-1):
#            plt.imsave('%s/fake_sample.png' %  (opt.outf), functions.convert_image_np(fake.detach()), vmin=0, vmax=1)
#            plt.imsave('%s/G(z_opt).png'    % (opt.outf),  functions.convert_image_np(netG(Z_opt.detach(), z_prev).detach()), vmin=0, vmax=1)
            #plt.imsave('%s/D_fake.png'   % (opt.outf), functions.convert_image_np(D_fake_map))
            #plt.imsave('%s/D_real.png'   % (opt.outf), functions.convert_image_np(D_real_map))
            #plt.imsave('%s/z_opt.png'    % (opt.outf), functions.convert_image_np(z_opt.detach()), vmin=0, vmax=1)
            #plt.imsave('%s/prev.png'     %  (opt.outf), functions.convert_image_np(prev), vmin=0, vmax=1)
            #plt.imsave('%s/noise.png'    %  (opt.outf), functions.convert_image_np(noise), vmin=0, vmax=1)
            #plt.imsave('%s/z_prev.png'   % (opt.outf), functions.convert_image_np(z_prev), vmin=0, vmax=1)
            functions.VideoSave(opt.outf,'fake_sample',fake.detach()[0])
            functions.VideoSave(opt.outf,'G(z_opt)',netG(Z_opt.detach(), z_prev).detach()[0])

            torch.save(z_opt, '%s/z_opt.pth' % (opt.outf))

        schedulerD.step()
        schedulerG.step()

    functions.save_networks(netG,netD,z_opt,opt)
    return z_opt,in_s,netG

def draw_concat(Gs,Zs,reals,NoiseAmp,in_s,mode,m_noise,m_image,opt):
    G_z = in_s
    if len(Gs) > 0:
        if mode == 'rand':
            count = 0
            pad_noise = int(((opt.ker_size-1)*opt.num_layer)/2)
            if opt.mode == 'animation_train':
                pad_noise = 0
            for G,Z_opt,real_curr,real_next,noise_amp in zip(Gs,Zs,reals,reals[1:],NoiseAmp):
                if count == 0:
                    #creates noise, 1 color channel, with no padding
                    z = functions.generate_noise([1,Z_opt.shape[2] - 2 * pad_noise, Z_opt.shape[3] - 2 * pad_noise, Z_opt.shape[4] - 2 * pad_noise], device=opt.device)

                    #changed 1 to opt.nzz
                    #expand across other channels
                    z = z.expand(1, 3,z.shape[2],z.shape[3],z.shape[4])
                else:
                    #color channels are also are random
                    z = functions.generate_noise([opt.nc_z,Z_opt.shape[2] - 2 * pad_noise, Z_opt.shape[3] - 2 * pad_noise,Z_opt.shape[4] - 2 * pad_noise], device=opt.device)
                z = m_noise(z)

#                G_z = G_z[:,:,0:real_curr.shape[2],0:real_curr.shape[3]] original
#                print(G_z.shape)
#                print(real_curr.shape)
                G_z = G_z[:,:,0:real_curr.shape[1],0:real_curr.shape[2],0:real_curr.shape[3]]

                G_z = m_image(G_z)
#                print('Z_opt',Z_opt.shape)
#                print('noise_amp',noise_amp)
#                print('z',z.shape)
#                print('G_z.shape',G_z.shape)
                z_in = noise_amp*z+G_z
                G_z = G(z_in.detach(),G_z)

                G_z = imresize4d(G_z,[1/opt.scale_factor,1/opt.scale_factor,1/opt.scale_factor],opt)
#                print('G_z.shape',G_z.shape)
#                print('real_next',real_next.shape)
                G_z = G_z[:,:,:real_next.shape[1],:real_next.shape[2],:real_next.shape[3]]
#                print('G_z.shape',G_z.shape)
                count += 1
        if mode == 'rec':
#            print(mode)
            count = 0
            for G,Z_opt,real_curr,real_next,noise_amp in zip(Gs,Zs,reals,reals[1:],NoiseAmp):
#                print("G_z",G_z.shape)
#                print("real_curr",real_curr.shape)
                G_z = G_z[:, :, 0:real_curr.shape[2], 0:real_curr.shape[3]]
#                print("G_z1",G_z.shape) #c
                G_z = m_image(G_z)
#                print("G_z2",G_z.shape) #c
                z_in = noise_amp*Z_opt+G_z
                G_z = G(z_in.detach(),G_z)
#                print("G_z3",G_z.shape) #c
                G_z = imresize4d(G_z,[1/opt.scale_factor,1/opt.scale_factor,1/opt.scale_factor],opt)
#                print("G_z4",G_z.shape) #ic
                G_z = G_z[:,:,:real_next.shape[1],:real_next.shape[2],:real_next.shape[3]]
#                print("G_z5",G_z.shape)
#                sys.exit(1)
                #if count != (len(Gs)-1):
                #    G_z = m_image(G_z)
                count += 1
    return G_z

def train_paint(opt,Gs,Zs,reals,NoiseAmp,centers,paint_inject_scale):
    in_s = torch.full(reals[0].shape, 0, device=opt.device)
    scale_num = 0
    nfc_prev = 0

    while scale_num<opt.stop_scale+1:
        if scale_num!=paint_inject_scale:
            scale_num += 1
            nfc_prev = opt.nfc
            continue
        else:
            opt.nfc = min(opt.nfc_init * pow(2, math.floor(scale_num / 4)), 128)
            opt.min_nfc = min(opt.min_nfc_init * pow(2, math.floor(scale_num / 4)), 128)

            opt.out_ = functions.generate_dir2save(opt)
            opt.outf = '%s/%d' % (opt.out_,scale_num)
            try:
                os.makedirs(opt.outf)
            except OSError:
                    pass

            #plt.imsave('%s/in.png' %  (opt.out_), functions.convert_image_np(real), vmin=0, vmax=1)
            #plt.imsave('%s/original.png' %  (opt.out_), functions.convert_image_np(real_), vmin=0, vmax=1)

            plt.imsave('%s/in_scale.png' %  (opt.outf), functions.convert_image_np(reals[scale_num]), vmin=0, vmax=1)

            D_curr,G_curr = init_models(opt)

            z_curr,in_s,G_curr = train_single_scale(D_curr,G_curr,reals[:scale_num+1],Gs[:scale_num],Zs[:scale_num],in_s,NoiseAmp[:scale_num],opt,centers=centers)

            G_curr = functions.reset_grads(G_curr,False)
            G_curr.eval()
            D_curr = functions.reset_grads(D_curr,False)
            D_curr.eval()

            Gs[scale_num] = G_curr
            Zs[scale_num] = z_curr
            NoiseAmp[scale_num] = opt.noise_amp

            torch.save(Zs, '%s/Zs.pth' % (opt.out_))
            torch.save(Gs, '%s/Gs.pth' % (opt.out_))
            torch.save(reals, '%s/reals.pth' % (opt.out_))
            torch.save(NoiseAmp, '%s/NoiseAmp.pth' % (opt.out_))

            scale_num+=1
            nfc_prev = opt.nfc
        del D_curr,G_curr
    return

def init_models(opt):

    #generator initialization:
    netG = models.GeneratorConcatSkip2CleanAdd(opt).to(opt.device)
    netG.apply(models.weights_init)
    if opt.netG != '':
        netG.load_state_dict(torch.load(opt.netG))
#    print(netG)

    #discriminator initialization:
    netD = models.WDiscriminator(opt).to(opt.device)
    netD.apply(models.weights_init)
    if opt.netD != '':
        netD.load_state_dict(torch.load(opt.netD))
#    print(netD)

    return netD, netG
