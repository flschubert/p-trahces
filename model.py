# copyright 2025 Florian Schubert


##### IMPORTS #####

from streamlit import session_state

import data_handler as dh

import copy
from typing import Tuple

import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.optimize import fsolve
from datetime import datetime



##### CONSTANTS #####

C_TO_K = 273.15 # [K]

GRAVITAIONAL_ACCELERATION = 9.81 # [m/s²]
C_P_AIR = 1004      # mass-specific heat capacity of air (at T=20°C, p=1050hPa) [J/kgK]

RHO_AIR = 1.275     # density of air (at T=20°C, p=1050hPa) [kg/m³]
HEAT_PERSON = 116   # average heat generation by on person (under sitting conditions) [W]

DOOR_DISCHARGE_COEFFICIENT = 0.6 # discharge coefficient for open doors [-]

MINIMUM_ANGLE_ARCTAN_APPROXIMATION_CONSTANT = 1e3
NORMAL_DIRECT_SOLAR_IRRADIATION_UPPER_BOUND = 1000 # [W/m²]
FLOAT_TOLERANCE = 1e-5 # tolerance for floating point comparisons

MONTH_DAYS_BEGIN = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366]     # day in year of monthly beginning
MONTH_DAYS_MID = [16, 46, 75, 106, 136, 167, 197, 228, 259, 289, 320, 350]          # day in year of mid-month

INFINITE_EFFICIENCY = 1e12 # Carnot efficiency for zero temperature difference



##### FUNCTION DEFINITIONS #####

def simulate_solar_absorption_single_orientation(angle_orientation:float,
                                                 vehicle:dict,
                                                 obstacle_distance:float,
                                                 obstacle_height:float,
                                                 angle_altitude:float,
                                                 angle_azimuth:float,
                                                 solar_irradiation_horizontal:float,
                                                 solar_irradiation_vertical:float)->float:

    angle_altitude_min = abs(np.arctan((obstacle_height - vehicle["height"]) * np.sin(angle_azimuth - angle_orientation)
                                       / obstacle_distance))

    minimum_angle_factor = (np.arctan((angle_altitude - angle_altitude_min)
                                      * MINIMUM_ANGLE_ARCTAN_APPROXIMATION_CONSTANT)/ np.pi + 0.5)
    angle_factor_length = abs(np.sin(angle_azimuth - angle_orientation))
    angle_factor_width = abs(np.cos(angle_azimuth - angle_orientation))
    # print("angle_factor_length=" + str(angle_factor_length) + ", angle_factor_width=" + str(angle_factor_width) +
    #      ", angle_factor_height=" + str(angle_factor_height) + ", angle_factor_roof=" + str(angle_factor_roof))

    area_absorption_roof = vehicle["length"] * vehicle["width"] * (1-vehicle["fraction_obstruction_roof"])
    absorption_roof = (minimum_angle_factor * vehicle["cabin_absorptivity"] * area_absorption_roof
                       * solar_irradiation_horizontal)

    area_front_cabin = vehicle["width"] * vehicle["height"] - vehicle["area_windows_front"]
    absorption_front_cabin = (minimum_angle_factor * angle_factor_width * vehicle["cabin_absorptivity"]
                              * area_front_cabin * solar_irradiation_vertical)
    absorption_front_window = (minimum_angle_factor * angle_factor_width * vehicle["window_transmissivity"]
                               * vehicle["area_windows_front"] * solar_irradiation_vertical)

    area_side_cabin = vehicle["length"] * vehicle["height"] - vehicle["area_windows_side"]
    absorption_side_cabin = (minimum_angle_factor * vehicle["cabin_absorptivity"] * angle_factor_length
                            * area_side_cabin * solar_irradiation_vertical)
    absorption_side_window = (minimum_angle_factor * angle_factor_length * vehicle["window_transmissivity"]
                              * vehicle["area_windows_side"] * solar_irradiation_vertical)

    if False:  # debug
        print("-----  orientation=" + str(180 / np.pi * angle_orientation) + "° -----")
        print("I_solar_horizontal=" + str(I_solar_horizontal))
        print("I_solar_vertical=" + str(I_solar_vertical))
        print("absorption_roof=" + str(absorption_roof))
        print("absorption_front_wall=" + str(absorption_front_wall))
        print("absorption_front_window=" + str(absorption_front_window))
        print("absorption_side_wall=" + str(absorption_side_wall))
        print("absorption_side_window=" + str(absorption_side_window))

    absorption_total = (absorption_roof + absorption_front_cabin + absorption_front_window + absorption_side_cabin
                        + absorption_side_window)
    return absorption_total



