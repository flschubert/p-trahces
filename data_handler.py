# copyright 2025 Florian Schubert


##### IMPORTS #####

import model as md
import location_database as ldb

import json
import copy
from typing import Tuple, Union

import numpy as np
import pandas as pd
from datetime import datetime
from operator import itemgetter
import itertools



##### CONSTANTS #####

PATH_DEFAULT = "default.json"
PATH_PARAMETER_OPTIONS = "parameter_options.json"

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]

DATA_DEFAULT = None
DATA_PARAMETER_OPTIONS = None



##### FUNCTION DEFINITIONS #####

def overwrite_paths(path_default:str, path_parameter_options:str)->None:
    global PATH_DEFAULT
    global PATH_PARAMETER_OPTIONS

    PATH_DEFAULT = path_default
    PATH_PARAMETER_OPTIONS = path_parameter_options



def read_json_file(path:str)->dict:
    with open(path, 'r') as file:
        data = json.load(file)
    return data



def load_defaults()->None:
    global DATA_DEFAULT
    global DATA_PARAMETER_OPTIONS

    DATA_DEFAULT = read_json_file(PATH_DEFAULT)
    DATA_PARAMETER_OPTIONS = read_json_file(PATH_PARAMETER_OPTIONS)



def sort_dict(dictionary:dict)->None:
    dictionary_sorted = {key: value for key, value in sorted(dictionary.items(), key=lambda item: item[0])}
    dictionary.clear()
    dictionary.update(dictionary_sorted)



def sort_dict_list(dict_list:list, keys:list)->None:
    dict_list.sort(key=itemgetter(*keys))



def get_defaults(key:str)->Union[str,dict,Tuple[str,dict]]:
    # DATA_DEFAULT loaded at the end of this script

    if key in ["default_name", "temperature_control_curves", "vehicle_parameter_alternative",
               "operation_schedule_parameter_alternative", "scenarios"]:
        return DATA_DEFAULT[key]
    elif key in ["vehicle", "operation_schedule"]:
        entry = DATA_DEFAULT[key]
        return entry["name"], entry["data"]



def get_parameter_option(group:str, option:str)->Union[int,float,str]:
    # DATA_PARAMETER_OPTIONS loaded at the end of this script
    return DATA_PARAMETER_OPTIONS[group][option]



def get_decimal_digits(number:float)->int:
    number_str = f"{number:.16f}".rstrip('0')
    decimal_pos = number_str.find('.')
    if decimal_pos == -1:
        return 0
    return len(number_str) - decimal_pos - 1



def get_parameter_decimal_step_precision(group:str, option:str)->int:
    step = get_parameter_option(group, option)
    return get_decimal_digits(step)



def get_parameter_format_from_step(group:str, option:str)->str:
    step_precision = get_parameter_decimal_step_precision(group, option)
    format = str(f"%.{step_precision}f")
    return format



def get_vehicle_parameter_names()->list:
    parameter_names = list(DATA_PARAMETER_OPTIONS["parameters_vehicle"].keys())
    parameter_names.remove("name")
    parameter_names.remove("heating_cooling_devices")
    return parameter_names



def get_vehicle_parameter_display_names()->list:
    return [DATA_PARAMETER_OPTIONS["parameters_vehicle"][name] for name in get_vehicle_parameter_names()]



def create_session_state_dictionaries(session_state:dict)->None:
    # specification
    session_state["specification"] = {
        "temperature_control_curves": {},
        "vehicles": {},
        "vehicle_versions": {},
        "vehicle_parameter_alternatives": [],
        "operation_schedules": {},
        "scenario_options": {},
        "scenarios": {},
        "scenario_reference": None,
    }

    # flags
    session_state["flag_input_changed"] = False
    session_state["flag_stop"] = False

    # nominatim email
    session_state["nominatim_email"] = ""

    # temporary data
    session_state["tmp"] = {}



def import_specification_dictionary(session_state:dict, import_dict:dict)->None:

    # content checks
    if "temperature_control_curves" not in import_dict.keys():
        raise ValueError("Imported dictionary does not contain key 'temperature_control_curves'.")
    if "vehicles" not in import_dict.keys():
        raise ValueError("Imported dictionary does not contain 'vehicles'.")
    if "vehicle_parameter_alternatives" not in import_dict.keys():
        raise ValueError("Imported dictionary does not contain key 'vehicle_parameter_alternatives'.")
    if "operation_schedules" not in import_dict.keys():
        raise ValueError("Imported dictionary does not contain key 'operation_schedules'.")

    # overwrite specification
    session_state["specification"] = {}
    session_state["specification"] = import_dict

    reload_vehicle_version_and_scenario_data(session_state)
    session_state["flag_input_changed"] = True



def load_default_specification(session_state:dict)->None:
    create_session_state_dictionaries(session_state)

    load_default_temperature_curves(session_state)

    default_vehicle_name = get_defaults("vehicle")[0]
    add_vehicle(session_state, default_vehicle_name, init_with_default_parameters=True)

    default_operation_schedule_name = get_defaults("operation_schedule")[0]
    add_operation_schedule(session_state, default_operation_schedule_name, init_with_default_parameters=True)

    load_default_vehicle_parameter_alternative(session_state)

    session_state["specification"]["scenarios"] = copy.deepcopy(DATA_DEFAULT["scenarios"])
    reload_vehicle_version_and_scenario_data(session_state)

    session_state["specification"]["scenario_reference"] = DATA_DEFAULT["scenario_reference"]

    session_state["flag_input_changed"] = True



def convert_str_to_date(date_str:str)->datetime.date:
    if date_str is None:
        return None
    return datetime.strptime(date_str, "%m-%d").date()



def convert_date_to_str(date:datetime.date)->str:
    if date is None:
        return None
    return datetime.strftime(date, "%m-%d")



def convert_str_to_time(time_str:str)->datetime.time:
    if time_str is None:
        return None
    return datetime.strptime(time_str, "%H:%M").time()



def convert_time_to_str(time:datetime.time)->str:
    if time is None:
        return None
    return time.strftime("%H:%M")



def convert_dictionary_to_str(dictionary:dict, keys_to_display_names:bool=False)->str:
    if keys_to_display_names:
        parameter_set = {}
        for key, value in dictionary.items():
            parameter_set[get_parameter_option("parameters_vehicle", key)] = value
    else:
        parameter_set = dictionary
    return str(parameter_set).replace("'", "")



# temperature curves


def generate_dataframe_from_temperature_curves(session_state:dict)->pd.DataFrame:
    # generate data list
    df_data = []
    for name, data in session_state["specification"]["temperature_control_curves"].items():
        data_copy = copy.deepcopy(data)
        data_copy["name"] = name
        data_copy.pop("heating")
        data_copy.pop("cooling")

        # find min and max temperatures for heating and cooling
        heating_max = None
        cooling_min = None
        for entry in data["heating"]:
            if heating_max is None or entry[1] > heating_max:
                heating_max = entry[1]
        for entry in data["cooling"]:
            if cooling_min is None or entry[1] < cooling_min:
                cooling_min = entry[1]
        data_copy["temperature_heating_max"] = heating_max
        data_copy["temperature_cooling_min"] = cooling_min

        df_data.append(data_copy)

    column_names = ["name", "temperature_heating_max", "temperature_cooling_min"]

    # create dataframe
    df = pd.DataFrame(df_data, index=list(session_state["specification"]["temperature_control_curves"].keys()),
                      columns=column_names)
    df.set_index("name", inplace=True)

    return df



def initialize_temperature_curve_empty(session_state:dict, overwrite:bool=False)->None:
    flag_create = False
    if "temperature_curve_editor" in session_state["tmp"].keys():
        flag_create = overwrite
    else:
        flag_create = True

    if flag_create:
        session_state["tmp"]["temperature_curve_editor"] = {}
        session_state["tmp"]["temperature_curve_editor"]["heating"] = []
        session_state["tmp"]["temperature_curve_editor"]["cooling"] = []



def initialize_temperature_curve_default(session_state:dict, name:str)->None:
    default_curves = get_defaults("temperature_control_curves")

    session_state["tmp"]["temperature_curve_editor"] = {}
    session_state["tmp"]["temperature_curve_editor"]["heating"] = (
        copy.deepcopy(default_curves[name]["heating"]))
    session_state["tmp"]["temperature_curve_editor"]["cooling"] = (
        copy.deepcopy(default_curves[name]["cooling"]))



def initialize_temperature_curve_constant(session_state:dict, heating_temperature:float, cooling_temperature:float)->None:
    session_state["tmp"]["temperature_curve_editor"] = {}
    session_state["tmp"]["temperature_curve_editor"]["heating"] = [[heating_temperature, heating_temperature]]
    session_state["tmp"]["temperature_curve_editor"]["cooling"] = [[cooling_temperature, cooling_temperature]]



def clear_temperature_curve(session_state:dict)->None:
    if "temperature_curve_editor" in session_state["tmp"].keys():
        session_state["tmp"].pop("temperature_curve_editor")



