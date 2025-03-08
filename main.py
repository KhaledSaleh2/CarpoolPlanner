import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import googlemaps as gmaps
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('API_KEY')
service_account_credentials_path = os.getenv('SERVICE_ACCOUNT_CREDENTIALS_PATH')
# Define the scope
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authenticate with JSON key file
creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_credentials_path, scope)
client = gspread.authorize(creds)

# Open the Google Sheet
spreadsheet = client.open("Club Tennis Carpools")  # Use the name of the sheet
practice_worksheet = spreadsheet.worksheet("Form Responses 3")
player_worksheet = spreadsheet.worksheet("PLAYER INFO")

# Read data for lookup table
data = player_worksheet.get('A:I')
lookupdf = pd.DataFrame(data[1:], columns=data[0])
lookupdf = lookupdf.apply(lambda x: x.str.upper() if x.dtype == "object" else x)

# Read all data into a list
data = practice_worksheet.get('A:C')

# Convert to Pandas DataFrame
practicedf = pd.DataFrame(data[1:], columns=data[0])
# Rename columns
practicedf = practicedf.rename(columns={"Name (first and last no abbreviations)": "Name", "Do you need a ride?": "IsGoing"})
practicedf = practicedf.apply(lambda x: x.str.upper() if x.dtype == "object" else x)

drivers = {}
passengers = {}

# Loop through form results and sort into drivers and passengers
driver_idx = 0
passenger_idx = 0
for index, row in practicedf.iterrows():
    temp_row = lookupdf.loc[row['Name'] == lookupdf['Name']]
    if temp_row.empty:
        print(str(row['Name']) + " was not found in the lookup table")
    if row['IsGoing'] == "NO (I HAVE A CAR AND CAN DRIVE OTHERS)":
        drivers[row['Name']] = [list(temp_row['Address'])[0], list(temp_row['Phone Number'])[0], 4, driver_idx, []]
        driver_idx += 1
    elif row['IsGoing'] == "YES":
        passengers[row['Name']] = [list(temp_row['Address'])[0], list(temp_row['Phone Number'])[0], passenger_idx, int(list(temp_row['Num Months in Club'])[0])]
        passenger_idx += 1
    # If we added participation tracking add some code here

# Reverse mapping to find driver name from ID
driver_id_to_name = {info[3]: name for name, info in drivers.items()}

sorted_passengers = dict(sorted(passengers.items(), key=lambda item: item[1][3], reverse=True))

num_drivers = len(drivers)
num_riders = min(len(sorted_passengers), num_drivers * 4)

count = 0
kept_passengers = {}
bus_riders = []
for key in sorted_passengers:
    if count < num_riders:
        kept_passengers[key] = sorted_passengers[key]
    else:
        bus_riders.append(key)
    count += 1

passengers = dict(kept_passengers)

# Fix the indices for the passengers
passenger_idx = 0
for key, value in passengers.items():
    passengers[key][2] = passenger_idx
    passenger_idx += 1

print("Drivers:")
for key in drivers:
    print(key)
print("Passengers after filter:")
for key in passengers:
    print(key)

# Reverse mapping to find passenger name from ID
passenger_id_to_name = {info[2]: name for name, info in passengers.items()}

# Create 2D adjacency matrix passengers as rows and cols
riders_matrix = [[0 for i in range(len(passengers))] for j in range(len(passengers))]

# Calculate distances between points and fill in matrix
gmaps = gmaps.Client(key=api_key)

for row, passKey1 in enumerate(passengers):
    for col, passKey2 in enumerate(passengers):
        # driverAddress = drivers[driverKey][0]
        # driverIndex = drivers[driverKey][3]
        passAddress1 = passengers[passKey1][0]
        pass_index_1 = passengers[passKey1][2]
        passAddress2 = passengers[passKey2][0]
        pass_index_2 = passengers[passKey2][2]
        if pass_index_1 == pass_index_2:
            riders_matrix[row][col] = (10000, pass_index_1)
            continue
        riders_matrix[row][col] = (float(gmaps.distance_matrix(passAddress1, passAddress2, units="imperial")["rows"][0]["elements"][0]["distance"]["text"][:-3]), col)