def simulate_solar_absorption(vehicle:dict,
                              vehicle_name_version:str,
                              obstacle_distance:float,
                              obstacle_height:float,
                              irradiation:float,
                              month:int,
                              hour:int,
                              latitude:float,
                              solar_heating_lookup_table:dict,
                              irradiation_normal:bool=True)->float:
    # (horizontal solar irradiation measurement)
    delta = 23.45 / 180 * np.pi * np.sin(2 * np.pi / 365 * (284 + MONTH_DAYS_MID[month-1]))
    omega = 15 / 180 * np.pi * (hour - 12)

    # convert latitude from degree to radians
    angle_latitude = np.pi/180 * latitude

    # calculate solar angles
    trigon_arg = (np.cos(angle_latitude) * np.cos(delta) * np.cos(omega)
                  + np.sin(angle_latitude) * np.sin(delta))
    angle_zenith = np.arccos(trigon_arg)
    # source: duffie, equation (1.6.5)
    angle_altitude = np.arcsin(trigon_arg)

    arg_arccos = ((np.cos(angle_zenith)*np.sin(angle_latitude) - np.sin(delta))
                  /(np.sin(angle_zenith) * np.cos(angle_latitude)))
    arg_arccos = min(arg_arccos, 1)
    arg_arccos = max(arg_arccos, -1)
    angle_azimuth_south = np.sign(omega) * np.abs(np.arccos(arg_arccos))
    # source: duffie, equation (1.6.6)
    angle_azimuth = np.mod(np.pi-angle_azimuth_south, 2*np.pi)
    #print("month=" + str(month) + ",\t hour=" + str(hour) + ", \t angle_altitude=" + str(180/np.pi*angle_altitude)
    #     + "°,\t azimuth=" + str(180/np.pi*angle_azimuth) + "°")

    #print("month=" + str(month) + ",\t hour=" + str(hour) + ", \t angle_altitude_min="
    #      + str(180/np.pi * angle_altitude_min) + "°")
    #if (angle_altitude < angle_altitude_min):
    #    return 0

     # differentiate between normal and horizontal irradiation
    if irradiation_normal:
        irradiation_horizontal = max(0, np.cos(angle_altitude)) * irradiation
        irradiation_vertical = max(0, np.sin(angle_altitude)) * irradiation
    else:
        irradiation_normal_theoretical = irradiation / max(1e-10, np.cos(angle_zenith))
        if (irradiation_normal_theoretical > NORMAL_DIRECT_SOLAR_IRRADIATION_UPPER_BOUND):
            irradiation_horizontal = (irradiation
                                      * NORMAL_DIRECT_SOLAR_IRRADIATION_UPPER_BOUND/irradiation_normal_theoretical)
            irradiation_vertical = (max(0, np.tan(angle_zenith)) * irradiation_horizontal
                                    * NORMAL_DIRECT_SOLAR_IRRADIATION_UPPER_BOUND/irradiation_normal_theoretical)
        else:
            irradiation_horizontal = irradiation
            irradiation_vertical = max(0, np.tan(angle_zenith)) * irradiation

    # TODO check SOLAR calculation

    # integrate over angle_orientation [0, pi] and calculate average absorption (if already calculated, use table)
    key = (vehicle_name_version, obstacle_distance, obstacle_height, angle_altitude, angle_azimuth,
           irradiation_horizontal, irradiation_vertical)
    if key in solar_heating_lookup_table.keys():
        absorption_average = solar_heating_lookup_table[key]
    else:
        absorption_integrated, absorption_error = quad(
            simulate_solar_absorption_single_orientation, 0, np.pi,
            args=(vehicle, obstacle_distance, obstacle_height, angle_altitude, angle_azimuth,
                  irradiation_horizontal, irradiation_vertical))
        absorption_average = np.abs(absorption_integrated / np.pi)
        solar_heating_lookup_table[key] = absorption_average

    return absorption_average



def simulate_passive_heat_flows(vehicle:dict,
                                vehicle_name_version:str,
                                obstacle_distance:float,
                                obstacle_height:float,
                                passenger_number:float,
                                temperature_vehicle:float,
                                temperature_environment:float,
                                irradiation:float,
                                month:int,
                                hour:int,
                                latitude:float,
                                consider_solar_heating:bool,
                                solar_heating_lookup_table:dict=None,
                                irradiation_normal:bool=True)->Tuple[float,float,float,float,float,float]:

    # calculate solar heat flow
    heat_solar = 0
    if consider_solar_heating:
        heat_solar = 1e-3 * simulate_solar_absorption(vehicle, vehicle_name_version, obstacle_distance, obstacle_height,
                                                      irradiation, month, hour, latitude,
                                                      solar_heating_lookup_table, irradiation_normal)

    area_convection = (2 * vehicle["length"] * vehicle["height"] + 2 * vehicle["width"] * vehicle["height"]
                       + (2 - vehicle["fraction_obstruction_roof"] - vehicle["fraction_obstruction_floor"])
                       * vehicle["length"] * vehicle["width"])

    # calculate remaining heat flows [kW]
    heat_passenger = 1e-3 * passenger_number * HEAT_PERSON
    heat_auxiliary_devices = vehicle["heating_power_auxiliary"]
    heat_convection = (1e-3 * area_convection * vehicle["heat_transfer_coefficient_chassis"]
                       * (temperature_environment - temperature_vehicle))
    heat_ventilation = (1e-3 * vehicle["volume_flow_rate_ventilation"] * RHO_AIR * C_P_AIR
                        * (temperature_environment - temperature_vehicle))
    heat_doors = (1e-3*(1/3)
                  * RHO_AIR * C_P_AIR * np.sqrt(GRAVITAIONAL_ACCELERATION* np.power(vehicle["door_height"], 3))
                  * np.sqrt(np.abs(temperature_vehicle - temperature_environment) / (C_TO_K + temperature_environment))
                  * (temperature_environment - temperature_vehicle)
                  * vehicle["door_width_total"] * vehicle["time_fraction_door_open"] * DOOR_DISCHARGE_COEFFICIENT)

    return heat_solar, heat_passenger, heat_auxiliary_devices, heat_convection, heat_ventilation, heat_doors



