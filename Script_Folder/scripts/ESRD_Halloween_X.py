# -*- coding: utf-8 -*-
"""
4/30/2021

Creates an emergency spillway release diagram (ESRD), otherwise known as special curves.
See EM 1110-2-3600 (2017 version), section 4.5.4 for the method

Updated by Josh Roach 20Dec2023 to include pool elevation rate of rise ESRD tables.

@author: Ryan Cahill: g2echrc9
"""
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
import ast

###############################################################################


## Read in a Configuration CSV and create all dataframes and parameters



CONFIG_File = "../config/COT_CONFIG.csv"



# These parameters are used to make the ESRD grid. The small step seems overkill, but needed for interpolation for ROC ESRD curved from Inflow ESRD curves.
INFLOW_INCREMENT = 1000. #cfs. there will be one curve on the ESRD for each inflow from 0 cfs up to max spillway capacity.
RELEASE_INCREMENT = 1000. #cfs. this should be small, it's how many points along the x-axis to compute to make the curve look smooth
ELEV_INCREMENT = 1. #ft. Elevation value spacing for final table. 
ELEV_BUFFER = 0.05 #ft, elev buffer for detecting if we hit the surcharge elevation or not

#Constant c in EM 1110-2-3600
c = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet/day (about 2)

def process_config(CONFIG_File):
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
    Inflow_Label_Angle = ast.literal_eval(df['Inflow_Label_Angle'].iloc[0])
    ROC_Min = param_dict['ROC_Min']
    ROC_Max = param_dict['ROC_Max']
    ROC_Step = param_dict['ROC_Step']
    ROC_Xlabel_Y_Buffer = param_dict['ROC_Xlabel_Y_Buffer']
    ROC_Xlabel_FirstX = param_dict['ROC_Xlabel_FirstX']
    ROC_Xlabel_Step = param_dict['ROC_Xlabel_Step']
    ROC_Label_Angle = ast.literal_eval(df['ROC_Label_Angle'].iloc[0])
    plot_dpi = 400
    SmoothFRN = False

    return (dfResv, dfSurchargeCurve, Ts, Reservoir, param_dict, dfTitleBlock, Label_X_Coord, Label_Angle, curve_dfs, 
            X_Lable_Angle, X_Min, X_Max, X_Step, Y_Min, Y_Max, Y_Step, Inflow_Min, Inflow_Max, Inflow_Step, 
            Inflow_Xlabel_Y_Buffer, Inflow_Xlabel_FirstX, Inflow_Xlabel_Step, Inflow_Label_Angle, ROC_Min, ROC_Max, 
            ROC_Step, ROC_Xlabel_Y_Buffer, ROC_Xlabel_FirstX, ROC_Xlabel_Step, ROC_Label_Angle, plot_dpi, SmoothFRN)

(dfResv, dfSurchargeCurve, Ts, Reservoir, param_dict, dfTitleBlock, Label_X_Coord, Label_Angle, curve_dfs, 
 X_Lable_Angle, X_Min, X_Max, X_Step, Y_Min, Y_Max, Y_Step, Inflow_Min, Inflow_Max, Inflow_Step, 
 Inflow_Xlabel_Y_Buffer, Inflow_Xlabel_FirstX, Inflow_Xlabel_Step, Inflow_Label_Angle, ROC_Min, ROC_Max, 
 ROC_Step, ROC_Xlabel_Y_Buffer, ROC_Xlabel_FirstX, ROC_Xlabel_Step, ROC_Label_Angle, plot_dpi, SmoothFRN) = process_config("../config/COT_CONFIG.csv")

# Put a copy of the CONFIG file in the Out folder as documentation
copy_CONFIG_File = os.path.splitext(CONFIG_File)[0] + '_'+ Reservoir+'.csv'
shutil.copy(CONFIG_File, f"../out/{Reservoir}_CONFIG.csv")
# Define where the Inflow spreadsheet will live. This sheet could be printed and used as a lookup table by an operator or regulator.
CSV_OUTPUT = "../out/" + Reservoir + "Inflow_ESRD.csv"

''' Calculate the ESRD curves - this is where the magic happens '''

