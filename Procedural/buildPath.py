# -*- coding: utf-8 -*-

from scipy.spatial.distance import pdist, cdist, cityblock, squareform
from tsp_solver.greedy import solve_tsp
import matplotlib.pyplot as plt
import numpy as np

def shortest_path(w):
    # Get points of interest
    POIs = w.loc[(w['has_prop']==True) | (w['has_objective']==True)]
    
    # Add entrance twice for full loop
    POIs = POIs.append(w.loc[w['has_entrance']==True])
    POIs = POIs.append(w.loc[w['has_entrance']==True])
    
    # Create matrix of locations
    locations = POIs['location'].as_matrix()
    X = np.zeros([len(POIs),2])
    for ind, location in enumerate(locations):
        X[ind,0] = location[0]
        X[ind,1] = location[1]

    # Get pairwise cityblock distance matrix
    D = squareform(pdist(X,'cityblock'))

    # Traveling Salesman
    path = solve_tsp(D,optim_steps=3,endpoints=(len(X)-1,len(X)-2))

    # Reorder points
    X_opt = X[path,:]

#    plt.figure()
#    plt.scatter(X[:,1],X[:,0])
#    plt.plot(X_opt[:,1],X_opt[:,0])

    return X_opt

def build_path(w):
    # Initialize room parameters
    w['has_path'] = False
    w['segment'] = ''
    w['leg'] = ''
    
    # Find shortest path
    X_opt = shortest_path(w)
    
    # Fill in path segments
    segment = 0
    leg = 'A'
    for i in range(len(X_opt)-1):
        p1 = X_opt[i,:] # Starting point
        p2 = X_opt[i+1,:] # Ending point
        
        # Make line of points from start to end
        # Collect all points that touch the line
        xpoints = np.round(np.linspace(p1[0],p2[0],100))
        ypoints = np.round(np.linspace(p1[1],p2[1],100))
        points = np.c_[xpoints,ypoints].astype(int)
        points = tuple(map(tuple, points))
        points = list(set(points))
        
        # Add path points to world
        for point in points:
            w.loc[w['location']==point,'has_path'] = True
            w.loc[w['location']==point,'segment'] = segment
            w.loc[w['location']==point,'leg'] = leg
            
        # Increment segment and check leg
        segment = segment + 1
        nextLoc = tuple(p2.astype(int))
        if(w.loc[w['location']==nextLoc]['has_objective'].iloc[0]==True):
            leg = 'B'
            
    return w

def connect_side_quests(w):
    # Initialize room parameters
    w['side_seg'] = ''
    w['side_leg'] = ''
    side_seg = 0
    for j, room in w.loc[w['has_sidequest']==True].iterrows():
        # Find closed point on the path
        room_loc = np.array([room['location']])
        path = w.loc[(w['has_path']==True) & (w['side_seg']=='')]
        path_loc = np.zeros([len(path),2])
        for i,location in enumerate(path['location']):
            path_loc[i,:] = np.array(location)
        dist = cdist(room_loc,path_loc,'cityblock')
        min_ind = np.argmin(dist) # closet room on path
        
        # Get segment of closest room
        seg = path.iloc[min_ind]['segment']
        
        # Find rooms in that segment
        seg_rooms = path.loc[(path['segment']==seg)]
        
        # Choose two random rooms from the segment to connect to
        tworooms = seg_rooms.sample(2)
        
        # Connect path to the two rooms
        for i, connect in tworooms.iterrows():
            p1 = room['location'] # Starting point
            p2 = connect['location'] # Ending point
            
            # Make line of points from start to end
            # Collect all points that touch the line
            xpoints = np.round(np.linspace(p1[0],p2[0]))
            ypoints = np.round(np.linspace(p1[1],p2[1]))
            points = np.c_[xpoints,ypoints].astype(int)
            points = tuple(map(tuple, points))
            points = list(set(points))
            
            # Add path points to world
            for point in points:
                w.loc[w['location']==point,'has_path'] = True
                w.loc[w['location']==point,'segment'] = connect['segment']
                w.loc[w['location']==point,'leg'] = connect['leg']
                w.loc[w['location']==point,'side_seg'] = side_seg
                if(i==0):
                   w.loc[w['location']==point,'side_leg'] = 'A'
                else:
                   w.loc[w['location']==point,'side_leg'] = 'B'
        side_seg = side_seg + 1
    return w

def make_connections(w):
    # Init connection holder
    connections = {}
    
    # Get rooms on path
    rooms = w.loc[w['has_path']==True]

    # Find connections
    for i, room in rooms.iterrows():
        connection = {}
        rx,ry = room['location']

        nx = rx - 1
        ny = ry - 1
        direction = 'nw'
        if(sum(w['location']==(nx,ny))>0): # Check if neighbor exists
            if(w.loc[w['location']==(nx,ny)]['has_path'].iloc[0]==True): # Check if neighbor is on path
                connection[direction] = w.loc[w['location']==(nx,ny)]['code'].iloc[0]
        nx = rx - 1
        ny = ry
        direction = 'w'
        if(sum(w['location']==(nx,ny))>0): # Check if neighbor exists
            if(w.loc[w['location']==(nx,ny)]['has_path'].iloc[0]==True): # Check if neighbor is on path
                connection[direction] = w.loc[w['location']==(nx,ny)]['code'].iloc[0]
        nx = rx - 1
        ny = ry + 1
        direction = 'sw'
        if(sum(w['location']==(nx,ny))>0): # Check if neighbor exists
            if(w.loc[w['location']==(nx,ny)]['has_path'].iloc[0]==True): # Check if neighbor is on path
                connection[direction] = w.loc[w['location']==(nx,ny)]['code'].iloc[0]
        nx = rx
        ny = ry - 1
        direction = 'n'
        if(sum(w['location']==(nx,ny))>0): # Check if neighbor exists
            if(w.loc[w['location']==(nx,ny)]['has_path'].iloc[0]==True): # Check if neighbor is on path
                connection[direction] = w.loc[w['location']==(nx,ny)]['code'].iloc[0]
        nx = rx
        ny = ry + 1
        direction = 's'
        if(sum(w['location']==(nx,ny))>0): # Check if neighbor exists
            if(w.loc[w['location']==(nx,ny)]['has_path'].iloc[0]==True): # Check if neighbor is on path
                connection[direction] = w.loc[w['location']==(nx,ny)]['code'].iloc[0]
        nx = rx + 1
        ny = ry - 1
        direction = 'ne'
        if(sum(w['location']==(nx,ny))>0): # Check if neighbor exists
            if(w.loc[w['location']==(nx,ny)]['has_path'].iloc[0]==True): # Check if neighbor is on path
                connection[direction] = w.loc[w['location']==(nx,ny)]['code'].iloc[0]
        nx = rx + 1
        ny = ry
        direction = 'e'
        if(sum(w['location']==(nx,ny))>0): # Check if neighbor exists
            if(w.loc[w['location']==(nx,ny)]['has_path'].iloc==True): # Check if neighbor is on path
                connection[direction] = w.loc[w['location']==(nx,ny)]['code'].iloc[0]
        nx = rx + 1
        ny = ry + 1
        direction = 'se'
        if(sum(w['location']==(nx,ny))>0): # Check if neighbor exists
            if(w.loc[w['location']==(nx,ny)]['has_path'].iloc[0]==True): # Check if neighbor is on path
                connection[direction] = w.loc[w['location']==(nx,ny)]['code'].iloc[0]
                
        connections[room['code']] = connection
        
    return w, connections
