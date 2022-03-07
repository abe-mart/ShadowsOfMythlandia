# -*- coding: utf-8 -*-

import glob
import json
import random
import os
import sys

print('Welcome to the Forest')
print('')

folder = random.choice(glob.glob("Procedural/Rooms/*"))

room = random.choice(glob.glob(folder+'/*'))
    
running = True
while running == True:
    with open(room) as json_data:
        room_data = json.load(json_data)
    print('')
    print('---'+room_data['IdentificationComponent']['m_name']+'---')
    print(room_data['RoomComponent']['m_description'])
    dirlist = []
    codelist = []
    for door in room_data['m_doors']:
        dirlist.append(door['dir'])
        codelist.append(door['code'])
    dirlist.append('q to quit')
    print('')
    print('Available Exits: ' + str(dirlist))
    dir = input('Choose direction: ')
    if(dir=='q'):
        running = False
    elif dir in dirlist:
        print('You move ' +str(dir))
        newCode = codelist[dirlist.index(dir)]
        room = os.path.join(folder,newCode+'.json')
    else:
        print('Invalid direction')
    
print('Thanks for playing!')