def calculate_esrd_inflow_curves(dfResv, dfSurchargeCurve, Inflow_Max, Ts, c, ELEV_BUFFER, INFLOW_INCREMENT, RELEASE_INCREMENT, ELEV_INCREMENT, CSV_OUTPUT):
    inflows = np.arange(INFLOW_INCREMENT, Inflow_Max+1, INFLOW_INCREMENT)
    releases = np.arange(RELEASE_INCREMENT, dfResv["MaxRel"].max(), RELEASE_INCREMENT)  # x-axis values (can't actually start from 0)

    # Set up your interpolation tables 
    interpElevStor = interpolate.interp1d(dfResv["Elev"], dfResv["Stor"])
    interpStorElev = interpolate.interp1d(dfResv["Stor"], dfResv["Elev"], fill_value=(dfResv["Elev"].min(), dfResv["Elev"].max()), bounds_error=False)
    interpMaxRelElev = interpolate.interp1d(dfResv["MaxRel"], dfResv["Elev"])
    interpSurchargeRelElev = interpolate.interp1d(dfSurchargeCurve["Release"], dfSurchargeCurve["Env_Elev"])

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
    dfTable = dfTable.round(0)
    dfTable.to_csv(CSV_OUTPUT)

    return dfInOutElev

dfInOutElev = calculate_esrd_inflow_curves(dfResv, dfSurchargeCurve, Inflow_Max, Ts, c, ELEV_BUFFER, INFLOW_INCREMENT, RELEASE_INCREMENT, ELEV_INCREMENT, CSV_OUTPUT)

#Create ESRD Tables

def create_roc_esrd_curves(dfInOutElev, dfResv, dfSurchargeCurve, Inflow_Min, Inflow_Max, Inflow_Step, X_Max, ROC_Max, ROC_Step, Reservoir):
    pivotOutflowInflowElev = dfInOutElev.reset_index()
    pivotOutflowInflowElev.rename(columns={'index': 'outflow'}, inplace=True)
    # Melt the DataFrame to long format
    OutflowInflowElev = pd.melt(pivotOutflowInflowElev, id_vars=['outflow'], var_name='inflow', value_name='elev')
    OutflowInflowElev['inflow'] = pd.to_numeric(OutflowInflowElev['inflow'])
    # renaming for further calcs for error checking later
    dfElevROC = OutflowInflowElev
    # Concert the change in flow (cfs) to acre feet, assuming 1 hour duration flow
    dfElevROC['Dstor'] = (dfElevROC['inflow'] - dfElevROC['outflow']) * 0.0826
    # # Why are ther inflow outflow pairs with outflows higher than inflows? Get rid of them....
    # dfElevROC['Dstor'] = dfElevROC['Dstor'].clip(lower=0)

    # Create an interpolation function for the storage-elevation curve
    # The interp1d function will create an interpolation object

    # interp_func = interp1d(dfResv['Stor'], dfResv['Elev'], bounds_error=False, fill_value='extrapolate') # Not sure which fill_value is appropriate
    interp_func = interp1d(dfResv['Stor'], dfResv['Elev'], bounds_error=False, fill_value=0)

    # Find the storage at the current elevation, delete the storage and find out where you would have been. This give the stor before the pool rise.
    dfElevROC['new_stor'] = np.interp(dfElevROC['elev'], dfResv['Elev'], dfResv['Stor']) - dfElevROC['Dstor']
    # Get the elev before the pool rise
    dfElevROC['new_elev'] = interp_func(dfElevROC['new_stor'])
    # Calculate the Elevation rate of change by subtracting the elevation before the pool rise from the current elevation
    dfElevROC['Elev_ROC'] = dfElevROC['elev'] - dfElevROC['new_elev']
    # Why are there negative rate of pool elevation changes? Get rid of them....
    dfElevROC = dfElevROC[dfElevROC['Elev_ROC'] > 0]

    # Define your new outflow and Elev_ROC increments
    outflow_increments = np.arange(dfElevROC['outflow'].min(), dfElevROC['outflow'].max() + 1000, 1000)
    Elev_ROC_increments = np.arange(0, ROC_Max, ROC_Step)  # Elev_ROC from 0 to 4 in increments of 0.05
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
        elevation_range = np.arange(np.floor(min_elevation), np.ceil(max_elevation) + 1, 1)

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

    transformed_df = transform_df(dfPlotROC)
    transformed_df[transformed_df < 0] = 0
    transformed_df.index = transformed_df.index.round(1)
    transformed_df = transformed_df.round(0)
    transformed_df = transformed_df.transpose()
    transformed_df.to_csv("../out/" + Reservoir + "ROC_ESRD.csv")

    dfInflowPlot = dfInOutElev
    # dfInflowPlot.index = dfInflowPlot.index.map(int)
    # dfInflowPlot.columns = dfInflowPlot.columns.map(int)

    columns_to_select = np.arange(Inflow_Min, Inflow_Max + 1, Inflow_Step)
    # rows_to_select = [5000]
    # rows_to_select = np.append(rows_to_select,np.arange(10000, X_Max + 1,10000 ))
    rows_to_select = np.arange(1000, X_Max + 1, 1000)
    # Use .iloc to select based on integer location indexing
    dfInflowPlot = dfInflowPlot.loc[rows_to_select, columns_to_select]

    # Define the interpolation function for Max Release Elevation
    interpMaxRelElev = interpolate.interp1d(dfResv["MaxRel"], dfResv["Elev"], fill_value="extrapolate")

    # The Max Release needs to be interpolated to line up with the inflows and releases
    Max_Rel = pd.DataFrame()
    Max_Rel["Elev"] = interpMaxRelElev(dfInflowPlot.index.values)
    Max_Rel.index = dfInflowPlot.index

    return dfInflowPlot, Max_Rel, dfPlotROC

