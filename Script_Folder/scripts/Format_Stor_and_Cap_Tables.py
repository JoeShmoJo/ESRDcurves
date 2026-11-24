# -*- coding: utf-8 -*-
"""
Created on Thu Dec 14 11:53:58 2023

@author: g2encjer
"""


import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline
from scipy.interpolate import interp1d
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress only the single InsecureRequestWarning from urllib3 needed for bypassing SSL verification
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# List of reservoirs
Reservoirs = ['BCL','BLU','CGR','COT','DET','DEX','DOR','FAL','FOS','FRN','GPR','HCR','LOP']

Reservoir_fullname = ['Big Cliff','Blue River','Cougar','Cottage Grove','Detroit','Dexter','Dorena','Fall Creek','Foster','Fern Ridge','Green Peter','Hills Creek','Lookout Point']

name_mapping = dict(zip(Reservoir_fullname, Reservoirs))

# Base URL
base_url = "https://nwp-wmops.nwp.usace.army.mil/nwp/ratings/www/rating_links/"

# Dictionary to hold data
reservoir_stor = {}

spline_order = 2  # Define the order of the spline here

for reservoir in Reservoirs:
    url = f"{base_url}{reservoir}.rdb.txt"
    response = requests.get(url, verify=False)
    if response.status_code == 200:
        lines = [line for line in response.text.split('\n') if line and not line.startswith('#') and not '16N' in line]
        data_lines = lines[1:]
        data = []
        for line in data_lines:
            parts = line.split()
            if len(parts) >= 3:
                elevation, storage = float(parts[0]), float(parts[2])
                data.append([elevation, storage])
        df = pd.DataFrame(data, columns=['Elevation', 'Storage'])
        df = df.drop_duplicates(subset='Storage')  # Remove duplicates

        # Perform Spline Regression
        spline = UnivariateSpline(df['Elevation'], df['Storage'], k=spline_order)

        # Add Predicted Storage
        df['Predicted_Storage'] = spline(df['Elevation'])

        # Filter DataFrame to keep only whole foot elevations
        df = df[df['Elevation'].apply(lambda x: x.is_integer())]

        # Plotting
        plt.figure()
        plt.scatter(df['Elevation'], df['Storage'], label='Original Storage')
        plt.plot(df['Elevation'], df['Predicted_Storage'], label='Predicted Storage', color='red')
        plt.xlabel('Elevation')
        plt.ylabel('Storage')
        plt.title(f"{reservoir} Reservoir Storage vs. Elevation")
        plt.legend()

        # Calculate and Adjust R2 Value Position
        y_true = df['Storage']
        y_pred = df['Predicted_Storage']
        r2 = 1 - ((y_true - y_pred) ** 2).sum() / ((y_true - y_true.mean()) ** 2).sum()
        plt.text(0.05, 0.85, f'R²: {r2:.2f}', transform=plt.gca().transAxes)

        plt.show()

        reservoir_stor[reservoir] = df
    else:
        print(f"Failed to retrieve data for {reservoir}")

### Release Capacity Curves

# Assuming you have the actual CSV file path
csv_file_path = "../ReleaseCapacity.csv"

# Read the CSV data into a DataFrame
# If your file is an Excel file, replace the following line with:
# df = pd.read_excel(csv_file_path, sheet_name='ReleaseCapacity')
df = pd.read_csv(csv_file_path)

# Initialize an empty dictionary to hold the dataframes for each reservoir
capacity_dict = {}

# Group the data by Reservoir
grouped = df.groupby('Reservoir')

# Iterate over each group to process and interpolate data
for reservoir_name, group in grouped:
    outlets = group['Outlet'].unique()
    min_elevation = int(np.floor(group['Elevation'].min()))
    max_elevation = int(np.ceil(group['Elevation'].max()))
    
    # Create a DataFrame for the range of elevations
    reservoir_df = pd.DataFrame(index=np.arange(min_elevation, max_elevation + 1))
    
    # Interpolate for each outlet
    for outlet in outlets:
        outlet_df = group[group['Outlet'] == outlet].copy()
        
        # Ensure that Elevation is sorted before interpolation
        outlet_df.sort_values(by='Elevation', inplace=True)
        
        # Use scipy's interp1d for interpolation with no extrapolation
        interp_func = interp1d(outlet_df['Elevation'], outlet_df['Release Capacity'], 
                               kind='linear', bounds_error=False, fill_value=(0, 0))
        
        # Apply the interpolation function to the defined elevation range
        reservoir_df[outlet] = interp_func(reservoir_df.index)

    # Store the DataFrame in the dictionary
    capacity_dict[reservoir_name] = reservoir_df

capacity_dict = {name_mapping[key]: value for key, value in capacity_dict.items() if key in name_mapping}

# Now reservoir_dict contains a DataFrame for each reservoir with interpolated values

def calculate_max_release(df):
    # Columns to exclude from the direct sum
    excluded_columns = ['SluiceGate', 'Diversion Tunnel', 'Spillway', 'Power Plant']

    # Check which columns are present in the DataFrame
    relevant_columns = [col for col in df.columns if col not in excluded_columns]

    # Initialize the 'Max Release' column
    df['Max Release'] = df[relevant_columns].sum(axis=1)

    # Check if both 'Power Plant' and 'Spillway' are present and add the greater of the two to 'Max Release'
    if 'Power Plant' in df.columns and 'Spillway' in df.columns:
        df['Max Release'] += df[['Power Plant', 'Spillway']].max(axis=1)
    elif 'Power Plant' in df.columns:
        df['Max Release'] += df['Power Plant']
    elif 'Spillway' in df.columns:
        df['Max Release'] += df['Spillway']

    return df

