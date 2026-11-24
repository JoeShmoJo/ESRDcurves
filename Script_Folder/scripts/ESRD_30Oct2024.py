# -*- coding: utf-8 -*-
"""
4/30/2021

Creates an emergency spillway release diagram (ESRD), otherwise known as special curves.
See EM 1110-2-3600 (2017 version), section 4.5.4 for the method

Updated by Josh Roach 20Dec2023 to include pool elevation rate of rise ESRD tables.

@author: Ryan Cahill: g2echrc9
"""
#%%

import shutil
import os
import matplotlib
import datetime
import random
import time
from matplotlib.ticker import ScalarFormatter, FuncFormatter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import interpolate
from scipy.interpolate import interp1d
from matplotlib.patches import Rectangle
import matplotlib.patches as patches
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from scipy.interpolate import griddata

###############################################################################


## Read in a Configuration CSV and create all dataframes and parameters

CONFIG_File = "../config/MOS_Table_CONFIG.csv"


df = pd.read_csv(CONFIG_File, skiprows=5)
dfResv = df[['Elev', 'Stor', 'MaxRel']].dropna()
dfSurchargeCurve = df[['Env_Elev', 'Release']].dropna()
Ts = float(df[['TS']].values[0]/24)
Reservoir = str(df['Reservoir'].values[0])
Paramsdf = df[['Param','Values']].dropna()
param_dict = Paramsdf.set_index('Param').to_dict()['Values']
dfTitleBlock = df[['Line','Text']].dropna()
Label_X_Coord = float(df[['Label_X_Coord']].values[0])
Label_Angle = float(df[['Label_Angle']].values[0])

curve_dfs = {}  # Dictionary to store the new DataFrames

if df['CurveName1'].isna().all():
    curve_dfs = 'None'
else:
    curve_dfs = {}
    for i in range(1, 6):  # Check for CurveName1 to CurveName5
        curve_name_col = f'CurveName{i}'
        x_col = f'X{i}'
        y_col = f'Y{i}'
        
        if curve_name_col in df.columns and x_col in df.columns and y_col in df.columns:
            curve_name = df[curve_name_col].iloc[0]
            if pd.notna(curve_name):  # Ensure the curve_name is not NaN
                curve_dfs[curve_name] = df[[x_col, y_col]].copy()
                curve_dfs[curve_name].columns = ['Elev', 'Release']


# Parameters from CONFIG file mostly for plotting but also used in calculations.
X_Lable_Angle = param_dict['X_Lable_Angle']
X_Min = param_dict['X_Min']
X_Max = param_dict['X_Max']
X_Step = param_dict['X_Step']
Y_Min = param_dict['Y_Min']
Y_Max = param_dict['Y_Max']
Y_Step = param_dict['Y_Step']
Inflow_Min = param_dict['Inflow_Min']
Inflow_Max = param_dict['Inflow_Max']
Inflow_Step = param_dict['Inflow_Step']
Inflow_Xlabel_Y_Buffer = param_dict['Inflow_Xlabel_Y_Buffer']
Inflow_Xlabel_FirstX = param_dict['Inflow_Xlabel_FirstX']
Inflow_Xlabel_Step = param_dict['Inflow_Xlabel_Step']
Inflow_Label_Angle = param_dict['Inflow_Label_Angle']
ROC_Min = param_dict['ROC_Min']
ROC_Max = param_dict['ROC_Max']
ROC_Step = param_dict['ROC_Step']
ROC_Xlabel_Y_Buffer = param_dict['ROC_Xlabel_Y_Buffer']
ROC_Xlabel_FirstX = param_dict['ROC_Xlabel_FirstX']
ROC_Xlabel_Step = param_dict['ROC_Xlabel_Step']
ROC_Label_Angle = param_dict['ROC_Label_Angle']


# Put a copy of the CONFIG file in the Out folder as documentation
copy_CONFIG_File = os.path.splitext(CONFIG_File)[0] + '_'+ Reservoir+'.csv'
shutil.copy(CONFIG_File, f"../out/{Reservoir}_CONFIG.csv")

