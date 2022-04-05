# -*- coding: utf-8 -*-

from genTerrain import genTerrain
from describeRoom import describe_terrain, describe_surroundings_simple, describe_room_name
from seedLocations import place_props, place_obj, place_entrance, place_sidequests
from buildPath import build_path, connect_side_quests, make_connections
from makeCycles import make_cycles
from writeFiles import write_files
import yaml
import random
import matplotlib.pyplot as plt

map_name = 'Cave'

# Load description file
with open('./Words/'+map_name+'.yaml') as f:
    words = yaml.safe_load(f)

# Random seed
seed = 14

# Generate base terrain
w = genTerrain(seed,map_name,words)

# Place props
w = place_props(words,w,6)
# Place main objective
w = place_obj(words,w)
# Place entrance
w = place_entrance(w)
# Connect points of interest with path
w = build_path(w)

# Place sidequests
w = place_sidequests(words,w,4)
# Connect sidequests with path
w = connect_side_quests(w)

# Record connections
w,connections = make_connections(w)

w = make_cycles(w,words,connections)

rooms = w.loc[(w['has_prop']==True) | (w['has_objective']==True) | (w['has_entrance']==True) | (w['has_path']==True) | (w['has_sidequest']==True)]

for ind, room in rooms.iterrows():
    x = room['location'][0]
    y = room['location'][1]
        
    # Print room name
    print('Room ' + str(x) + ' ' + str(y))
    room_name = describe_room_name(words,w,x,y)
    print(room_name)
    w.loc[w['code']==room['code'],'name'] = room_name
    
    # Room description
    d = describe_terrain(words,room['base_terrain'])
    
    if(room['has_objective']==True):
        d += room['objective'].split('$')[0]
    elif(room['has_sidequest']==True):
        d += room['sidequest'].split('$')[0]
    elif(room['has_prop']==True):
        d += room['prop'].split('$')[0]
    elif(room['has_barrier']==True):
        d += room['barrier']
    else:
        d += ''
        
    if(random.random()>0.5):
        d += describe_surroundings_simple(words,w,x,y)
    else:
        d += ''
        
    description = d
    print(description)
    print()
    w.loc[w['code']==room['code'],'description'] = description
    
    # Plot path on map
    if(room['has_objective']==True):
        plt.scatter([y],[x],color='r',marker='x')
    elif(room['has_entrance']==True):
        plt.scatter([y],[x],c='tab:orange')
    elif(room['has_sidequest']==True):
        plt.scatter([y],[x],c='m')
    elif(room['has_prop']==True):
        plt.scatter([y],[x],c='k')
    elif(room['has_path']==True and room['leg']=='A'):
        plt.scatter([y],[x],color='0.5')
    elif(room['has_path']==True and room['leg']=='B'):
        plt.scatter([y],[x],color='0.75')
    else:
        pass
    
# Write files to json
write_files(w,connections,seed)