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

###############################################################################


## Read in a Configuration CSV and create all dataframes and parameters

CONFIG_File = "../config/COT_CONFIG.csv"


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





# lines = dfTitleBlock['Text']


# # Corresponding font sizes for each line in the order they appear
# font_sizes = [35, 35, 30, 30, 30, 30, 30, 30, 30, 30]
# # Only lines identified will be bolded
# bold_lines = [0,1]
# # Spacing factor (e.g., 0.5 for tighter spacing)
# line_spacing = 0.35
# # Create a figure large enough to accommodate the text
# fig, ax = plt.subplots()
# fig.set_size_inches(5, 6)
# canvas = FigureCanvas(fig)

# # Calculate total text block height and the height of a single line space
# total_height = 0
# single_line_space_height = 0
# for index, (line, font_size) in enumerate(zip(lines, font_sizes)):
#     text = ax.text(0, 0, line, fontsize=font_size, ha='center', va='top')
#     canvas.draw()
#     window_extent = text.get_window_extent(renderer=canvas.get_renderer())
#     text_height = window_extent.height / fig.dpi
#     total_height += text_height * line_spacing
#     text.remove()
#     if index == 0:  # Grab the height of the first line to determine single line space
#         single_line_space_height = text_height

# # Adjust border based on total height plus two times the single line space (top and bottom)
# border_height = total_height + (1 * single_line_space_height * line_spacing)
# data_min_y = 0.5 - (border_height / 2)
# data_max_y = 0.5 + (border_height / 2)

# # Set the initial y position to just below the top border's y-coordinate
# current_height = data_max_y - single_line_space_height * line_spacing

# # Add the texts to the axes at the center, adjust spacing, and set bold selectively
# for index, line in enumerate(lines):
#     font_size = font_sizes[index]
#     fontweight = 'bold' if index in bold_lines else 'normal'
#     text = ax.text(0.5, current_height, line, fontsize=font_size, ha='center', va='top', fontweight=fontweight)
#     canvas.draw()
#     window_extent = text.get_window_extent(renderer=canvas.get_renderer())
#     text_height = window_extent.height / fig.dpi
#     current_height -= text_height * line_spacing


# # Adjust the axis limits to contain the rectangle
# ax.set_xlim(0, 1)
# ax.set_ylim(0, 1)

# # Hide the axes
# ax.axis('off')

# # fig_width, fig_height = fig.get_size_inches()

# # Calculate the desired padding in inches
# padding_in_inches = 0.1  # Adjust this value as needed, it should be relatively small


# # Save the figure with the new bounding box as the limit. The dpi can be adjusted to make the text box bigger or smaller with all the text scaling
# plt.savefig(f"../out/{Reservoir}_Title_Block.png", dpi=450, bbox_inches='tight', pad_inches=.1)

# # Display the plot
# plt.show()



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



##Turn it into a table ResSim can use (x-axis is elevation)
# elevs = np.arange(dfResv["Elev"].min(), dfResv["Elev"].max(), ELEV_INCREMENT)  #there will be one curve on the ESRD for each inflow.
# dfTable = pd.DataFrame(index=elevs)
# for i, inflow in enumerate(inflows):
#     interpObj = interpolate.interp1d(dfPlot[inflow], releases, fill_value=0, bounds_error = False)
#     dfTable[inflow] = interpObj(elevs)
#     dfTable[inflow] = dfTable[inflow].apply(lambda x: min(x, inflow))
# dfTable.to_csv(CSV_OUTPUT)

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
dfElevROC = OutflowInflowElev
# Concert the change in flow (cfs) to acre feet, assuming 1 hour duration flow
dfElevROC['Dstor'] = (dfElevROC['inflow'] - dfElevROC['outflow'])*0.0826
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

# dfElevROCtrim = dfElevROC[['outflow','elev','Elev_ROC']]

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