# These parameters are used to make the ESRD grid. The small step seems overkill, but needed for interpolation for ROC ESRD curved from Inflow ESRD curves.
INFLOW_INCREMENT = 1000. #cfs. there will be one curve on the ESRD for each inflow from 0 cfs up to max spillway capacity.
RELEASE_INCREMENT = 1000. #cfs. this should be small, it's how many points along the x-axis to compute to make the curve look smooth
ELEV_INCREMENT = 1. #ft. Elevation value spacing for final table. 
ELEV_BUFFER = 0.05 #ft, elev buffer for detecting if we hit the surcharge elevation or not

# Define where the Inflow spreadsheet will live. This sheet could be printed and used as a lookup table by an operator or regulator.
CSV_OUTPUT = "../out/" + Reservoir + "Inflow_ESRD.csv"

#Constant c in EM 1110-2-3600
c = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet/day (about 2)

################################################################################
# FUNCTION DEFINITIONS

    
#####  Main  ###################################################################
# MAIN CODE

# Make arrays of inflows and releases of interest for ESRD curve.This produces a fine mesh that can be filtered later,
#  but is initially good for doing interpolations on.
inflows = np.arange(INFLOW_INCREMENT, Inflow_Max+1, INFLOW_INCREMENT)
releases = np.arange(RELEASE_INCREMENT, dfResv["MaxRel"].max() , RELEASE_INCREMENT) #x-axis values (can't actually start from 0)

# Set up your interpolation tables 
interpElevStor = interpolate.interp1d(dfResv["Elev"],dfResv["Stor"])
interpStorElev = interpolate.interp1d(dfResv["Stor"],dfResv["Elev"], fill_value=(dfResv["Elev"].min(), dfResv["Elev"].max()), bounds_error = False)
interpMaxRelElev = interpolate.interp1d(dfResv["MaxRel"],dfResv["Elev"])
interpSurchargeRelElev = interpolate.interp1d(dfSurchargeCurve["Release"],dfSurchargeCurve["Env_Elev"])


''' Calculate the ESRD curves - this is where the magic happens '''
# dfPlot = pd.DataFrame(index=releases)
dfInOutElev = pd.DataFrame(index=releases)

# Initialize a dictionary to collect DataFrame columns
columns_dict = {}

for inflow in inflows:
    dfOneInflow = pd.DataFrame(index=releases)
    dfOneInflow["Release"] = releases
    Q1 = inflow  # inflow, per EM
    Q2 = dfOneInflow["Release"].values
    # Step 2: Inflow Storage (SA)
    dfOneInflow["SA"] = c * Ts * (Q1 - Q2 * (1 + np.log(Q1/Q2)))
    # Step 3: Elevation on surcharge curve corresponding to each inflow
    dfOneInflow["ElE"] = interpSurchargeRelElev(inflow)
    # Step 4: Corresponding reservoir storage
    dfOneInflow["SE"] = interpElevStor(dfOneInflow["ElE"].values)
    # Step 5: Calculate critical storage for each SA
    dfOneInflow["SC"] = dfOneInflow["SE"] - dfOneInflow["SA"]
    # Step 6: Determine tentative maximum allowable pool elevation
    dfOneInflow["ElT"] = interpStorElev(dfOneInflow["SC"].values)
    # Step 7: Test against limits
    dfOneInflow["LowerBound"] = interpMaxRelElev(dfOneInflow["Release"].values)
    dfOneInflow["ElC"] = np.maximum(dfOneInflow["ElT"], dfOneInflow["LowerBound"])
    # The upper bound on the induced surcharge curve is trickier.
    dfOneInflow["UpperBound"] = interpSurchargeRelElev(dfOneInflow["Release"].values)
    
    hitTheEnvelope = False
    for release in releases:
        if hitTheEnvelope:  # Already hit it, stick on it.
            dfOneInflow.at[release, "ElC"] = dfOneInflow.at[release, "UpperBound"]
        elif dfOneInflow.at[release, "ElC"] > (dfOneInflow.at[release, "UpperBound"] - ELEV_BUFFER):  # Need a small buffer
            dfOneInflow.at[release, "ElC"] = dfOneInflow.at[release, "UpperBound"]
            hitTheEnvelope = True
    # Add the computed column to the dictionary with inflow as the key
    columns_dict[inflow] = dfOneInflow["ElC"].values