def extend_temperature_curve(points_heating:list, points_cooling:list)->Tuple[list,list,list]:
    # find segments for environment temperatures and vehicle temperatures on segment breaks

    def complete_vehicle_temperatures(temperature_environment_breaks: list, points_raw: list) -> list:
        # create raw lists with missing vehicle temperatures
        temperature_vehicle = []
        for x in temperature_environment_breaks:
            flag_found = False
            for point in points_raw:
                if point[0] == x:
                    temperature_vehicle.append(point[1])
                    flag_found = True
                    break
            if not flag_found:
                temperature_vehicle.append(None)

        # interpolate missing vehicle temperatures (use dataframe)
        df = pd.DataFrame(
            {"temperature_environment": temperature_environment_breaks, "temperature_vehicle": temperature_vehicle})
        df.set_index("temperature_environment", inplace=True)
        df = df.interpolate(method="index", limit_direction="both")

        return df["temperature_vehicle"].tolist()

    temperature_environment_breaks_heating = [point[0] for point in points_heating]
    temperature_environment_breaks_cooling = [point[0] for point in points_cooling]
    temperature_environment_breaks = sorted(
        set(temperature_environment_breaks_heating + temperature_environment_breaks_cooling))

    temperature_vehicle_heating = []
    temperature_vehicle_cooling = []
    if len(points_heating) > 0:
        temperature_vehicle_heating = complete_vehicle_temperatures(temperature_environment_breaks, points_heating)
    if len(points_cooling) > 0:
        temperature_vehicle_cooling = complete_vehicle_temperatures(temperature_environment_breaks, points_cooling)

    return temperature_environment_breaks, temperature_vehicle_heating, temperature_vehicle_cooling



def is_temperature_curve_valid(points_heating:list, points_cooling:list)->bool:
    temperature_environment_breaks, temperature_vehicle_heating, temperature_vehicle_cooling = (
        extend_temperature_curve(points_heating, points_cooling))

    if len(temperature_vehicle_heating) > 0 and len(temperature_vehicle_cooling):
        for i in range(len(temperature_environment_breaks)):
            if temperature_vehicle_heating[i] is not None and temperature_vehicle_cooling[i] is not None:
                if temperature_vehicle_heating[i] > temperature_vehicle_cooling[i]:
                    return False
    return True



def generate_temperature_curve_point_lists(points_heating:list,
                                           points_cooling:list)->Tuple[list,list,list,list,list,list,list,list]:
    extend_environment = [
        get_parameter_option("temperature_control_curve", "plot_temperature_environment_min"),
        get_parameter_option("temperature_control_curve", "plot_temperature_environment_max")
    ]
    default_range_environment = [
        get_parameter_option("temperature_control_curve", "plot_temperature_environment_default_min"),
        get_parameter_option("temperature_control_curve", "plot_temperature_environment_default_max")
    ]
    default_range_vehicle = [
        get_parameter_option("temperature_control_curve", "plot_temperature_vehicle_default_min"),
        get_parameter_option("temperature_control_curve", "plot_temperature_vehicle_default_max")
    ]
    range_extend = get_parameter_option("temperature_control_curve", "plot_temperature_range_extend")
    undefined_vehicle_temperature_range = [
        get_parameter_option("temperature_control_curve", "plot_temperature_vehicle_heating_undefined"),
        get_parameter_option("temperature_control_curve", "plot_temperature_vehicle_cooling_undefined")
    ]

    # extract points

    heating_temperature_environment = []
    heating_temperature_vehicle = []
    for i in range(len(points_heating)):
        heating_temperature_environment.append(points_heating[i][0])
        heating_temperature_vehicle.append(points_heating[i][1])

    cooling_temperature_environment = []
    cooling_temperature_vehicle = []
    for i in range(len(points_cooling)):
        cooling_temperature_environment.append(points_cooling[i][0])
        cooling_temperature_vehicle.append(points_cooling[i][1])

    # range

    temperature_environment_min = default_range_environment[0]
    temperature_environment_max = default_range_environment[1]
    if len(heating_temperature_environment) > 0 and len(cooling_temperature_environment) > 0:
        temperature_environment_min = min(
            min(heating_temperature_environment, cooling_temperature_environment)) - range_extend
        temperature_environment_max = max(
            max(heating_temperature_environment, cooling_temperature_environment)) + range_extend
    elif len(heating_temperature_environment) > 0:
        temperature_environment_min = min(heating_temperature_environment) - range_extend
        temperature_environment_max = max(heating_temperature_environment) + range_extend
    elif len(cooling_temperature_environment) > 0:
        temperature_environment_min = min(cooling_temperature_environment) - range_extend
        temperature_environment_max = max(cooling_temperature_environment) + range_extend

    temperature_vehicle_min = default_range_vehicle[0]
    temperature_vehicle_max = default_range_vehicle[1]
    if len(heating_temperature_vehicle) > 0 and len(cooling_temperature_vehicle) > 0:
        temperature_vehicle_min = min(
            min(heating_temperature_vehicle, cooling_temperature_vehicle)) - range_extend
        temperature_vehicle_max = max(
            max(heating_temperature_vehicle, cooling_temperature_vehicle)) + range_extend
    elif len(heating_temperature_vehicle) > 0:
        temperature_vehicle_min = min(heating_temperature_vehicle) - range_extend
        temperature_vehicle_max = max(heating_temperature_vehicle) + range_extend
    elif len(cooling_temperature_vehicle) > 0:
        temperature_vehicle_min = min(cooling_temperature_vehicle) - range_extend
        temperature_vehicle_max = max(cooling_temperature_vehicle) + range_extend

    if temperature_environment_min > default_range_environment[0]:
        temperature_environment_min = default_range_environment[0]
    if temperature_environment_max < default_range_environment[1]:
        temperature_environment_max = default_range_environment[1]

    if temperature_vehicle_min > default_range_vehicle[0]:
        temperature_vehicle_min = default_range_vehicle[0]
    if temperature_vehicle_max < default_range_vehicle[1]:
        temperature_vehicle_max = default_range_vehicle[1]

    range_environment = [temperature_environment_min, temperature_environment_max]
    range_vehicle = [temperature_vehicle_min, temperature_vehicle_max]

    # complete segments and extend environment

    temperature_environment_breaks, temperature_vehicle_heating, temperature_vehicle_cooling = (
        extend_temperature_curve(points_heating, points_cooling))

    if len(temperature_environment_breaks) == 0:
        return (heating_temperature_environment, heating_temperature_vehicle,
                cooling_temperature_environment, cooling_temperature_vehicle,
                [], [], range_environment, range_vehicle)

    if extend_environment[0] < temperature_environment_breaks[0]:
        temperature_environment_breaks.insert(0, extend_environment[0])
        if len(temperature_vehicle_heating) > 0:
            temperature_vehicle_heating.insert(0, temperature_vehicle_heating[0])
        if len(temperature_vehicle_cooling) > 0:
            temperature_vehicle_cooling.insert(0, temperature_vehicle_cooling[0])
    if extend_environment[1] > temperature_environment_breaks[-1]:
        temperature_environment_breaks.append(extend_environment[1])
        if len(temperature_vehicle_heating) > 0:
            temperature_vehicle_heating.append(temperature_vehicle_heating[-1])
        if len(temperature_vehicle_cooling) > 0:
            temperature_vehicle_cooling.append(temperature_vehicle_cooling[-1])

    temperature_environment_breaks_united = np.concatenate((temperature_environment_breaks,
                                                            temperature_environment_breaks[::-1]))
    temperature_vehicle = np.concatenate((temperature_vehicle_heating, temperature_vehicle_cooling[::-1]))

    if len(temperature_vehicle_heating) == 0:
        temperature_environment_breaks_united = np.concatenate(([temperature_environment_min,
                                                                 temperature_environment_max],
                                                                temperature_environment_breaks_united))
        temperature_vehicle = np.concatenate(([undefined_vehicle_temperature_range[0],
                                               undefined_vehicle_temperature_range[0]], temperature_vehicle))
    if len(temperature_vehicle_cooling) == 0:
        temperature_environment_breaks_united = np.concatenate((temperature_environment_breaks_united,
                                                                [temperature_environment_max,
                                                                 temperature_environment_min]))
        temperature_vehicle = np.concatenate((temperature_vehicle,
                                              [undefined_vehicle_temperature_range[1],
                                               undefined_vehicle_temperature_range[1]]))

    return (heating_temperature_environment, heating_temperature_vehicle,
            cooling_temperature_environment, cooling_temperature_vehicle,
            temperature_environment_breaks_united, temperature_vehicle,
            range_environment, range_vehicle)



