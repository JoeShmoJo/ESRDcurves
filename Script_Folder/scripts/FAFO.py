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
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import ast

# Read in the first CONFIG CSV
CONFIG_File1 = "../config/COT_CONFIG.csv"
# Read in the second CONFIG CSV
CONFIG_File2 = "../config/COT_CONFIG_2.csv"

# Function to process a given CONFIG file
def process_config(CONFIG_File):
    df = pd.read_csv(CONFIG_File, skiprows=5)
    dfResv = df[['Elev', 'Stor', 'MaxRel']].dropna()
    dfSurchargeCurve = df[['Env_Elev', 'Release']].dropna()
    Ts = float(df[['TS']].values[0] / 24)
    Reservoir = str(df['Reservoir'].values[0])
    Paramsdf = df[['Param', 'Values']].dropna()
    param_dict = Paramsdf.set_index('Param').to_dict()['Values']
    dfTitleBlock = df[['Line', 'Text']].dropna()
    Label_X_Coord = float(df[['Label_X_Coord']].values[0])
    Label_Angle = float(df[['Label_Angle']].values[0])

    curve_dfs = {}
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
                if pd.notna(curve_name):
                    curve_dfs[curve_name] = df[[x_col, y_col]].copy()
                    curve_dfs[curve_name].columns = ['Elev', 'Release']

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

# Load both configurations
config1 = process_config(CONFIG_File1)
config2 = process_config(CONFIG_File2)

# Define a function to calculate esrd inflow curves (code simplified for demonstration)
def calculate_esrd_inflow_curves(dfResv, dfSurchargeCurve, Inflow_Max, Ts, c, ELEV_BUFFER, INFLOW_INCREMENT, RELEASE_INCREMENT, ELEV_INCREMENT, CSV_OUTPUT):
    inflows = np.arange(INFLOW_INCREMENT, Inflow_Max + 1, INFLOW_INCREMENT)
    releases = np.arange(RELEASE_INCREMENT, dfResv["MaxRel"].max(), RELEASE_INCREMENT)
    dfInOutElev = pd.DataFrame(index=releases)
    return dfInOutElev

# Inset plot function to superimpose second ESRD at half size in lower right