# Concatenate all the collected columns at once to dfInOutElev
dfInOutElev = pd.concat([dfInOutElev, pd.DataFrame(columns_dict, index=releases)], axis=1)


elevs = np.arange(dfResv["Elev"].min(), dfResv["Elev"].max(), ELEV_INCREMENT)
dfTable = pd.DataFrame(index=elevs)

# Prepare a list to hold the data columns
columns = []

for i, inflow in enumerate(inflows):
    interpObj = interpolate.interp1d(dfInOutElev[inflow], releases, fill_value=0, bounds_error=False)
    column = pd.Series(interpObj(elevs), index=elevs)
    column = column.apply(lambda x: min(x, inflow))
    columns.append(column)

dfTable = pd.concat(columns, axis=1, keys=inflows)
dfTable=dfTable.round(0)
dfTable.to_csv(CSV_OUTPUT)

### Format a new grid for elevation rate of rise

pivotOutflowInflowElev = dfInOutElev.reset_index()
pivotOutflowInflowElev.rename(columns={'index': 'outflow'}, inplace=True)
# Melt the DataFrame to long format
OutflowInflowElev = pd.melt(pivotOutflowInflowElev, id_vars=['outflow'], var_name='inflow', value_name='elev')
OutflowInflowElev['inflow'] = pd.to_numeric(OutflowInflowElev['inflow'])
# renaming for further calcs for error checking later
dfElevROC = OutflowInflowElev.copy()
# Convert the change in flow (cfs) to acre feet, assuming 1 hour duration flow
dfElevROC['Dstor'] = (dfElevROC['inflow'] - dfElevROC['outflow'])*0.0826
# # Why are ther inflow outflow pairs with outflows higher than inflows? Get rid of them....
# dfElevROC['Dstor'] = dfElevROC['Dstor'].clip(lower=0)

# Create an interpolation function for the storage-elevation curve

interp_func = interp1d(dfResv['Stor'], dfResv['Elev'], bounds_error=False, fill_value=0)

# Find the storage at the current elevation, delete the storage and find out where you would have been. This give the stor before the pool rise.
dfElevROC['new_stor'] = np.interp(dfElevROC['elev'], dfResv['Elev'], dfResv['Stor']) - dfElevROC['Dstor']
# Get the elev before the pool rise
dfElevROC['new_elev'] = interp_func(dfElevROC['new_stor'])
# Calculate the Elevation rate of change by subtracting the elevation before the pool rise from the current elevation
dfElevROC['Elev_ROC'] = dfElevROC['elev'] - dfElevROC['new_elev']
# Why are there negative rate of pool elevation changes? Get rid of them....
dfElevROC = dfElevROC[dfElevROC['Elev_ROC'] > 0]
#%%
# Define your new outflow and Elev_ROC increments
outflow_increments = np.arange(dfElevROC['outflow'].min(), dfElevROC['outflow'].max() + 1000, 1000)
Elev_ROC_increments = np.arange(0, ROC_Max, ROC_Step)  
# Create a mesh grid for outflow and Elev_ROC
XX, YY = np.meshgrid(outflow_increments, Elev_ROC_increments)
points = np.vstack((XX.ravel(), YY.ravel())).T
# Perform the interpolation
elev_interpolated = griddata(dfElevROC[['outflow', 'Elev_ROC']], dfElevROC['elev'], points, method='linear')
# Create the new DataFrame
df_interpolated = pd.DataFrame(points, columns=['outflow', 'Elev_ROC'])
df_interpolated['elev'] = elev_interpolated
# Drop any rows with NaN values if interpolation could not be done due to extrapolation issues
df_interpolated.dropna(inplace=True)
# Create pivot table
dfPlotROC = df_interpolated.pivot(index='outflow', columns='Elev_ROC', values='elev')



