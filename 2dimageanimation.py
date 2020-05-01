from PIL import Image, ImageDraw
import numpy as np

w, h = 512, 512
data = np.zeros((h, w, 3), dtype=np.uint8)


#img = Image.new(mode, size, color)
#img.save(filename)


class randomselectmove():
	
	def randomselectmove(self,start,end,numframes):
		print(len(start.shape))
		for dimension in range(0,len(start.shape)):
			print(dimension)
			
	def getnext(self):
		pass
		

rsm = randomselectmove()
rsm.randomselectmove(data,data,4)