def simulate_heat_flows(vehicle:dict,
                        vehicle_name_version:str,
                        obstacle_distance:float,
                        obstacle_height:float,
                        passenger_number:float,
                        temperature_vehicle:float,
                        temperature_environment:float,
                        irradiation:float,
                        month:int,
                        hour:int,
                        latitude:float,
                        consider_solar_heating:bool,
                        solar_heating_lookup_table:dict=None,
                        irradiation_normal:bool=True)->dict:
    (heat_solar, heat_passenger, heat_auxiliary_devices, heat_convection, heat_ventilation, heat_doors)\
        = simulate_passive_heat_flows(vehicle, vehicle_name_version, obstacle_distance, obstacle_height,
                                      passenger_number, temperature_vehicle, temperature_environment, irradiation,
                                      month, hour, latitude, consider_solar_heating, solar_heating_lookup_table,
                                      irradiation_normal)

    heat_difference = (heat_solar + heat_passenger + heat_auxiliary_devices
                       + heat_convection + heat_ventilation + heat_doors)

    heating_demand = max(0, -heat_difference)
    cooling_demand = -max(0, heat_difference)

    # write values to dictionaries
    heat_flows = {'demand_heating': heating_demand, 'demand_cooling': cooling_demand,
                  'solar_absorption': heat_solar, 'heating_passengers': heat_passenger,
                  'heating_auxiliary': heat_auxiliary_devices, 'heating_convection': heat_convection,
                  'heating_ventilation_air': heat_ventilation, 'heating_doors_air': heat_doors}

    return heat_flows



def simulate_device_electricity_demand(vehicle:dict,
                                       heat_demand:float,
                                       temperature_environment:float,
                                       temperature_vehicle:float)->Tuple[list,bool,bool]:

    electricity_consumption = list(np.zeros(1 + len(vehicle["heating_cooling_devices"]["heat_pumps"])))

    if heat_demand == 0:
        return electricity_consumption, True, True

    # TODO check Carnot efficiency calculation
    temperature_environment_kelvin = temperature_environment + C_TO_K
    temperature_vehicle_kelvin = temperature_vehicle + C_TO_K
    if temperature_environment == temperature_vehicle:
        carnot_efficiency_heating = INFINITE_EFFICIENCY
        carnot_efficiency_cooling = INFINITE_EFFICIENCY
    elif temperature_environment < temperature_vehicle:
        carnot_efficiency_heating = (temperature_vehicle_kelvin /
                                     (temperature_vehicle_kelvin - temperature_environment_kelvin))
        carnot_efficiency_cooling = (temperature_environment_kelvin /
                                     (temperature_vehicle_kelvin - temperature_environment_kelvin))
    else: # temperature_environment > temperature_vehicle
        carnot_efficiency_heating = (temperature_vehicle_kelvin /
                                     (temperature_environment_kelvin - temperature_vehicle_kelvin))
        carnot_efficiency_cooling = (temperature_environment_kelvin /
                                     (temperature_environment_kelvin - temperature_vehicle_kelvin))
    """
    print("temperature_environment", temperature_environment, "temperature_vehicle", temperature_vehicle,
          #"temperature_environment_kelvin", temperature_environment_kelvin, "temperature_vehicle_kelvin", temperature_vehicle_kelvin,
          "carnot_efficiency_heating", carnot_efficiency_heating, "carnot_efficiency_cooling", carnot_efficiency_cooling)
    """

    # calculate minimum exergy efficiency eta_ex_min for T_env, T_veh such that COP_res >= 1
    # arrange heat pumps in order of decreasing exergy efficiency:
    # 1: all heat pumps with eta_ex > eta_ex_min (in order of decreasing eta_ex)
    # 2: all resistive heaters
    # 3: all heat pumps with eta_ex <= eta_ex_min (in order of decreasing eta_ex)
    heat_pumps_sorted = copy.deepcopy(vehicle["heating_cooling_devices"]["heat_pumps"])
    sorted(heat_pumps_sorted, key=lambda x: x["exergy_efficiency"], reverse=True)
    # TODO check sorting

    heat_demand_remainder = heat_demand
    k = 1
    for heat_pump in heat_pumps_sorted:
        if (heat_demand > 0) and heat_pump['heating']:
            heating_efficiency = heat_pump['exergy_efficiency'] * carnot_efficiency_heating
            #print("heat", T_environment, T_setpoint, carnot_efficiency_heating, heating_efficiency)
            heat_pump_max_heat = heat_pump['electric_power_max'] * heating_efficiency
            heat = min(heat_demand_remainder, heat_pump_max_heat)
            heat_demand_remainder -= heat
            electricity_consumption[k] = heat_pump['electric_power_max'] * (heat / heat_pump_max_heat)
        elif (heat_demand < 0) and heat_pump['cooling']:
            cooling_efficiency = heat_pump['exergy_efficiency'] * carnot_efficiency_cooling
            #print("cool", T_environment, T_setpoint, carnot_efficiency_cooling, cooling_efficiency)
            heat_pump_max_cool = -heat_pump['electric_power_max'] * cooling_efficiency
            heat = max(heat_demand_remainder, heat_pump_max_cool)
            heat_demand_remainder -= heat
            electricity_consumption[k] = heat_pump['electric_power_max'] * (heat / heat_pump_max_cool)
        k += 1
    if (heat_demand > 0):
        heat = min(heat_demand_remainder, vehicle["heating_cooling_devices"]["resistive_heating_power_max"])
        heat_demand_remainder -= heat
        electricity_consumption[0] = heat

    heating_satisfied = (heat_demand_remainder <= FLOAT_TOLERANCE)
    cooling_satisfied = (heat_demand_remainder >= -FLOAT_TOLERANCE)
    #raise ValueError("Vehicle \'" + vehicle_name
    #                     + "\' does not have enough heaters to satisfy the heating demand. "
    #                       "Please add heaters and/or increase their thermal heating power!")
    #raise ValueError("Vehicle \'" + vehicle_name
    #                 + "\' does not have enough cooling heat pumps to satisfy the cooling demand. "
    #                   "Please add heat pumps for cooling and/or increase their thermal cooling power!")

    return electricity_consumption, heating_satisfied, cooling_satisfied