def transform_df(original_df):
    # Get the min and max elevation across all columns
    min_elevation = original_df.min().min()
    max_elevation = original_df.max().max()
    
    # Create a list of elevations in 1 ft increments
    elevation_range = np.arange(np.floor(min_elevation), np.ceil(max_elevation)+1, 1)
    
    # Create an empty DataFrame to store the results
    transformed_df = pd.DataFrame(index=elevation_range)
    
    # Interpolate for each rate of change column
    for rate in original_df.columns:
        # Exclude 'outflow' from the interpolation columns if it's included
        if rate != 'outflow':
            # Create interpolation function
            f = interp1d(original_df[rate], original_df.index, kind='linear', fill_value="extrapolate")
            # Interpolate and add to DataFrame
            transformed_df[rate] = f(elevation_range)
    
    # Transpose the DataFrame to have elevations as rows
    transformed_df = transformed_df.transpose()
    
    return transformed_df


transformed_df  = transform_df(dfPlotROC)
transformed_df[transformed_df<0]=0
transformed_df.index = transformed_df.index.round(1)
transformed_df=transformed_df.round(0)
transformed_df=transformed_df.transpose()
transformed_df.to_csv("../out/" + Reservoir + "ROC_ESRD.csv")


########


dfInflowPlot = dfInOutElev.copy()
# dfInflowPlot.index = dfInflowPlot.index.map(int)
# dfInflowPlot.columns = dfInflowPlot.columns.map(int)

columns_to_select = np.arange(Inflow_Min, Inflow_Max + 1, Inflow_Step)
# rows_to_select = [5000]
# rows_to_select = np.append(rows_to_select,np.arange(10000, X_Max + 1,10000 ))
rows_to_select = np.arange(1000, X_Max + 1,1000 )
# Use .iloc to select based on integer location indexing
dfInflowPlot = dfInflowPlot.loc[rows_to_select, columns_to_select]


### Plot Inflow ESRD

# The Max Release needs to be interpolated to line up with the inflows and releases
Max_Rel = pd.DataFrame()
Max_Rel["Elev"] = interpMaxRelElev(dfInflowPlot.index.values)
Max_Rel.index = dfInflowPlot.index

'''
PLOTTING CODE
'''

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def plot_inflow_esrd(df_inflow_plot, max_rel, df_surcharge_curve, curve_dfs, label_x_coord, label_angle,
                     y_min, y_max, y_step, x_min, x_max, x_step, inflow_xlabel_firstx, inflow_xlabel_step,
                     inflow_xlabel_y_buffer, inflow_label_angle, x_label_angle, reservoir, plot_dpi=400):
    plt.close('all')
    plt.rcParams["font.family"] = "Verdana"
    # fig, axes = plt.subplots(figsize=(6.5, 9))
    fig, axes = plt.subplots(figsize=(7, 7))
    fig.set_dpi(plot_dpi)
    # Plot the inflow ESRD curves
    df_inflow_plot.plot(ax=axes, legend=None, color='red')
    # Plot Max Discharge curve
    axes.plot(max_rel.index, max_rel['Elev'], label="Max Discharge", color='black')
    # Plot Induced Surcharge Envelope Curve
    axes.plot(df_surcharge_curve["Release"], df_surcharge_curve["Env_Elev"],
              label="Induced Surcharge Envelope Curve", color='black')

    # Plot additional curves if provided
    if curve_dfs != 'None':
        for curve_name, curve_df in curve_dfs.items():
            axes.plot(curve_df['Release'], curve_df['Elev'], label=curve_name,
                      color='gray', linestyle='--')
            # Label the curves
            x_label = label_x_coord
            idx = np.abs(curve_df['Release'] - x_label).idxmin()
            x = curve_df['Release'][idx]
            y = curve_df['Elev'][idx]
            y_offset = -1  # Adjust as needed
            axes.text(x, y + y_offset, curve_name, rotation=label_angle,
                      ha='center', va='bottom', fontsize=10, color='gray')

    # Set y-ticks and labels
    axes.set_yticks(np.arange(y_min, y_max + y_step + 1, y_step))
    axes.set_ylabel("Pool Elevation (feet, project datum)")
    axes.set_xlabel("Reservoir Release in 1,000 cfs")

    # Set axis limits
    axes.set_xlim(x_min, x_max)
    axes.set_ylim(y_min, y_max)

    # Add inflow labels at the top boundary of the plot
    top_y = df_surcharge_curve['Env_Elev'].iloc[0] - 0.2
    axes.text(x_max / 3, top_y + 0.5, 'Reservoir Inflow in 1,000 cfs',
              ha='left', va='bottom')

    # Define x_values for inflow labels
    x_values = [inflow_xlabel_firstx + i * inflow_xlabel_step
                for i in range(len(df_inflow_plot.columns))]

    # Add inflow labels
    for column, desired_x in zip(df_inflow_plot.columns, x_values):
        if desired_x <= x_max:
            y_value = np.interp(desired_x, df_inflow_plot.index,
                                df_inflow_plot[column]) + inflow_xlabel_y_buffer
            axes.text(desired_x, y_value, f'{int(column / 1000)}',
                      ha='center', va='bottom', color='black',
                      rotation=inflow_label_angle)

    # Customize x-ticks and grid
    axes.grid(alpha=0.5)
    axes.set_xticks(np.arange(0, x_max + 1, x_step))
    xlabels = ['{:,.0f}'.format(x) for x in axes.get_xticks() / 1000]
    axes.set_xticklabels(xlabels, rotation=x_label_angle)

    plt.subplots_adjust(left=0.15, right=0.975, top=0.99, bottom=0.08)
    plt.savefig(f"../out/{reservoir}_Inflow_ESRD.png", dpi=plot_dpi,
                #  bbox_inches='tight'
                 )
    plt.show()

