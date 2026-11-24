# -*- coding: utf-8 -*-
"""
Created on Thu Aug 29 10:06:37 2024

@author: g2encjer
"""

import pandas as pd
import numpy as np
import matplotlib as plt

Spillway = pd.read_clipboard()
RO= pd.read_clipboard()
Penstock = pd.read_clipboard()



merged_df = RO.merge(Penstock, on='Elev', how='outer', suffixes=('_RO', '_Penstock'))
merged_df_2 = merged_df.merge(Spillway.rename(columns={'Release':'Release_Spillway'}), on='Elev', how='outer')
merged_df_2=merged_df_2.set_index('Elev',drop=True)
merged_df_2=merged_df_2.drop(columns=['Elev'])
elev_range = np.arange(merged_df_2.index.min(), merged_df_2.index.max() + 1, 1)
elev_df=pd.DataFrame(index=elev_range)
merged_df_3=elev_df.join(merged_df_2)


filled_df = merged_df_3.interpolate(method='linear', limit_area='inside')
filled_df['Capacity']=filled_df.sum(axis=1)

import JoshModules as JR
import numpy as np

Rating_Dict = JR.get_rating_tables(['FRN'])

Rating_df = Rating_Dict['FRN']
# Rating_df=Rating_df.set_index('ELEV')

Rating_df.plot()

Rating_df=Rating_df[Rating_df['ELEV'] % 1 == 0]



Rating_df=Rating_df[Rating_df['ELEV'] > 359]
# Rating_df=Rating_df[Rating_df['ELEV'] <1482]

from numpy.polynomial.polynomial import Polynomial

coeffs = np.polyfit(Rating_df['ELEV'], Rating_df['STOR'], 2)
p = Polynomial(coeffs[::-1])
Rating_df['STOR_Poly'] = p(Rating_df['ELEV'])
Rating_df=Rating_df.set_index('ELEV')
Rating_df.plot()
