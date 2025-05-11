# copyright 2025 Florian Schubert


# ##### IMPORTS #####

from typing import Tuple
import pandas as pd
import copy

import requests

import pytz
from datetime import datetime, timezone
from timezonefinder import TimezoneFinder

import json



##### CONSTANTS #####

TIME_ZONE_REFERENCE_YEAR = 2025



##### FUNCTION DEFINITIONS #####

def retrieve_coordinates_nominatim(location_name:str, email_nominatim:str)->Tuple[float, float, str]:
    # api: https://nominatim.org/release-docs/develop/api/Search/

    url = (f"https://nominatim.openstreetmap.org/search?q={location_name}"
           f"&email={email_nominatim}&format=json&limit=1")

    response = requests.get(url)
    if response.status_code == 200:
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            raise ConnectionError("Failed to decode JSON response from Nominatim API.")
    else:
        raise ConnectionError(f"Failed to get data from Nominatim API. Status code: {response.status_code}")

    if not data:
        raise ConnectionError("Failed to get data from Nominatim API.")

    latitude = float(data[0]['lat'])
    longitude = float(data[0]['lon'])
    location_name = data[0]['display_name']

    return latitude, longitude, location_name



def retrieve_time_zone_name(latitude:float, longitude:float)->str:
    time_zone_finder = TimezoneFinder()

    time_zone_name = time_zone_finder.timezone_at(lng=longitude, lat=latitude)

    if time_zone_name is None:
        raise ValueError(f"Could not determine the time zone for the coordinates "
                         f"(latitude={latitude}, longitude={longitude}).")

    return time_zone_name



def convert_utc_to_local_time(utc_datetime:datetime, time_zone_name:str)->datetime:
    time_zone = pytz.timezone(time_zone_name)
    local_datetime = utc_datetime.replace(tzinfo=pytz.utc).astimezone(time_zone)

    return local_datetime



def retrieve_climate_data(latitude:float, longitude:float, time_zone_name:str, path_output_raw_data:str=None)\
        ->Tuple[list, list]:
    # tool: https://re.jrc.ec.europa.eu/pvg_tools/en/

    url = f"https://re.jrc.ec.europa.eu/api/tmy?lat={latitude}&lon={longitude}&outputformat=json"
    response = requests.get(url)

    if response.status_code == 200:
        try:
            data_raw = response.json()
        except requests.exceptions.JSONDecodeError:
            raise ConnectionError("Failed to decode JSON response from PVGIS API.")
    else:
        raise ConnectionError(f"Failed to get data from PVGIS API. Status code: {response.status_code}")

    if not data_raw:
        raise ConnectionError("Failed to get data from PVGIS API.")

    # save raw data
    if path_output_raw_data is not None:
        data_raw_json = json.dumps(data_raw, indent=4)
        with open(path_output_raw_data, "w") as file:
            file.write(data_raw_json)

    # extract climate data
    climate_data = []
    try:
        for entry in data_raw['outputs']['months_selected']:
            month = entry['month']
            year = entry['year']
            year_month_str = f"{year}{str(month).zfill(2)}"
            keys_year_month = [entry["time(UTC)"] for entry in data_raw['outputs']['tmy_hourly']
                               if entry["time(UTC)"].startswith(year_month_str)]
            for key in keys_year_month:
                # key format "YYYYMMDD:HH00"
                day = int(key[6:8])
                hour = int(key[9:11])
                data_entry_raw = [entry for entry in data_raw['outputs']['tmy_hourly']
                                  if entry["time(UTC)"] == key][0]
                row_data = {
                    "utc_month": month,
                    "utc_day": day,
                    "utc_hour": hour,
                    "temperature": data_entry_raw["T2m"],
                    "irradiation_direct_normal": data_entry_raw["Gb(n)"]
                }
                climate_data.append(row_data)
    except KeyError:
        raise ValueError("Failed to extract climate data from the PVGIS API response.")

    df_climate_data = pd.DataFrame(climate_data)

    # convert utc time into local time
    for index, row in df_climate_data.iterrows():
        utc_datetime = datetime(TIME_ZONE_REFERENCE_YEAR, int(row["utc_month"]), int(row["utc_day"]),
                                int(row["utc_hour"]), tzinfo=timezone.utc)
        local_datetime = convert_utc_to_local_time(utc_datetime, time_zone_name)
        df_climate_data.at[index, "local_month"] = local_datetime.month
        df_climate_data.at[index, "local_day"] = local_datetime.day
        df_climate_data.at[index, "local_hour"] = local_datetime.hour

    # group data for month and hour
    df_climate_data_grouped = df_climate_data.groupby(["local_month", "local_hour"]).agg(
        temperature=("temperature", "mean"),
        irradiation_direct_normal=("irradiation_direct_normal", "mean")
    ).reset_index()

    # convert dataframe into lists
    temperature_list = []
    irradiation_list = []
    for month_id in range(0, 12):
        month_temperature_list = []
        month_irradiation_list = []
        month = month_id + 1
        for hour in range(0, 24):
            try:
                df_grouped_row = df_climate_data_grouped[
                    (df_climate_data_grouped["local_month"] == month) & (df_climate_data_grouped["local_hour"] == hour)
                ]
                month_temperature_list.append(df_grouped_row["temperature"].iloc[0])
                month_irradiation_list.append(df_grouped_row["irradiation_direct_normal"].iloc[0])
            except ValueError:
                raise ValueError("Failed to convert climate dataframe to lists.")
        temperature_list.append(copy.deepcopy(month_temperature_list))
        irradiation_list.append(copy.deepcopy(month_irradiation_list))


    return temperature_list, irradiation_list



def retrieve_location_data(location_name:str, email_nominatim:str, path_directory_raw_climate_data:str=None)->dict:

    flag_workaround = False

    if flag_workaround:
        with open("./operation_annual/simulation_dict.json", 'r') as file:
            data_file = json.load(file)
        if location_name == "Zurich":
            return copy.deepcopy(data_file["zurich"]["location_data"]["Zurich"])
        elif location_name == "Rome":
            return copy.deepcopy(data_file["rome"]["location_data"]["Rome"])
        elif location_name == "Helsinki":
            return copy.deepcopy(data_file["helsinki"]["location_data"]["Helsinki"])
        else:
            raise ValueError(f"Location name \'{location_name}\' not available for work around (offline).")

    else:
        latitude, longitude, location_name_lookup = retrieve_coordinates_nominatim(location_name, email_nominatim)

        time_zone_name = retrieve_time_zone_name(latitude, longitude)

        if path_directory_raw_climate_data is not None:
            location_name_print = (location_name.replace(" ", "_")
                                   .replace(",", "_")
                                   .replace(".", "_")
                                   .replace(":", "_")
                                   .lower())
            path_output_raw_climate_data = (path_directory_raw_climate_data + "climate_data_raw_" + location_name_print
                                            + ".json")

            temperature_data, solar_irradiation_data = retrieve_climate_data(latitude, longitude, time_zone_name,
                                                                             path_output_raw_climate_data)
        else:
            temperature_data, solar_irradiation_data = retrieve_climate_data(latitude, longitude, time_zone_name,
                                                                             None)

        data = {
            "location_name": location_name_lookup,
            "latitude": latitude,
            "longitude": longitude,
            "time_zone": time_zone_name,
            "temperature": copy.deepcopy(temperature_data),
            "irradiation_direct_normal": copy.deepcopy(solar_irradiation_data)
        }

        return data