def add_point_to_temporary_temperature_curve(points_heating:list, points_cooling:list, heating:bool,
                                             temperature_environment:float, temperature_vehicle:float)->None:

    # check point existence

    if heating:
        points = copy.deepcopy(points_heating)
    else:
        points = copy.deepcopy(points_cooling)

    for i in range(len(points)):
        if points[i][0] == temperature_environment:
            raise ValueError(f"Point with environmental temperature {temperature_environment}°C already exists.")

    index = 0
    if len(points) == 0:
        index = 0
    elif points[0][0] > temperature_environment:
        index = 0
    elif points[-1][0] < temperature_environment:
        index = len(points)
    else:
        for i in range(len(points)):
            if temperature_environment < points[i][0]:
                index = i
                break

    # check overlap existence

    points.insert(index, [temperature_environment, temperature_vehicle])

    validity = None
    if heating:
        validity = is_temperature_curve_valid(points, points_cooling)
    else:
        validity = is_temperature_curve_valid(points_heating, points)

    if not validity:
        raise ValueError("Heating and cooling curve must not overlap "
                         "and vehicle temperature for heating mus be below cooling temperature for each environment temperature.")

    # add point to actual list

    if heating:
        points_heating.insert(index, [temperature_environment, temperature_vehicle])
    else:
        points_cooling.insert(index, [temperature_environment, temperature_vehicle])



def update_point_in_temporary_temperature_curve(points_heating:list, points_cooling:list, heating:bool, index:int,
                                                temperature_environment:float, temperature_vehicle:float)->None:

    # check overlap existence

    if heating:
        points = copy.deepcopy(points_heating)
    else:
        points = copy.deepcopy(points_cooling)
    points[index][0] = temperature_environment
    points[index][1] = temperature_vehicle

    validity = None
    if heating:
        validity = is_temperature_curve_valid(points, points_cooling)
    else:
        validity = is_temperature_curve_valid(points_heating, points)

    if not validity:
        raise ValueError("Heating and cooling curve must not overlap "
                         "and vehicle temperature for heating mus be below cooling temperature for each environment temperature.")

    # update point

    if heating:
        points_heating[index][0] = temperature_environment
        points_heating[index][1] = temperature_vehicle
    else:
        points_cooling[index][0] = temperature_environment
        points_cooling[index][1] = temperature_vehicle



def remove_point_from_temporary_temperature_curve(points_heating:list, points_cooling:list, heating:bool, index:int)->None:

    # check overlap existence

    if heating:
        points = copy.deepcopy(points_heating)
    else:
        points = copy.deepcopy(points_cooling)
    points.pop(index)

    validity = None
    if heating:
        validity = is_temperature_curve_valid(points, points_cooling)
    else:
        validity = is_temperature_curve_valid(points_heating, points)

    if not validity:
        raise ValueError("Heating and cooling curve must not overlap "
                         "and vehicle temperature for heating mus be below cooling temperature for each environment temperature.")

    # remove point

    if heating:
        points_heating.pop(index)
    else:
        points_cooling.pop(index)



def register_temperature_curve(session_state:dict, name:str)->None:
    if name == "":
        raise ValueError("Name cannot be empty.")
    elif name in session_state["specification"]["temperature_control_curves"].keys():
        raise ValueError("Name already exists. Please choose another name.")

    session_state["specification"]["temperature_control_curves"][name] = {
        "heating": copy.deepcopy(session_state["tmp"]["temperature_curve_editor"]["heating"]),
        "cooling": copy.deepcopy(session_state["tmp"]["temperature_curve_editor"]["cooling"])
    }

    sort_dict(session_state["specification"]["temperature_control_curves"])

    session_state["flag_input_changed"] = True



def update_temperature_curve(session_state:dict, name:str)->None:
    session_state["specification"]["temperature_control_curves"][name] = {
        "heating": copy.deepcopy(session_state["tmp"]["temperature_curve_editor"]["heating"]),
        "cooling": copy.deepcopy(session_state["tmp"]["temperature_curve_editor"]["cooling"])
    }

    session_state["flag_input_changed"] = True



def remove_temperature_curve(session_state:dict, name:str)->None:
    session_state["specification"]["temperature_control_curves"].pop(name)

    sort_dict(session_state["specification"]["temperature_control_curves"])

    # propagate remove through vehicles and operation schedules
    for vehicle_name, vehicle_data in session_state["specification"]["vehicles"].items():
        if vehicle_data["temperature_control_curve"] == name:
            vehicle_data["temperature_control_curve"] = None

    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["parameter"] == "temperature_control_curve" and name in alternative["values"]:
            alternative["values"].remove(name)

    session_state["flag_input_changed"] = True




def remove_all_temperature_curves(session_state:dict)->None:
    for name in session_state["specification"]["temperature_control_curves"].keys():
        remove_temperature_curve(session_state, name)



def get_registered_default_temperature_curves(session_state:dict)->list:
    default_curves = get_defaults("temperature_control_curves")

    registered_curves = []
    for key in session_state["specification"]["temperature_control_curves"].keys():
        if key in default_curves.keys():
            registered_curves.append(key)

    return registered_curves



def load_default_temperature_curves(session_state:dict, overwrite:bool=False)->None:
    default_curves = get_defaults("temperature_control_curves")

    for key, value in default_curves.items():
        if key not in session_state["specification"]["temperature_control_curves"].keys() or overwrite:
            session_state["specification"]["temperature_control_curves"][key] = copy.deepcopy(value)

    sort_dict(session_state["specification"]["temperature_control_curves"])

    session_state["flag_input_changed"] = True



def rename_temperature_curve(session_state:dict, old_name:str, new_name:str)->None:
    if new_name == old_name:
        return

    if new_name == "":
        raise ValueError("Name cannot be empty.")
    elif new_name in session_state["specification"]["temperature_control_curves"].keys():
        raise ValueError("Name already exists. Please choose another name.")
    else:
        curve_data = copy.deepcopy(session_state["specification"]["temperature_control_curves"][old_name])
        session_state["specification"]["temperature_control_curves"].pop(old_name)
        session_state["specification"]["temperature_control_curves"][new_name] = curve_data

    sort_dict(session_state["specification"]["temperature_control_curves"])

    # propagate rename through vehicles and operation schedules
    for vehicle_name, vehicle_data in session_state["specification"]["vehicles"].items():
        if vehicle_data["temperature_control_curve"] == old_name:
            vehicle_data["temperature_control_curve"] = new_name

    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["parameter"] == "temperature_control_curve" and old_name in alternative["values"]:
            alternative["values"].remove(old_name)
            alternative["values"].append(new_name)
            alternative["values"].sort()

    session_state["flag_input_changed"] = True

    reload_vehicle_version_and_scenario_data(session_state)



def load_registered_temperature_curve(session_state:dict, name:str, overwrite:bool=False)->None:

    initialize_temperature_curve_empty(session_state, overwrite=False)

    flag_load = False
    if not "name" in session_state["tmp"]["temperature_curve_editor"].keys():
        flag_load = True
    elif session_state["tmp"]["temperature_curve_editor"]["name"] != name or overwrite:
        flag_load = True

    if flag_load:
        session_state["tmp"]["temperature_curve_editor"] = {}
        session_state["tmp"]["temperature_curve_editor"]["name"] = name
        session_state["tmp"]["temperature_curve_editor"]["heating"] =(
            copy.deepcopy(session_state["specification"]["temperature_control_curves"][name]["heating"]))
        session_state["tmp"]["temperature_curve_editor"]["cooling"] = (
            copy.deepcopy(session_state["specification"]["temperature_control_curves"][name]["cooling"]))



def get_temperature_control_curve_names(session_state:dict)->list:
    return list(session_state["specification"]["temperature_control_curves"].keys())



# vehicles


def generate_dataframe_from_vehicles(session_state:dict)->pd.DataFrame:
    # generate data list
    df_data = []
    for name, data in session_state["specification"]["vehicles"].items():
        data_copy = copy.deepcopy(data)
        data_copy["name"] = name
        data_copy.pop("heating_cooling_devices")

        # format heating_cooling_devices
        hp_heating_power = 0
        hp_cooling_power = 0
        for hp in data["heating_cooling_devices"]["heat_pumps"]:
            if hp["heating"]:
                hp_heating_power += hp["electric_power_max"]
            if hp["cooling"]:
                hp_cooling_power += hp["electric_power_max"]

        device_list = []
        if data["heating_cooling_devices"]["resistive_heating_power_max"] is not None:
            if data["heating_cooling_devices"]["resistive_heating_power_max"] > 0:
                power = np.round(data["heating_cooling_devices"]["resistive_heating_power_max"],1)
                device_list.append(f"resistive heating: {power}")
        if hp_heating_power > 0:
            device_list.append(f"heat pump heating: {np.round(hp_heating_power,1)}")
        if hp_cooling_power > 0:
            device_list.append(f"heat pump cooling: {np.round(hp_cooling_power,1)}")

        if len(device_list) == 0:
            data_copy["heating_cooling_devices"] = None
        else:
            device_str = ", ".join(device_list)
            data_copy["heating_cooling_devices"] = device_str

        df_data.append(data_copy)

    default_name, default_data = get_defaults("vehicle")
    column_names = list(default_data.keys())
    column_names.insert(0, "name")

    # create dataframe
    df = pd.DataFrame(df_data, index=list(session_state["specification"]["vehicles"].keys()), columns=column_names)
    df.set_index("name", inplace=True)

    return df



