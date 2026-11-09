import numpy as np
import scipy.ndimage 

x = np.array([[1, 2, 3], [4, 5, 6]], np.int32)
mean_x = x.mean()
print(mean_x)

# high =  band - low_kernel
band = np.random.rand(100, 100) # random unreal band
low_kernel = np.ones((3,3))/9
low = convolve(band,low_kernel) # -> create concolve func