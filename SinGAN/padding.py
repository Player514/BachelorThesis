import torch.nn.functional as F


#TODO name/structure fixing...
class padding:
    def __init__(self, pad, custompadding = False):
        self.pad = pad
    def add3dpadding(self,tensor):
        return F.pad(tensor,(self.pad,self.pad,self.pad,self.pad,self.pad,self.pad))
    def add2dpadding(self,tensor):
        return F.pad(tensor,(self.pad,self.pad,self.pad,self.pad))
    #TODO combine into one function and include custom padding
    def __call__(self,tensor):
        return self.add3dpadding(tensor)