def update_vehicle_specification(session_state:dict, df_updated:pd.DataFrame)->None:
    for name, data in session_state["specification"]["vehicles"].items():
        for key in data.keys():
            if not key in ["name", "heating_cooling_devices"]:
                value = df_updated.loc[name, key]
                if isinstance(value, (int, float)) and np.isnan(value):
                    value = None
                value_old = session_state["specification"]["vehicles"][name][key]
                session_state["specification"]["vehicles"][name][key] = copy.copy(value)

                if value_old != value:
                    #print("key", key, "changed from", value_old, "to", value)
                    session_state["flag_input_changed"] = True

    # update scenario values
    reload_vehicle_version_and_scenario_data(session_state)



def add_vehicle(session_state:dict, name:str, init_with_default_parameters:bool=False)->None:
    if name == "":
        raise ValueError("Name cannot be empty.")
    elif name in session_state["specification"]["vehicles"].keys():
        raise ValueError("Name already exists. Please choose another name.")

    if init_with_default_parameters:
        default_vehicle_name, default_vehicle_data = get_defaults("vehicle")
        data = copy.deepcopy(default_vehicle_data)

        control_curve_name = default_vehicle_data["temperature_control_curve"]
        if control_curve_name not in session_state["specification"]["temperature_control_curves"].keys():
            default_control_curve = get_defaults("temperature_control_curves")[control_curve_name]
            session_state["specification"]["temperature_control_curves"][control_curve_name] = (
                copy.deepcopy(default_control_curve))
    else:
        data = {
            "length": None,
            "width": None,
            "height": None,
            "area_windows_front": None,
            "area_windows_side": None,
            "door_height": None,
            "door_width_total": None,
            "time_fraction_door_open": None,
            "heat_transfer_coefficient_chassis": None,
            "cabin_absorptivity": None,
            "window_transmissivity": None,
            "fraction_obstruction_roof": None,
            "fraction_obstruction_floor": None,
            "volume_flow_rate_ventilation": None,
            "heating_power_auxiliary": None,
            "temperature_control_curve": None,
            "heating_cooling_devices": {
                "resistive_heating_power_max": None,
                "heat_pumps": {}
            }
        }
    session_state["specification"]["vehicles"][name] = data

    sort_dict(session_state["specification"]["vehicles"])

    session_state["flag_input_changed"] = True



def set_default_parameters_vehicle(session_state:dict, name:str, overwrite:bool=False)->None:
    # load default data
    default_data = get_defaults("vehicle")[1]

    # set parameters to default values
    for key in default_data.keys():
        if session_state["specification"]["vehicles"][name][key] is None or overwrite:
            if key != "heating_cooling_devices":
                session_state["specification"]["vehicles"][name][key] = default_data[key]

    if session_state["specification"]["vehicles"][name]["heating_cooling_devices"]["resistive_heating_power_max"] is None or overwrite:
        session_state["specification"]["vehicles"][name]["heating_cooling_devices"]["resistive_heating_power_max"] =(
            default_data)["heating_cooling_devices"]["resistive_heating_power_max"]

    if len(session_state["specification"]["vehicles"][name]["heating_cooling_devices"]["heat_pumps"]) == 0 or overwrite:
        session_state["specification"]["vehicles"][name]["heating_cooling_devices"]["heat_pumps"] = copy.deepcopy(
            default_data["heating_cooling_devices"]["heat_pumps"])

    session_state["flag_input_changed"] = True



def set_default_parameters_all_vehicles(session_state:dict, overwrite:bool=False)->None:
    for name in session_state["specification"]["vehicles"].keys():
        set_default_parameters_vehicle(session_state, name, overwrite=overwrite)



def rename_vehicle(session_state:dict, old_name:str, new_name:str)->None:
    if new_name == old_name:
        return

    if new_name == "":
        raise ValueError("Name cannot be empty.")
    elif new_name in session_state["specification"]["vehicles"].keys():
        raise ValueError("Name already exists. Please choose another name.")
    else:
        vehicle_data = copy.deepcopy(session_state["specification"]["vehicles"][old_name])
        session_state["specification"]["vehicles"].pop(old_name)
        session_state["specification"]["vehicles"][new_name] = vehicle_data

    sort_dict(session_state["specification"]["vehicles"])

    # propagate rename through parameter alternatives and operation schedules
    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["vehicle"] == old_name:
            alternative["vehicle"] = new_name

    sort_dict_list(session_state["specification"]["vehicle_parameter_alternatives"],
                   ["vehicle", "parameter"])

    for name, operation_schedule in session_state["specification"]["operation_schedules"].items():
        if old_name in operation_schedule["vehicles_in_operation"]:
            number = operation_schedule["vehicles_in_operation"][old_name]
            operation_schedule["vehicles_in_operation"].pop(old_name)
            operation_schedule["vehicles_in_operation"][new_name] = number
            sort_dict(operation_schedule["vehicles_in_operation"])

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



def generate_dataframe_from_vehicle_heat_pumps(session_state:dict, vehicle_name:str)->pd.DataFrame:
    # generate data list
    df_data = []
    for hp in session_state["specification"]["vehicles"][vehicle_name]["heating_cooling_devices"]["heat_pumps"]:
        hp_copy = copy.deepcopy(hp)
        df_data.append(hp_copy)

    # create dataframe
    df = pd.DataFrame(
        df_data,
        columns=["name", "electric_power_max", "exergy_efficiency", "heating", "cooling"]
    )
    #df.set_index("name", inplace=True)

    return df



def update_vehicle_heating_cooling_devices(session_state:dict, vehicle_name:str, resistive_heating_power:float,
                                           df_original:pd.DataFrame, state_update:dict)->None:

    # update dataframe
    df_updated = copy.deepcopy(df_original)

    # updated rows
    for index_number, updates in state_update["edited_rows"].items():
        for key, value in updates.items():
            df_updated.loc[df_original.index[index_number], key] = value

    # deleted rows
    for index_number in state_update["deleted_rows"]:
        df_updated.drop(df_updated.index[index_number], inplace=True)

    # added rows
    for added_row_dict in state_update["added_rows"]:
        if "name" not in added_row_dict.keys():
            raise ValueError("Heat pump name cannot be empty.")
        else:
            data_dict = {
                "name": None,
                "electric_power_max": None,
                "exergy_efficiency": None,
                "heating": False,
                "cooling": False
            }
            for key, value in added_row_dict.items():
                if key != "_index":
                    data_dict[key] = value
            # add row to dataframe
            row = pd.DataFrame(data_dict, index=[0])
            df_updated = pd.concat([df_updated, row], ignore_index=True)


    # check whether all heat pump names are unique
    for name in df_updated.index:
        if name == "" or name is None:
            raise ValueError("Heat pump name cannot be empty.")
        occurrences = len([n for n in df_updated["name"].tolist() if n == name])
        if occurrences > 1:
            raise ValueError(f"Heat pump names must be unique. Name '{name}' is used more than once.")

    # update resistive heating power
    session_state["specification"]["vehicles"][vehicle_name]["heating_cooling_devices"]["resistive_heating_power_max"] = resistive_heating_power

    # update heat pumps
    heat_pumps = []
    for name, data in df_updated.iterrows():
        heat_pumps.append({
            "name": data["name"],
            "electric_power_max": data["electric_power_max"],
            "exergy_efficiency": data["exergy_efficiency"],
            "heating": data["heating"],
            "cooling": data["cooling"]
        })

    sort_dict_list(heat_pumps, ["name"])

    session_state["specification"]["vehicles"][vehicle_name]["heating_cooling_devices"]["heat_pumps"] = copy.deepcopy(heat_pumps)

    session_state["flag_input_changed"] = True

    reload_vehicle_version_and_scenario_data(session_state)



def remove_vehicle(session_state:dict, name:str)->None:
    session_state["specification"]["vehicles"].pop(name)

    # propagate remove through parameter alternatives and operation schedules
    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["vehicle"] == name:
            session_state["specification"]["vehicle_parameter_alternatives"].remove(alternative)

    for name, operation_schedule in session_state["specification"]["operation_schedules"].items():
        if name in operation_schedule["vehicles_in_operation"]:
            operation_schedule["vehicles_in_operation"].remove(name)
            sort_dict(operation_schedule["vehicles_in_operation"])

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



def remove_all_vehicles(session_state:dict)->None:
    for name in session_state["specification"]["vehicles"].keys():
        remove_vehicle(session_state, name)



# vehicle parameter alternatives

def get_parameter_alternative_values(session_state:dict, vehicle:str, parameter:str,
                                     hide_default_value:bool=False):

    values = []
    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["vehicle"] == vehicle and alternative["parameter"] == parameter:
            values = copy.deepcopy(alternative["values"])

    if hide_default_value:
        default_value = session_state["specification"]["vehicles"][vehicle][parameter]
        if default_value in values:
            values.remove(default_value)

    return values



