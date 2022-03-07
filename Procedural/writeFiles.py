# -*- coding: utf-8 -*-

import pandas as pd
import json
import os

def write_files(w,connections,seed):
    rooms = []     
    
    # Read in room data from mudmap 
    for i, place in w.loc[w['has_path']==True].iterrows():
        room = {}
        room['IdentificationComponent'] = {'m_name':place['name']}
        room['InventoryComponent'] = {}
        room['LocalMessageComponent'] = {}
        room['RoomComponent'] = {}
        room['RoomComponent']['m_code'] = place['code']
        room['RoomComponent']['m_description'] = place['description']
            
        room['m_doors'] = []
        for direction in connections[place['code']]:
            door = {}
            door['code'] = connections[place['code']][direction]
            door['dir']  = direction
            door['status'] = 'open'
            room['m_doors'].append(door)
        
        rooms.append(room)
        
    # Write out room data in Derek's json format
    
    folder = r'C:\Users\oacom\Documents\Python Scripts\mudworlds\Procedural\Rooms/skole'+str(seed)+'/'
    
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
        
    for room in rooms:
        filepath = os.path.join(folder,room['RoomComponent']['m_code']+'.json')
        with open(filepath, 'w') as f:
         json.dump(room, f)