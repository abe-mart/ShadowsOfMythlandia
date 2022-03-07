# -*- coding: utf-8 -*-

import random
#import language_check
#grammar = language_check.LanguageTool('en-US')
sr = random.SystemRandom()
import re
import pandas as pd

def describe_terrain_simple(words,terrain):
    sentence = words[terrain]['simple']
    return sentence

def describe_surroundings_simple(words,w,x,y):
    terrain = w.loc[w['location']==(x,y)]['base_terrain'].iloc[0]
    
    # Get neighbors
    neighbors = get_neighbors(w,x,y)
    
    # Filter to neighbors with paths
    neighbors = neighbors.loc[neighbors['has_path']==True]
    
    # Filter to neighbors with different terrain
    neighbors = neighbors.loc[neighbors['base_terrain']!=terrain]
    
    if(len(neighbors)>0):
        chosen_neighbor = neighbors.sample(1)
        neighbor_terrain = chosen_neighbor['base_terrain'].iloc[0]
        sentence = words[neighbor_terrain]['surrounding']
    else:
        sentence = ''
                    
    return sentence

def describe_terrain(words,terrain):
    sentence = ''
    if('desc' in words[terrain]):
        for d in words[terrain]['desc']:
            sentence += sr.choice(words[terrain]['desc'][d]) + ' '
    else:
        sentence = describe_terrain_simple(words,terrain)
    return replace_lists(sentence)

def describe_room_name(words,w,x,y):
    room = w.loc[w['location']==(x,y)].iloc[0]
    
    room_name = ''
    preposition = random.choice(['Near','Beside','Before','By'])
    
    if(room['has_entrance']==True):
        room_name = 'Entrance to the Sapwood'
    elif(room['has_objective']==True):
        room_name = preposition + ' ' + room['objective'].split('$')[1]
    elif(room['has_sidequest']==True):
        room_name = preposition + ' ' + room['sidequest'].split('$')[1]
    elif(room['has_prop']==True):
        room_name = preposition + ' ' + room['prop'].split('$')[1]
    else:
        room_name = words[room['base_terrain']]['name']
        
    return replace_lists(room_name)

def describe_barrier(words,w,room):
    return 'This room has a barrier'

def replace_lists(string):
    # Find all lists in description
    lists = re.findall(r'\((.*?)\)', string)
    # Replace list with a random element from the list
    for l in lists:
        string = string.replace('('+l+')',random.choice(l.split(',')))
        
    return string

def get_neighbors(w,x,y):
    p = []
    p.append((x-1,y-1))
    p.append((x,y-1))
    p.append((x+1,y-1))
    p.append((x-1,y))
    p.append((x+1,y))
    p.append((x-1,y+1))
    p.append((x,y+1))
    p.append((x+1,y+1))
    
    neighbors = pd.DataFrame()
    for loc in p:
        neighbors = neighbors.append(w[w['location'] == loc])

    return neighbors
    
#print(describe_ground(words,terrain))
#print(describe_plants(words,terrain))