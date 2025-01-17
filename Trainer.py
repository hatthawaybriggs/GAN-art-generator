from __future__ import print_function
#%matplotlib inline
import os
import random
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim as optim
import torch.utils.data
import torchvision.datasets as dset
import torchvision.transforms as transforms
import torchvision.utils as vutils
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from IPython.display import HTML
from Configuration import *
from Generator import *
from Discriminator import *

class Trainer:
    def showImages(path):
        device = torch.device("cuda:0" if (torch.cuda.is_available() and ngpu > 0) else "cpu")
        fixed_noise = torch.randn(64, nz, 1, 1, device=device)
        #total = torch.load(path)
        firstModel = torch.load(".art0.model")
        print(firstModel["generator_state_dict"])
        print("______________________________________________________________")
        netG = Generator(ngpu).to(device)
        netG.load_state_dict(firstModel["generator_state_dict"])
        netG.eval()
        fake1 = netG(fixed_noise).detach().cpu()
        firstModel = torch.load(".art1.model")
        print(firstModel["generator_state_dict"])
        netG.load_state_dict(firstModel["generator_state_dict"])
        netG.eval()
        fake2 = netG(fixed_noise).detach().cpu()
        plt.figure(figsize=(15,15))
        plt.subplot(1,2,2)
        plt.axis("off")
        plt.title("Fake 1")
        plt.imshow(np.transpose(vutils.make_grid(fake1, padding=2, normalize=True),(1,2,0)))
        plt.subplot(1,2,1)
        plt.axis("off")
        plt.title("Fake2")
        plt.imshow(np.transpose(vutils.make_grid(fake2, padding=2, normalize=True),(1,2,0)))
        plt.show()
        
        
        
        
    def train(dr):
        manualSeed = random.randint(1, 10000) # use if you want new results
        print("Random Seed: ", manualSeed)
        random.seed(manualSeed)
        torch.manual_seed(manualSeed)
        # We can use an image folder dataset the way we have it setup.
        # Create the dataset
        print("loading dataset")
        dataset = dset.ImageFolder(root=dr,
                                   transform=transforms.Compose([
                                       transforms.Resize(image_size),
                                       transforms.CenterCrop(image_size),
                                       transforms.ToTensor(),
                                       transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
                                   ]))
        # Create the dataloader
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size,
                                                 shuffle=True, num_workers=workers)
        print("cuda working:" + str(torch.cuda.is_available()))
        # Decide which device we want to run on
        device = torch.device("cuda:0" if (torch.cuda.is_available() and ngpu > 0) else "cpu")
        # Plot some training images
        real_batch = next(iter(dataloader))
        plt.figure(figsize=(8,8))
        plt.axis("off")
        plt.title("Training Images")
        plt.imshow(np.transpose(vutils.make_grid(real_batch[0].to(device)[:64], padding=2, normalize=True).cpu(),(1,2,0)))
                
        # Generator Code
        firstModel = torch.load("models/celeba/celeba14.model")
        print("generator setup")
        # Create the generator
        netG = Generator(ngpu).to(device)

        # Handle multi-gpu if desired
        if (device.type == 'cuda') and (ngpu > 1):
            netG = nn.DataParallel(netG, list(range(ngpu)))

        # Apply the weights_init function to randomly initialize all weights
        #  to mean=0, stdev=0.2.
        #netG.apply(weights_init)
        netG.load_state_dict(torch.load(datarootmodel+resume+".model")["generator_state_dict"])
        # Print the model
        print(netG)

        # Create the Discriminator
        print("Discrimantor setup")
        netD = Discriminator(ngpu).to(device)
        netD.train()
        # Handle multi-gpu if desired
        if (device.type == 'cuda') and (ngpu > 1):
            netD = nn.DataParallel(netD, list(range(ngpu)))

        # Apply the weights_init function to randomly initialize all weights
        #  to mean=0, stdev=0.2.
        #netD.apply(weights_init)
        netD.load_state_dict(torch.load(datarootmodel+resume+".model")["discrimantor_state_dict"])
        # Print the model
        print(netD)

        # Initialize BCELoss function
        criterion = nn.BCELoss()

        # Create batch of latent vectors that we will use to visualize
        #  the progression of the generator
        fixed_noise = torch.randn(64, nz, 1, 1, device=device)

        # Establish convention for real and fake labels during training
        real_label = 1.
        fake_label = 0.


        # Setup optimizers for both G and D
        optimizerD = optim.RMSprop(netD.parameters(), lr=lr)
        optimizerG = optim.RMSprop(netG.parameters(), lr=lr)



        # Lists to keep track of progress
        img_list = []
        G_losses = []
        D_losses = []
        iters = 0

        print("Starting Training Loop...")
        # For each epoch
        progress = {}
        for epoch in range(14,num_epochs):
            print("Epoch "+ str(epoch))
            # For each batch in the dataloader
            thisEpoch = {}
            for i, data in enumerate(dataloader, 0):
                ############################
                # (1) Update D network: maximize log(D(x)) + log(1 - D(G(z)))
                ###########################
                ## Train with all-real batch
                netD.zero_grad()
                # Format batch
                real_cpu = data[0].to(device)
                b_size = real_cpu.size(0)
                label = torch.full((b_size,), real_label, dtype=torch.float, device=device)
                # Forward pass real batch through D
                output = netD(real_cpu).view(-1)
                # Calculate loss on all-real batch
                #errD_real = criterion(output, label)
                errD_real = output.mean()
                # Calculate gradients for D in backward pass
                D_x = output.mean().item()
                ## Train with all-fake batch
                # Generate batch of latent vectors
                noise = torch.randn(b_size, nz, 1, 1, device=device)
                # Generate fake image batch with G
                fake = netG(noise)
                label.fill_(fake_label)
                # Classify all fake batch with D
                output = netD(fake.detach()).view(-1)
                # Calculate D's loss on the all-fake batch
                #errD_fake = criterion(output, label)
                errD_fake = output.mean()
                # Calculate the gradients for this batch
                D_G_z1 = output.mean().item()
                # Add the gradients from the all-real and all-fake batches
                errD = -errD_real + errD_fake
                errD.backward()
                # Update D
                optimizerD.step()
                
                for p in netD.parameters():
                    p.data.clamp_(-0.1, 0.1)
                ############################
                # (2) Update G network: maximize log(D(G(z)))
                ###########################
                netG.zero_grad()
                label.fill_(real_label)  # fake labels are real for generator cost
                # Since we just updated D, perform another forward pass of all-fake batch through D
                output = netD(fake).view(-1)
                # Calculate G's loss based on this output
                #errG = criterion(output, label)
                errG = -output.mean()
                # Calculate gradients for G
                errG.backward()
                D_G_z2 = output.mean().item()
                # Update G
                optimizerG.step()
                # Output training stats
                if i % 50 == 0:
                    print('[%d/%d][%d/%d]\tLoss_D: %.4f\tLoss_G: %.4f\tD(x): %.4f\tD(G(z)): %.4f / %.4f'
                          % (epoch, num_epochs, i, len(dataloader),
                             errD.item(), errG.item(), D_x, D_G_z1, D_G_z2))

                # Save Losses for plotting later
                G_losses.append(errG.item())
                D_losses.append(errD.item())
                # Check how the generator is doing by saving G's output on fixed_noise
                if (iters % 500 == 0) or ((epoch == num_epochs-1) and (i == len(dataloader)-1)):
                    with torch.no_grad():
                        fake = netG(fixed_noise).detach().cpu()
                    img_list.append(vutils.make_grid(fake, padding=2, normalize=True))

                iters += 1
            thisEpoch = {
            'generator_state_dict': netG.state_dict(),
            'discrimantor_state_dict': netD.state_dict(),
            'GENoptimizer_state_dict': optimizerG.state_dict(),
            'DISoptimizer_state_dict': optimizerD.state_dict(),    
            }
            #progress[str(epoch)] =  thisEpoch
            name = "models/" + dr.split("/")[2] + str(epoch) + ".model"
            #torch.save(progress,name)
            if (epoch % save_dist == 0):
                torch.save(thisEpoch,name)
        plt.figure(figsize=(10,5))
        plt.title("Generator and Discriminator Loss During Training")
        plt.plot(G_losses,label="G")
        plt.plot(D_losses,label="D")
        plt.xlabel("iterations")
        plt.ylabel("Loss")
        plt.legend()
        plt.show()
        #%%capture
        fig = plt.figure(figsize=(8,8))
        plt.axis("off")
        ims = [[plt.imshow(np.transpose(i,(1,2,0)), animated=True)] for i in img_list]
        ani = animation.ArtistAnimation(fig, ims, interval=1000, repeat_delay=1000, blit=True)

        HTML(ani.to_jshtml())

        # Grab a batch of real images from the dataloader
        real_batch = next(iter(dataloader))
        # Plot the real images
        plt.figure(figsize=(15,15))
        plt.subplot(1,2,1)
        plt.axis("off")
        plt.title("Real Images")
        plt.imshow(np.transpose(vutils.make_grid(real_batch[0].to(device)[:64], padding=5, normalize=True).cpu(),(1,2,0)))

        # Plot the fake images from the last epoch
        plt.subplot(1,2,2)
        plt.axis("off")
        plt.title("Fake Images")
        plt.imshow(np.transpose(img_list[-1],(1,2,0)))
        plt.show()
        
        
        
if __name__ == "__main__":
    Trainer.train(dataroot)