def generate_dataframe_from_vehicle_parameter_alternatives(session_state:dict)->pd.DataFrame:
    # generate data list
    df_data = []
    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        values_alternatives = get_parameter_alternative_values(
            session_state, alternative["vehicle"], alternative["parameter"],
            hide_default_value=True
        )
        values_alternatives_str = []
        if len(values_alternatives) == 0:
            values_alternatives_str = None
        else:
            for value in values_alternatives:
                values_alternatives_str.append(str(value))

        df_data.append({
            "vehicle": alternative["vehicle"],
            "parameter": get_parameter_option("parameters_vehicle", alternative["parameter"]),
            "value_default": session_state["specification"]["vehicles"][alternative["vehicle"]][alternative["parameter"]],
            "values_alternative": values_alternatives_str
        })

    column_names = ["vehicle", "parameter", "value_default", "values_alternative"]

    # create dataframe
    df = pd.DataFrame(df_data, columns=column_names)

    return df



def generate_parameter_alternative_value_edit_str(session_state:dict, vehicle:str, parameter:str)->str:
    values = get_parameter_alternative_values(session_state, vehicle, parameter)
    value_str = None
    if not (len(values) == 0 or values is None):
        if not values[0] is None:
            value_str = ", ".join([str(value) for value in values])
    return value_str



def convert_display_name_to_parameter_name(display_name:str)->str:
    for key, value in DATA_PARAMETER_OPTIONS["parameters_vehicle"].items():
        if value == display_name:
            return key
    return None



def get_vehicle_parameter_boundary_precision(parameter:str)->Tuple[float,float,int]:
    value_min = None
    value_max = None
    precision = None
    if parameter == "length":
        value_min = get_parameter_option("vehicle", "length_min")
        value_max = get_parameter_option("vehicle", "length_max")
        precision = get_parameter_decimal_step_precision("vehicle", "geometry_step")
    elif parameter == "width":
        value_min = get_parameter_option("vehicle", "width_min")
        value_max = get_parameter_option("vehicle", "width_max")
        precision = get_parameter_decimal_step_precision("vehicle", "geometry_step")
    elif parameter == "height":
        value_min = get_parameter_option("vehicle", "height_min")
        value_max = get_parameter_option("vehicle", "height_max")
        precision = get_parameter_decimal_step_precision("vehicle", "geometry_step")
    elif parameter == "door_height":
        value_min = get_parameter_option("vehicle", "door_height_min")
        value_max = get_parameter_option("vehicle", "door_height_max")
        precision = get_parameter_decimal_step_precision("vehicle", "geometry_step")
    elif parameter == "door_width_total":
        value_min = get_parameter_option("vehicle", "door_width_total_min")
        value_max = get_parameter_option("vehicle", "door_width_total_max")
        precision = get_parameter_decimal_step_precision("vehicle", "geometry_step")
    elif parameter == "area_windows_front":
        value_min = get_parameter_option("vehicle", "area_windows_front_min")
        value_max = get_parameter_option("vehicle", "area_windows_front_max")
        precision = get_parameter_decimal_step_precision("vehicle", "geometry_step")
    elif parameter == "area_windows_side":
        value_min = get_parameter_option("vehicle", "area_windows_side_min")
        value_max = get_parameter_option("vehicle", "area_windows_side_max")
        precision = get_parameter_decimal_step_precision("vehicle", "geometry_step")
    elif parameter == "time_fraction_door_open":
        value_min = get_parameter_option("vehicle", "fraction_min")
        value_max = get_parameter_option("vehicle", "fraction_max")
        precision = get_parameter_decimal_step_precision("vehicle", "fraction_step")
    elif parameter == "heat_transfer_coefficient_chassis":
        value_min = get_parameter_option("vehicle", "heat_transfer_coefficient_chassis_min")
        value_max = get_parameter_option("vehicle", "heat_transfer_coefficient_chassis_max")
        precision = get_parameter_decimal_step_precision("vehicle", "heat_transfer_coefficient_step")
    elif parameter == "cabin_absorptivity":
        value_min = get_parameter_option("vehicle", "cabin_absorptivity_min")
        value_max = get_parameter_option("vehicle", "cabin_absorptivity_max")
        precision = get_parameter_decimal_step_precision("vehicle", "fraction_step")
    elif parameter == "window_transmissivity":
        value_min = get_parameter_option("vehicle", "window_transmissivity_min")
        value_max = get_parameter_option("vehicle", "window_transmissivity_max")
        precision = get_parameter_decimal_step_precision("vehicle", "fraction_step")
    elif parameter == "fraction_obstruction_roof":
        value_min = get_parameter_option("vehicle", "fraction_obstruction_roof_min")
        value_max = get_parameter_option("vehicle", "fraction_obstruction_roof_max")
        precision = get_parameter_decimal_step_precision("vehicle", "fraction_step")
    elif parameter == "fraction_obstruction_floor":
        value_min = get_parameter_option("vehicle", "fraction_obstruction_floor_min")
        value_max = get_parameter_option("vehicle", "fraction_obstruction_floor_max")
        precision = get_parameter_decimal_step_precision("vehicle", "fraction_step")
    elif parameter == "volume_flow_rate_ventilation":
        value_min = get_parameter_option("vehicle", "volume_flow_rate_ventilation_min")
        value_max = get_parameter_option("vehicle", "volume_flow_rate_ventilation_max")
        precision = get_parameter_decimal_step_precision("vehicle", "volume_flow_rate_step")
    elif parameter == "heating_power_auxiliary":
        value_min = get_parameter_option("vehicle", "heating_power_auxiliary_min")
        value_max = get_parameter_option("vehicle", "heating_power_auxiliary_max")
        precision = get_parameter_decimal_step_precision("vehicle", "power_step")

    return value_min, value_max, precision



def update_vehicle_parameter_alternative_float(session_state:dict, vehicle:str, parameter:str, value_str:str)->None:
    value_list = []
    for value in value_str.split(","):
        value_min, value_max, precision = get_vehicle_parameter_boundary_precision(parameter)

        try:
            value_float = float(value)
        except ValueError:
            raise ValueError(f"Value \'{value}\' is not a valid float number.")

        if value_float < value_min or value_float > value_max:
            parameter_display_name = get_parameter_option("parameters_vehicle", parameter)
            raise ValueError(f"Value \'{value}\' is out of bounds for parameter \'{parameter_display_name}\' "
                             f"(allowed range: {value_min} to {value_max}).")

        value_list.append(round(value_float, precision))

    value_list = list(set(value_list))
    value_list.sort()

    session_state["flag_input_changed"] = True

    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["vehicle"] == vehicle and alternative["parameter"] == parameter:
            alternative["values"] = value_list
            break

    reload_vehicle_version_and_scenario_data(session_state)



def update_vehicle_parameter_alternative_temperature_curve(session_state:dict, vehicle:str, parameter:str, value_list:list)->None:
    value_list = list(set(value_list))
    value_list.sort()

    session_state["flag_input_changed"] = True

    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["vehicle"] == vehicle and alternative["parameter"] == parameter:
            alternative["values"] = value_list
            break

    reload_vehicle_version_and_scenario_data(session_state)



def add_vehicle_parameter_alternative(session_state:dict, vehicle:str, parameter_display_name:str)->None:
    parameter = convert_display_name_to_parameter_name(parameter_display_name)

    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["vehicle"] == vehicle and alternative["parameter"] == parameter:
            raise ValueError(f"Parameter alternative for vehicle \'{vehicle}\' and parameter  \'{parameter_display_name}\' already exists. "
                             f"Please edit the existing alternative.")

    session_state["specification"]["vehicle_parameter_alternatives"].append({
        "vehicle": vehicle,
        "parameter": convert_display_name_to_parameter_name(parameter_display_name),
        "values": [session_state["specification"]["vehicles"][vehicle][parameter]]
    })

    sort_dict_list(session_state["specification"]["vehicle_parameter_alternatives"], ["vehicle", "parameter"])

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



def get_registered_default_vehicle_parameter_alternatives(session_state:dict)->Tuple[str,str]:
    default_vehicle_name = get_defaults("vehicle")[0]
    default_alternative_parameter = get_defaults("vehicle_parameter_alternative")["parameter"]

    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["vehicle"] == default_vehicle_name and alternative["parameter"] == default_alternative_parameter:
            return default_vehicle_name, default_alternative_parameter

    return default_vehicle_name, None



def complement_default_vehicle_parameter_alternative(session_state:dict, vehicle:str, parameter:str)->None:
    if vehicle not in session_state["specification"]["vehicles"].keys():
        add_vehicle(session_state, vehicle, init_with_default_parameters=True)

    if parameter == "temperature_control_curve":
        load_default_temperature_curves(session_state, overwrite=False)



def load_default_vehicle_parameter_alternative(session_state:dict, append:bool=False, overwrite:bool=False)->None:
    default_alternative = get_defaults("vehicle_parameter_alternative")
    default_vehicle_name = get_defaults("vehicle")[0]

    exists_index = 0
    flag_exists = False
    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["vehicle"] == default_vehicle_name and alternative["parameter"] == default_alternative["parameter"]:
            if overwrite or append:
                flag_exists = True
                break
            else:
                return
        exists_index += 1

    if flag_exists:
        if overwrite:
            alternative = copy.deepcopy(default_alternative)
            alternative["vehicle"] = default_vehicle_name
            session_state["specification"]["vehicle_parameter_alternatives"][exists_index] = alternative
        else: # append
            for value in default_alternative["values"]:
                if value not in session_state["specification"]["vehicle_parameter_alternatives"][exists_index]["values"]:
                    session_state["specification"]["vehicle_parameter_alternatives"][exists_index]["values"].append(value)
            session_state["specification"]["vehicle_parameter_alternatives"][exists_index]["values"].sort()
    else:
        alternative = copy.deepcopy(default_alternative)
        alternative["vehicle"] = default_vehicle_name
        session_state["specification"]["vehicle_parameter_alternatives"].append(alternative)

    complement_default_vehicle_parameter_alternative(session_state, default_vehicle_name, default_alternative["parameter"])

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