def plot_roc_esrd(df_plot_roc, roc_step, df_surcharge_curve, df_resv, curve_dfs, label_x_coord, label_angle,
                  y_min, y_max, y_step, x_min, x_max, x_step, roc_xlabel_firstx, roc_xlabel_step,
                  roc_xlabel_y_buffer, roc_label_angle, x_label_angle, reservoir, plot_dpi=400):
    # Determine the number of decimal places in roc_step
    decimal_places = len(str(roc_step).split('.')[1]) if '.' in str(roc_step) else 0

    # Format column names
    df_plot_roc.columns = [f'{float(col):.{decimal_places}f}' for col in df_plot_roc.columns]

    # Remove decreasing sections
    for column in df_plot_roc.columns:
        rate_of_change = df_plot_roc[column].diff()
        decreasing = rate_of_change < 0
        first_decreasing_index = decreasing.idxmax() if decreasing.any() else None
        if first_decreasing_index is not None:
            df_plot_roc.loc[first_decreasing_index:, column] = np.nan

    plt.close('all')
    plt.rcParams["font.family"] = "Verdana"
    fig, axes = plt.subplots(figsize=(7, 7), dpi=plot_dpi)
    # Plot the ROC ESRD curves
    df_plot_roc.plot(ax=axes, legend=None, color='black')
    # Plot Induced Surcharge Envelope Curve
    axes.plot(df_surcharge_curve["Release"], df_surcharge_curve["Env_Elev"],
              label="Induced Surcharge Envelope Curve", color='black')
    # Plot Spillway Max Discharge
    axes.plot(df_resv["MaxRel"], df_resv["Elev"], label="Spillway Max Discharge", color='black')

    # Plot additional curves if provided
    if curve_dfs != 'None':
        for curve_name, curve_df in curve_dfs.items():
            axes.plot(curve_df['Release'], curve_df['Elev'], label=curve_name,
                      color='gray', linestyle='--')
            # Label the curves
            x_label = label_x_coord
            idx = np.abs(curve_df['Release'] - x_label).idxmin()
            x = curve_df['Release'][idx]
            y = curve_df['Elev'][idx]
            y_offset = -1  # Adjust as needed
            axes.text(x, y + y_offset, curve_name, rotation=label_angle,
                      ha='center', va='bottom', fontsize=10, color='gray')

    # Set y-ticks and labels
    axes.set_yticks(np.arange(y_min, y_max + y_step + 1, y_step))
    axes.set_ylabel("Pool Elevation (feet, project datum)")
    axes.set_xlabel("Reservoir Release in 1,000 cfs")

    # Set axis limits
    axes.set_xlim(x_min, x_max)
    axes.set_ylim(y_min, y_max)

    # Add pseudo axis label
    top_y = df_surcharge_curve['Env_Elev'].iloc[0] - 0.2
    axes.text(x_max / 4, top_y + 0.5, 'Reservoir Elevation Change in ft/hr',
              ha='left', va='bottom')

    # Define x_values for ROC labels
    x_values = [roc_xlabel_firstx + i * roc_xlabel_step
                for i in range(len(df_plot_roc.columns))]

    # Add ROC labels
    for column, desired_x in zip(df_plot_roc.columns, x_values):
        y_value = np.interp(desired_x, df_plot_roc.index,
                            df_plot_roc[column]) + roc_xlabel_y_buffer
        try:
            column_value = float(column)
            label_text = f'{column_value:.{decimal_places}f}'
        except ValueError:
            label_text = column
        axes.text(desired_x, y_value, label_text, ha='center', va='bottom',
                  rotation=roc_label_angle)

    # Customize x-ticks and grid
    axes.grid(alpha=0.5)
    axes.set_xticks(np.arange(0, x_max + 1, x_step))
    xlabels = ['{:,.0f}'.format(x) for x in axes.get_xticks() / 1000]
    axes.set_xticklabels(xlabels, rotation=x_label_angle)
    # plt.subplots_adjust(left=0.13, right=0.75, top=0.975, bottom=0.1)
    plt.subplots_adjust(left=0.15, right=0.975, top=0.99, bottom=0.08)
    plt.savefig(f"../out/{reservoir}_ROC_ESRD.png", dpi=plot_dpi,
                #  bbox_inches='tight'
                 )
    plt.show()