# Sort each column in each row and append row number at end to keep track of original row index
for i in range(num_riders):
    riders_matrix[i].sort()
    riders_matrix[i].append(i)

# Sort matrix by row with lowest distance
riders_matrix.sort()

group_assigned = {} # key: passenger index, val: group index
people_in_group = {} # key: group index, val: num people in group (4 means full)
num_groups_assigned = 0

for i in range(num_riders):
    # ignore when first rider has been assigned a group
    pass_index_1 = riders_matrix[i][-1]
    if pass_index_1 in group_assigned:
        continue
    curr_index = -1
    for j in range(num_riders):
        pass_index_2 = riders_matrix[i][j][1]
        # ignore when both passengers are the same or when second rider is in full group
        if pass_index_1 != pass_index_2 and (pass_index_2 not in group_assigned or len(people_in_group[group_assigned[pass_index_2]]) < 4):
            curr_index = pass_index_2
            break
    # Rare edge case where last group only gets assigned one person
    if curr_index == -1:
        group_assigned[pass_index_1] = num_groups_assigned + 1
        num_groups_assigned += 1
        people_in_group[num_groups_assigned] = [pass_index_1]
    else:
        # Case where second rider is already assigned a group
        if curr_index in group_assigned:
            group = group_assigned[curr_index]
            group_assigned[pass_index_1] = group
            people_in_group[group].append(pass_index_1)
        # Case where neither rider is assigned a group yet
        else:
            group = num_groups_assigned + 1
            num_groups_assigned += 1
            group_assigned[pass_index_1] = group
            group_assigned[curr_index] = group
            people_in_group[group] = [pass_index_1, pass_index_2]

# Create matrix that stores distance between each driver and rider
drivers_matrix = [[0 for _ in range(len(passengers))] for __ in range(len(drivers))]

# Find distandce between each driver and passenger
for row, driverKey in enumerate(drivers):
    for col, passKey in enumerate(passengers):
        driverAddress = drivers[driverKey][0]
        driverIndex = drivers[driverKey][3]
        passAddress = passengers[passKey][0]
        passIndex = passengers[passKey][2]
        drivers_matrix[row][col] = (float(gmaps.distance_matrix(driverAddress, passAddress, units="imperial")["rows"][0]["elements"][0]["distance"]["text"][:-3]), col)

# Sort each row by minimum distance
for i in range(num_drivers):
    drivers_matrix[i].sort()
    drivers_matrix[i].append(i)

# Sort entire matrix by row with minimum distance
drivers_matrix.sort()

assigned_driver = set() # keeps track of whos in a car
cars = [0 for i in range(num_drivers)] # keeps track of final car assignments

# Assign drivers to groups
for row in range(num_drivers):
    driver_index = drivers_matrix[row][-1]
    cars[row] = [driver_index]
    for col in range(num_riders):
        rider_index = drivers_matrix[row][col][1]
        if rider_index not in assigned_driver:
            break
    group_num = group_assigned[rider_index]
    for person in people_in_group[group_num]:
        cars[row].append(person)
        assigned_driver.add(person)

print(cars)

print("Riders Matrix")
for row in riders_matrix:
    print()
    print(passenger_id_to_name[row[-1]])
    for j in range(num_riders):
        print(passenger_id_to_name[row[j][1]], row[j][0])
    print()

print("Drivers Matrix")
for row in drivers_matrix:
    print()
    print(driver_id_to_name[row[-1]])
    for j in range(num_riders):
        print(passenger_id_to_name[row[j][1]], row[j][0])
    print()
    
# Print out each car
for i in range(num_drivers):
    print("Car", i + 1)
    for j in range(len(cars[i])):
        # Print the actual name of each person in each car
        if j == 0:
            print("Driver:", driver_id_to_name[cars[i][j]])
        else:
            print(passenger_id_to_name[cars[i][j]])
    print()

# Print bus riders
print("Bus riders")
for person in bus_riders:
    print(person)