def plot_inflow_esrd_with_inset(dfInflowPlot, Max_Rel, dfSurchargeCurve, curve_dfs, Label_X_Coord, Label_Angle, 
                                Y_Min, Y_Max, Y_Step, X_Min, X_Max, Inflow_Xlabel_FirstX, Inflow_Xlabel_Step, 
                                Inflow_Xlabel_Y_Buffer, Inflow_Label_Angle, X_Lable_Angle, X_Step, Reservoir, plot_dpi,
                                inset_dfInflowPlot, inset_Max_Rel, inset_dfSurchargeCurve, inset_curve_dfs, 
                                inset_Label_X_Coord, inset_Label_Angle, inset_Y_Min, inset_Y_Max, inset_Y_Step, 
                                inset_X_Min, inset_X_Max, inset_Inflow_Xlabel_FirstX, inset_Inflow_Xlabel_Step, 
                                inset_Inflow_Xlabel_Y_Buffer, inset_Inflow_Label_Angle, inset_X_Lable_Angle, inset_X_Step):

    plt.close('all')
    fig, ax = plt.subplots(figsize=(7, 7))

    # Plot main ESRD inflow curve
    dfInflowPlot.plot(ax=ax, legend=None, color='black')
    ax.plot(Max_Rel.index, Max_Rel['Elev'], label="Max Discharge", color='black')
    ax.plot(dfSurchargeCurve["Release"], dfSurchargeCurve["Env_Elev"], label="Induced Surcharge Envelope Curve", color='black')

    # Plot additional curves if available
    if curve_dfs != 'None':
        for curve_name, curve_df in curve_dfs.items():
            ax.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='gray', linestyle='--')

    # Set axis limits and labels
    ax.set_xlim(X_Min, X_Max)
    ax.set_ylim(Y_Min, Y_Max)
    ax.set_yticks(np.arange(Y_Min, Y_Max + Y_Step + 1, Y_Step))
    ax.set_ylabel("Pool Elevation (feet, project datum)")
    ax.set_xlabel("Reservoir Release in 1,000 cfs")
    ax.grid(alpha=0.5)
    ax.set_xticks(np.arange(0, X_Max + 1, X_Step))
    xlabels = ['{:,.0f}'.format(x) for x in ax.get_xticks() / 1000]
    ax.set_xticklabels(xlabels, rotation=X_Lable_Angle)

        # Inset plot
    inset_ax = inset_axes(ax, width="50%", height="50%", loc="lower right")
    inset_ax.tick_params(axis='both', which='major', labelsize=7)  # Reduce font size for the inset

    # Plot inset ESRD inflow curve
    inset_dfInflowPlot.plot(ax=inset_ax, legend=None, color='black')
    inset_ax.plot(inset_Max_Rel.index, inset_Max_Rel['Elev'], label="Max Discharge", color='black')
    inset_ax.plot(inset_dfSurchargeCurve["Release"], inset_dfSurchargeCurve["Env_Elev"], label="Induced Surcharge Envelope Curve", color='black')

    # Plot additional curves if available for inset
    if inset_curve_dfs != 'None':
        for curve_name, curve_df in inset_curve_dfs.items():
            inset_ax.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='gray', linestyle='--')

    # Set axis limits and labels for inset plot
    inset_ax.set_xlim(inset_X_Min, inset_X_Max)
    inset_ax.set_ylim(inset_Y_Min, inset_Y_Max)
    inset_ax.set_yticks(np.arange(inset_Y_Min, inset_Y_Max + inset_Y_Step + 1, inset_Y_Step))
    inset_ax.set_xlabel("Release (in 1,000 cfs)", fontsize=7)
    inset_ax.set_ylabel("Elevation (feet)", fontsize=7)
    inset_ax.grid(alpha=0.5)
    inset_ax.set_xticks(np.arange(0, inset_X_Max + 1, inset_X_Step))
    inset_xlabels = ['{:,.0f}'.format(x) for x in inset_ax.get_xticks() / 1000]
    inset_ax.set_xticklabels(inset_xlabels, rotation=inset_X_Lable_Angle, fontsize=7)

    plt.subplots_adjust(left=0.1, right=0.98, top=0.98, bottom=0.1)
    plt.savefig("../out/"+Reservoir+"_Inflow_ESRD_with_inset.png", dpi=plot_dpi, bbox_inches='tight', pad_inches=0)
    plt.show()

# ROC ESRD plot function with inset