# Apply the function to each DataFrame in the dictionary
capacity_dict = {key: calculate_max_release(df) for key, df in capacity_dict.items()}


with pd.ExcelWriter('capacity_dict.xlsx', engine='openpyxl') as writer:
    for sheet_name, df in capacity_dict.items():
        df.to_excel(writer, sheet_name=sheet_name)


# Step 1: Reshape 'capacity_dict' DataFrames
for key, df in capacity_dict.items():
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Elevation'}, inplace=True)

# Step 2 & 3: Merge, Interpolate, and Select Columns
merged_dict = {}
for key in capacity_dict:
    if key in reservoir_stor:
        # Merge on 'Elevation', using an outer join to keep all elevation values
        merged_df = pd.merge(capacity_dict[key], reservoir_stor[key], on='Elevation', how='outer')

        # Sort by 'Elevation' to ensure proper interpolation
        merged_df.sort_values(by='Elevation', inplace=True)

        # Interpolate 'Max Release' only (to avoid extrapolation)
        merged_df['Max Release'] = merged_df['Max Release'].interpolate(method='linear', limit_direction='forward', axis=0)

        # Keep only rows where 'Predicted_Storage' is not NaN (to avoid extrapolation)
        merged_df = merged_df[merged_df['Predicted_Storage'].notna()]

        # Select only the required columns
        merged_df = merged_df[['Elevation', 'Predicted_Storage', 'Max Release']]

        merged_dict[key] = merged_df

# 'merged_dict' now contains the merged dataframes with only the required columns


from numpy.polynomial.polynomial import Polynomial

# Define reservoirs for polynomial regression and their elevation ranges
poly_reservoirs = {
    'BLU': {'lower': 1180, 'upper': 1362}, 
    'CGR': {'lower': 1532, 'upper': 1705}, 
    'HCR': {'lower': 1448, 'upper': 1548},  
    'LOP': {'lower': 825, 'upper': 941}, 
    'DEX': {'lower': 693, 'upper': 698},
    'FAL': {'lower': 728, 'upper': 839}, 
    'COT': {'lower': 750, 'upper': 808}, 
    'DOR': {'lower': 771, 'upper': 866}, 
    'FRN': {'lower': 353, 'upper': 380}, 
    'FOS': {'lower': 613, 'upper': 646}, 
    'GPR': {'lower': 922, 'upper': 1020}, 
    # ... Add other reservoirs and their ranges here
}

# Degree of the polynomial regression
poly_degree = 3

# Function for polynomial regression
def polynomial_regression(df, degree):
    # Fit polynomial regression
    p = Polynomial.fit(df['Elevation'], df['Storage'], degree)
    return p

# Initialize poly_dict
poly_dict = {}

# Perform polynomial regression and store results in poly_dict
for reservoir, range_limits in poly_reservoirs.items():
    if reservoir in reservoir_stor:
        df = reservoir_stor[reservoir]
        
        # Trim the rating table to exclude upper and lower elevations
        df_trimmed = df[(df['Elevation'] >= range_limits['lower']) & (df['Elevation'] <= range_limits['upper'])]
        
        if not df_trimmed.empty:
            # Perform polynomial regression
            poly_model = polynomial_regression(df_trimmed, poly_degree)
            
            # Generate predictions
            df_trimmed['Poly_Predicted_Storage'] = poly_model(df_trimmed['Elevation'])
            
            # Merge with capacity data
            if reservoir in capacity_dict:
                merged_df = pd.merge(df_trimmed, capacity_dict[reservoir], on='Elevation', how='inner')
                poly_dict[reservoir] = merged_df[['Elevation', 'Poly_Predicted_Storage', 'Max Release']]

# ... [previous code]

# Function to perform polynomial regression and return a DataFrame with original and polyfit data
def prepare_polyfit_data(df, degree):
    # Fit polynomial regression
    p = Polynomial.fit(df['Elevation'], df['Storage'], degree)
    
    # Prepare DataFrame for plotting
    plot_df = pd.DataFrame()
    plot_df['Elevation'] = df['Elevation']
    plot_df['Original'] = df['Storage']
    plot_df['Polyfit'] = p(df['Elevation'])
    
    return plot_df

# Function to plot original and polynomial regression data
def plot_regression(df, reservoir_name, degree):
    plt.figure()
    
    # Plot original data
    plt.scatter(df['Elevation'], df['Original'], label='Original Storage', color='blue')

    # Plot polynomial regression
    plt.plot(df['Elevation'], df['Polyfit'], label=f'Polynomial Regression (Degree {degree})', color='green')
    
    plt.xlabel('Elevation')
    plt.ylabel('Storage')
    plt.title(f"{reservoir_name} Reservoir: Storage vs. Elevation")
    plt.legend()
    plt.show()

# Perform polynomial regression and store results in poly_dict
for reservoir, range_limits in poly_reservoirs.items():
    if reservoir in reservoir_stor:
        df = reservoir_stor[reservoir]

        # Trim the rating table
        df_trimmed = df[(df['Elevation'] >= range_limits['lower']) & (df['Elevation'] <= range_limits['upper'])]

        if not df_trimmed.empty:
            # Prepare data for polynomial regression plot
            plot_df = prepare_polyfit_data(df_trimmed, poly_degree)

            # Plot with original and polynomial regression data
            plot_regression(plot_df, reservoir, poly_degree)

            # Merge with capacity data and store in poly_dict
            if reservoir in capacity_dict:
                merged_df = pd.merge(plot_df, capacity_dict[reservoir], on='Elevation', how='inner')
                poly_dict[reservoir] = merged_df[['Elevation', 'Original', 'Polyfit', 'Max Release']]