def power_difference(temperature_vehicle:float,
                     vehicle:dict,
                     vehicle_name_version:str,
                     obstacle_distance:float,
                     obstacle_height:float,
                     passenger_number:float,
                     temperature_environment:float,
                     irradiation:float,
                     month:int,
                     hour:int,
                     latitude:float,
                     consider_solar_heating:bool,
                     solar_heating_lookup_table:dict=None,
                     irradiation_normal:bool=True)->float:

    (heat_solar, heat_passenger, heat_auxiliary_devices, heat_convection, heat_ventilation, heat_doors) \
        = simulate_passive_heat_flows(vehicle, vehicle_name_version, obstacle_distance, obstacle_height,
                                      passenger_number, temperature_vehicle, temperature_environment, irradiation,
                                      month, hour, latitude, consider_solar_heating, solar_heating_lookup_table,
                                      irradiation_normal)

    return (heat_solar + heat_passenger + heat_auxiliary_devices + heat_convection + heat_ventilation + heat_doors)



def interpolate_temperature_points(temperature_points:list, temperature_environment:float)->float:
    if len(temperature_points) == 1:
        return temperature_points[1]

    for i in range(1, len(temperature_points)):
        x0, y0 = temperature_points[i - 1]
        x1, y1 = temperature_points[i]
        if x0 <= temperature_environment <= x1:
            return y0 + (y1 - y0) * (temperature_environment - x0) / (x1 - x0)



def simulate_vehicle_temperature(vehicle:dict,
                                 vehicle_name_version:str,
                                 temperature_control_curve:dict,
                                 obstacle_distance:float,
                                 obstacle_height:float,
                                 passenger_number:float,
                                 temperature_environment:float,
                                 irradiation:float,
                                 month:int,
                                 hour:int,
                                 latitude:float,
                                 consider_solar_heating:bool,
                                 solar_heating_lookup_table:dict=None,
                                 irradiation_normal:bool=True)->float:

    # calculate theoretical vehicle temperature from heat balance
    # TODO check parameters
    theoretical_temperature_vehicle = fsolve(power_difference, temperature_environment,
                    args=(vehicle, vehicle_name_version, obstacle_distance, obstacle_height, passenger_number,
                          temperature_environment, irradiation, month, hour, latitude, consider_solar_heating,
                          solar_heating_lookup_table, irradiation_normal))[0]

    # ensure sorted input data
    temperature_control_curve["heating"].sort(key=lambda point: point[0])
    temperature_control_curve["cooling"].sort(key=lambda point: point[0])

    # calculate heating & cooling temperature
    heating_temperature = -np.inf
    if len(temperature_control_curve["heating"]) > 0:
        if (temperature_control_curve["heating"][0][0] <= temperature_environment
                and temperature_environment <= temperature_control_curve["heating"][-1][0]):
            heating_temperature = interpolate_temperature_points(temperature_control_curve["heating"],
                                                                 temperature_environment)
        elif temperature_environment < temperature_control_curve["heating"][0][0]:
            heating_temperature = temperature_control_curve["heating"][0][1]
        else:
            heating_temperature = temperature_control_curve["heating"][-1][1]

    cooling_temperature = np.inf
    if len(temperature_control_curve["cooling"]) > 0:
        if (temperature_control_curve["cooling"][0][0] <= temperature_environment
                and temperature_environment <= temperature_control_curve["cooling"][-1][0]):
            cooling_temperature = interpolate_temperature_points(temperature_control_curve["cooling"],
                                                                 temperature_environment)
        elif temperature_environment < temperature_control_curve["cooling"][0][0]:
            cooling_temperature = temperature_control_curve["cooling"][0][1]
        else:
            cooling_temperature = temperature_control_curve["cooling"][-1][1]

    # check whether theoretical temperature is within heating & cooling temperature range
    if (heating_temperature <= theoretical_temperature_vehicle
            and theoretical_temperature_vehicle <= cooling_temperature):
        return theoretical_temperature_vehicle
    elif theoretical_temperature_vehicle < heating_temperature:
        return heating_temperature
    else:
        return cooling_temperature



