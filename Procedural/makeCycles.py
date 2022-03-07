# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import random
from describeRoom import describe_barrier

def make_cycles(w,words,connections):
    # Get both legs of the main cycle
    legA = w.loc[w['leg']=='A']
    legB = w.loc[w['leg']=='B']
    
    # Check length of main legs
    lenA = len(legA)
    lenB = len(legB)
    
    # Init barriers
    w['has_barrier'] = False
    w['barrier_desc'] = ''
    
    if(lenA > lenB+10):
        print('Lock and Key')
        # Choose lock point
        lock_room = legA.sample(1)
        w[w['code']==lock_room['code']]['has_barrier'] = True
        w[w['code']==lock_room['code']]['barrier'] = 'This room has a barrier'
    elif(lenB > lenA+10):
        print('Secret Passage')
    else:
        print('Traps or Danger')
        
    return w