def remove_vehicle_parameter_alternative(session_state:dict, vehicle:str, parameter:str)->None:
    index = 0
    for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
        if alternative["vehicle"] == vehicle and alternative["parameter"] == parameter:
            break
        index += 1

    session_state["specification"]["vehicle_parameter_alternatives"].pop(index)

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



def remove_all_vehicle_parameter_alternatives(session_state:dict)->None:
    session_state["specification"]["vehicle_parameter_alternatives"] = []

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



# operation schedules


def generate_dataframe_from_operation_schedules(session_state:dict)->pd.DataFrame:
    # generate data list
    df_data = []
    for name, data in session_state["specification"]["operation_schedules"].items():
        data_copy = copy.deepcopy(data)
        data_copy["name"] = name
        data_copy.pop("vehicles_in_operation")

        vehicle_list = []
        for name, value in data["vehicles_in_operation"].items():
            if value is not None and value > 0:
                vehicle_list.append(f"{name}: {value}")

        if len(vehicle_list) == 0:
            data_copy["vehicles_in_operation"] = None
        else:
            device_str = ", ".join(vehicle_list)
            data_copy["vehicles_in_operation"] = device_str

        df_data.append(data_copy)

    # convert dates and times
    for entry in df_data:
        entry["date_begin"] = convert_str_to_date(entry["date_begin"])
        entry["date_end"] = convert_str_to_date(entry["date_end"])
        entry["time_begin"] = convert_str_to_time(entry["time_begin"])
        entry["time_end"] = convert_str_to_time(entry["time_end"])

    default_schedule_name, default_schedule_data = get_defaults("operation_schedule")
    column_names = list(default_schedule_data.keys())
    column_names.insert(0, "name")

    # create dataframe
    df = pd.DataFrame(df_data, index=list(session_state["specification"]["operation_schedules"].keys()),
                      columns=column_names)
    df.set_index("name", inplace=True)

    return df



def update_operation_schedule_specification(session_state:dict, df_updated:pd.DataFrame)->None:
    for name, data in session_state["specification"]["operation_schedules"].items():
        for key in data.keys():
            if not key in ["name", "vehicles_in_operation"]:
                value = df_updated.loc[name, key]
                if isinstance(value, (int, float)) and np.isnan(value):
                    value = None
                value_old = session_state["specification"]["operation_schedules"][name][key]
                if key in ["date_begin", "date_end"]:
                    value = convert_date_to_str(value)
                    session_state["specification"]["operation_schedules"][name][key] = copy.copy(value)
                elif key in ["time_begin", "time_end"]:
                    value = convert_time_to_str(value)
                    session_state["specification"]["operation_schedules"][name][key] = copy.copy(value)
                else:
                    session_state["specification"]["operation_schedules"][name][key] = copy.copy(value)

                if value_old != value:
                    session_state["flag_input_changed"] = True
                    pass



def complement_default_operation_schedule(session_state:dict, vehicle:str)->None:
    if vehicle not in session_state["specification"]["vehicles"].keys():
        add_vehicle(session_state, vehicle, init_with_default_parameters=True)



def add_operation_schedule(session_state:dict, name:str, init_with_default_parameters:bool=False)->None:
    if name == "":
        raise ValueError("Name cannot be empty.")
    elif name in session_state["specification"]["operation_schedules"].keys():
        raise ValueError("Name already exists. Please choose another name.")

    if init_with_default_parameters:
        default_schedule_name, default_schedule_data = get_defaults("operation_schedule")
        data = copy.deepcopy(default_schedule_data)

        default_vehicle_name = get_defaults("vehicle")[0]
        complement_default_operation_schedule(session_state, default_vehicle_name)
    else:
        data = {
            "location": None,
            "date_begin": None,
            "date_end": None,
            "time_begin": None,
            "time_end": None,
            "passenger_number": None,
            "obstacle_distance": None,
            "obstacle_height": None,
            "cost_electricity": None,
            "vehicles_in_operation": {},
        }
    session_state["specification"]["operation_schedules"][name] = data

    sort_dict(session_state["specification"]["operation_schedules"])

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



def set_default_parameters_operation_schedule(session_state:dict, name:str, overwrite:bool=False)->None:
    # load default data
    default_data = get_defaults("operation_schedule")[1]

    # set parameters to default values
    for key in default_data.keys():
        if session_state["specification"]["operation_schedules"][name][key] is None or overwrite:
            session_state["specification"]["operation_schedules"][name][key] = default_data[key]

            default_vehicle_name = get_defaults("vehicle")[0]
            complement_default_operation_schedule(session_state, default_vehicle_name)

    session_state["flag_input_changed"] = True



def set_default_parameters_all_operation_schedules(session_state:dict, overwrite:bool=False)->None:
    for name in session_state["specification"]["operation_schedules"].keys():
        set_default_parameters_operation_schedule(session_state, name, overwrite=overwrite)



def rename_operation_schedule(session_state:dict, old_name:str, new_name:str)->None:
    if new_name == old_name:
        return

    if new_name == "":
        raise ValueError("Name cannot be empty.")
    elif new_name in session_state["specification"]["operation_schedules"].keys():
        raise ValueError("Name already exists. Please choose another name.")
    else:
        vehicle_data = copy.deepcopy(session_state["specification"]["operation_schedules"][old_name])
        session_state["specification"]["operation_schedules"].pop(old_name)
        session_state["specification"]["operation_schedules"][new_name] = vehicle_data

    sort_dict(session_state["specification"]["operation_schedules"])

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



def generate_dataframe_from_operation_schedule_vehicles(session_state:dict, schedule_name:str)->pd.DataFrame:
    # generate data list
    df_data = []
    for vehicle in session_state["specification"]["vehicles"].keys():
        number = 0
        if vehicle in session_state["specification"]["operation_schedules"][schedule_name]["vehicles_in_operation"].keys():
            number = session_state["specification"]["operation_schedules"][schedule_name]["vehicles_in_operation"][vehicle]
        df_data.append({
            "vehicle": vehicle,
            "number": number
        })

    sort_dict_list(df_data, ["vehicle"])

    # create dataframe
    df = pd.DataFrame(
        df_data,
        columns=["vehicle", "number"]
    )
    #df.set_index("name", inplace=True)

    return df



def update_operation_schedule_vehicles(session_state:dict, schedule_name:str,
                                       df_original:pd.DataFrame, state_update:dict)->None:

    # update dataframe
    df_updated = copy.deepcopy(df_original)

    # updated rows
    for index_number, updates in state_update["edited_rows"].items():
        for key, value in updates.items():
            df_updated.loc[df_original.index[index_number], key] = value

    # update heat pumps
    vehicles_in_operation = {}
    for name, data in df_updated.iterrows():
        vehicles_in_operation[data["vehicle"]] = data["number"]

    session_state["specification"]["operation_schedules"][schedule_name]["vehicles_in_operation"] = copy.deepcopy(vehicles_in_operation)

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



def remove_operation_schedule(session_state:dict, name:str)->None:
    session_state["specification"]["operation_schedules"].pop(name)

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



def remove_all_operation_schedules(session_state:dict)->None:
    session_state["specification"]["operation_schedules"] = {}

    session_state["flag_input_changed"] = True
    reload_vehicle_version_and_scenario_data(session_state)



# scenarios


def regenerate_vehicle_versions(session_state:dict):

    version_data = {}

    for vehicle_name, vehicle_data in session_state["specification"]["vehicles"].items():
        version_data[vehicle_name] = {
            "default": {
                "vehicle_data": copy.deepcopy(vehicle_data),
                "parameter_set": {}
            }
        }

        # create vehicle parameter sets
        vehicle_parameter_alternative_values = {}
        for alternative in session_state["specification"]["vehicle_parameter_alternatives"]:
            if alternative["vehicle"] == vehicle_name:
                vehicle_parameter_alternative_values[alternative["parameter"]] = copy.deepcopy(alternative["values"])

        if len(vehicle_parameter_alternative_values) > 0:
            parameters, values = zip(*vehicle_parameter_alternative_values.items())

            for parameter in parameters:
                version_data[vehicle_name]["default"]["parameter_set"][parameter] = vehicle_data[parameter]

            combinations = list(itertools.product(*values))
            alternative_number = 1
            for combination in combinations:
                # check whether combination is identical to default
                flag_identical = True
                for parameter, value in zip(parameters, combination):
                    if value != vehicle_data[parameter]:
                        flag_identical = False
                        break
                if not flag_identical:
                    vehicle_version = copy.deepcopy(vehicle_data)
                    parameter_set = {}
                    for parameter, value in zip(parameters, combination):
                        vehicle_version[parameter] = value
                        parameter_set[parameter] = value
                    version_name = "alternative_" + str(alternative_number)
                    version_data[vehicle_name][version_name] = {
                        "vehicle_data": copy.deepcopy(vehicle_version),
                        "parameter_set": copy.deepcopy(parameter_set)
                    }
                    alternative_number += 1

    session_state["specification"]["vehicle_versions"] = copy.deepcopy(version_data)



