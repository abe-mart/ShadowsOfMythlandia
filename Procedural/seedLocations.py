# -*- coding: utf-8 -*-
"""
Created on Mon Dec 18 21:41:21 2017

@author: oacom
"""

import yaml
import pandas as pd
import numpy as np

def place_props(words,w,num_props):
    # Init prop status
    w['has_prop'] = False
    w['prop'] = ''
    
    # Choose some props
    props = np.random.choice(words['generic_props'],num_props,replace=False)

    inds = np.random.randint(0,len(w),num_props)

    for i, ind in enumerate(inds):
        w.loc[ind,'has_prop'] = True
        w.loc[ind,'prop'] = props[i]
        
    return w

def place_obj(words,w):
    # Init objective status
    w['has_objective'] = False
    w['objective'] = False
    
    # Choose objective
    obj = np.random.choice(words['objectives'])
    
    ind = np.random.randint(0,len(w))
    
    w.loc[ind,'has_objective'] = True
    w.loc[ind,'objective'] = obj
    
    return w

def place_entrance(w):
    # Init entrance status
    w['has_entrance'] = False
    
    ind = np.random.randint(0,len(w))
    
    w.loc[ind,'has_entrance'] = True
    
    return w

def place_sidequests(words,w,num_sidequests):
    # Init sidequest status
    w['has_sidequest'] = False
    w['sidequest'] = False
    
    # Choose some sidequests
    sidequests = np.random.choice(words['sidequests'],num_sidequests,replace=False)
    
    # Pick some map locations
    allowed_inds = set(range(len(w)))
    disallowed_inds = set(w.loc[w['has_path']==True].index.values)
    allowed_inds = list(allowed_inds - disallowed_inds) # Exclude path values
    inds = np.random.choice(allowed_inds,num_sidequests,replace=False)

    for i, ind in enumerate(inds):
        w.loc[ind,'has_sidequest'] = True
        w.loc[ind,'sidequest'] = sidequests[i]
        
    return w