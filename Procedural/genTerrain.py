# -*- coding: utf-8 -*-

import numpy as np
from perlin import perlin
from matplotlib import pyplot as plt
import pandas as pd
import yaml
import random as sr

def genTerrain(seed,map_name,words):
    plt.close('all')
    
#    map_name = 'Forest1'
    
    # Make perlin noise for base terrain    
    lin = np.linspace(0,10,30,endpoint=False) # map size
    x,y = np.meshgrid(lin,lin) # generate grid
    t = perlin(x,y,seed) # make noise on grid
        
    # Show base terrain
    plt.figure()
    plt.imshow(t, interpolation='nearest',cmap='terrain')
    plt.title('Base Terrain')
    plt.colorbar()
    
    # Open description file
#    with open('./Words/terrains3.yaml') as f:
#        words = yaml.safe_load(f)

    # Make world dataframe
    w = pd.DataFrame(columns=['location','code','base_terrain'])
    terrainTypes = words['terrainTypes']
    ranges = np.linspace(t.min(),t.max(),len(terrainTypes)+1)
    for i,value in np.ndenumerate(t):
        # Assign base terrain
        if(value==0):
            base_terrain = 'forest'
        elif(value==-1):
            base_terrain = 'water'
        elif(value==1):
            base_terrain = 'clearing'
        elif(value==2):
            base_terrain = 'mountain'
          
        # Assign base terrain
        for j in range(len(ranges)-1):
            if(value >= ranges[j] and value < ranges[j+1]):
                base_terrain = terrainTypes[j]

        # Generate room code
        code = map_name+'_'+str(0)+'_'+str(i[0])+'_'+str(i[1])
        # Add to master list
        wnew = {}
        wnew['location'] = i
        wnew['code'] = code
        wnew['base_terrain'] = base_terrain
        w = w.append(wnew,ignore_index=True)
        
    return w