def plot_roc_esrd_with_inset(dfPlotROC, dfSurchargeCurve, dfResv, curve_dfs, Label_X_Coord, Label_Angle, 
                              Y_Min, Y_Max, Y_Step, X_Min, X_Max, ROC_Xlabel_FirstX, ROC_Xlabel_Step, 
                              ROC_Xlabel_Y_Buffer, ROC_Label_Angle, X_Lable_Angle, X_Step, Reservoir, plot_dpi, 
                              inset_dfPlotROC, inset_dfSurchargeCurve, inset_dfResv, inset_curve_dfs, 
                              inset_Label_X_Coord, inset_Label_Angle, inset_Y_Min, inset_Y_Max, inset_Y_Step, 
                              inset_X_Min, inset_X_Max, inset_ROC_Xlabel_FirstX, inset_ROC_Xlabel_Step, 
                              inset_ROC_Xlabel_Y_Buffer, inset_ROC_Label_Angle, inset_X_Lable_Angle, inset_X_Step):

    plt.close('all')
    fig, ax = plt.subplots(figsize=(7, 7))

    # Plot main ROC ESRD curve
    dfPlotROC.plot(ax=ax, legend=None, color='black')
    ax.plot(dfSurchargeCurve["Release"], dfSurchargeCurve["Env_Elev"], label="Induced Surcharge Envelope Curve", color='black')
    ax.plot(dfResv["MaxRel"], dfResv["Elev"], label="Spillway Max Discharge", color='black')

    # Plot additional curves if available
    if curve_dfs != 'None':
        for curve_name, curve_df in curve_dfs.items():
            ax.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='gray', linestyle='--')

    # Set axis limits and labels
    ax.set_xlim(X_Min, X_Max)
    ax.set_ylim(Y_Min, Y_Max)
    ax.set_yticks(np.arange(Y_Min, Y_Max + Y_Step + 1, Y_Step))
    ax.set_ylabel("Pool Elevation (feet, project datum)")
    ax.set_xlabel("Reservoir Release in 1,000 cfs")
    ax.grid(alpha=0.5)
    ax.set_xticks(np.arange(0, X_Max + 1, X_Step))
    xlabels = ['{:,.0f}'.format(x / 1000) for x in ax.get_xticks()]
    ax.set_xticklabels(xlabels, rotation=X_Lable_Angle)

        # Inset plot for ROC ESRD
    inset_ax = inset_axes(ax, width="50%", height="50%", loc="lower right")
    inset_ax.tick_params(axis='both', which='major', labelsize=7)  # Reduce font size for the inset

    # Plot inset ROC ESRD curve
    inset_dfPlotROC.plot(ax=inset_ax, legend=None, color='black')
    inset_ax.plot(inset_dfSurchargeCurve["Release"], inset_dfSurchargeCurve["Env_Elev"], label="Induced Surcharge Envelope Curve", color='black')
    inset_ax.plot(inset_dfResv["MaxRel"], inset_dfResv["Elev"], label="Spillway Max Discharge", color='black')

    # Plot additional curves if available for inset
    if inset_curve_dfs != 'None':
        for curve_name, curve_df in inset_curve_dfs.items():
            inset_ax.plot(curve_df['Release'], curve_df['Elev'], label=curve_name, color='gray', linestyle='--')

    # Set axis limits and labels for inset plot
    inset_ax.set_xlim(inset_X_Min, inset_X_Max)
    inset_ax.set_ylim(inset_Y_Min, inset_Y_Max)
    inset_ax.set_yticks(np.arange(inset_Y_Min, inset_Y_Max + inset_Y_Step + 1, inset_Y_Step))
    inset_ax.set_xlabel("Release (in 1,000 cfs)", fontsize=7)
    inset_ax.set_ylabel("Elevation (feet)", fontsize=7)
    inset_ax.grid(alpha=0.5)
    inset_ax.set_xticks(np.arange(0, inset_X_Max + 1, inset_X_Step))
    inset_xlabels = ['{:,.0f}'.format(x / 1000) for x in inset_ax.get_xticks()]
    inset_ax.set_xticklabels(inset_xlabels, rotation=inset_X_Lable_Angle, fontsize=7)

    plt.subplots_adjust(left=0.1, right=0.98, top=0.98, bottom=0.1)
    plt.savefig("../out/"+Reservoir+"_ROC_ESRD_with_inset.png", dpi=plot_dpi, bbox_inches='tight', pad_inches=0)
    plt.show()

# Sample call with parameters from both configs for ROC ESRD plot with inset
plot_roc_esrd_with_inset(config1[0], config1[1], config1[0], config1[8], config1[6], config1[7],
                         config1[14], config1[15], config1[16], config1[11], config1[12], config1[24], config1[25],
                         config1[26], config1[27], config1[28], config1[29], config1[30], config1[13],
                         config2[0], config2[1], config2[0], config2[8], config2[6], config2[7],
                         config2[14], config2[15], config2[16], config2[11], config2[12], config2[24], config2[25],
                         config2[26], config2[27], config2[28], config2[29], config2[30], config2[13])