def regenerate_scenario_data(session_state:dict)->None:

    # generate scenario options
    session_state["specification"]["scenario_options"] = {}
    for operation_name, operation_data in session_state["specification"]["operation_schedules"].items():
        for vehicle_name, vehicle_number in operation_data["vehicles_in_operation"].items():
            if vehicle_number > 0:
                vehicle_versions = []
                for version_name, version_data in session_state["specification"]["vehicle_versions"][vehicle_name].items():
                    vehicle_versions.append(convert_dictionary_to_str(version_data["parameter_set"],
                                                                      keys_to_display_names=True))
                session_state["specification"]["scenario_options"][f"{operation_name} - {vehicle_name}"] = {
                    "description": f"For operation \'{operation_name}\' and vehicle \'{vehicle_name}\', "
                                   f"select the vehicle version according to its parameter set.",
                    "possible_values": copy.deepcopy(vehicle_versions)
                }

    # generate scenario data
    scenario_data_previous = copy.deepcopy(session_state["specification"]["scenarios"])
    session_state["specification"]["scenarios"] = {}

    for scenario_pre_name, scenario_pre_data in scenario_data_previous.items():
        scenario_data = {}
        for key, options in session_state["specification"]["scenario_options"].items():
            if key in scenario_pre_data.keys() and scenario_pre_data[key] in options["possible_values"]:
                scenario_data[key] = scenario_pre_data[key]
            else:
                scenario_data[key] = None
        session_state["specification"]["scenarios"][scenario_pre_name] = copy.deepcopy(scenario_data)



def reload_vehicle_version_and_scenario_data(session_state:dict)->None:
    regenerate_vehicle_versions(session_state)
    regenerate_scenario_data(session_state)



def generate_dataframe_from_scenarios(session_state:dict)->pd.DataFrame:

    data = []
    for scenario_name, scenario_data in session_state["specification"]["scenarios"].items():
        row_data = {"name": scenario_name}
        for key, value in scenario_data.items():
            row_data[key] = value
        data.append(copy.deepcopy(row_data))

    column_names = ["name"]
    for key, options in session_state["specification"]["scenario_options"].items():
        column_names.append(key)
    if len(column_names) == 1:
        column_names.append("no_option")
        for row in data:
            row["no_option"] = None

    df = pd.DataFrame(data, index=list(session_state["specification"]["scenarios"].keys()), columns=column_names)
    df.set_index("name", inplace=True)

    return df



def update_scenario_specification(session_state:dict, df_updated:pd.DataFrame)->None:
    for name, data in session_state["specification"]["scenarios"].items():
        for key in data.keys():
            if not key in ["name"]:
                value = df_updated.loc[name, key]
                if isinstance(value, (int, float)) and np.isnan(value):
                    value = None
                value_old = session_state["specification"]["scenarios"][name][key]
                session_state["specification"]["scenarios"][name][key] = copy.copy(value)

                if value_old != value:
                    session_state["flag_input_changed"] = True
                    pass
    """
    scenarios = {}
    for row in df_updated.iterrows():
        scenarios.append(copy.deepcopy(row[1].to_dict()))
    session_state["specification"]["scenarios"] = copy.deepcopy(scenarios)
    """



def add_scenario(session_state:dict, name:str)->None:
    if name == "":
        raise ValueError("Name cannot be empty.")
    elif name in session_state["specification"]["scenarios"].keys():
        raise ValueError("Name already exists. Please choose another name.")

    scenario_data = {}
    for key, options in session_state["specification"]["scenario_options"].items():
        scenario_data[key] = None

    session_state["specification"]["scenarios"][name] = copy.deepcopy(scenario_data)


    session_state["flag_input_changed"] = True



def rename_scenario(session_state:dict, old_name:str, new_name:str)->None:
    if new_name == old_name:
        return

    if new_name == "":
        raise ValueError("Name cannot be empty.")
    elif new_name in session_state["specification"]["scenarios"].keys():
        raise ValueError("Name already exists. Please choose another name.")
    else:
        scenario_data = copy.deepcopy(session_state["specification"]["scenarios"][old_name])
        session_state["specification"]["scenarios"].pop(old_name)
        session_state["specification"]["scenarios"][new_name] = scenario_data

    sort_dict(session_state["specification"]["scenarios"])

    session_state["flag_input_changed"] = True



def remove_scenario(session_state:dict, name:str)->None:
    session_state["specification"]["scenarios"].pop(name)

    if session_state["specification"]["scenario_reference"] == name:
        session_state["specification"]["scenario_reference"] = None

    session_state["flag_input_changed"] = True



def remove_all_scenarios(session_state:dict)->None:
    session_state["specification"]["scenarios"] = {}

    session_state["flag_input_changed"] = True



def set_reference_scenario(session_state:dict, name:str)->None:
    if session_state["specification"]["scenario_reference"] != name:
        session_state["flag_input_changed"] = True

    session_state["specification"]["scenario_reference"] = name



# results


def generate_location_data(specification:dict, nominatim_email:str, path_directory_raw_climate_data:str=None)->dict:
    location_data = {}
    for key, data in specification["operation_schedules"].items():
        if data["location"] is None:
            raise ValueError(f"Location for operation schedule \'{key}\' is not defined.")
        if data["location"] not in location_data.keys():
            location_data[data["location"]] = ldb.retrieve_location_data(data["location"],
                                                                         nominatim_email,
                                                                         path_directory_raw_climate_data)

    return location_data



def calculate_results(session_state:dict, path_directory_raw_climate_data:str=None)->None:
    session_state["flag_input_changed"] = False

    # reset result data
    session_state["results"] = {}

    # verify specification data

    for key_curve, data_curve in session_state["specification"]["temperature_control_curves"].items():
        if len(data_curve["heating"]) == 0:
            raise ValueError(f"For temperature control curve \'{key_curve}\', no heating temperatures were specified. "
                             f"Please complete the specification by adding at least one heating temperature point.")
        if len(data_curve["cooling"]) == 0:
            raise ValueError(
                f"For temperature control curve \'{key_curve}\', no cooling temperatures were specified. "
                f"Please complete the specification by adding at least one cooling temperature point.")

    if len(session_state["specification"]["vehicles"]) == 0:
        raise ValueError("No vehicles were specified. Please add at least one vehicle.")
    for key_vehicle, data_vehicle in session_state["specification"]["vehicles"].items():
        for key_parameter_name, data_parameter in data_vehicle.items():
            if key_parameter_name == "heating_cooling_devices":
                if data_parameter["resistive_heating_power_max"] is None:
                    parameter_name = get_parameter_option("parameters_vehicle", "resistive_heating_power_max")
                    raise ValueError(f"For vehicle \'{key_vehicle}\', parameter \'{parameter_name}\' is not defined. "
                                     f"Please complete the specification.")
                for data_device in data_parameter["heat_pumps"]:
                    if data_device["name"] is None:
                        raise ValueError(f"For vehicle \'{key_vehicle}\', parameter \'Name\' of at least one heat pump "
                                         "is not defined. Please complete the specification.")
                    for key_device_parameter, data_device_parameter in data_device.items():
                        if data_device_parameter is None:
                            heat_pump_name = data_device["name"]
                            raise ValueError(f"For vehicle \'{key_vehicle}\' and heat pump \'{heat_pump_name}\', "
                                             "at least one parameter is undefined. Please complete the specification.")
            else:
                if data_parameter is None:
                    parameter_name = get_parameter_option("parameters_vehicle", key_parameter_name)
                    raise ValueError(f"For vehicle \'{key_vehicle}\', parameter \'{parameter_name}\' is not defined. "
                                     f"Please complete the specification.")

    if len(session_state["specification"]["operation_schedules"]) == 0:
        raise ValueError("No operation schedules were specified. Please add at least one operation schedule.")
    for key_schedule, data_schedule in session_state["specification"]["operation_schedules"].items():
        for key_parameter, data_parameter in data_schedule.items():
            if not key_parameter == "vehicles_in_operation":
                if data_parameter is None:
                    parameter_name = get_parameter_option("parameters_operation_schedule", key_parameter)
                    raise ValueError(f"For operation schedule \'{key_schedule}\', parameter \'{parameter_name}\' "
                                     f"is not defined. Please complete the specification.")
        if len(data_schedule["vehicles_in_operation"]) == 0:
            raise ValueError(f"For operation schedule \'{key_schedule}\', no vehicles were specified. "
                             f"Please add at least one vehicle to the operation schedule.")

    for key_scenario, data_scenario in session_state["specification"]["scenarios"].items():
        for key_parameter, data_parameter in data_scenario.items():
            if data_parameter is None:
                raise ValueError(f"For scenario \'{key_scenario}\', parameter \'{key_parameter}\' is not defined. "
                                 f"Please complete the specification.")
    if len(session_state["specification"]["scenarios"]) > 0 and session_state["specification"]["scenario_reference"] is None:
        raise ValueError("No reference scenario was specified. Please select a reference scenario.")

    # location data
    location_data = generate_location_data(session_state["specification"], session_state["nominatim_email"],
                                           path_directory_raw_climate_data)
    session_state["location_data"] = location_data

    # run model
    vehicle_results, vehicle_operation_totals, scenario_totals, demand_not_satisfied_warning = md.simulate_system(
        session_state["specification"]["operation_schedules"],
        session_state["specification"]["vehicle_versions"],
        session_state["specification"]["temperature_control_curves"],
        session_state["location_data"],
        session_state["specification"]["scenarios"],
        session_state["specification"]["scenario_reference"]
    )

    # store results
    session_state["results"]["vehicles"] = vehicle_results
    session_state["results"]["vehicle_operation_totals"] = vehicle_operation_totals
    session_state["results"]["scenario_totals"] = scenario_totals
    session_state["results"]["warning"] = demand_not_satisfied_warning