def simulate_vehicle(vehicle:dict,
                     vehicle_name_version:str,
                     temperature_control_curve:dict,
                     obstacle_distance:float,
                     obstacle_height:float,
                     passenger_number:float,
                     temperature_environment:float,
                     irradiation:float,
                     month:int,
                     hour:int,
                     latitude:float,
                     consider_solar_heating:bool,
                     solar_heating_lookup_table:dict=None,
                     irradiation_normal:bool=True)->Tuple[float,dict,list,bool,bool]:

    temperature_vehicle = simulate_vehicle_temperature(vehicle, vehicle_name_version, temperature_control_curve,
                                                       obstacle_distance, obstacle_height, passenger_number,
                                                       temperature_environment, irradiation, month, hour,
                                                       latitude, consider_solar_heating, solar_heating_lookup_table,
                                                       irradiation_normal)

    heat_flows = simulate_heat_flows(vehicle, vehicle_name_version, obstacle_distance, obstacle_height,
                                     passenger_number, temperature_vehicle, temperature_environment, irradiation,
                                     month, hour, latitude, consider_solar_heating, solar_heating_lookup_table,
                                     irradiation_normal)

    electricity_demand, heating_satisfied, cooling_satisfied =(
        simulate_device_electricity_demand(vehicle,
                                           heat_flows["demand_heating"] + heat_flows["demand_cooling"],
                                           temperature_environment, temperature_vehicle))

    return temperature_vehicle, heat_flows, electricity_demand, heating_satisfied, cooling_satisfied



def calculate_monthly_operation_days(date_begin:str, date_end:str)->list:
    # convert date str to datetime
    date_begin = datetime.strptime(date_begin, "%m-%d")
    date_end = datetime.strptime(date_end, "%m-%d")

    # convert dates to int
    begin_month = date_begin.month
    begin_day = date_begin.day
    end_month = date_end.month
    end_day = date_end.day

    # convert dates to day in year
    day_begin = MONTH_DAYS_BEGIN[begin_month - 1] + begin_day - 1
    day_end = MONTH_DAYS_BEGIN[end_month - 1] + end_day - 1

    # create list with operation days per months (1 to 12 for January to December with indices 0 to 11)
    operation_days = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for m in range(0, 12):
        if day_begin <= day_end:
            day_begin_m = max(day_begin - 1, MONTH_DAYS_BEGIN[m])
            day_end_m = min(day_end, MONTH_DAYS_BEGIN[m + 1] - 1)
            operation_days[m] = max(0, day_end_m - day_begin_m + 1)
        else:
            day_begin_m = max(day_end, MONTH_DAYS_BEGIN[m])
            day_end_m = min(day_begin - 1, MONTH_DAYS_BEGIN[m + 1] - 1)
            operation_days[m] = ((MONTH_DAYS_BEGIN[m + 1] - MONTH_DAYS_BEGIN[m])
                                 - max(0, day_end_m - day_begin_m + 1))

    return operation_days



def calculate_daily_operation_hours(time_begin:str, time_end:str)->list:
    # convert time str to datetime
    time_begin = datetime.strptime(time_begin, "%H:%M")

    time_end = time_end.replace("24:", "00:")
    time_end = datetime.strptime(time_end, "%H:%M")

    # convert times to float
    hour_begin = time_begin.hour + time_begin.minute / 60.0
    hour_end = time_end.hour + time_end.minute / 60.0
    if hour_end < hour_begin:
        hour_end = hour_end + 24

    # calculate operation hours
    operation_hours = 24*[0]
    for hour in range(int(hour_begin), int(hour_end)+1):
        hour_index = hour % 24
        if hour == int(hour_begin):
            operation_hours[hour_index] = 1 - (hour_begin - int(hour_begin))
        elif hour < int(hour_end):
            operation_hours[hour_index] = 1
        else:
            operation_hours[hour_index] = hour_end - int(hour_end)

    return operation_hours



