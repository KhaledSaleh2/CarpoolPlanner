# CarpoolPlanner

## Overview

This Python script automates the process of assigning carpool groups for the UW-Madison Club Tennis team. It retrieves data from Google Sheets, processes participant information, and optimally assigns passengers to drivers based on location proximity.

## Features

- Google Sheets Integration: Fetches carpool data using the gspread library and service account authentication.

- Automated Sorting: Categorizes members into drivers and passengers based on their responses.

- Optimized Grouping: Uses Google Maps API to calculate distances and efficiently assigns riders to cars.

- Prioritized Matching: Considers seniority (months in the club) when sorting passengers.

## Prerequisites

Ensure you have the following installed:

- Python 3

- Required libraries (gspread, oauth2client, pandas, googlemaps, dotenv)

## Future Potential Enhancements
- Implement a web interface for easier data input and real-time visualization.
- Enable notifications via SMS or email for ride confirmations.