def generate_dataframe_from_location_data(session_state:dict)->pd.DataFrame:
    data = []
    for location_input, location_data in session_state["location_data"].items():
        data.append({
            "location_input": location_input,
            "location_name": location_data["location_name"],
            "latitude": location_data["latitude"],
            "longitude": location_data["longitude"],
            "time_zone": location_data["time_zone"]
        })

    df = pd.DataFrame(data)

    return df



def scale_scenario_totals(df_unscaled:pd.DataFrame)->Tuple[pd.DataFrame,str]:

    max_energy = df_unscaled["electric_energy_scenario_total"].max()

    factor = None
    unit = None
    if max_energy < 1e3:
        factor = 1
        unit = "kWh"
    elif max_energy < 1e6:
        factor = 1e-3
        unit = "MWh"
    elif max_energy < 1e9:
        factor = 1e-6
        unit = "GWh"
    elif max_energy < 1e12:
        factor = 1e-9
        unit = "TWh"
    elif max_energy < 1e15:
        factor = 1e-12
        unit = "PWh"

    df_scaled = copy.deepcopy(df_unscaled)
    df_scaled["electric_energy_scenario_total"] = factor * df_scaled["electric_energy_scenario_total"]
    df_scaled["electric_energy_scenario_heating_total"] = factor * df_scaled["electric_energy_scenario_heating_total"]
    df_scaled["electric_energy_scenario_cooling_total"] = factor * df_scaled["electric_energy_scenario_cooling_total"]

    return df_scaled, unit



def get_hour_list(df_heat_flows:pd.DataFrame, month_name:str)->list:

    hours = df_heat_flows[df_heat_flows["month_name"] == month_name]["hour"].unique()
    hour_min = int(hours.min())
    hour_max = int(hours.max())

    hour_list = list(range(hour_min, hour_max + 1))

    return hour_list



def select_vehicle_comparison_heat_flows(df_results:pd.DataFrame, month_name, hour)->pd.DataFrame:

    df_filtered = copy.deepcopy(df_results)

    # select month and hour
    df_filtered = df_filtered[df_filtered["month_name"] == month_name]
    df_filtered = df_filtered[df_filtered["hour"] == hour]

    # split convection and air exchange
    df_filtered["power_heating_convection_pos"] =(
        df_filtered["power_heating_convection"].apply(lambda x: x if x > 0 else 0))
    df_filtered["power_heating_convection_neg"] =(
        df_filtered["power_heating_convection"].apply(lambda x: x if x < 0 else 0))

    df_filtered["power_heating_ventilation_air_pos"] = (
        df_filtered["power_heating_ventilation_air"].apply(lambda x: x if x > 0 else 0))
    df_filtered["power_heating_ventilation_air_neg"] = (
        df_filtered["power_heating_ventilation_air"].apply(lambda x: x if x < 0 else 0))

    df_filtered["power_heating_doors_air_pos"] = (
        df_filtered["power_heating_doors_air"].apply(lambda x: x if x > 0 else 0))
    df_filtered["power_heating_doors_air_neg"] = (
        df_filtered["power_heating_doors_air"].apply(lambda x: x if x < 0 else 0))

    # select columns
    df_filtered = df_filtered[[
        "operation_schedule", "vehicle_name", "vehicle_version_parameter_set",
        "power_solar_absorption", "power_heating_passengers", "power_heating_auxiliary",
        "power_heating_convection_pos", "power_heating_convection_neg",
        "power_heating_ventilation_air_pos", "power_heating_ventilation_air_neg",
        "power_heating_doors_air_pos", "power_heating_doors_air_neg",
        "power_demand_heating", "power_demand_cooling"
    ]]

    return df_filtered



def generate_vehicle_annual_heat_flows(session_state:dict, df_selection:pd.DataFrame, index_month_spacer:int)\
        ->pd.DataFrame:

    df_generated = copy.deepcopy(df_selection)
    df_generated.reset_index(inplace=True)

    if len(df_generated) == 0:
        return df_generated

    # connect climate data
    location = session_state["specification"]["operation_schedules"][df_generated["operation_schedule"][0]]["location"]
    temperature_environment = session_state["location_data"][location]["temperature"]
    solar_irradiation = session_state["location_data"][location]["irradiation_direct_normal"]

    df_generated["month_index"] = df_generated["month_name"].apply(lambda x: MONTH_NAMES.index(x))
    df_generated["temperature_environment"] = df_generated.apply(
        lambda row: temperature_environment[row["month_index"]][row["hour"]],
        axis=1
    )
    df_generated["solar_irradiation"] = df_generated.apply(
        lambda row: solar_irradiation[row["month_index"]][row["hour"]],
        axis=1
    )

    # split convection and air exchange
    df_generated["power_heating_convection_pos"] = (
        df_generated["power_heating_convection"].apply(lambda x: x if x > 0 else 0))
    df_generated["power_heating_convection_neg"] = (
        df_generated["power_heating_convection"].apply(lambda x: x if x < 0 else 0))

    df_generated["power_heating_ventilation_air_pos"] = (
        df_generated["power_heating_ventilation_air"].apply(lambda x: x if x > 0 else 0))
    df_generated["power_heating_ventilation_air_neg"] = (
        df_generated["power_heating_ventilation_air"].apply(lambda x: x if x < 0 else 0))

    df_generated["power_heating_doors_air_pos"] = (
        df_generated["power_heating_doors_air"].apply(lambda x: x if x > 0 else 0))
    df_generated["power_heating_doors_air_neg"] = (
        df_generated["power_heating_doors_air"].apply(lambda x: x if x < 0 else 0))

    # add electric heat pump power sum
    df_generated["electric_power_heat_pumps_sum"] = (df_generated["electric_power_vehicle"]
                                                     - df_generated["electric_power_resistive_heating"])
    df_generated["electric_power_heat_pumps_heating"] = df_generated.apply(
        lambda row: row["electric_power_heat_pumps_sum"] if row["power_demand_heating"] > 0 else 0,
        axis=1
    )
    df_generated["electric_power_heat_pumps_cooling"] = df_generated.apply(
        lambda row: row["electric_power_heat_pumps_sum"] if row["power_demand_cooling"] < 0 else 0,
        axis=1
    )

    # add tick markers und labels
    hour_min = df_generated["hour"].unique().min()
    hour_max = df_generated["hour"].unique().max()
    hour_mid = int((hour_min + hour_max) / 2)

    df_generated["time"] = np.nan
    df_generated["ticklabel"] = ""

    tick_index = 0
    last_month_name = None
    for index, row in df_generated.iterrows():
        if row["month_name"] != last_month_name:
            if last_month_name is not None:
                tick_index += 1 + index_month_spacer
        else:
            tick_index += 1
        last_month_name = row["month_name"]

        df_generated.at[index, "time"] = tick_index

        if row["hour"] == hour_min:
            df_generated.at[index, "ticklabel"] = str(row["hour"])
        elif row["hour"] == hour_mid:
            df_generated.at[index, "ticklabel"] = str(row["hour"]) + "<br>" + row["month_name"]
        elif row["hour"] == hour_max:
            df_generated.at[index, "ticklabel"] = str(row["hour"])

    # select columns
    df_generated = df_generated[[
        "time", "ticklabel",
        "temperature_environment", "solar_irradiation", "temperature_vehicle",
        "power_demand_heating", "power_demand_cooling",
        "power_solar_absorption", "power_heating_passengers", "power_heating_auxiliary",
        "power_heating_convection_pos", "power_heating_convection_neg",
        "power_heating_ventilation_air_pos", "power_heating_ventilation_air_neg",
        "power_heating_doors_air_pos", "power_heating_doors_air_neg",
        "electric_power_resistive_heating", "electric_power_heat_pumps_heating", "electric_power_heat_pumps_cooling"
    ]]

    return df_generated