'''
FIRST PLOT
'''
#%%
def plot_inflow_esrd(dfInflowPlot, Max_Rel, dfSurchargeCurve, curve_dfs, Label_X_Coord, Label_Angle, Y_Min, Y_Max, Y_Step, X_Min, X_Max, Inflow_Xlabel_FirstX, Inflow_Xlabel_Step, Inflow_Xlabel_Y_Buffer, Inflow_Label_Angle, X_Lable_Angle, X_Step, Reservoir, plot_dpi):
    plt.close('all')

    SpillwayOnlyFontsize = 14
    plt.rcParams["font.size"] = 14  # Adjust as needed
    plt.rcParams["axes.labelsize"] = 16
    plt.rcParams["xtick.labelsize"] = 14
    plt.rcParams["ytick.labelsize"] = 14
    plt.rcParams["legend.fontsize"] = 14

    # Create the figure and axes
    fig, ax = plt.subplots(figsize=(7, 7))  # Changed 'axes' to 'ax' to avoid confusion

    # Plot the inflow data on the existing axes
    dfInflowPlot.plot(ax=ax, legend=None, color='black')

    # Set the font family for the plot
    plt.rcParams["font.family"] = "Verdana"

    # Plot other datasets on the same axes
    ax.plot(Max_Rel.index, Max_Rel['Elev'], label="Max Discharge", color='black')
    ax.plot(dfSurchargeCurve["Release"], dfSurchargeCurve["Env_Elev"], 
            label="Induced Surcharge Envelope Curve", color='black')

    # Conditionally plot additional curves if available
    if curve_dfs != 'None':
        for curve_name, curve_df in curve_dfs.items():
            ax.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, 
                    color='gray', linestyle='--')

            # Add labels to the curves
            x_label = Label_X_Coord
            idx = np.abs(curve_df['Release'] - x_label).idxmin()
            x = curve_df['Release'][idx]
            y = curve_df['Elev'][idx]
            y_offset = -1  # Adjust offset as needed

            ax.text(x, y + y_offset, curve_name, rotation=Label_Angle, 
                    ha='center', va='bottom', fontsize=SpillwayOnlyFontsize, color='gray')

    # Set the y-axis ticks
    ax.set_yticks(np.arange(Y_Min, Y_Max + Y_Step + 1, Y_Step))

    # Set axis labels
    ax.set_ylabel("Pool Elevation (feet, project datum)")
    ax.set_xlabel("Reservoir Release in 1,000 cfs")

    # Set axis limits
    ax.set_xlim(X_Min, X_Max)
    ax.set_ylim(Y_Min, Y_Max)

    # Add inflow labels at the top boundary of the plot
    top_y = dfSurchargeCurve['Env_Elev'].iloc[0] - 0.2
    ax.text(X_Max / 3, top_y + 0.5, 'Reservoir Inflow in 1,000 cfs', ha='left', va='bottom')

    # Generate x-values dynamically based on the number of columns
    x_values = [Inflow_Xlabel_FirstX + i * Inflow_Xlabel_Step for i in range(len(dfInflowPlot.columns))]

    # Add labels for each column
    num_labels = len(dfInflowPlot.columns)
    if len(Inflow_Label_Angle) < num_labels:
        # Extend the list of angles by repeating the last angle as needed
        Inflow_Label_Angle.extend([Inflow_Label_Angle[-1]] * (num_labels - len(Inflow_Label_Angle)))
    elif len(Inflow_Label_Angle) > num_labels:
        # Trim the list of angles to match the number of labels
        Inflow_Label_Angle = Inflow_Label_Angle[:num_labels]

    # Loop through the columns and plot with appropriate angles
    for (column, desired_x), angle in zip(zip(dfInflowPlot.columns, x_values), Inflow_Label_Angle):
        if desired_x <= X_Max:
            y_value = np.interp(desired_x, dfInflowPlot.index, dfInflowPlot[column]) + Inflow_Xlabel_Y_Buffer
            ax.text(desired_x, y_value, f'{int(column / 1000)}', ha='center', va='bottom', 
                    color='black', rotation=angle)

    # Customize the grid and ticks
    ax.grid(alpha=0.5)
    ax.set_xticks(np.arange(0, X_Max + 1, X_Step))

    # Format x-axis tick labels
    xlabels = ['{:,.0f}'.format(x) for x in ax.get_xticks() / 1000]
    ax.set_xticklabels(xlabels, rotation=X_Lable_Angle)

    plt.subplots_adjust(left=0.1, right=0.98, top=0.98, bottom=0.1)
    plt.savefig("../out/"+Reservoir+"_Inflow_ESRD.png", dpi=plot_dpi, bbox_inches='tight', pad_inches=0)
    plt.show()