def main():
    # Load or define all the variables needed here
    # For example:
    # df_inflow_plot = pd.read_csv('path_to_inflow_plot.csv')
    # max_rel = pd.read_csv('path_to_max_rel.csv')
    # df_surcharge_curve = pd.read_csv('path_to_surcharge_curve.csv')
    # Define all other variables used in the plotting functions

    # Call the plotting functions
    plot_inflow_esrd(
        df_inflow_plot=dfInflowPlot,
        max_rel=Max_Rel,
        df_surcharge_curve=dfSurchargeCurve,
        curve_dfs=curve_dfs,
        label_x_coord=Label_X_Coord,
        label_angle=Label_Angle,
        y_min=Y_Min,
        y_max=Y_Max,
        y_step=Y_Step,
        x_min=X_Min,
        x_max=X_Max,
        x_step=X_Step,
        inflow_xlabel_firstx=Inflow_Xlabel_FirstX,
        inflow_xlabel_step=Inflow_Xlabel_Step,
        inflow_xlabel_y_buffer=Inflow_Xlabel_Y_Buffer,
        inflow_label_angle=Inflow_Label_Angle,
        x_label_angle=X_Lable_Angle,
        reservoir=Reservoir
    )

    plot_roc_esrd(
        df_plot_roc=dfPlotROC,
        roc_step=ROC_Step,
        df_surcharge_curve=dfSurchargeCurve,
        df_resv=dfResv,
        curve_dfs=curve_dfs,
        label_x_coord=Label_X_Coord,
        label_angle=Label_Angle,
        y_min=Y_Min,
        y_max=Y_Max,
        y_step=Y_Step,
        x_min=X_Min,
        x_max=X_Max,
        x_step=X_Step,
        roc_xlabel_firstx=ROC_Xlabel_FirstX,
        roc_xlabel_step=ROC_Xlabel_Step,
        roc_xlabel_y_buffer=ROC_Xlabel_Y_Buffer,
        roc_label_angle=ROC_Label_Angle,
        x_label_angle=X_Lable_Angle,
        reservoir=Reservoir
    )

if __name__ == '__main__':
    main()








# %%
