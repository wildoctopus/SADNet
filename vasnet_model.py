__author__ = 'Jiri Fajtl'
__email__ = 'ok1zjf@gmail.com'
__version__= '3.6'
__status__ = "Research"
__date__ = "1/12/2018"
__license__= "MIT License"


import torch
import torch.nn as nn
import torch.nn.functional as F
from config import  *
from layer_norm import  *
import numpy as np



class SelfAttention(nn.Module):

    def __init__(self, apperture=-1, ignore_itself=False, input_size=1024, output_size=1024):
        super(SelfAttention, self).__init__()

        self.apperture = apperture
        self.ignore_itself = ignore_itself

        self.m = input_size
        self.output_size = output_size

        self.K = nn.Linear(in_features=self.m, out_features=self.output_size, bias=False)
        self.Q = nn.Linear(in_features=self.m, out_features=self.output_size, bias=False)
        self.V = nn.Linear(in_features=self.m, out_features=self.output_size, bias=False)
        self.output_linear = nn.Linear(in_features=self.output_size, out_features=self.m, bias=False)

        self.drop50 = nn.Dropout(0.5)



    def forward(self, x):
        n = x.shape[0]  # sequence length

        K = self.K(x)  # ENC (n x m) => (n x H) H= hidden size
        Q = self.Q(x)  # ENC (n x m) => (n x H) H= hidden size
        V = self.V(x)

        Q *= 0.06
        logits = torch.matmul(Q, K.transpose(1,0))

        if self.ignore_itself:
            # Zero the diagonal activations (a distance of each frame with itself)
            logits[torch.eye(n).byte()] = -float("Inf")

        if self.apperture > 0:
            # Set attention to zero to frames further than +/- apperture from the current one
            onesmask = torch.ones(n, n)
            trimask = torch.tril(onesmask, -self.apperture) + torch.triu(onesmask, self.apperture)
            logits[trimask == 1] = -float("Inf")

        att_weights_ = nn.functional.softmax(logits, dim=-1)
        weights = self.drop50(att_weights_)
        y = torch.matmul(V.transpose(1,0), weights).transpose(1,0)
        y = self.output_linear(y)

        return y, att_weights_





#Difference Attention Module 

class DAM(nn.Module):
    def __init__(self):
        super(DAM, self).__init__()

        self.dropout1 = nn.Dropout2d(0.5)
        self.fc1 = nn.Linear(1024, 1024)
        self.fc2 = nn.Linear(1024, 1024)

    # x represents our data
    def forward(self, x):
        d1 = self.fc1(torch.abs(x[1] - x[0]))
        d1 = F.relu(d1)
        # d1 = self.dropout1(d1)
        # d1 = self.fc2(d1)

        d2 = self.fc1(torch.abs(x[2] - x[0]))
        d2 = F.relu(d2)
        # d2 = self.dropout1(d2)
        # d2 = self.fc2(d2)

        d3 = self.fc1(torch.abs(x[4] - x[0]))
        d3 = F.relu(d3)
        # d3 = self.dropout1(d3)
        # d3 = self.fc2(d3)

        t = d1 + d2 + d3

        for i in range(1, len(x) - 4):
            d1 = self.fc1(torch.abs(x[i+1] - x[i]))
            d1 = F.relu(d1)
            # d1 = self.dropout1(d1)
            # d1 = self.fc2(d1)

            d2 = self.fc1(torch.abs(x[i+2] - x[i]))
            d2 = F.relu(d2)
            # d2 = self.dropout1(d2)
            # d2 = self.fc2(d2)

            d3 = self.fc1(torch.abs(x[i+4] - x[i]))
            d3 = F.relu(d3)
            # d3 = self.dropout1(d3)
            # d3 = self.fc2(td3)

            temp = d1 + d2 + d3

            t = torch.cat((t, temp))
        
        for i in range(len(x)-4, len(x)):
            t = torch.cat((t, x[i]))


        #print("shape of t ", t.shape)
        t = torch.reshape(t, (len(x), 1024))
        t = self.dropout1(t)
        
        return t     



#VASNet module
class VASNet(nn.Module):

    def __init__(self):
        super(VASNet, self).__init__()

        self.m = 1024 # cnn features size
        self.hidden_size = 1024

        self.att = SelfAttention(input_size=self.m, output_size=self.m)
        self.dam = DAM()
        self.ka = nn.Linear(in_features=self.m, out_features=1024)
        self.kb = nn.Linear(in_features=self.ka.out_features, out_features=1024)
        self.kc = nn.Linear(in_features=self.kb.out_features, out_features=1024)
        self.kd = nn.Linear(in_features=self.ka.out_features, out_features=1)

        self.sig = nn.Sigmoid()
        self.relu = nn.ReLU()
        self.drop50 = nn.Dropout(0.5)
        self.softmax = nn.Softmax(dim=0)
        self.layer_norm_y = LayerNorm(self.m)
        self.layer_norm_ka = LayerNorm(self.ka.out_features)


    def forward(self, x, seq_len):

        m = x.shape[2] # Feature size

        # Place the video frames to the batch dimension to allow for batch arithm. operations.
        # Assumes input batch size = 1.

        #mn = self.dam(x)
        #print("Shape of x", x.shape)

        x = x.view(-1, m)

        mn = self.dam(x)

        #print("Shape of x", x.shape)
        y, att_weights_ = self.att(x)

        #print("Shape of y", y.shape)

        

        

        #y = y + mn
        y = self.drop50(y)
        y = y + mn
        y = self.layer_norm_y(y)

        # Frame level importance score regression
        # Two layer NN
        y = self.ka(y)
        y = self.relu(y)
        y = self.drop50(y)
        y = self.layer_norm_ka(y)

        y = self.kd(y)
        y = self.sig(y)
        y = y.view(1, -1)

        return y, att_weights_



if __name__ == "__main__":
    pass