''' ROC PLOT '''
## plot for ROC ESRD curves

#%%


def plot_roc_esrd(dfPlotROC, dfSurchargeCurve, dfResv, curve_dfs, 
                  Label_X_Coord, Label_Angle, Y_Min, Y_Max, Y_Step, 
                  X_Min, X_Max, ROC_Xlabel_FirstX, ROC_Xlabel_Step, 
                  ROC_Xlabel_Y_Buffer, ROC_Label_Angle, X_Lable_Angle, 
                  X_Step, Reservoir, plot_dpi, SmoothFRN=False):

    decimal_places = len(str(ROC_Xlabel_Step).split('.')[1]) if '.' in str(ROC_Xlabel_Step) else 0

    SpillwayOnlyFontsize = 14
    plt.rcParams["font.size"] = 14  # Adjust as needed
    plt.rcParams["axes.labelsize"] = 16
    plt.rcParams["xtick.labelsize"] = 14
    plt.rcParams["ytick.labelsize"] = 14
    plt.rcParams["legend.fontsize"] = 14

    dfPlotROC.columns = [f'{float(col):.{decimal_places}f}' for col in dfPlotROC.columns]

    # Process the data to handle decreasing values
    for column in dfPlotROC.columns:
        rate_of_change = dfPlotROC[column].diff()
        decreasing = rate_of_change < 0
        first_decreasing_index = decreasing.idxmax() if decreasing.any() else None
        if first_decreasing_index is not None:
            dfPlotROC.loc[first_decreasing_index:, column] = np.nan

    # Smooth FRN ROC if required
    if SmoothFRN:
        MaxRel = dfResv[dfResv.index.isin(dfPlotROC.index)]
        dfPlotROC['MaxRel'] = MaxRel['Elev'].reindex(dfPlotROC.index, method='ffill')
        MaxRel = dfPlotROC.pop('MaxRel')

        for col in dfPlotROC.columns:
            dfPlotROC[col] = dfPlotROC[col].combine(MaxRel, lambda val, ref: np.nan if abs(val - ref) <= 0.05 else val)
            mask = ~dfPlotROC[col].isna()
            coefficients = np.polyfit(dfPlotROC.index[mask], dfPlotROC[col][mask], 2)
            poly_values = np.polyval(coefficients, dfPlotROC.index[mask])
            dfPlotROC.loc[mask, col] = poly_values

    # Create the figure and axes
    plt.close('all')
    fig, ax = plt.subplots(figsize=(7, 7))

    # Plot data on the existing axes
    dfPlotROC.plot(ax=ax, legend=None, color='black')
    plt.rcParams["font.family"] = "Verdana"

    # Plot additional curves
    ax.plot(dfSurchargeCurve["Release"], dfSurchargeCurve["Env_Elev"], label="Induced Surcharge Envelope Curve", color='black')
    ax.plot(dfResv["MaxRel"], dfResv["Elev"], label="Spillway Max Discharge", color='black')

    if curve_dfs != 'None':
        for curve_name, curve_df in curve_dfs.items():
            ax.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='gray', linestyle='--')
            idx = np.abs(curve_df['Release'] - Label_X_Coord).idxmin()
            ax.text(curve_df['Release'][idx], curve_df['Elev'][idx] - 1, curve_name, 
                    rotation=Label_Angle, ha='center', va='bottom', fontsize=SpillwayOnlyFontsize, color='gray')

    # Set axis limits and labels
    ax.set_xlim(X_Min, X_Max)
    ax.set_ylim(Y_Min, Y_Max)
    ax.set_yticks(np.arange(Y_Min, Y_Max + Y_Step + 1, Y_Step))
    ax.set_ylabel("Pool Elevation (feet, project datum)")
    ax.set_xlabel("Reservoir Release in 1,000 cfs")

    # Add text labels
    top_y = dfSurchargeCurve['Env_Elev'].iloc[0] - 0.2
    ax.text(X_Max / 4, top_y + 0.5, 'Reservoir Elevation Change in ft/hr', ha='left', va='bottom')

    x_values = [ROC_Xlabel_FirstX + i * ROC_Xlabel_Step for i in range(len(dfPlotROC.columns))]
    num_labels = len(dfPlotROC.columns)
    if len(ROC_Label_Angle) < num_labels:
        # Extend the list of angles by repeating the last angle as needed
        ROC_Label_Angle.extend([ROC_Label_Angle[-1]] * (num_labels - len(ROC_Label_Angle)))
    elif len(ROC_Label_Angle) > num_labels:
        # Trim the list of angles to match the number of labels
        ROC_Label_Angle = ROC_Label_Angle[:num_labels]

    # Loop through the columns and plot with appropriate angles
    for (column, desired_x), angle in zip(zip(dfPlotROC.columns, x_values), ROC_Label_Angle):
        if desired_x <= X_Max:
            y_value = np.interp(desired_x, dfPlotROC.index, dfPlotROC[column]) + ROC_Xlabel_Y_Buffer
            label_text = f'{float(column):.{decimal_places}f}' if column.replace('.', '', 1).isdigit() else column
            ax.text(desired_x, y_value, label_text, ha='center', va='bottom', rotation=angle)

    # Customize ticks and grid
    ax.set_xticks(np.arange(0, X_Max + 1, X_Step))
    xlabels = ['{:,.0f}'.format(x / 1000) for x in ax.get_xticks()]
    ax.set_xticklabels(xlabels, rotation=X_Lable_Angle)
    ax.grid(alpha=0.5)

    # Adjust layout and save the plot
    plt.subplots_adjust(left=0.1, right=0.98, top=0.98, bottom=0.1)
    plt.savefig(f"../out/{Reservoir}_ElevROC_ESRD.png", dpi=plot_dpi, bbox_inches='tight')
    plt.show()