def simulate_system(operation_schedules:dict,
                    vehicle_versions:dict,
                    temperature_control_curves:dict,
                    location_data:dict,
                    scenarios:dict,
                    reference_scenario_name:str)->Tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,Warning]:

    heating_not_satisfied = {}
    cooling_not_satisfied = {}

    # simulate single hours
    result_data_vehicles = []
    for operation_schedule_name, operation_schedule_data in operation_schedules.items():

        # calculate operation days and hours
        operation_days = calculate_monthly_operation_days(operation_schedule_data["date_begin"],
                                                          operation_schedule_data["date_end"])
        operation_hours = calculate_daily_operation_hours(operation_schedule_data["time_begin"],
                                                          operation_schedule_data["time_end"])

        # simulate result data for vehicles
        for month_id in range(0, 12):
            month = month_id+1
            for hour in range(0, 24):
                if operation_days[month_id] > 0 and operation_hours[hour] > 0:
                    for vehicle_name, vehicle_number in operation_schedule_data["vehicles_in_operation"].items():
                        for vehicle_version, vehicle_version_data in vehicle_versions[vehicle_name].items():
                            solar_heating_lookup_table = {}
                            temperature_vehicle, heat_flows, electricity_demand, heating_satisfied, cooling_satisfied =(
                                simulate_vehicle(
                                vehicle_version_data["vehicle_data"],
                                vehicle_name + "_" + vehicle_version,
                                temperature_control_curves[vehicle_version_data["vehicle_data"]["temperature_control_curve"]],
                                operation_schedule_data["obstacle_distance"],
                                operation_schedule_data["obstacle_height"],
                                operation_schedule_data["passenger_number"],
                                location_data[
                                    operation_schedule_data["location"]]["temperature"][month_id][hour],
                                location_data[
                                    operation_schedule_data["location"]]["irradiation_direct_normal"][month_id][hour],
                                month,
                                hour,
                                location_data[operation_schedule_data["location"]]["latitude"],
                                True,
                                solar_heating_lookup_table=solar_heating_lookup_table,
                                irradiation_normal=True
                            ))

                            # manage satisfied data

                            if not heating_satisfied:
                                if not operation_schedule_name in heating_not_satisfied.keys():
                                    heating_not_satisfied[operation_schedule_name] = {}
                                if not vehicle_name in heating_not_satisfied[operation_schedule_name].keys():
                                    heating_not_satisfied[operation_schedule_name][vehicle_name] = {}
                                if not vehicle_version in heating_not_satisfied[operation_schedule_name][vehicle_name].keys():
                                    heating_not_satisfied[operation_schedule_name][vehicle_name][vehicle_version] = {}
                                if not dh.MONTH_NAMES[month_id] in heating_not_satisfied[operation_schedule_name][vehicle_name][vehicle_version].keys():
                                    heating_not_satisfied[operation_schedule_name][vehicle_name][vehicle_version][dh.MONTH_NAMES[month_id]] = []
                                heating_not_satisfied[operation_schedule_name][vehicle_name][vehicle_version][dh.MONTH_NAMES[month_id]].append(hour)

                            if not cooling_satisfied:
                                if not operation_schedule_name in cooling_not_satisfied.keys():
                                    cooling_not_satisfied[operation_schedule_name] = {}
                                if not vehicle_name in cooling_not_satisfied[operation_schedule_name].keys():
                                    cooling_not_satisfied[operation_schedule_name][vehicle_name] = {}
                                if not vehicle_version in cooling_not_satisfied[operation_schedule_name][
                                    vehicle_name].keys():
                                    cooling_not_satisfied[operation_schedule_name][vehicle_name][vehicle_version] = {}
                                if not dh.MONTH_NAMES[month_id] in \
                                       cooling_not_satisfied[operation_schedule_name][vehicle_name][
                                           vehicle_version].keys():
                                    cooling_not_satisfied[operation_schedule_name][vehicle_name][vehicle_version][
                                        dh.MONTH_NAMES[month_id]] = []
                                cooling_not_satisfied[operation_schedule_name][vehicle_name][vehicle_version][
                                    dh.MONTH_NAMES[month_id]].append(hour)

                            # create vehicle result data row
                            electric_power_heating = electricity_demand[0]
                            electric_power_cooling = 0
                            if len(electricity_demand) > 0:
                                if heat_flows["demand_heating"] > 0:
                                    electric_power_heating += sum(electricity_demand[1:])
                                else:
                                    electric_power_cooling += sum(electricity_demand[1:])

                            result_data_vehicles_row = {
                                "operation_schedule": operation_schedule_name,
                                "vehicle_name": vehicle_name,
                                "vehicle_version_parameter_set":
                                    dh.convert_dictionary_to_str(
                                        vehicle_versions[vehicle_name][vehicle_version]["parameter_set"],
                                        keys_to_display_names=True),
                                "month_name": dh.MONTH_NAMES[month-1],
                                "hour": hour,
                                "electric_energy_vehicle_operation": None,
                                "electric_energy_vehicle_operation_heating": None,
                                "electric_energy_vehicle_operation_cooling": None,
                                "electricity_cost_vehicle_operation": None,
                                "electric_power_vehicle": sum(electricity_demand),
                                "electric_power_vehicle_heating": electric_power_heating,
                                "electric_power_vehicle_cooling": electric_power_cooling,
                                "electric_power_resistive_heating": electricity_demand[0]
                            }

                            if len(electricity_demand) > 1:
                                heat_pump_power_dict = {}
                                index = 1
                                for heat_pump in vehicle_version_data["vehicle_data"]["heating_cooling_devices"]["heat_pumps"]:
                                    heat_pump_power_dict[heat_pump["name"]] = electricity_demand[index]
                                    index += 1
                                #print("\npre", heat_pump_power_dict)
                                result_data_vehicles_row["electric_power_heat_pumps"] = dh.convert_dictionary_to_str(heat_pump_power_dict)
                                #print("post", result_data_vehicles_row["electric_power_heat_pumps"])

                            for key, value in heat_flows.items():
                                result_data_vehicles_row["power_" + key] = value

                            result_data_vehicles_row["operation_days"] = operation_days[month_id]
                            result_data_vehicles_row["operation_hours"] = operation_hours[hour]
                            result_data_vehicles_row["number_of_vehicles"] = vehicle_number
                            result_data_vehicles_row["unit_cost_electricity"] = operation_schedule_data["cost_electricity"]
                            result_data_vehicles_row["temperature_vehicle"] = temperature_vehicle
                            result_data_vehicles_row["temperature_environment"] =(
                                location_data[operation_schedule_data["location"]]["temperature"][month_id][hour])
                            result_data_vehicles_row["irradiation_direct_normal"] = location_data[
                                operation_schedule_data["location"]]["irradiation_direct_normal"][month_id][hour]

                            result_data_vehicles.append(result_data_vehicles_row)

    # unsatisfied demand warning
    warning = (len(heating_not_satisfied) > 0 or len(cooling_not_satisfied) > 0)
    demand_not_satisfied_warning = None
    if warning:
        warning_text = "For at least one operation schedule, vehicle and hour the heating or cooling demand was not satisfied, as the maximum power of the heating or cooling devices did not suffice. "
        warning_text += "The displayed vehicle temperature, heat flows and electricity consumption for the respective entry/entries are not valid. "
        warning_text += "Please check the vehicle configuration or the operation schedule and consider increasing the heating or cooling device maximum power."

        if len(heating_not_satisfied) > 0:
            warning_text += "\n- Time steps with unsatisfied heating demand:"
            for key_operation_schedule, data_operation_schedule in heating_not_satisfied.items():
                warning_text += "\n\t- " + key_operation_schedule
                for key_vehicle, data_vehicle in data_operation_schedule.items():
                    for key_version, data_version in data_vehicle.items():
                        version_parameter_set_str = dh.convert_dictionary_to_str(
                            session_state["specification"]["vehicle_versions"][key_vehicle][key_version][
                                "parameter_set"],
                            keys_to_display_names=True)
                        warning_text += "\n\t\t- " + key_vehicle + " " + version_parameter_set_str + ": "
                        first_month = True
                        for month_name, hours in data_version.items():
                            if first_month:
                                first_month = False
                            else:
                                warning_text += ", "
                            warning_text += month_name + " (" + str(hours).replace("[", "").replace("]",
                                                                                                    "") + " o'clock)"

        if len(cooling_not_satisfied) > 0:
            warning_text += "\n- Time steps with unsatisfied cooling demand:"
            for key_operation_schedule, data_operation_schedule in cooling_not_satisfied.items():
                warning_text += "\n\t- " + key_operation_schedule
                for key_vehicle, data_vehicle in data_operation_schedule.items():
                    for key_version, data_version in data_vehicle.items():
                        version_parameter_set_str = dh.convert_dictionary_to_str(
                            session_state["specification"]["vehicle_versions"][key_vehicle][key_version][
                                "parameter_set"],
                            keys_to_display_names=True)
                        warning_text += "\n\t\t- " + key_vehicle + " " + version_parameter_set_str + ": "
                        first_month = True
                        for month_name, hours in data_version.items():
                            if first_month:
                                first_month = False
                            else:
                                warning_text += ", "
                            warning_text += month_name + " (" + str(hours).replace("[", "").replace("]",
                                                                                                    "") + " o'clock)"

        demand_not_satisfied_warning = Warning(warning_text)

    df_vehicle_results = pd.DataFrame(result_data_vehicles)

    df_vehicle_results["electric_energy_vehicle_operation"] = (df_vehicle_results["electric_power_vehicle"]
                                                               * df_vehicle_results["operation_hours"]
                                                               * df_vehicle_results["operation_days"])
    df_vehicle_results["electric_energy_vehicle_operation_heating"] = (df_vehicle_results["electric_power_vehicle_heating"]
                                                                       * df_vehicle_results["operation_hours"]
                                                                       * df_vehicle_results["operation_days"])
    df_vehicle_results["electric_energy_vehicle_operation_cooling"] = (df_vehicle_results["electric_power_vehicle_cooling"]
                                                                       * df_vehicle_results["operation_hours"]
                                                                       * df_vehicle_results["operation_days"])
    df_vehicle_results["electricity_cost_vehicle_operation"] = (df_vehicle_results["electric_energy_vehicle_operation"]
                                                                * df_vehicle_results["unit_cost_electricity"])


    # group by and sum for operation schedule and vehicle version

    df_vehicle_operation_totals = copy.deepcopy(df_vehicle_results)
    df_vehicle_operation_totals = df_vehicle_operation_totals.groupby(
        ["operation_schedule", "vehicle_name", "vehicle_version_parameter_set", "number_of_vehicles"]).sum()

    df_vehicle_operation_totals.reset_index(inplace=True)
    df_vehicle_operation_totals = df_vehicle_operation_totals[[
        "operation_schedule", "vehicle_name", "vehicle_version_parameter_set", "number_of_vehicles",
        "electric_energy_vehicle_operation", "electric_energy_vehicle_operation_heating",
        "electric_energy_vehicle_operation_cooling", "electricity_cost_vehicle_operation"
    ]]
    df_vehicle_operation_totals = df_vehicle_operation_totals.rename(columns={
        "electric_energy_vehicle_operation": "electric_energy_vehicle_operation_total",
        "electric_energy_vehicle_operation_heating": "electric_energy_vehicle_operation_heating_total",
        "electric_energy_vehicle_operation_cooling": "electric_energy_vehicle_operation_cooling_total",
        "electricity_cost_vehicle_operation": "electricity_cost_vehicle_operation_total"
    })


    # scenarios

    data_scenarios = []
    reference_scenario_energy = None
    for scenario_name, scenario_data in scenarios.items():
        scenario_row = {
            "scenario_name": scenario_name,
            "electric_energy_scenario_total": 0.0,
            "electric_energy_scenario_heating_total": 0.0,
            "electric_energy_scenario_cooling_total": 0.0,
            "electricity_cost_scenario_total": 0.0,
            "comparison_to_reference": None,
            "reference_scenario": scenario_name == reference_scenario_name
        }
        for operation_schedule_name, operation_schedule_data in operation_schedules.items():
            for vehicle_name, vehicle_number in operation_schedule_data["vehicles_in_operation"].items():
                if vehicle_number > 0:
                    vehicle_version_parameter_set = scenario_data[f"{operation_schedule_name} - {vehicle_name}"]
                    operation_schedule_row = df_vehicle_operation_totals.loc[
                        (df_vehicle_operation_totals['operation_schedule'] == operation_schedule_name)
                        & (df_vehicle_operation_totals['vehicle_name'] == vehicle_name)
                        & (df_vehicle_operation_totals['vehicle_version_parameter_set'] == vehicle_version_parameter_set)
                    ]
                    scenario_row["electric_energy_scenario_total"] += (
                            vehicle_number * float(operation_schedule_row["electric_energy_vehicle_operation_total"].iloc[0]))
                    scenario_row["electric_energy_scenario_heating_total"] += (
                            vehicle_number * float(operation_schedule_row["electric_energy_vehicle_operation_heating_total"].iloc[0]))
                    scenario_row["electric_energy_scenario_cooling_total"] += (
                            vehicle_number * float(operation_schedule_row["electric_energy_vehicle_operation_cooling_total"].iloc[0]))
                    scenario_row["electricity_cost_scenario_total"] += (
                            vehicle_number * float(operation_schedule_row["electricity_cost_vehicle_operation_total"].iloc[0]))
        if scenario_name == reference_scenario_name:
            reference_scenario_energy = scenario_row["electric_energy_scenario_total"]
        data_scenarios.append(scenario_row)

    for scenario_row in data_scenarios:
        if not scenario_row["scenario_name"] == reference_scenario_name:
            scenario_row["comparison_to_reference"] = (
                    100 * (scenario_row["electric_energy_scenario_total"] - reference_scenario_energy)
                    / reference_scenario_energy)

    df_scenario_totals = pd.DataFrame(data_scenarios)


    # round dataframe floats

    rounding_digits = dh.get_decimal_digits(dh.get_parameter_option("results", "rounding_precision"))
    df_vehicle_results = df_vehicle_results.round(rounding_digits)
    df_vehicle_operation_totals = df_vehicle_operation_totals.round(rounding_digits)
    df_scenario_totals = df_scenario_totals.round(rounding_digits)


    return df_vehicle_results, df_vehicle_operation_totals, df_scenario_totals, demand_not_satisfied_warning