dfInflowPlot = dfInOutElev
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
FIRST PLOT
'''

plt.close('all')
fig, axes = plt.subplots(figsize=(6.5, 9))


axes = dfInflowPlot.plot(legend=None, color = 'black')
plt.rcParams["font.family"] = "Verdana"
axes.plot(Max_Rel.index,Max_Rel['Elev'], label="Max Discharge", color = 'black')
axes.plot(dfSurchargeCurve["Release"], dfSurchargeCurve["Env_Elev"], label = "Induced Surcharge Envelope Curve", color = 'black')
# axes.plot(dfResv["MaxRel"], dfResv["Elev"], label="Spillway Max Discharge", color = 'black')


# for curve_name, curve_df in curve_dfs.items():
#     axes.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='gray', linestyle = '--')
''''''''

if curve_dfs == 'None':
    pass
else:
    for curve_name, curve_df in curve_dfs.items():
            # Plotting the curve
            axes.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='Gray', linestyle='--')

            # Define the x-coordinate for the label
            x_label = Label_X_Coord

            # Find the nearest point on the curve
            idx = np.abs(curve_df['Release'] - x_label).idxmin()
            x = curve_df['Release'][idx]
            y = curve_df['Elev'][idx]

            # Adjust the vertical offset
            y_offset = -1  # Increased offset, adjust as needed for your plot

            # Use the fixed angle for text rotation
            # This replaces the previously calculated angle based on slope
            angle = Label_Angle

            # Plotting the text with fixed rotation and alignment
            axes.text(x, y + y_offset, curve_name, rotation=angle, ha='center', va='bottom', fontsize=10, color='Gray')




    

''''''
axes.set_yticks(np.arange(Y_Min,Y_Max + Y_Step+1,Y_Step))

axes.set_ylabel("Pool Elevation (feet, project datum)")
# axes.set_xlabel("Reservoir Release in 1,000 cfs")
xlabel = axes.set_xlabel("Reservoir Release in 1,000 cfs")

### Could add pertinant elevations
#Put a horizontal line at normal max pool
# axes.axhline(1574, linestyle="dashed", color = 'black')
# #Put a horizontal line at the critical elevation
# axes.axhline(1570, linestyle="dashed", color = 'black')
# #Put a horizontal line at the irrm summer pool
# axes.axhline(1558.5, linestyle="dashed", color = 'black')
# #Put a horizontal line at top of dam
# axes.axhline(1579, linestyle="dashed", color = 'black')
#axes.grid()  

# Set axis limits
axes.set_xlim(X_Min,X_Max)
axes.set_ylim(Y_Min,Y_Max)










# Add inflow labels at the top boundary of the plot
top_y = dfSurchargeCurve['Env_Elev'].iloc[0] -.2 # Top boundary of the plot
axes.text(X_Max / 3, top_y + .5, 'Reservoir Inflow in 1,000 cfs', ha='left', va='bottom') # add inflow psuedo axis label

# Define x_values dynamically based on the number of columns
x_values = [Inflow_Xlabel_FirstX + i * Inflow_Xlabel_Step for i in range(len(dfInflowPlot.columns))]

# Iterate over each column and the corresponding x_values
for column, desired_x in zip(dfInflowPlot.columns, x_values):
    # Check if desired_x is within the x-axis limits
    if desired_x <= X_Max:
        # Get the closest y value at desired_x
        y_value = np.interp(desired_x, dfInflowPlot.index, dfInflowPlot[column]) + Inflow_Xlabel_Y_Buffer
        # Add label with the desired formatting
        axes.text(desired_x, y_value, f'{int(column / 1000)}', ha='center', va='bottom', color = 'black',rotation=Inflow_Label_Angle
                  # fontsize = 7.5
                  )

axes.grid(alpha=0.5)
#axes.legend()
axes.set_xticks(np.arange(0,X_Max + 1, X_Step), )
xlabels = ['{:,.0f}'.format (x) for x in axes.get_xticks()/1000] 
axes.set_xticklabels(xlabels, rotation=X_Lable_Angle)


# # Load your PNG file for Title BLock
# img = Image.open("../out/" +Reservoir+"_Title_Block.png")
# # Guess I need to do this before adding Title Block so sizing is right
# plot_dpi = 400
# fig.set_dpi(plot_dpi)
# # Convert the image to a numpy array
# image_array = np.array(img)
# # Get the extent of the original plot
# x_min, x_max = axes.get_xlim()
# y_min, y_max = axes.get_ylim()
# # Calculate where you want to place the image (in this case, lower right corner)
# # The extents are (left, right, bottom, top) in data coordinates
# image_extent = [x_max - (img.size[0] / fig.dpi) * (x_max - x_min) / fig.get_size_inches()[0], 
#                 x_max, 
#                 y_min, 
#                 y_min + (img.size[1] / fig.dpi) * (y_max - y_min) / fig.get_size_inches()[1]]
# # Create a slightly larger extent for the black border
# border_width = 2  # the border width in pixels
# border_extent = [image_extent[0] - border_width / fig.dpi / fig.get_size_inches()[0] * (x_max - x_min),
#                  image_extent[1] + border_width / fig.dpi / fig.get_size_inches()[0] * (x_max - x_min),
#                  image_extent[2] - border_width / fig.dpi / fig.get_size_inches()[1] * (y_max - y_min),
#                  image_extent[3] + border_width / fig.dpi / fig.get_size_inches()[1] * (y_max - y_min)]
# # Create a rectangle patch with the border extent and add it to the axes
# border = Rectangle((border_extent[0], border_extent[2]), 
#                    border_extent[1] - border_extent[0], 
#                    border_extent[3] - border_extent[2],
#                    linewidth=border_width, 
#                    edgecolor='black', 
#                    facecolor='none',
#                    zorder=9)
# axes.add_patch(border)
# # Overlay the image onto the plot using Axes.imshow
# # Set the extent to the boundaries where you want the image to be placed
# # Adjust the aspect of the image to 'auto' so that it stretches to fill the extent
# axes.imshow(image_array, aspect='auto', extent=image_extent, zorder=10)

# #Set Xlim again after adding title block
# axes.set_xlim(X_Min,X_Max)
plot_dpi=400


plt.subplots_adjust(left=0.13, right=0.75, top=0.975, bottom=0.1)
# plt.savefig("../out/"+Reservoir+"_Inflow_ESRD.png", dpi= plot_dpi, bbox_inches='tight', pad_inches=0)
plt.savefig("../out/"+Reservoir+"_Inflow_ESRD.png", dpi= plot_dpi,bbox_inches='tight')
plt.show()
'''
new plot code
'''



''' ROC PLOT '''
## plot for ROC ESRD curves
# Clean up ft/hour numbers because some had many, many trailing zeros

decimal_places = len(str(ROC_Step).split('.')[1]) if '.' in str(ROC_Step) else 0

dfPlotROC.columns = [f'{float(col):.{decimal_places}f}' for col in dfPlotROC.columns]



# lines were going across the envelop, but this is also where they were reducing (which is bad) so trim when this happens
for column in dfPlotROC.columns:
    # Calculate the difference between consecutive values to find the rate of change
    rate_of_change = dfPlotROC[column].diff()
    # Identify where the rate of change is negative
    decreasing = rate_of_change < 0
    # Once the rate of change is negative, set all subsequent values to NaN
    first_decreasing_index = decreasing.idxmax() if decreasing.any() else None
    # If a decreasing section is found, set all values after that to NaN
    if first_decreasing_index is not None:
        dfPlotROC.loc[first_decreasing_index:, column] = np.nan

''' Section below to smooth out FRN ROC '''

# # Final_Column = dfPlotROC.iloc[:, -1]
# # dfPlotROC.drop(dfPlotROC.columns[-1], axis=1, inplace=True)
# MaxRel = dfResv
# MaxRel = Max_Rel[Max_Rel.index.isin(dfPlotROC.index)]
# dfPlotROC['MaxRel'] = MaxRel['Elev']
# dfPlotROC['MaxRel'] = dfPlotROC['MaxRel'].fillna(method='ffill')
# MaxRel = dfPlotROC['MaxRel'].copy()
# dfPlotROC=dfPlotROC.drop(columns=['MaxRel'])
# MaxRel.index=dfPlotROC.index

# # Function to check if the difference is within the threshold
# def check_and_replace(value, reference_value):
#     return np.nan if abs(value - reference_value) <= .05 else value

# # Apply the function to each element in the DataFrame
# for col in dfPlotROC.columns:
#     dfPlotROC[col] = dfPlotROC[col].combine(MaxRel, check_and_replace)

# # Assume dfPlotROC is your dataframe with 'outflow' as the index
# # Create a copy of the dataframe to avoid modifying the original one

# # Loop through each column in the dataframe
# for col in dfPlotROC.columns:
#     # Get the elevation values (assuming 'outflow' is your elevation index)
#     elevation = dfPlotROC.index.values
    
#     # Mask to identify the non-NaN values
#     mask = ~dfPlotROC[col].isna()
    
#     # Fit a 2nd-degree polynomial to the non-NaN data
#     coefficients = np.polyfit(elevation[mask], dfPlotROC[col][mask], 2)
    
#     # Generate polynomial values using the fitted coefficients
#     poly_values = np.polyval(coefficients, elevation[mask])
    
#     # Replace the original column values with the polynomial-fitted values, but only for non-NaN entries
#     dfPlotROC[col].loc[mask] = poly_values


# # Now dfPlotROC_poly contains the polynomial-fitted values, with NaNs preserved

''' End Fix for FRN '''
# actually plot the ROC ESRD curves

plt.close('all')

# Assume dfPlotROC is your dataframe with 'outflow' as the index
# Create a copy of the dataframe to avoid modifying the original one
# dfPlotROC_poly = dfPlotROC.copy()

# Loop through each column in the dataframe


# Now dfPlotROC_poly contains the polynomial-fitted values


# fig, axes = plt.subplots(figsize=(30, 20))
fig, axes = plt.subplots(figsize=(6.5, 9))
# fig, axes = plt.subplots(figsize=(30, 20), dpi = 400)

axes = dfPlotROC.plot(legend=None, color = 'black')
plt.rcParams["font.family"] = "Verdana"
axes.plot(dfSurchargeCurve["Release"], dfSurchargeCurve["Env_Elev"], label = "Induced Surcharge Envelope Curve", color = 'black')
axes.plot(dfResv["MaxRel"], dfResv["Elev"], label="Spillway Max Discharge", color = 'black')

# for curve_name, curve_df in curve_dfs.items():
#     axes.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='gray', linestyle = '--')




if curve_dfs == 'None':
    pass
else:
    for curve_name, curve_df in curve_dfs.items():
            # Plotting the curve
            axes.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='Gray', linestyle='--')

            # Define the x-coordinate for the label
            x_label = Label_X_Coord

            # Find the nearest point on the curve
            idx = np.abs(curve_df['Release'] - x_label).idxmin()
            x = curve_df['Release'][idx]
            y = curve_df['Elev'][idx]

            # Adjust the vertical offset
            y_offset = -1  # Increased offset, adjust as needed for your plot

            # Use the fixed angle for text rotation
            # This replaces the previously calculated angle based on slope
            angle = Label_Angle

            # Plotting the text with fixed rotation and alignment
            axes.text(x, y + y_offset, curve_name, rotation=angle, ha='center', va='bottom', fontsize=10, color='Gray')
''''''
# for curve_name, curve_df in curve_dfs.items():
#     # Plotting the curve
#     axes.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='Gray', linestyle='--')

#     # Define the x-coordinate for the label
#     x_label = Label_X_Coord

#     # Find the nearest point on the curve
#     idx = np.abs(curve_df['Release'] - x_label).idxmin()
#     x = curve_df['Release'][idx]
#     y = curve_df['Elev'][idx]

#     # Adjust the vertical offset
#     y_offset = -1  # Increased offset, adjust as needed for your plot

#     # Use the fixed angle for text rotation
#     # This replaces the previously calculated angle based on slope
#     angle= Label_Angle

#     # Plotting the text with fixed rotation and alignment
#     axes.text(x, y + y_offset, curve_name, rotation=angle, ha='center', va='bottom', fontsize=10, color='Gray')
''''''





axes.set_yticks(np.arange(Y_Min,Y_Max + Y_Step+1,Y_Step))

axes.set_ylabel("Pool Elevation (feet, project datum)")
axes.set_xlabel("Reservoir Release in 1,000 cfs")

# Set axis limits
axes.set_xlim(X_Min,X_Max)
axes.set_ylim(Y_Min,Y_Max)
# Add psudo axis label
top_y = dfSurchargeCurve['Env_Elev'].iloc[0] -.2 # Top boundary of the plot
axes.text(X_Max / 4, top_y + .5, 'Reservoir Elevation Change in ft/hr', ha='left', va='bottom') # add inflow psuedo axis label

# Determine the number of decimal places in ROC_Step


# Define x_values dynamically based on the number of columns
x_values = [ROC_Xlabel_FirstX + i * ROC_Xlabel_Step for i in range(len(dfPlotROC.columns))]

# Iterate over each column and the corresponding x_values
for column, desired_x in zip(dfPlotROC.columns, x_values):
    # Get the closest y value at desired_x
    y_value = np.interp(desired_x, dfPlotROC.index, dfPlotROC[column]) + ROC_Xlabel_Y_Buffer
    
    # Attempt to convert column to float and format label
    try:
        column_value = float(column)
        label_text = f'{column_value:.{decimal_places}f}'
    except ValueError:
        # If conversion fails, use the column value as is
        label_text = column

    # Add label with the desired formatting
    axes.text(desired_x, y_value, label_text, ha='center', va='bottom',rotation = ROC_Label_Angle)

## For adding labels that aren't active
# axes.axhline(1541, linestyle="dashed", color = 'black')
#axes.text(axes.get_xlim()[0],2435, "Spillway Crest (2435')", fontsize="small")
# axes.grid(alpha=0.5)
#axes.legend()

axes.set_xticks(np.arange(0,X_Max + 1, X_Step))
xlabels = ['{:,.0f}'.format (x) for x in axes.get_xticks()/1000] 
axes.set_xticklabels(xlabels, rotation=X_Lable_Angle)
### Loading the text block same as for previous plot.
# Load your PNG file

# img = Image.open("../out/" +Reservoir+"_Title_Block.png")
# # Convert the image to a numpy array
# image_array = np.array(img)
# # Get the extent of the original plot
# x_min, x_max = axes.get_xlim()
# y_min, y_max = axes.get_ylim()
# # Calculate where you want to place the image (in this case, lower right corner)
# # The extents are (left, right, bottom, top) in data coordinates
# image_extent = [x_max - (img.size[0] / fig.dpi) * (x_max - x_min) / fig.get_size_inches()[0], 
#                 x_max, 
#                 y_min, 
#                 y_min + (img.size[1] / fig.dpi) * (y_max - y_min) / fig.get_size_inches()[1]]
# # Create a slightly larger extent for the black border
# border_width = 2  # the border width in pixels
# border_extent = [image_extent[0] - border_width / fig.dpi / fig.get_size_inches()[0] * (x_max - x_min),
#                  image_extent[1] + border_width / fig.dpi / fig.get_size_inches()[0] * (x_max - x_min),
#                  image_extent[2] - border_width / fig.dpi / fig.get_size_inches()[1] * (y_max - y_min),
#                  image_extent[3] + border_width / fig.dpi / fig.get_size_inches()[1] * (y_max - y_min)]
# # Create a rectangle patch with the border extent and add it to the axes
# border = Rectangle((border_extent[0], border_extent[2]), 
#                    border_extent[1] - border_extent[0], 
#                    border_extent[3] - border_extent[2],
#                    linewidth=border_width, 
#                    edgecolor='black', 
#                    facecolor='none',
#                    zorder=9)
# axes.add_patch(border)
# # Overlay the image onto the plot using Axes.imshow
# # Set the extent to the boundaries where you want the image to be placed
# # Adjust the aspect of the image to 'auto' so that it stretches to fill the extent
# axes.imshow(image_array, aspect='auto', extent=image_extent, zorder=10)

# Add gridlines
axes.grid(alpha=0.5)

# Resest x limits after title block
axes.set_xlim(X_Min,X_Max)

plot_dpi=400


plt.subplots_adjust(left=0.13, right=0.75, top=0.975, bottom=0.1)

# Save the figure with the image overlay
plt.savefig(f"../out/{Reservoir}_ElevROC_ESRD.png", dpi=400, bbox_inches='tight')



# After calculating 'Elev_ROC'
print("Sample Elev_ROC values:", dfElevROC['Elev_ROC'].head())
print("Data type of Elev_ROC:", dfElevROC['Elev_ROC'].dtype)

# After defining Elev_ROC_increments
print("Elev_ROC increments:", Elev_ROC_increments)

# After interpolation
print("Sample interpolated values:", elev_interpolated[:5])

# After creating dfPlotROC
print("dfPlotROC sample data:")
print(dfPlotROC.head())

# Check the unique values in the 'Elev_ROC' column of dfPlotROC to see if they align with the expected increments
unique_roc_values = dfPlotROC.columns.unique()
print("Unique ROC values in dfPlotROC:", unique_roc_values)