dfInOutElev = calculate_esrd_inflow_curves(dfResv, dfSurchargeCurve, Inflow_Max,
                                           Ts, c, ELEV_BUFFER, INFLOW_INCREMENT,
                                           RELEASE_INCREMENT, ELEV_INCREMENT, CSV_OUTPUT)

dfInflowPlot, Max_Rel, dfPlotROC = create_roc_esrd_curves(dfInOutElev, dfResv, dfSurchargeCurve,
                                                          Inflow_Min, Inflow_Max, Inflow_Step,
                                                          X_Max, ROC_Max, ROC_Step, Reservoir)

plot_inflow_esrd(dfInflowPlot, Max_Rel, dfSurchargeCurve,
                 curve_dfs, Label_X_Coord, Label_Angle,
                 Y_Min, Y_Max, Y_Step, X_Min, X_Max,
                 Inflow_Xlabel_FirstX, Inflow_Xlabel_Step,
                 Inflow_Xlabel_Y_Buffer, Inflow_Label_Angle, X_Lable_Angle, X_Step, Reservoir, plot_dpi)

plot_roc_esrd(dfPlotROC, dfSurchargeCurve, dfResv, curve_dfs, 
              Label_X_Coord, Label_Angle, Y_Min, Y_Max, Y_Step, 
              X_Min, X_Max, ROC_Xlabel_FirstX, ROC_Xlabel_Step, 
              ROC_Xlabel_Y_Buffer, ROC_Label_Angle, X_Lable_Angle, 
              X_Step, Reservoir, plot_dpi, SmoothFRN)



