# -*- coding: utf-8 -*-
"""
Created on Mon Sep 27 13:04:23 2021

@author: jruthe
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
import math
import statistics
from math import sin, cos, sqrt, atan2, radians
# from shapely.geometry import Point, LineString
import os, os.path
# import win32com.client
# from win32com.client import Dispatch,constants

## Define functions

def lookup_func(field_mean):

    Prod_Mat_Gas = pd.read_csv(path_Local + 'Productivity_Gas.csv', header = 0, index_col = 0)
       
    tmp = Prod_Mat_Gas[(Prod_Mat_Gas['Bin low'] < field_mean) & (Prod_Mat_Gas['Bin high'] >= field_mean)].index.values.astype(int)[0]
    
    return   tmp    

def lookup_func_2(Loss_Mat_Ave, assignment):
   
    tmp = Loss_Mat_Ave.iloc[assignment-1, :]
    
    return   tmp      

## Import data

productivity = 212 # mscf/well/day
GOR = 200 # mscf/bbl
GOR_cutoff = 100 # mscf/bbl

path_Local          = 'C:\\Users\\wennan\\Downloads\\clone\\OPGEEv4\\fugitive_model\\'

Loss_Mat_Gas = pd.read_csv(path_Local + 'Loss_Matrix_Gas.csv', header = 0, index_col = 0)
Loss_Mat_Oil = pd.read_csv(path_Local + 'Loss_Matrix_Oil.csv', header = 0, index_col = 0)
Prod_Mat_Gas = pd.read_csv(path_Local + 'Productivity_Gas.csv', header = 0, index_col = 0)
Prod_Mat_Oil = pd.read_csv(path_Local + 'Productivity_Oil.csv', header = 0, index_col = 0)

## Calculations

# (1) Appeoximate field productivity distribution

cols = ['Assignment', 'col_shift', 'Mean gas rate (Mscf/well/day)', 'Frac total gas']
Field_Productivity = pd.DataFrame(columns = cols, index = Prod_Mat_Gas.index)

if (GOR > GOR_cutoff):
    Field_Productivity['Mean gas rate (Mscf/well/day)'] = Prod_Mat_Gas['Normalized rate'] * productivity
    Field_Productivity['Frac total gas'] = Prod_Mat_Gas['Frac total gas']
else:
    Field_Productivity['Mean gas rate (Mscf/well/day)'] = Prod_Mat_Oil['Normalized rate'] * productivity 
    Field_Productivity['Frac total gas'] = Prod_Mat_Oil['Frac total gas']
    
Field_Productivity['Assignment'] = Field_Productivity.apply(lambda row: lookup_func(row['Mean gas rate (Mscf/well/day)']), axis = 1)

# (2) Choose deterministic loss rate

cols_gas = ['Well', 'Header', 'Heater', 'Separator', 'Meter', 'Tanks-leaks', 'Tank-thief hatch', 'Recip Comp', 'Dehydrator', 'Chem Inj Pump', 'Pneum Controllers', 'Flash factor', 'LU-plunger', 'LU-no plunger']
cols_oil = ['Well', 'Header', 'Heater', 'Separator', 'Meter', 'Tanks-leaks', 'Tank-thief hatch', 'Recip Comp', 'Dehydrator', 'Chem Inj Pump', 'Pneum Controllers', 'Flash factor']
tranch = range(10)

if (GOR > GOR_cutoff):
    # Get a numpy array
    Loss_Mat_Ave = Loss_Mat_Gas.mean(axis = 0).values
    # reshape
    Loss_Mat_Ave = Loss_Mat_Ave.reshape(10,14)
    df = pd.DataFrame(Loss_Mat_Ave, columns=cols_gas, index=range(10))
else:
    # Get a numpy array
    Loss_Mat_Ave = Loss_Mat_Oil.mean(axis = 0).values
    # reshape
    Loss_Mat_Ave = Loss_Mat_Ave.reshape(10,12)
    df = pd.DataFrame(Loss_Mat_Ave, columns=cols_oil, index=range(10))    

df = Field_Productivity.apply(lambda row: lookup_func_2(df, row['Assignment']), axis = 1)

# Equipment level loss rates are the weighted average across all tranches

result = df.T.dot(Field_Productivity['Frac total gas'])