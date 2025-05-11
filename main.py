# copyright 2025 Florian Schubert


##### IMPORTS #####

import data_handler as dh

import streamlit as st

import pandas as pd
from pandas.io.formats.style import Styler
import re

import copy

import json
from io import StringIO
import datetime

from PIL import Image
import plotly.graph_objects as go
from plotly.subplots import make_subplots



##### CONSTANTS #####

PAGE_URL = "p-trahces.streamlit.app"
PAGE_TITLE = "P-TRAHCES"
PAGE_SUBTITLE = "Public Transport Heating and Cooling Energy Simulator"
#PATH_ICON = "icon.webp"
#PATH_LOGO = "logo.png"

URL_GITHUB = "https://github.com/flschubert"
URL_GITHUB_BUG = "https://github.com/flschubert/p-trahces/issues"
URL_HELP = URL_GITHUB_BUG # TODO set url
URL_LINKEDIN = "https://linkedin.com/in/f-schubert"
URL_PAPER = "" # TODO set url
URL_LOGO = URL_HELP

ICON_INFO = "ℹ️"
ICON_WARNING = "⚠️"

COLOUR_HEATING = "rgb(166, 0, 0)"
COLOUR_COOLING = "rgb(0, 0, 166)"
COLOUR_FLOATING = "thistle"

COLOUR_TEMPERATURE_ENVIRONMENT = "rgb(0, 140, 0)"
COLOUR_TEMPERATURE_VEHICLE = "black"
COLOUR_SOLAR_IRRADIATION = "rgb(249, 214, 0)"

COLOUR_HEAT_FLOW_HEATING = COLOUR_HEATING
COLOUR_HEAT_FLOW_COOLING = COLOUR_COOLING
COLOUR_HEAT_FLOW_SOLAR_ABSORPTION = COLOUR_SOLAR_IRRADIATION
COLOUR_HEAT_FLOW_PASSENGERS = "rgb(255, 153, 51)"
COLOUR_HEAT_FLOW_AUXILIARY_DEVICES = "rgb(140, 153, 140)"
COLOUR_HEAT_FLOW_CONVECTION = "rgb(102, 216, 102)"
COLOUR_HEAT_FLOW_AIR_VENTILATION = "rgb(51, 178, 178)"
COLOUR_HEAT_FLOW_AIR_DOORS = "rgb(153, 102, 229)"

COLOUR_ELECTRIC_HEATING_RESISTIVE = COLOUR_HEATING
COLOUR_ELECTRIC_POWER_HEAT_PUMP_HEATING = "coral"
COLOUR_ELECTRIC_POWER_HEAT_PUMP_COOLING = COLOUR_COOLING

dh.load_defaults()
CURRENCY = dh.get_parameter_option("units", "cost")



##### FUNCTIONS #####

def setup()->None:
    # TODO icon
    #icon = Image.open(PATH_ICON)
    st.set_page_config(
        page_title=PAGE_TITLE,
        #page_icon=icon,
        layout="wide",
        menu_items={"Report a Bug": URL_GITHUB_BUG, "Get help": URL_HELP,
                    "About": f"This website has been developed by Florian Schubert ([GitHub]({URL_GITHUB}) | [LinkedIn]({URL_LINKEDIN})). " +
                             "A journal article by Florian Schubert, André Bardow and Emiliano Casati is being published on the methodology and validation of the thermodynamic model. " +
                             "The default specification data is based on the Cobra tram fleet operated by [Verkehrsbetriebe Zürich](https://www.stadt-zuerich.ch/vbz.html) (VBZ) in Zurich, Switzerland, and has been provided by Geoffrey Klein and Fabio Inderbitzin. " +
                             "Location data (coordinates and location name) is retrieved from [Nominatim](https://nominatim.org) and climate data for a typical meteorological year from [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/). " +
                             "A guide and legal information can be found in the sidebar (top left arrow). By using this website, you agree to the terms of service."
        },
        initial_sidebar_state="expanded"
    )

    # TODO logo
    #logo = Image.open(PATH_LOGO)
    #st.logo(
    #    logo,
    #    link=URL_LOGO
    #)

    st.markdown("""
    <style>
    .block-container
    {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        margin-top: 0rem;
        margin-bottom: 0rem;
        margin-left: 0rem;
        margin-right: 0rem;
    }
    </style>
    """, unsafe_allow_html=True)



def sidebar():

    expander_acknowledgements = st.sidebar.expander("Acknowledgements", expanded=True)
    expander_acknowledgements.markdown(f"""
        This website has been developed by Florian Schubert ([GitHub]({URL_GITHUB}) | [LinkedIn]({URL_LINKEDIN})).
        
        A journal article by Florian Schubert, André Bardow and Emiliano Casati is being published on the methodology and validation of the thermodynamic model.
        
        The default specification data is mostly based on the Cobra tram fleet operated by [Verkehrsbetriebe Zürich](https://www.stadt-zuerich.ch/vbz.html) (VBZ) in Zurich, Switzerland, and has been provided by Geoffrey Klein and Fabio Inderbitzin.
        The journal article indicates the source for each parameter value (table A.2).
        
        Location data (coordinates and location name) is retrieved from [Nominatim](https://nominatim.org) and climate data for a typical meteorological year from [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/).
    """)
    # todo change sentence: A [journal article]({URL_PAPER}) by Florian Schubert, André Bardow and Emiliano Casati has been published on the methodology and validation of the thermodynamic model.

    expander_acknowledgements = st.sidebar.expander("User Guide", expanded=False)
    expander_acknowledgements.markdown(f"""
        The website is structured into to main sections: Specification and results (see tabs at page top).
        
        The vehicle(s), operation schedule(s) and scenario(s) need to be defined as follows, starting on the Specification tab.
        1. Define all temperature control curves that shall be used by the vehicles later-on.
        Each curve is defined by two list, one for heating and one cooling, each containing set-point temperatures for the vehicle cabin in dependence of the environmental temperature.
        2. Define all vehicles with their default parameters.
        Each vehicle needs to be linked to a specific (default) temperature control curve, defined in step 1.
        3. Define parameter alternatives for the vehicles for scenarios definition later-on.
        For each vehicle and parameter, a list of alternative values (to the default defined in step 2) can be specified.
        4. Define the operation schedules, specifying the timeframe and location, as well as list and number of vehicles in operation.
        5. Define scenarios, specifying which vehicle parameter set (see default values from step 2 and alternatives from step 3) should be used to simulate the operation schedules.
        6. Scroll up and switch to the Results tab.
        7. Enter your email, to be used only to retrieve location data from [Nominatim](https://nominatim.org).
        8. Click Calculate Results, to calculate the results.
        9. The result plots and tables can be displayed by expanding the respective sections (click on the tiles).
        
        Additional notes:
        - The specification can be adapted after calculating the results, but switching back to the results tab requires re-clicking the Calculate Results button.
        Otherwise, errors might arise.
        - The specification can be imported from a previous run or exported to be imported later-on.
        To use these functions, click on Import/export specification on the top (left) of the Specification tab.
        - The default values can be loaded in two ways:
        Globally, overwriting all specifications, using the Load default specification button on the top (right) of the Specification tab.
        Locally, by
        
    """)


    expander_license = st.sidebar.expander("License & Copyright", expanded=False)
    expander_license.markdown(f"""
        P-TRAHCES, Public Transport Heating and Cooling Energy Simulator

        Copyright (C) 2025 Florian Schubert
        
        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
        
        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
        
        You should have received a copy of the GNU General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>.
    """)

    expander_privacy = st.sidebar.expander("Privacy Policy", expanded=False)
    expander_privacy.markdown(f"""
        This website does not store or use personal data or information from users apart from the in the [Streamlit privacy notice](https://streamlit.io/privacy-policy?ref=streamlit) listed cases and purposes. 
        
        The service [Nominatim](https://nominatim.org) is used to retrieve location coordinates and full name.
        For this purpose, the user's email address and the location name are transmitted to the service.
        
        The database [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/) is used to retrieve climate data for a typical meteorological year.
        For this purpose, the location coordinates are transmitted to the service.
        The privacy policies of the respective service applies.
    """)


    expander_terms = st.sidebar.expander("Terms of Service", expanded=False)
    expander_terms.markdown(f"""
        Effective Date: 2025-05-10

        Welcome to {PAGE_TITLE} ("we", "us", or "our"). By accessing or using our website, located at [{PAGE_URL}]({PAGE_URL}) ("Website"), you agree to be bound by the following Terms of Service.
        
        Please read them carefully.
        
        The license and privacy policy stated above are part of these Terms of Service.
        
        ---
        
        #### 1. Services Provided
        
        Our Website allows users to submit input data, which is then processed using external services ("the Service").
        Our Website runs on [Streamlit](https://streamlit.io/) and uses the external services [Nominatim](https://nominatim.org) and [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/).
        The respective terms of service apply.
        The output provided is generated algorithmically and is intended for informational or illustrative purposes only.
        
        ---
        
        #### 2. User Responsibilities
        
        - You are solely responsible for the accuracy and legality of the input data you submit.
        - You agree not to use the Website for any unlawful or unauthorized purpose.
        
        ---
        
        #### 3. No Warranty & Limitation of Liability
        
        - The Service is provided "as is" and "as available" without warranties of any kind, either express or implied.
        - We make no guarantees regarding the accuracy, completeness, or usefulness of the output provided.
        - **To the fullest extent permitted by law, we disclaim all liability for any loss, damage, or harm (including consequential or indirect damages) arising out of or in connection with the use of our Website or reliance on its output.**
    
        ---
        
        #### 4. Modifications
        
        We reserve the right to change these Terms at any time.
        Continued use of the Website after such changes constitutes your acceptance of the revised Terms.
        
        ---
        
        #### 5. Governing Law and Jurisdiction
        
        These Terms shall be governed by and construed in accordance with the laws of Switzerland.
        Any disputes shall be subject to the exclusive jurisdiction of the competent courts of Zurich, Switzerland.
        
        ---
        
        #### 6. External Links

        Our Website may contain links to external websites or resources.
        These links are provided for convenience only and do not imply endorsement.  
        **We are not responsible for the content or practices of any third-party websites. Visiting external links is done at your own risk.**
        
        ---
        
        If you do not agree to these Terms, please do not use our Website.
    """)

    expander_notice = st.sidebar.expander("Legal Notice", expanded=False)
    expander_notice.write("Responsible for this website is:  \n  \n "
                          + "Emiliano Casati  \n ETH Zurich  \n Tannenstrasse 3  \n 8092 Zürich  \n Switzerland  \n  \n "
                          + "E-Mail: [casatie@ethz.ch](mailto:casatie@ethz.ch)")



def handle_import_export_specification()->None:

    # import/export dialog
    @st.dialog("Import & Export Specification", width="large")
    def dialog_import_export()->None:
        tab_import, tab_export = st.tabs(["Import", "Export"])

        # import tab
        tab_import.write("Import specification from JSON file")
        import_json = tab_import.file_uploader("File upload:", type="json", key="file_import")
        tab_import.write(ICON_WARNING + " Erroneous data in the input file can lead to unhandled errors.")
        tab_import.write(ICON_WARNING + " Import overwrites current specification!")
        if tab_import.button("Import & overwrite specification"):
            if import_json is None:
                tab_import.error("No file selected.")
            else:
                try:
                    import_str = StringIO(import_json.getvalue().decode("utf-8")).read()
                    tab_import.write(import_str)
                    import_dict = json.loads(import_str)
                    dh.import_specification_dictionary(st.session_state, import_dict)
                    st.rerun()
                except ValueError as e:
                    tab_import.error(e)

        # export tab

        tab_export.write("Current specification:")
        tab_export.json(st.session_state["specification"], expanded=1)
        if tab_export.download_button(
                "Export specification as JSON file",
                json.dumps(st.session_state["specification"], indent=4),
                file_name="specification.json"
            ):
            st.rerun()


    dialog_import_export()

    st.session_state["flag_stop"] = True



def handle_load_default_specification()->None:
    # confirmation dialog
    @st.dialog("Load Default Specification: " + dh.get_defaults("default_name"), width="large")
    def dialog_confirmation() -> None:
        st.write(ICON_WARNING + " Loading default specification overwrites current specification!")
        st.write("Do you want to proceed?")
        col1, col2 = st.columns(2)
        if col1.button("Overwrite & load default", use_container_width=True, key="load_default"):
            dh.load_default_specification(st.session_state)
            st.rerun()
        if col2.button("Cancel", use_container_width=True, key="cancel_load_default"):
            st.rerun()

    dialog_confirmation()

    st.session_state["flag_stop"] = True



# temperature curves


def temperature_curve_editor(container:st.delta_generator.DeltaGenerator)->None:

    # templates

    popover = container.popover("Load template", use_container_width=True)
    template_option = popover.selectbox("Select template:",
                                        ["Create empty curve", "Load curve from default", "Create constant curve"],
                                        key="option_template")
    if template_option is not None:
        if template_option == "Create empty curve":
            popover.write(ICON_WARNING + " Creating an empty curve overwrites the current curve.")

            if popover.button("Create curve", use_container_width=True, key="create_empty_curve"):
                dh.initialize_temperature_curve_empty(st.session_state, overwrite=True)
                popover.empty()

        elif template_option == "Load curve from default":
            default_curves = dh.get_defaults("temperature_control_curves")
            curve_option = popover.selectbox("Select default curve:", list(default_curves.keys()),
                                             key="option_default_curve")

            popover.write(ICON_WARNING + " Loading the default curve overwrites the current curve.")

            if popover.button("Load curve", use_container_width=True, key="load_default_curve"):
                dh.initialize_temperature_curve_default(st.session_state, curve_option)
                popover.empty()

        elif template_option == "Create constant curve":
            col1, col2 = popover.columns(2)
            heating_temperature = col1.number_input(
                "Environment [°C]:",
                value=15.0,
                step=0.01,
                format="%.2f",
                key=f"option_heating_temperature"
            )
            cooling_temperature = col2.number_input(
                "Vehicle [°C]:",
                value=20.0,
                step=0.01,
                format="%.2f",
                key=f"option_cooling_temperature"
            )

            popover.write(ICON_WARNING + " Generating the curve overwrites the current curve.")

            if popover.button("Generate curve", use_container_width=True, key="load_default_curve"):
                dh.initialize_temperature_curve_constant(st.session_state, heating_temperature, cooling_temperature)
                popover.empty()

    dh.initialize_temperature_curve_empty(st.session_state)

    points_heating = st.session_state["tmp"]["temperature_curve_editor"]["heating"]
    points_cooling = st.session_state["tmp"]["temperature_curve_editor"]["cooling"]



    # plot

    heating_x, heating_y, cooling_x, cooling_y, area_x, area_y, x_range, y_range =(
        dh.generate_temperature_curve_point_lists(points_heating, points_cooling))

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=area_x, y=area_y, fill='toself', mode='none', showlegend=True,
                             fillcolor=COLOUR_FLOATING, opacity=0.5, name="Floating", hoverinfo='text',
                             text="Temperature is not controlled in this area; heating and cooling are off."))

    fig.add_trace(go.Scatter(
        x=heating_x,
        y=heating_y,
        mode='lines+markers',
        name="Heating",
        line=dict(color=COLOUR_HEATING),
        marker=dict(size=10),
        legendrank=0
    ))

    fig.add_trace(go.Scatter(
        x=cooling_x,
        y=cooling_y,
        mode='lines+markers',
        name="Cooling",
        line=dict(color=COLOUR_COOLING),
        marker = dict(size=10),
        legendrank=1
    ))

    fig.update_layout(
        title="Temperature Curve",
        xaxis_title="Environment Temperature [°C]",
        yaxis_title="Vehicle Temperature [°C]",
        clickmode='event+select'
    )

    fig.update_layout(xaxis_range=x_range, yaxis_range=y_range)

    event_data = container.plotly_chart(
            fig,
            use_container_width=True,
            theme="streamlit",
            on_select="rerun",
            selection_mode="points",
            config={
                'modeBarButtonsToRemove': ['autoScale2d', 'lasso2d', 'select2d'],
                'displaylogo': False
            }
        )
    container.write("Click on a point to edit or remove it.")

    # point options

    def add_edit_popover(popover:st.delta_generator.DeltaGenerator, add:bool, heating:bool,
                         selected_index:int=None)-> None:

        points = []
        heating_cooling_str = ""
        if heating:
            points = points_heating
            heating_cooling_str = "heating"
        else:
            points = points_cooling
            heating_cooling_str = "cooling"

        add_str = ""
        if add:
            popover.write(f"Add temperature point:")
            add_str = "add"
        else:
            popover.write(f"Edit/remove {heating_cooling_str} temperature point:")
            add_str = "edit"

        value_environment = 0
        value_vehicle = 0
        if add:
            if len(points) == 0:
                if heating:
                    value_environment = 10.0
                    value_vehicle = 15.0
                else:
                    value_environment = 25.0
                    value_vehicle = 20.0
            else:
                if heating:
                    value_environment = points[-1][0] + 1
                    value_vehicle = points[-1][1]
                else:
                    value_environment = points[0][0] - 1
                    value_vehicle = points[0][1]
        else:
            value_environment = points[selected_index][0]
            value_vehicle = points[selected_index][1]

        popover_col1, popover_col2 = popover.columns(2)
        temperature_environment = popover_col1.number_input(
            "Environment temperature [°C]:",
            value=float(value_environment),
            step=0.01,
            format="%.2f",
            key=f"constant_{heating_cooling_str}_{add_str}_temperature_environment"
        )
        temperature_vehicle = popover_col2.number_input(
            f"{heating_cooling_str.capitalize()} temperature [°C]:",
            value=float(value_vehicle),
            step=0.01,
            format="%.2f",
            key=f"constant_{heating_cooling_str}_{add_str}_temperature_vehicle"
        )

        def add_point()->None:
            try:
                if heating:
                    dh.add_point_to_temporary_temperature_curve(points_heating, points_cooling, heating,
                                                                temperature_environment, temperature_vehicle)
                else:
                    dh.add_point_to_temporary_temperature_curve(points_heating, points_cooling, heating,
                                                                temperature_environment, temperature_vehicle)
                popover.empty()

            except ValueError as e:
                popover.error(e)

        def update_point()->None:
            try:
                dh.update_point_in_temporary_temperature_curve(points_heating, points_cooling, heating, selected_index,
                                                               temperature_environment, temperature_vehicle)
                popover.empty()
            except ValueError as e:
                popover.error(e)

        def remove_point() -> None:
            try:
                dh.remove_point_from_temporary_temperature_curve(points_heating, points_cooling, heating,
                                                                 selected_point["point_index"])
                popover.empty()
            except ValueError as e:
                popover.error(e)

        popover_col1, popover_col2 = popover.columns(2)
        if add:
            popover.button("Add point", on_click=add_point, use_container_width=True,
                           key=f"{heating_cooling_str}_add_point")
        else:
            popover_col1.button("Update", on_click=update_point, use_container_width=True,
                                key=f"{heating_cooling_str}_update_point")
            popover_col2.button("Remove", on_click=remove_point, use_container_width=True,
                                key=f"{heating_cooling_str}_remove_point")



    col1, col2 = container.columns(2)

    # add
    popover_add = col1.popover("Add point", use_container_width=True)
    index_heating_cooling = popover_add.selectbox("Select curve:", ["Heating", "Cooling"],
                                                  key="add_to_curve", index=0)
    if index_heating_cooling == "Heating":
        add_edit_popover(popover_add, True, True)
    else:
        add_edit_popover(popover_add, True, False)

    # edit
    edit_placeholder = col2.empty()
    if event_data is not None and len(event_data["selection"]["points"]) > 0:
        selected_point = event_data["selection"]["points"][0]

        popover_edit = edit_placeholder.popover("Edit or remove point", use_container_width=True)
        if selected_point["curve_number"] == 1:
            add_edit_popover(popover_edit, False, True,
                             selected_point["point_index"])
        elif selected_point["curve_number"] == 2:
            add_edit_popover(popover_edit, False, False,
                             selected_point["point_index"])



def handle_add_temperature_curve()->None:

    # dialog for name input and plot
    @st.dialog("Add Temperature Control Curve", width="large")
    def dialog_add_curve():

        name = st.text_input("Unique temperature curve name:",
                             max_chars=dh.get_parameter_option("temperature_control_curve", "name_char_length_max"))

        st.divider()

        temperature_curve_editor(st)

        st.divider()

        col1, col2 = st.columns(2)
        if col1.button("Add curve", use_container_width=True):
            try:
                dh.register_temperature_curve(st.session_state, name)
                st.rerun()
            except ValueError as e:
                st.error(e)
        if col2.button(f"Cancel", use_container_width=True):
            st.rerun()


    dh.clear_temperature_curve(st.session_state)

    dialog_add_curve()

    st.session_state["flag_stop"] = True



def handle_load_default_temperature_curves()->None:

    # check for registered curves
    registered_default_curves = dh.get_registered_default_temperature_curves(st.session_state)

    # overwrite dialog
    @st.dialog("Load and Overwrite Existing Temperature Controller Curves", width="large")
    def dialog_overwrite_curves()->None:
        st.write("The following curves are already defined and have an identical name as a default curve:")
        for curve in registered_default_curves:
            st.write(f"- {curve}")

        st.divider()

        st.write("Do you want to load all curves and overwrites the curves indicated above, "
                 "or do you only want to load the curves which are not yet defined?")

        col1, col2, col3 = st.columns([2, 2, 1])
        if col1.button("Load all & overwrite", use_container_width=True):
            dh.load_default_temperature_curves(st.session_state, overwrite=True)
            st.rerun()
        if col2.button("Load only undefined", use_container_width=True):
            dh.load_default_temperature_curves(st.session_state, overwrite=False)
            st.rerun()
        if col3.button("Cancel", use_container_width=True):
            st.rerun()

    # differentiating between loading and overwriting

    if len(registered_default_curves) == 0:
        dh.load_default_temperature_curves(st.session_state)
    else:
        dialog_overwrite_curves()

    st.session_state["flag_stop"] = True



def handle_edit_remove_temperature_curves()->None:

    # dialog for editing or removing curves
    @st.dialog("Edit or Remove Temperature Control Curve(s)", width="large")
    def dialog_edit_remove_curve():

        tab1, tab2, tab3 = st.tabs(["Rename curve", "Edit curve temperatures", "Remove curve(s)"])

        # edit curve name

        name_edit_name = tab1.selectbox(
            "Select curve:",
            list(st.session_state["specification"]["temperature_control_curves"].keys()),
            key="name_rename_curve"
        )

        if name_edit_name is not None:

            tab1.write("Rename curve")
            new_name = tab1.text_input("New name:", name_edit_name,
                                       max_chars=dh.get_parameter_option("temperature_control_curve", "name_char_length_max"))

            tab1.write(ICON_WARNING + " Only one curve can be edited at a time. "
                                      "Please click the rename button below to edit the name, before editing another curve.")

            col1, col2 = tab1.columns(2)
            if new_name is not None:
                if col1.button("Rename", use_container_width=True, key="rename_curve"):
                    try:
                        dh.rename_temperature_curve(st.session_state, name_edit_name, new_name)
                        st.rerun()
                    except ValueError as e:
                        tab1.error(e)
                if col2.button("Cancel", use_container_width=True, key="cancel_rename_curve"):
                    st.rerun()


        # edit curve temperatures

        name_edit_temperatures = tab2.selectbox(
            "Select curve:",
            list(st.session_state["specification"]["temperature_control_curves"].keys()),
            key="name_edit_curve_temperatures"
        )

        if name_edit_temperatures is not None:
            dh.load_registered_temperature_curve(st.session_state, name_edit_temperatures)

            tab2.divider()

            temperature_curve_editor(tab2)

            tab2.divider()

            tab2.write(ICON_WARNING + " Only one curve can be edited at a time. "
                                      "Please click the update button below to edit the curve, before editing another curve.")

            col1, col2 = tab2.columns(2)
            if col1.button("Update curve", use_container_width=True):
                try:
                    dh.update_temperature_curve(st.session_state, name_edit_temperatures)
                    dh.clear_temperature_curve(st.session_state)
                    st.rerun()
                except ValueError as e:
                    st.error(e)
            if col2.button(f"Cancel", use_container_width=True):
                dh.clear_temperature_curve(st.session_state)
                st.rerun()


        # remove curve(s)

        remove_col1, remove_col2 = tab3.columns([1, 2])
        remove_col1.write("Remove single curve")
        name_remove_curve = remove_col2.selectbox(
            "Select curve:",
            list(st.session_state["specification"]["temperature_control_curves"].keys()),
            key="name_remove_curve"
        )
        if name_remove_curve is not None:
            if remove_col2.button("Remove curve", use_container_width=True, key="remove_curve"):
                dh.remove_temperature_curve(st.session_state, name_remove_curve)
                st.rerun()

        tab3.divider()

        remove_col1, remove_col2 = tab3.columns([1, 2])
        remove_col1.write("Remove all curves")
        if remove_col2.button("Remove all curves", use_container_width=True, key="remove_all_curves"):
            dh.remove_all_temperature_curves(st.session_state)
            st.rerun()

        tab3.divider()

        if tab3.button("Cancel", use_container_width=True, key="cancel_remove_curve"):
            st.rerun()

    dh.clear_temperature_curve(st.session_state)

    dialog_edit_remove_curve()

    st.session_state["flag_stop"] = True



# vehicles


def handle_vehicle_specification_change(df:pd.DataFrame)->None:
    dh.update_vehicle_specification(st.session_state, df)



def handle_add_vehicle()->None:

    # function to add vehicle
    def add_vehicle(name:str, init_with_default_parameters:bool=False)->None:
        try:
            dh.add_vehicle(st.session_state, name, init_with_default_parameters)
            st.rerun()
        except ValueError as e:
            st.error(e)
            return

    # dialog for name input
    @st.dialog("Add Vehicle", width="large")
    def dialog_add_vehicle():
        name = st.text_input("Unique vehicle name:",
                             max_chars=dh.get_parameter_option("vehicle", "name_char_length_max"))

        col1, col2 = st.columns([2,5])
        default_vehicle_name = dh.get_defaults("vehicle")[0]

        if col1.button("Add", use_container_width=True):
            add_vehicle(name)
        if col2.button(f"Add with default parameters ({default_vehicle_name})", use_container_width=True):
            add_vehicle(name, init_with_default_parameters=True)

    dialog_add_vehicle()

    st.session_state["flag_stop"] = True



def handle_vehicles_set_default_parameters()->None:
    default_name = dh.get_defaults("vehicle")[0]

    # confirmation dialog
    @st.dialog(f"Set Vehicle Parameters to Default ({default_name})", width="large")
    def dialog_set_default_parameters():
        st.write(f"Fill empty or overwrite all vehicle parameters with default values ({default_name}):")
        overwrite = st.checkbox("Overwrite", key="overwrite_default_parameters", value=False)

        st.divider()

        action_str = "Fill empty parameters"
        if overwrite:
            action_str = "Overwrite all parameters"

        col1, col2 = st.columns([1, 2])
        col1.write("Apply for single vehicle")
        vehicle_name = col2.selectbox(
            "Select vehicle:", list(st.session_state["specification"]["vehicles"].keys()),
            key="set_default_vehicle_name"
        )
        if vehicle_name is not None:
            if col2.button(action_str + " of single vehicle", use_container_width=True, key="default_single_vehicle"):
                dh.set_default_parameters_vehicle(st.session_state, vehicle_name, overwrite=overwrite)
                st.rerun()

        st.divider()

        col1, col2 = st.columns([1, 2])
        col1.write("Apply for all vehicles")
        if col2.button(action_str + " of all vehicles", use_container_width=True, key="default_all_vehicles"):
            dh.set_default_parameters_all_vehicles(st.session_state, overwrite=overwrite)
            st.rerun()

        st.divider()

        if st.button("Cancel", use_container_width=True, key="cancel_default_vehicles"):
            st.rerun()


    dialog_set_default_parameters()

    st.session_state["flag_stop"] = True



def handle_edit_remove_vehicles()->None:

    # edit / remove dialog
    @st.dialog("Edit or Remove Vehicle(s)", width="large")
    def dialog_edit_remove_vehicles():
        tab_edit_name, tab_edit_devices, tab_remove = st.tabs(["Edit vehicle name",
                                                               "Edit heating & cooling devices",
                                                               "Remove vehicle(s)"])


        # edit name tab

        edit_name_vehicle_name = tab_edit_name.selectbox(
            "Select vehicle:", list(st.session_state["specification"]["vehicles"].keys()),
            key="edit_name_vehicle_name"
        )
        if edit_name_vehicle_name is not None:
            # rename vehicle
            tab_edit_name.write("Edit vehicle name")
            new_name = tab_edit_name.text_input("New name:", edit_name_vehicle_name,
                                                max_chars=dh.get_parameter_option("vehicle", "name_char_length_max"))

            tab_edit_name.write(ICON_WARNING + " Only one vehicle can be edited at a time. "
                                               "Please click the rename button below to edit the name, "
                                               "before editing another vehicle.")
            col1, col2 = tab_edit_name.columns(2)
            if new_name is not None:
                if col1.button("Rename", use_container_width=True, key="rename_vehicle"):
                    try:
                        dh.rename_vehicle(st.session_state, edit_name_vehicle_name, new_name)
                        st.rerun()
                    except ValueError as e:
                        tab_edit_name.error(e)
                if col2.button("Cancel", use_container_width=True, key="cancel_rename_vehicle"):
                    st.rerun()


        # edit heating & cooling devices tab

        edit_devices_vehicle_name = tab_edit_devices.selectbox(
            "Select vehicle:", list(st.session_state["specification"]["vehicles"].keys()),
            key="edit_devices_vehicle_name"
        )
        if edit_devices_vehicle_name is not None:

            # resistive heater

            tab_edit_devices.write("Resistive heater:")
            resistive_power_max = tab_edit_devices.number_input(
                "Maximum heating power [kW]:",
                value=st.session_state["specification"]["vehicles"][edit_devices_vehicle_name]["heating_cooling_devices"]["resistive_heating_power_max"],
                key="resistive_heating_power_max",
                min_value=dh.get_parameter_option("vehicle", "resistive_heating_power_min"),
                max_value=dh.get_parameter_option("vehicle", "resistive_heating_power_max"),
                step=dh.get_parameter_option("vehicle", "power_step"),
                format=dh.get_parameter_format_from_step("vehicle", "power_step")
            )


            # heat pumps

            tab_edit_devices.write("Heat pumps:")

            df_heat_pumps = dh.generate_dataframe_from_vehicle_heat_pumps(st.session_state, edit_devices_vehicle_name)
            name_char_length_max = dh.get_parameter_option("vehicle", "name_char_length_max")

            tab_edit_devices.data_editor(
                df_heat_pumps,
                hide_index=True,
                use_container_width=True,
                key="editor_heat_pumps",
                num_rows="dynamic",
                column_config={
                    "name": st.column_config.TextColumn(
                        "Name",
                        help=f"Unique heat pump name (maximum {name_char_length_max} characters)",
                        max_chars=name_char_length_max
                    ),
                    "electric_power_max": st.column_config.NumberColumn(
                        "Max. electric power [kW]",
                        help="Maximum electric power of the heat pump in kW",
                        min_value=dh.get_parameter_option("vehicle", "heat_pump_electric_power_min"),
                        max_value=dh.get_parameter_option("vehicle", "heat_pump_electric_power_max"),
                        step=dh.get_parameter_option("vehicle", "power_step"),
                        format=dh.get_parameter_format_from_step("vehicle", "power_step")
                    ),
                    "exergy_efficiency": st.column_config.NumberColumn(
                        "Exergy efficiency",
                        help="Exergy efficiency of the heat pump (relative to the Carnot efficiency)",
                        min_value=dh.get_parameter_option("vehicle", "fraction_min"),
                        max_value=dh.get_parameter_option("vehicle", "fraction_max"),
                        step=dh.get_parameter_option("vehicle", "fraction_step_fine"),
                        format=dh.get_parameter_format_from_step("vehicle", "fraction_step_fine"),
                    ),
                    "heating": st.column_config.CheckboxColumn(
                        "Heating",
                        help="Indicator whether the heat pump can be used for heating"
                    ),
                    "cooling": st.column_config.CheckboxColumn(
                        "Cooling",
                        help="Indicator whether the heat pump can be used for cooling"
                    )
                }
            )


            # confirmation

            tab_edit_devices.write(ICON_WARNING + " Only one vehicle can be edited at a time. "
                                               "Please click the save button below to edit the device configuration, "
                                                  "before editing another vehicle.")
            col1, col2 = tab_edit_devices.columns(2)
            if col1.button("Save configuration", use_container_width=True, key="save_device_configuration"):
                try:
                    dh.update_vehicle_heating_cooling_devices(st.session_state, edit_devices_vehicle_name,
                                                              resistive_power_max,
                                                              df_heat_pumps, st.session_state["editor_heat_pumps"])
                    st.rerun()
                except ValueError as e:
                    tab_edit_devices.error(e)
            if col2.button("Cancel", use_container_width=True, key="cancel_device_configuration"):
                st.rerun()


        # remove tab

        remove_col1, remove_col2 = tab_remove.columns([1,2])
        remove_col1.write("Remove single vehicle")
        remove_vehicle_name = remove_col2.selectbox(
            "Select vehicle:", list(st.session_state["specification"]["vehicles"].keys()),
            key="remove_vehicle_name"
        )
        if remove_vehicle_name is not None:
            if remove_col2.button("Remove vehicle", use_container_width=True, key="remove_vehicle"):
                dh.remove_vehicle(st.session_state, remove_vehicle_name)
                st.rerun()

        tab_remove.divider()

        remove_col1, remove_col2 = tab_remove.columns([1,2])
        remove_col1.write("Remove all vehicles")
        if remove_col2.button("Remove all vehicles", use_container_width=True, key="remove_all_vehicles"):
            dh.remove_all_vehicles(st.session_state)
            st.rerun()

        tab_remove.divider()

        if tab_remove.button("Cancel", use_container_width=True, key="cancel_remove_vehicle"):
            st.rerun()


    dialog_edit_remove_vehicles()

    st.session_state["flag_stop"] = True



# vehicle parameter alternatives

def handle_add_vehicle_parameter_alternative()->None:
    # dialog for name input
    @st.dialog("Add Vehicle Parameter Alternative", width="large")
    def dialog_add_alternative():
        vehicle = st.selectbox("Select vehicle:", list(st.session_state["specification"]["vehicles"].keys()),
                            key="vehicle_add_vehicle_alternative")
        if vehicle is not None:
            parameter_display_name = st.selectbox("Select parameter:", dh.get_vehicle_parameter_display_names(),
                                                 key="add_vehicle_alternative_parameter")

            if parameter_display_name is not None:
                col1, col2 = st.columns([3,2])

                if col1.button("Add alternative", use_container_width=True):
                    try:
                        dh.add_vehicle_parameter_alternative(st.session_state, vehicle, parameter_display_name)
                        st.rerun()
                    except ValueError as e:
                        st.error(e)
                        return
                if col2.button(f"Cancel", use_container_width=True):
                    st.rerun()

    dialog_add_alternative()

    st.session_state["flag_stop"] = True



def handle_load_default_vehicle_parameter_alternative()->None:
    # overwrite dialog
    @st.dialog("Overwrite Existing Vehicle Parameter Alternative", width="large")
    def dialog_overwrite_alternative(default_vehicle:str, default_parameter:str) -> None:
        parameter_display_name = dh.get_parameter_option("parameters_vehicle", default_parameter)
        st.write(f"The parameter alternative for vehicle \'{default_vehicle}\' and parameter \'{parameter_display_name}\' is already defined.")
        st.write("Do you want to overwrite this alternative or append missing default values to the alternative?")

        col1, col2, col3 = st.columns(3)
        if col1.button("Overwrite", use_container_width=True):
            dh.load_default_vehicle_parameter_alternative(st.session_state, append=False, overwrite=True)
            st.rerun()
        if col2.button("Append", use_container_width=True):
            dh.load_default_vehicle_parameter_alternative(st.session_state, append=True, overwrite=False)
            st.rerun()
        if col3.button("Cancel", use_container_width=True):
            st.rerun()

    # check for registered alternatives
    default_vehicle, default_parameter = dh.get_registered_default_vehicle_parameter_alternatives(st.session_state)
    if default_parameter is not None:
        dialog_overwrite_alternative(default_vehicle, default_parameter)
    else:
        dh.load_default_vehicle_parameter_alternative(st.session_state)

    st.session_state["flag_stop"] = True



def handle_edit_remove_vehicle_parameter_alternatives()->None:

    # dialog for editing or removing alternatives
    @st.dialog("Edit or Remove Vehicle Parameter Alternative(s)", width="large")
    def dialog_edit_remove_vehicle_alternatives():

        tab1, tab2 = st.tabs(["Edit alternative values", "Remove alternative(s)"])

        # edit alternatives

        alternative_vehicles = [alternative["vehicle"] for alternative in
                                st.session_state["specification"]["vehicle_parameter_alternatives"]]
        alternative_vehicles = list(dict.fromkeys(alternative_vehicles))

        vehicle_edit_alternative = tab1.selectbox("Select vehicle:", alternative_vehicles,
                                                  key="vehicle_edit_alternative")

        if vehicle_edit_alternative is not None:
            alternative_parameters = [
                dh.get_parameter_option("parameters_vehicle", alternative["parameter"])
                for alternative in st.session_state["specification"]["vehicle_parameter_alternatives"]
                if alternative["vehicle"] == vehicle_edit_alternative
            ]

            if alternative_parameters is None or len(alternative_parameters) == 0 or alternative_parameters[0] is None:
                alternative_parameters = []

            parameter_edit_alternative = tab1.selectbox("Select parameter:", alternative_parameters,
                                                        key="vehicle_edit_alternative_parameter")

            if parameter_edit_alternative is not None:
                if parameter_edit_alternative == dh.get_parameter_option("parameters_vehicle", "temperature_control_curve"):
                    values = []
                    for alternative in st.session_state["specification"]["vehicle_parameter_alternatives"]:
                        if (alternative["vehicle"] == vehicle_edit_alternative
                                and alternative["parameter"] == "temperature_control_curve"):
                            values = alternative["values"]
                    value_list = tab1.multiselect(
                        "Temperature control curve(s):",
                        st.session_state["specification"]["temperature_control_curves"].keys(),
                        default=values, key="vehicle_edit_alternative_curves"
                    )

                    tab1.write(ICON_WARNING + " Only one alternative can be edited at a time. "
                                              "Please click the update button below to edit the alternative, before editing another alternative.")

                    col1, col2 = tab1.columns(2)
                    if col1.button("Update alternative", use_container_width=True):
                        try:
                            dh.update_vehicle_parameter_alternative_temperature_curve(
                                st.session_state, vehicle_edit_alternative,
                                dh.convert_display_name_to_parameter_name(parameter_edit_alternative),
                                value_list
                            )
                            st.rerun()
                        except ValueError as e:
                            st.error(e)
                    if col2.button(f"Cancel", use_container_width=True):
                        st.rerun()
                else:
                    default_value_str = dh.generate_parameter_alternative_value_edit_str(
                        st.session_state, vehicle_edit_alternative,
                        dh.convert_display_name_to_parameter_name(parameter_edit_alternative)
                    )
                    if default_value_str is not None:
                        value_str = tab1.text_input(
                            "Value(s):",
                            default_value_str,
                            placeholder="Select alternative value(s)",
                            key="vehicle_edit_alternative_values"
                        )
                    else:
                        value_str = tab1.text_input(
                            "Value(s):",
                            placeholder="Select alternative value(s)",
                            key="vehicle_edit_alternative_values"
                        )

                    tab1.write(ICON_WARNING + " Only one alternative can be edited at a time. "
                                              "Please click the update button below to edit the alternative, before editing another alternative.")

                    col1, col2 = tab1.columns(2)
                    if col1.button("Update alternative", use_container_width=True):
                        try:
                            dh.update_vehicle_parameter_alternative_float(
                                st.session_state, vehicle_edit_alternative,
                                dh.convert_display_name_to_parameter_name(parameter_edit_alternative),
                                value_str
                            )
                            st.rerun()
                        except ValueError as e:
                            st.error(e)
                    if col2.button(f"Cancel", use_container_width=True):
                        st.rerun()

        # remove curve(s)

        remove_col1, remove_col2 = tab2.columns([1, 2])
        remove_col1.write("Remove single alternative")

        alternative_vehicles = [alternative["vehicle"] for alternative in
                                st.session_state["specification"]["vehicle_parameter_alternatives"]]
        alternative_vehicles = list(dict.fromkeys(alternative_vehicles))

        vehicle_remove_alternative = remove_col2.selectbox("Select vehicle:", alternative_vehicles,
                                                    key="vehicle_remove_alternative")

        if vehicle_remove_alternative is not None:
            alternative_parameters = [
                dh.get_parameter_option("parameters_vehicle", alternative["parameter"])
                for alternative in st.session_state["specification"]["vehicle_parameter_alternatives"]
                if alternative["vehicle"] == vehicle_edit_alternative
            ]

            parameter_remove_alternative = remove_col2.selectbox("Select parameter:", alternative_parameters,
                                                                 key="vehicle_remove_alternative_parameter")

            if parameter_remove_alternative is not None:
                if remove_col2.button("Remove alternative", use_container_width=True, key="remove_vehicle_alternative"):
                    dh.remove_vehicle_parameter_alternative(
                        st.session_state, vehicle_remove_alternative,
                        dh.convert_display_name_to_parameter_name(parameter_remove_alternative)
                    )
                    st.rerun()

        tab2.divider()

        remove_col1, remove_col2 = tab2.columns([1, 2])
        remove_col1.write("Remove all alternatives")
        if remove_col2.button("Remove all alternatives", use_container_width=True, key="remove_all_vehicle_alternatives"):
            dh.remove_all_vehicle_parameter_alternatives(st.session_state)
            st.rerun()

        tab2.divider()

        if tab2.button("Cancel", use_container_width=True, key="cancel_remove_vehicle_alternatives"):
            st.rerun()

    dialog_edit_remove_vehicle_alternatives()

    st.session_state["flag_stop"] = True



# operation schedules


def handle_operation_schedule_specification_change(df:pd.DataFrame)->None:
    dh.update_operation_schedule_specification(st.session_state, df)



def handle_add_operation_schedule()->None:

    # function to add schedule
    def add_schedule(name:str, init_with_default_parameters:bool=False)->None:
        try:
            dh.add_operation_schedule(st.session_state, name, init_with_default_parameters)
            st.rerun()
        except ValueError as e:
            st.error(e)
            return

    # dialog for name input
    @st.dialog("Add Operation Schedule", width="large")
    def dialog_add_schedule():
        name = st.text_input("Unique schedule name:",
                             max_chars=dh.get_parameter_option("operation_schedule", "name_char_length_max"))

        col1, col2 = st.columns([2,5])
        default_schedule_name = dh.get_defaults("operation_schedule")[0]

        if col1.button("Add", use_container_width=True):
            add_schedule(name)
        if col2.button(f"Add with default parameters ({default_schedule_name})", use_container_width=True):
            add_schedule(name, init_with_default_parameters=True)

    dialog_add_schedule()

    st.session_state["flag_stop"] = True



def handle_operation_schedules_set_default_parameters()->None:
    default_name = dh.get_defaults("operation_schedule")[0]

    # confirmation dialog
    @st.dialog(f"Set Parameters to Default ({default_name})", width="large")
    def dialog_set_default_parameters():
        st.write(f"Fill empty or overwrite all operation schedule parameters except for \'Vehicle types and amounts\' with default values ({default_name}):")
        overwrite = st.checkbox("Overwrite", key="operation_schedule_overwrite_default_parameters", value=False)

        st.divider()

        action_str = "Fill empty parameters"
        if overwrite:
            action_str = "Overwrite all parameters"

        col1, col2 = st.columns([1, 2])
        col1.write("Apply for single schedule")
        schedule_name = col2.selectbox(
            "Select schedule:", list(st.session_state["specification"]["operation_schedules"].keys()),
            key="set_default_operation_schedule_name"
        )
        if schedule_name is not None:
            if col2.button(action_str + " of single schedule", use_container_width=True, key="default_single_schedule"):
                dh.set_default_parameters_operation_schedule(st.session_state, schedule_name, overwrite=overwrite)
                st.rerun()

        st.divider()

        col1, col2 = st.columns([1, 2])
        col1.write("Apply for all schedules")
        if col2.button(action_str + " of all schedules", use_container_width=True, key="default_all_schedules"):
            dh.set_default_parameters_all_operation_schedules(st.session_state, overwrite=overwrite)
            st.rerun()

        st.divider()

        if st.button("Cancel", use_container_width=True, key="cancel_default_schedules"):
            st.rerun()

    dialog_set_default_parameters()

    st.session_state["flag_stop"] = True



def handle_edit_remove_operation_schedules()->None:
    # edit / remove dialog
    @st.dialog("Edit or Remove Operation Schedule(s)", width="large")
    def dialog_edit_remove_operation_schedules():
        tab_edit_name, tab_edit_vehicles, tab_remove = st.tabs(["Edit schedule name",
                                                                "Edit vehicles in operation",
                                                                "Remove schedule(s)"])

        # edit name tab

        edit_name_schedule_name = tab_edit_name.selectbox(
            "Select schedule:", list(st.session_state["specification"]["operation_schedules"].keys()),
            key="edit_name_schedule_name"
        )
        if edit_name_schedule_name is not None:
            # rename schedule
            tab_edit_name.write("Edit schedule name")
            new_name = tab_edit_name.text_input("New name:", edit_name_schedule_name,
                                                max_chars=dh.get_parameter_option("operation_schedule", "name_char_length_max"))

            col1, col2 = tab_edit_name.columns(2)
            if new_name is not None:
                if col1.button("Rename", use_container_width=True, key="rename_schedule"):
                    try:
                        dh.rename_operation_schedule(st.session_state, edit_name_schedule_name, new_name)
                        st.rerun()
                    except ValueError as e:
                        tab_edit_name.error(e)
                if col2.button("Cancel", use_container_width=True, key="cancel_rename_schedule"):
                    st.rerun()

        # edit vehicles

        edit_vehicles_schedule_name = tab_edit_vehicles.selectbox(
            "Select schedule:", list(st.session_state["specification"]["operation_schedules"].keys()),
            key="edit_vehicle_schedule_name"
        )
        if edit_vehicles_schedule_name is not None:

            tab_edit_vehicles.write("Vehicles in operation:")

            df_vehicles = dh.generate_dataframe_from_operation_schedule_vehicles(st.session_state, edit_vehicles_schedule_name)

            tab_edit_vehicles.data_editor(
                df_vehicles,
                hide_index=True,
                use_container_width=True,
                key="editor_operation_schedule_vehicles",
                column_config={
                    "vehicle": st.column_config.TextColumn(
                        "Vehicle type",
                        help=f"Vehicle type",
                        disabled=True
                    ),
                    "number": st.column_config.NumberColumn(
                        "Number of vehicles in operation",
                        help="Number of vehicles in operation",
                        min_value=0,
                        max_value=dh.get_parameter_option("operation_schedule", "vehicle_number_max"),
                        step=1,
                        format="%d"
                    )
                }
            )

            # confirmation

            col1, col2 = tab_edit_vehicles.columns(2)
            if col1.button("Save configuration", use_container_width=True, key="save_schedule_configuration"):
                try:
                    dh.update_operation_schedule_vehicles(st.session_state, edit_vehicles_schedule_name, df_vehicles,
                                                          st.session_state["editor_operation_schedule_vehicles"])
                    st.rerun()
                except ValueError as e:
                    tab_edit_vehicles.error(e)
            if col2.button("Cancel", use_container_width=True, key="cancel_schedule_configuration"):
                st.rerun()

        # remove tab

        remove_col1, remove_col2 = tab_remove.columns([1, 2])
        remove_col1.write("Remove single schedule")
        remove_schedule_name = remove_col2.selectbox(
            "Select schedule:", list(st.session_state["specification"]["operation_schedules"].keys()),
            key="remove_schedule_name"
        )
        if remove_schedule_name is not None:
            if remove_col2.button("Remove schedule", use_container_width=True, key="remove_schedule"):
                dh.remove_operation_schedule(st.session_state, remove_schedule_name)
                st.rerun()

        tab_remove.divider()

        remove_col1, remove_col2 = tab_remove.columns([1, 2])
        remove_col1.write("Remove all schedules")
        if remove_col2.button("Remove all schedules", use_container_width=True, key="remove_all_schedules"):
            dh.remove_all_operation_schedules(st.session_state)
            st.rerun()

        tab_remove.divider()

        if tab_remove.button("Cancel", use_container_width=True, key="cancel_remove_schedules"):
            st.rerun()

    dialog_edit_remove_operation_schedules()

    st.session_state["flag_stop"] = True



# scenarios


def handle_scenarios_specification_change(df:pd.DataFrame)->None:
    dh.update_scenario_specification(st.session_state, df)



def handle_add_scenario():
    # dialog for name input
    @st.dialog("Add Scenario")
    def dialog_add_scenario():
        name = st.text_input("Unique scenario name:",
                             max_chars=dh.get_parameter_option("scenario", "name_char_length_max"))

        col1, col2 = st.columns(2)

        if col1.button("Add", use_container_width=True):
            try:
                dh.add_scenario(st.session_state, name)
                st.rerun()
            except ValueError as e:
                st.error(e)
        if col2.button("Cancel", use_container_width=True):
            st.rerun()

    dialog_add_scenario()

    st.session_state["flag_stop"] = True



def handle_rename_remove_scenarios():
    # edit / remove dialog
    @st.dialog("Rename or Remove Scenario(s)", width="large")
    def dialog_rename_remove_scenarios():
        tab_edit_name, tab_remove = st.tabs(["Edit scenario name", "Remove scenario(s)"])

        # edit name tab

        edit_name_scenario_name = tab_edit_name.selectbox(
            "Select scenario:", list(st.session_state["specification"]["scenarios"].keys()),
            key="edit_name_scenario_name"
        )
        if edit_name_scenario_name is not None:
            # rename scenario
            tab_edit_name.write("Edit scenario name")
            new_name = tab_edit_name.text_input("New name:", edit_name_scenario_name,
                                                max_chars=dh.get_parameter_option("scenario",
                                                                                  "name_char_length_max"))

            tab_edit_name.write(ICON_WARNING + " Only one scenario can be edited at a time. "
                                               "Please click the rename button below to edit the name, "
                                               "before editing another scenario.")
            col1, col2 = tab_edit_name.columns(2)
            if new_name is not None:
                if col1.button("Rename", use_container_width=True, key="rename_scenario"):
                    try:
                        dh.rename_scenario(st.session_state, edit_name_scenario_name, new_name)
                        st.rerun()
                    except ValueError as e:
                        tab_edit_name.error(e)
                if col2.button("Cancel", use_container_width=True, key="cancel_rename_scenario"):
                    st.rerun()

        # remove tab

        remove_col1, remove_col2 = tab_remove.columns([1, 2])
        remove_col1.write("Remove single scenario")
        remove_scenario_name = remove_col2.selectbox(
            "Select scenario:", list(st.session_state["specification"]["scenarios"].keys()),
            key="remove_scenario_name"
        )
        if remove_scenario_name is not None:
            if remove_col2.button("Remove scenario", use_container_width=True, key="remove_vehicle"):
                dh.remove_scenario(st.session_state, remove_scenario_name)
                st.rerun()

        tab_remove.divider()

        remove_col1, remove_col2 = tab_remove.columns([1, 2])
        remove_col1.write("Remove all scenarios")
        if remove_col2.button("Remove all scenarios", use_container_width=True, key="remove_all_scenarios"):
            dh.remove_all_scenarios(st.session_state)
            st.rerun()

        tab_remove.divider()

        if tab_remove.button("Cancel", use_container_width=True, key="cancel_remove_scenarios"):
            st.rerun()

    dialog_rename_remove_scenarios()

    st.session_state["flag_stop"] = True



# general


def generate_specification_tab(tab:st.delta_generator.DeltaGenerator)->None:
    tab.write("## Specification")

    # import & export

    col1, col2 = tab.columns(2)
    col1.button("Import/export specification", on_click=handle_import_export_specification,
               key="import_export_specification", use_container_width=True)

    col2.button("Load default specification (" + dh.get_defaults("default_name") + ")",
                on_click=handle_load_default_specification,
                key="load_default_specification", use_container_width=True)

    # temperature control curves

    tab.write("### Temperature Control Curves")

    container_temperature_curves = tab.container()
    df_temperature_curves = container_temperature_curves.data_editor(
        dh.generate_dataframe_from_temperature_curves(st.session_state),
        hide_index=False,
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn(
                "Name",
                help="Unique temperature control curve name  (to edit, please click button \'Edit or remove curves(s)\' below)",
                disabled=True
            ),
            "temperature_heating_max": st.column_config.NumberColumn(
                "Max. heating temperature [°C]",
                help="Maximum heating temperature in °C",
                format=dh.get_parameter_format_from_step("temperature_control_curve", "temperature_step"),
                disabled=True
            ),
            "temperature_cooling_min": st.column_config.NumberColumn(
                "Min. cooling temperature [°C]",
                help="Minimum cooling temperature in °C",
                format=dh.get_parameter_format_from_step("temperature_control_curve", "temperature_step"),
                disabled=True
            )
        }
    )

    temperature_curve_col1, temperature_curve_col2, temperature_curve_col3 = tab.columns(3)
    temperature_curve_col1.button("Add curve", on_click=handle_add_temperature_curve,
                                  key="add_temperature_curve", use_container_width=True)
    temperature_curve_col2.button(f"Load default curves", on_click=handle_load_default_temperature_curves,
                                  key="add_default_temperature_curves", use_container_width=True)
    temperature_curve_col3.button("Edit or remove curve(s)", on_click=handle_edit_remove_temperature_curves,
                                  key="edit_remove_temperature_curve", use_container_width=True)



    # vehicle specification

    tab.write("### Vehicles")

    container_vehicle = tab.container()

    default_vehicle_name, default_vehicle_data = dh.get_defaults("vehicle")
    vehicles_temperature_control_curve_names = dh.get_temperature_control_curve_names(st.session_state)
    df_vehicles = container_vehicle.data_editor(
        dh.generate_dataframe_from_vehicles(st.session_state),
        hide_index=False,
        use_container_width=True,
        column_config={
            # todo add line breaks to shorten columns
            "name": st.column_config.TextColumn(
                dh.get_parameter_option("parameters_vehicle", "name"),
                help="Unique vehicle name (to edit, please click button \'Edit or remove vehicle(s)\' below)",
                disabled=True,
                required=True
            ),
            "length": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "length"),
                help="Vehicle length in meters",
                min_value=dh.get_parameter_option("vehicle", "length_min"),
                max_value=dh.get_parameter_option("vehicle", "length_max"),
                step=dh.get_parameter_option("vehicle", "geometry_step"),
                format=dh.get_parameter_format_from_step("vehicle", "geometry_step"),
                required=True
            ),
            "width": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "width"),
                help="Vehicle width in meters",
                min_value=dh.get_parameter_option("vehicle", "width_min"),
                max_value=dh.get_parameter_option("vehicle", "width_max"),
                step=dh.get_parameter_option("vehicle", "geometry_step"),
                format=dh.get_parameter_format_from_step("vehicle", "geometry_step"),
                required=True
            ),
            "height": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "height"),
                help="Vehicle height in meters",
                min_value=dh.get_parameter_option("vehicle", "height_min"),
                max_value=dh.get_parameter_option("vehicle", "height_max"),
                step=dh.get_parameter_option("vehicle", "geometry_step"),
                format=dh.get_parameter_format_from_step("vehicle", "geometry_step"),
                required=True
            ),
            "door_height": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "door_height"),
                help="Door height in meters",
                min_value=dh.get_parameter_option("vehicle", "door_height_min"),
                max_value=dh.get_parameter_option("vehicle", "door_height_max"),
                step=dh.get_parameter_option("vehicle", "geometry_step"),
                format=dh.get_parameter_format_from_step("vehicle", "geometry_step"),
                required=True
            ),
            "door_width_total": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "door_width_total"),
                help="Total width of all doors in meters",
                min_value=dh.get_parameter_option("vehicle", "door_width_total_min"),
                max_value=dh.get_parameter_option("vehicle", "door_width_total_max"),
                step=dh.get_parameter_option("vehicle", "geometry_step"),
                format=dh.get_parameter_format_from_step("vehicle", "geometry_step"),
                required=True
            ),
            "area_windows_front": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "area_windows_front"),
                help="Area of windows on the front side of the vehicle in square meters"
                     " (identical value is assumed for rear side)",
                min_value=dh.get_parameter_option("vehicle", "area_windows_front_min"),
                max_value=dh.get_parameter_option("vehicle", "area_windows_front_max"),
                step=dh.get_parameter_option("vehicle", "geometry_step"),
                format=dh.get_parameter_format_from_step("vehicle", "geometry_step"),
                required=True
            ),
            "area_windows_side": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "area_windows_side"),
                help="Area of windows on each side of the vehicle in square meters",
                min_value=dh.get_parameter_option("vehicle", "area_windows_side_min"),
                max_value=dh.get_parameter_option("vehicle", "area_windows_side_max"),
                step=dh.get_parameter_option("vehicle", "geometry_step"),
                format=dh.get_parameter_format_from_step("vehicle", "geometry_step"),
                required=True
            ),
            "time_fraction_door_open": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "time_fraction_door_open"),
                help="Time fraction during which the doors are opened",
                min_value=dh.get_parameter_option("vehicle", "fraction_min"),
                max_value=dh.get_parameter_option("vehicle", "fraction_max"),
                step=dh.get_parameter_option("vehicle", "fraction_step"),
                format=dh.get_parameter_format_from_step("vehicle", "fraction_step"),
                required=True
            ),
            "fraction_obstruction_roof": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "fraction_obstruction_roof"),
                help="Fraction of the roof area that is obstructed (e.g. by battery installations on the roof)",
                min_value=dh.get_parameter_option("vehicle", "fraction_min"),
                max_value=dh.get_parameter_option("vehicle", "fraction_max"),
                step=dh.get_parameter_option("vehicle", "fraction_step"),
                format=dh.get_parameter_format_from_step("vehicle", "fraction_step"),
                required=True
            ),
            "fraction_obstruction_floor": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "fraction_obstruction_floor"),
                help="Fraction of the floor area that is obstructed (e.g. by drive train)",
                min_value=dh.get_parameter_option("vehicle", "fraction_min"),
                max_value=dh.get_parameter_option("vehicle", "fraction_max"),
                step=dh.get_parameter_option("vehicle", "fraction_step"),
                format=dh.get_parameter_format_from_step("vehicle", "fraction_step"),
                required=True
            ),
            "heat_transfer_coefficient_chassis": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "heat_transfer_coefficient_chassis"),
                help="Thermal conductivity of the chassis in W/(m²K)",
                min_value=dh.get_parameter_option("vehicle", "heat_transfer_coefficient_min"),
                max_value=dh.get_parameter_option("vehicle", "heat_transfer_coefficient_max"),
                step=dh.get_parameter_option("vehicle", "heat_transfer_coefficient_step"),
                format=dh.get_parameter_format_from_step("vehicle", "heat_transfer_coefficient_step"),
                required=True
            ),
            "cabin_absorptivity": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "cabin_absorptivity"),
                help="Absorptivity of the cabin frame (non-window)",
                min_value=dh.get_parameter_option("vehicle", "fraction_min"),
                max_value=dh.get_parameter_option("vehicle", "fraction_max"),
                step=dh.get_parameter_option("vehicle", "fraction_step"),
                format=dh.get_parameter_format_from_step("vehicle", "fraction_step"),
                required=True
            ),
            "window_transmissivity": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "window_transmissivity"),
                help="Transmissivity of the windows",
                min_value=dh.get_parameter_option("vehicle", "fraction_min"),
                max_value=dh.get_parameter_option("vehicle", "fraction_max"),
                step=dh.get_parameter_option("vehicle", "fraction_step"),
                format=dh.get_parameter_format_from_step("vehicle", "fraction_step"),
                required=True
            ),
            "volume_flow_rate_ventilation": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "volume_flow_rate_ventilation"),
                help="Volume flow rate of the ventilation system in m³/s",
                min_value=dh.get_parameter_option("vehicle", "volume_flow_rate_min"),
                max_value=dh.get_parameter_option("vehicle", "volume_flow_rate_max"),
                step=dh.get_parameter_option("vehicle", "volume_flow_rate_step"),
                format=dh.get_parameter_format_from_step("vehicle", "volume_flow_rate_step"),
                required=True
            ),
            "heating_power_auxiliary": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_vehicle", "heating_power_auxiliary"),
                help="Power of the auxiliary heating system in kW",
                min_value=dh.get_parameter_option("vehicle", "heating_power_auxiliary_min"),
                max_value=dh.get_parameter_option("vehicle", "heating_power_auxiliary_max"),
                step=dh.get_parameter_option("vehicle", "power_step"),
                format=dh.get_parameter_format_from_step("vehicle", "power_step"),
                required=True
            ),
            "temperature_control_curve": st.column_config.SelectboxColumn(
                dh.get_parameter_option("parameters_vehicle", "temperature_control_curve"),
                help="Temperature control curve for the vehicle (specify control curves above)",
                options=vehicles_temperature_control_curve_names,
                required=True
            ),
            "heating_cooling_devices": st.column_config.TextColumn(
                dh.get_parameter_option("parameters_vehicle", "heating_cooling_devices"),
                help="List of heating and cooling devices with their specifications"
                     " (to edit, please click button \'Edit or remove vehicle(s)\' below)",
                disabled=True,
                required=True
            )
        }
    )
    if df_vehicles is not None:
        #print("MAIN:")
        #print(df_vehicles)
        # TODO fix variable update in df_vehicles
        # on changing a second variable, the value has to be changed twice as for the first time,
        # handle_vehicle_specification_change is called but with the old value
        handle_vehicle_specification_change(df_vehicles)

    vehicle_col1, vehicle_col2, vehicle_col3 = tab.columns(3)
    vehicle_col1.button("Add vehicle", on_click=handle_add_vehicle,
                        key="add_vehicle", use_container_width=True)
    vehicle_col2.button(f"Set to default parameters", on_click=handle_vehicles_set_default_parameters,
                        key="set_to_default_parameters", use_container_width=True)
    vehicle_col3.button("Edit or remove vehicle(s)", on_click=handle_edit_remove_vehicles,
                        key="edit_remove_vehicle", use_container_width=True)


    # vehicle parameter alternative

    tab.write("##### Parameter Alternatives")

    container_vehicle_alternatives = tab.container()

    container_vehicle_alternatives.data_editor(
        dh.generate_dataframe_from_vehicle_parameter_alternatives(st.session_state),
        hide_index=True,
        use_container_width=True,
        column_config={
            "vehicle": st.column_config.TextColumn(
                "Vehicle",
                help="Vehicle type, defined above",
                disabled=True
            ),
            "parameter": st.column_config.TextColumn(
                "Parameter",
                help="Parameter that is modified",
                disabled=True
            ),
            "value_default": st.column_config.TextColumn(
                "Default value",
                help="Default value as specified in vehicle definition",
                disabled=True
            ),
            "values_alternative": st.column_config.ListColumn(
                "Alternative value(s)",
                help="Alternative value(s) for the parameter",
            )
        }
    )

    alternative_vehicle_col1, alternative_vehicle_col2, alternative_vehicle_col3 = container_vehicle_alternatives.columns(3)
    alternative_vehicle_col1.button("Add alternative", on_click=handle_add_vehicle_parameter_alternative,
                                    key="add_vehicle_alternative", use_container_width=True)
    alternative_vehicle_col2.button(f"Load default alternative", on_click=handle_load_default_vehicle_parameter_alternative,
                                    key="load_vehicle_default_alternative", use_container_width=True)
    alternative_vehicle_col3.button("Edit or remove alternative(s)", on_click=handle_edit_remove_vehicle_parameter_alternatives,
                                    key="edit_remove_vehicle_alternative", use_container_width=True)


    # operation schedules

    tab.write("### Operation Schedules")

    container_operation_schedules = tab.container()
    df_operation_schedules = container_operation_schedules.data_editor(
        # TODO correct format of date & time editors
        dh.generate_dataframe_from_operation_schedules(st.session_state),
        hide_index=False,
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn(
                dh.get_parameter_option("parameters_operation_schedule", "name"),
                help="Unique operation schedule name (to edit, please click button \'Edit or remove schedule(s)\' below)",
                disabled=True
            ),
            "location": st.column_config.TextColumn(
                dh.get_parameter_option("parameters_operation_schedule", "location"),
                help="Location of operation (city)",
                required=True
            ),
            "date_begin": st.column_config.DateColumn(
                dh.get_parameter_option("parameters_operation_schedule", "date_begin"),
                help="Date of operations begin (without year) [MM-DD]",
                format="MM-DD",
                min_value=dh.convert_str_to_date("01-01"),
                max_value=dh.convert_str_to_date("12-31"),
                required=True
            ),
            "date_end": st.column_config.DateColumn(
                dh.get_parameter_option("parameters_operation_schedule", "date_end"),
                help="Date of operations end (without year) [MM-DD]",
                format="MM-DD",
                min_value=dh.convert_str_to_date("01-01"),
                max_value=dh.convert_str_to_date("12-31"),
                required=True
            ),
            "time_begin": st.column_config.TimeColumn(
                dh.get_parameter_option("parameters_operation_schedule", "time_begin"),
                help="Time of daily operations begin [HH:MM]",
                format="HH:mm",
                step=datetime.timedelta(minutes=1),
                required=True
            ),
            "time_end": st.column_config.TimeColumn(
                dh.get_parameter_option("parameters_operation_schedule", "time_end"),
                help="Time of daily operations end [HH:MM]",
                format="HH:mm",
                step=datetime.timedelta(minutes=1),
                required=True
            ),
            "passenger_number": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_operation_schedule", "passenger_number"),
                help="Average number of passengers throughout operations schedule",
                min_value=dh.get_parameter_option("operation_schedule", "passenger_number_min"),
                max_value=dh.get_parameter_option("operation_schedule", "passenger_number_max"),
                step=dh.get_parameter_option("operation_schedule", "passenger_number_step"),
                format=dh.get_parameter_format_from_step("operation_schedule", "passenger_number_step"),
                required=True
            ),
            "obstacle_distance": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_operation_schedule", "obstacle_distance"),
                help="Average distance to obstacles shielding the sun perpendicular to the vehicle driving direction, such as houses, trees, walls, hills, etc.",
                min_value=dh.get_parameter_option("operation_schedule", "obstacle_distance_min"),
                max_value=dh.get_parameter_option("operation_schedule", "obstacle_distance_max"),
                step=dh.get_parameter_option("operation_schedule", "geometry_step"),
                format=dh.get_parameter_format_from_step("operation_schedule", "geometry_step"),
                required=True
            ),
            "obstacle_height": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_operation_schedule", "obstacle_height"),
                help="Average height of obstacles shielding the sun, such as houses, trees, walls, hills, etc.",
                min_value=dh.get_parameter_option("operation_schedule", "obstacle_height_min"),
                max_value=dh.get_parameter_option("operation_schedule", "obstacle_height_max"),
                step=dh.get_parameter_option("operation_schedule", "geometry_step"),
                format=dh.get_parameter_format_from_step("operation_schedule", "geometry_step"),
                required=True
            ),
            "cost_electricity": st.column_config.NumberColumn(
                dh.get_parameter_option("parameters_operation_schedule", "cost_electricity"),
                help="Average cost of electricity per mega-watt hour",
                min_value=dh.get_parameter_option("operation_schedule", "cost_min"),
                max_value=dh.get_parameter_option("operation_schedule", "cost_max"),
                step=dh.get_parameter_option("operation_schedule", "cost_step"),
                format=dh.get_parameter_format_from_step("operation_schedule", "cost_step"),
                required=True
            ),
            "vehicles_in_operation": st.column_config.TextColumn(
                dh.get_parameter_option("parameters_operation_schedule", "vehicles_in_operation"),
                help="List of used vehicles with their amounts"
                     " (to edit, please click button \'Edit or remove schedule(s)\' below)",
                disabled=True,
                required=True
            )
        }
    )
    if df_operation_schedules is not None:
        # TODO fix variable update in df_operation_schedules
        # on changing a second variable, the value has to be changed twice as for the first time,
        # handle_vehicle_specification_change is called but with the old value
        handle_operation_schedule_specification_change(df_operation_schedules)

    operation_schedule_col1, operation_schedule_col2, operation_schedule_col3 = tab.columns(3)
    operation_schedule_col1.button("Add schedule", on_click=handle_add_operation_schedule,
                        key="add_operation_schedule", use_container_width=True)
    operation_schedule_col2.button(f"Set to default parameters", on_click=handle_operation_schedules_set_default_parameters,
                        key="default_operation_set_schedule_parameters", use_container_width=True)
    operation_schedule_col3.button("Edit or remove schedule(s)", on_click=handle_edit_remove_operation_schedules,
                                  key="edit_remove_operation_schedules", use_container_width=True)



    # scenarios

    tab.write("### Scenarios")

    column_config_scenarios = {
        "name": st.column_config.TextColumn(
            "Name",
            help="Scenario name",
            disabled=True
        ),
        "no_option": st.column_config.TextColumn(
            "[no options]",
            help="Modify operation schedules to generate options",
            disabled=True
        )
    }
    for key, option in st.session_state["specification"]["scenario_options"].items():
        column_config_scenarios[key] = st.column_config.SelectboxColumn(
            key,
            help=option["description"],
            options=option["possible_values"],
            required=False
        )

    container_scenarios = tab.container()
    data_scenarios = dh.generate_dataframe_from_scenarios(st.session_state)
    df_scenarios = container_scenarios.data_editor(
        data_scenarios,
        hide_index=False,
        use_container_width=True,
        column_config=column_config_scenarios
    )
    if df_scenarios is not None:
        # TODO fix variable update in df_scenarios
        # on changing a second variable, the value has to be changed twice as for the first time,
        # handle_vehicle_specification_change is called but with the old value
        handle_scenarios_specification_change(df_scenarios)

    scenario_col1, scenario_col2 = tab.columns(2)
    scenario_col1.button("Add scenario", on_click=handle_add_scenario,
                         key="add_scenario", use_container_width=True)
    scenario_col2.button("Rename or remove scenario(s)", on_click=handle_rename_remove_scenarios,
                         key="rename_remove_scenarios", use_container_width=True)

    if len(st.session_state["specification"]["scenarios"]) > 0:
        # get index of st.session_state["specification"]["scenario_reference"] in st.session_state["scenarios"].keys()
        if len(st.session_state["specification"]["scenarios"]) == 1:
            preselect_index = 0
        elif (st.session_state["specification"]["scenario_reference"] is None
                or st.session_state["specification"]["scenario_reference"] not in st.session_state["specification"]["scenarios"].keys()):
            preselect_index = None
        else:
            preselect_index = list(st.session_state["specification"]["scenarios"].keys()).index(
                st.session_state["specification"]["scenario_reference"])
        reference_scenario = tab.selectbox(
            "Select reference scenario:",
            st.session_state["specification"]["scenarios"].keys(),
            index=preselect_index
        )
        if reference_scenario is not None:
            dh.set_reference_scenario(st.session_state, reference_scenario)



# results



def format_result_dataframes(df:pd.DataFrame)->Styler:
    return df.style.format(
        thousands=" ",
        precision=dh.get_decimal_digits(dh.get_parameter_option("results", "rounding_precision"))
    )



def handle_calculate_results(result_tab:st.delta_generator.DeltaGenerator)->None:
    try:
        dh.calculate_results(st.session_state)
    except Exception as e:
        result_tab.error(e)



def generate_results_tab(tab:st.delta_generator.DeltaGenerator)->None:
    tab.write("## Results")

    container_dict = {}

    nominatim_email = tab.text_input("Email address (required by and transmitted to [Nominatim](https://nominatim.org) for coordinate data retrival):",
                                     value=st.session_state["nominatim_email"])

    if nominatim_email is not None and not nominatim_email == "":
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, nominatim_email):
            st.error("Please enter a valid email address.")
        else:
            st.session_state["nominatim_email"] = nominatim_email

    tab.button("Calculate results", on_click=handle_calculate_results, args=[tab], use_container_width=True,
               key="calculate_results", disabled=(st.session_state["nominatim_email"] == ""))

    if st.session_state["flag_input_changed"]:
        tab.write(ICON_INFO + " The input specification has been changed. Please (re-)calculate the results.")
        return

    if "results" not in st.session_state.keys() or len(st.session_state["results"]) == 0:
        return

    if len(st.session_state["location_data"]) > 0:
        if st.session_state["results"]["warning"] is not None:
            tab.warning(st.session_state["results"]["warning"])

        tab.write("The results are based on coordinate data from [Nominatim](https://nominatim.org) "
                  "and meteorological data from [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/).")

        location_data_expander = tab.expander("Retrieved locations", expanded=True)
        location_data_expander.write("Data for the following location data has been retrieved. "
                                     "Please check whether the correct locations were found. "
                                     "If not, please adapt the location in the specification operation schedule column "
                                     "(e.g. by indicating the country or region).")
        location_data_expander.dataframe(
            dh.generate_dataframe_from_location_data(st.session_state),
            hide_index=True,
            column_config={
                "location_input": st.column_config.TextColumn(
                    "Specified location",
                    help="Location name that has been given by the user in the specification"
                ),
                "location_name": st.column_config.TextColumn(
                    "Retrieved location",
                    help="Location name of the retrieved location based on the specified location name"
                ),
                "latitude": st.column_config.NumberColumn(
                    "Latitude",
                    help="Latitude of the retrieved location"
                ),
                "longitude": st.column_config.NumberColumn(
                    "Longitude",
                    help="Longitude of the retrieved location"
                ),
                "time_zone": st.column_config.TextColumn(
                    "Time zone",
                    help="Time zone of the retrieved location"
                )
            }
        )

    tab.write("### Plots")
    flag_plotted = False

    if len(st.session_state["results"]["scenario_totals"]) > 0:
        flag_plotted = True

        expander_heat_flow_comparison = tab.expander("Scenario Comparison", expanded=False)

        df_scenarios, energy_unit = dh.scale_scenario_totals(st.session_state["results"]["scenario_totals"])

        fig_scenarios = go.Figure()

        fig_scenarios.add_trace(go.Bar(
            y=df_scenarios["scenario_name"],
            x=df_scenarios["electric_energy_scenario_heating_total"],
            name="Heating energy",
            orientation='h',
            marker=dict(color=COLOUR_HEATING)
        ))

        fig_scenarios.add_trace(go.Bar(
            y=df_scenarios["scenario_name"],
            x=df_scenarios["electric_energy_scenario_cooling_total"],
            name="Cooling energy",
            orientation='h',
            marker=dict(color=COLOUR_COOLING)
        ))

        # todo add cost axis
        #fig_scenarios.add_trace(go.Bar(
        #    y=df_scenarios["scenario_name"],
        #    x=df_scenarios["electricity_cost_scenario_total"],
        #    name="Cost",
        #    orientation='h',
        #    xaxis='x2',
        #    visible=False
        #))

        fig_scenarios.update_layout(
            barmode='stack',
            title="Scenario Energy & Cost Comparison",
            xaxis=dict(
                title=f"Electricity consumption [{energy_unit}]",
                side='top'
            ),
            #xaxis2=dict(
            #    title=f"Electricity Cost [{CURRENCY}]",
            #    overlaying='x',
            #    side='bottom'
            #),
            yaxis=dict(
                title="Scenario",
                tickmode='array',
                tickvals=df_scenarios["scenario_name"]
            ),
            showlegend=False
        )

        expander_heat_flow_comparison.plotly_chart(fig_scenarios)


    # heat flow comparison

    if len(st.session_state["results"]["vehicles"]) > 0:
        flag_plotted = True

        expander_heat_flow_comparison = tab.expander("Heat Flow Comparison for Specific Time", expanded=False)
        col1, col2 = expander_heat_flow_comparison.columns(2)

        month_name = col1.selectbox("Select month:", dh.MONTH_NAMES,
                                    key="heat_flow_comparison_month")
        if month_name is not None:
            hour_range = dh.get_hour_list(st.session_state["results"]["vehicles"], month_name)
            hour = col2.selectbox("Select hour:", hour_range,
                                  key="heat_flow_comparison_hour")

            if hour_range is not None:

                df_heat_flow_comparison = dh.select_vehicle_comparison_heat_flows(
                    st.session_state["results"]["vehicles"], month_name, hour)

                if len(df_heat_flow_comparison) > 1:
                    fig_heat_flows = go.Figure()

                    # reference
                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=df_heat_flow_comparison["power_heating_convection_neg"]
                          + df_heat_flow_comparison["power_heating_ventilation_air_neg"]
                          + df_heat_flow_comparison["power_heating_doors_air_neg"]
                          + df_heat_flow_comparison["power_demand_cooling"],
                        showlegend=False,
                        orientation='h'
                    ))

                    # negative flows
                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=-df_heat_flow_comparison["power_demand_cooling"],
                        name="Cooling demand",
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_COOLING)
                    ))

                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=-df_heat_flow_comparison["power_heating_doors_air_neg"],
                        name="Doors openings (air exchange)",
                        showlegend=False,
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_AIR_DOORS)
                    ))

                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=-df_heat_flow_comparison["power_heating_ventilation_air_neg"],
                        name="Ventilation (air exchange)",
                        showlegend=False,
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_AIR_VENTILATION)
                    ))

                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=-df_heat_flow_comparison["power_heating_convection_neg"],
                        name="Convection",
                        showlegend=False,
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_CONVECTION)
                    ))

                    # positive flows
                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=df_heat_flow_comparison["power_heating_auxiliary"],
                        name="Auxiliary devices",
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_AUXILIARY_DEVICES)
                    ))

                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=df_heat_flow_comparison["power_heating_passengers"],
                        name="Passengers",
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_PASSENGERS)
                    ))

                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=df_heat_flow_comparison["power_solar_absorption"],
                        name="Solar absorption",
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_SOLAR_ABSORPTION)
                    ))

                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=df_heat_flow_comparison["power_heating_convection_pos"],
                        name="Convection",
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_CONVECTION)
                    ))

                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=df_heat_flow_comparison["power_heating_ventilation_air_pos"],
                        name="Ventilation (air exchange)",
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_AIR_VENTILATION)
                    ))

                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=df_heat_flow_comparison["power_heating_doors_air_pos"],
                        name="Doors openings (air exchange)",
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_AIR_DOORS)
                    ))

                    fig_heat_flows.add_trace(go.Bar(
                        y=df_heat_flow_comparison["operation_schedule"] + ", "
                          + df_heat_flow_comparison["vehicle_name"] + ", "
                          + df_heat_flow_comparison["vehicle_version_parameter_set"],
                        x=df_heat_flow_comparison["power_demand_heating"],
                        name="Heating demand",
                        orientation='h',
                        marker=dict(color=COLOUR_HEAT_FLOW_HEATING)
                    ))

                    tick_values = ((df_heat_flow_comparison["operation_schedule"] + ", "
                                    + df_heat_flow_comparison["vehicle_name"] + ", ")
                                   + df_heat_flow_comparison["vehicle_version_parameter_set"])
                    tick_text = [f"{operation_schedule},<br>{vehicle_name},<br>{vehicle_version_parameter_set}"
                                 for operation_schedule, vehicle_name, vehicle_version_parameter_set
                                 in zip(df_heat_flow_comparison["operation_schedule"],
                                        df_heat_flow_comparison["vehicle_name"],
                                        df_heat_flow_comparison["vehicle_version_parameter_set"])]
                    # todo correct trace names
                    fig_heat_flows.update_layout(
                        barmode='stack',
                        title="Heat Flow Comparison for " + month_name + " at " + str(hour) + " o'clock",
                        xaxis=dict(
                            title="Thermal power [kW]",
                            side='top'
                        ),
                        yaxis=dict(
                            title="Operation schedule, vehicle and parameters",
                            tickmode='array',
                            tickvals=tick_values,
                            ticktext=tick_text
                        ),
                        showlegend=True
                    )

                    expander_heat_flow_comparison.plotly_chart(fig_heat_flows)


    # annual heat flows single vehicle

    if len(st.session_state["results"]["vehicles"]) > 0:
        flag_plotted = True

        expander_heat_flow_annual = tab.expander("Hourly Heat Flows for Single Vehicle", expanded=False)
        col1, col2 = expander_heat_flow_annual.columns(2)

        df_selection = copy.deepcopy(st.session_state["results"]["vehicles"])
        operation_schedule_options = df_selection["operation_schedule"].unique()
        operation_schedule = col1.selectbox("Select operation schedule:", operation_schedule_options,
            key="heat_flow_annual_operation_schedule")

        if operation_schedule is not None:
            df_selection = df_selection[df_selection["operation_schedule"] == operation_schedule]
            vehicle_name_options = df_selection["vehicle_name"].unique()

            vehicle_name = col2.selectbox("Select vehicle:", vehicle_name_options,
                                          key="heat_flow_annual_vehicle_name")

            if vehicle_name is not None:
                df_selection = df_selection[df_selection["vehicle_name"] == vehicle_name]
                vehicle_version_options = df_selection["vehicle_version_parameter_set"].unique()

                vehicle_version = expander_heat_flow_annual.selectbox(
                    "Select vehicle version parameter set:", vehicle_version_options,
                    key="heat_flow_annual_vehicle_version_parameter_set")

                if vehicle_version is not None:
                    df_selection = df_selection[df_selection["vehicle_version_parameter_set"] == vehicle_version]
                    df_heat_flow_annual = dh.generate_vehicle_annual_heat_flows(st.session_state, df_selection,
                                                                                5)

                    if len(df_heat_flow_annual) > 1:

                        fig_heat_flows = make_subplots(
                            rows=3, cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.03,
                            subplot_titles=("", "", ""),
                        )

                        # temperatures & solar irradiation

                        #fig_heat_flows.add_trace(
                        #    go.Bar(x=df_heat_flow_annual.index, y=df_heat_flow_annual["solar_irradiation"],
                        #           marker=dict(color=COLOUR_SOLAR_IRRADIATION), orientation='v',
                        #           name='Solar irradiation', yaxis='y4'),
                        #    row=1, col=1
                        #)
                        # TODO fix: make y4 (see yaxis4 below) visible and display solar radiation to this side!

                        fig_heat_flows.add_trace(
                            go.Scatter(x=df_heat_flow_annual["time"], y=df_heat_flow_annual["temperature_environment"],
                                       mode='markers', marker=dict(color=COLOUR_TEMPERATURE_ENVIRONMENT),
                                       name='Environment temperature', yaxis='y1'),
                            row=1, col=1
                        )
                        fig_heat_flows.add_trace(
                            go.Scatter(x=df_heat_flow_annual["time"], y=df_heat_flow_annual["temperature_vehicle"],
                                       mode='markers', marker=dict(color=COLOUR_TEMPERATURE_VEHICLE),
                                       name='Vehicle temperature', yaxis='y1'),
                            row=1, col=1
                        )


                        # thermal powers

                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["power_heating_convection_neg"]
                              + df_heat_flow_annual["power_heating_ventilation_air_neg"]
                              + df_heat_flow_annual["power_heating_doors_air_neg"]
                              + df_heat_flow_annual["power_demand_cooling"],
                            showlegend=False, orientation='v', yaxis='y2'
                        ), row=2, col=1)

                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=-df_heat_flow_annual["power_demand_cooling"],
                            name="Cooling demand",
                            orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_COOLING)
                        ), row=2, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=-df_heat_flow_annual["power_heating_doors_air_neg"],
                            showlegend=False, orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEAT_FLOW_AIR_DOORS),
                            name="Doors openings (air exchange)"
                        ), row=2, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=-df_heat_flow_annual["power_heating_ventilation_air_neg"],
                            showlegend=False, orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEAT_FLOW_AIR_VENTILATION),
                            name="Ventilation (air exchange)"
                        ), row=2, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=-df_heat_flow_annual["power_heating_convection_neg"],
                            showlegend=False, orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEAT_FLOW_CONVECTION),
                            name="Convection"
                        ), row=2, col=1)

                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["power_heating_auxiliary"],
                            name="Auxiliary devices",
                            orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEAT_FLOW_AUXILIARY_DEVICES)
                        ), row=2, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["power_heating_passengers"],
                            name="Passengers",
                            orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEAT_FLOW_PASSENGERS)
                        ), row=2, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["power_solar_absorption"],
                            name="Solar absorption",
                            orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEAT_FLOW_SOLAR_ABSORPTION)
                        ), row=2, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["power_demand_heating"],
                            name="Heating demand",
                            orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEATING)
                        ), row=2, col=1)

                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["power_heating_convection_pos"],
                            name="Convection",
                            orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEAT_FLOW_CONVECTION)
                        ), row=2, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["power_heating_ventilation_air_pos"],
                            name="Ventilation (air exchange)",
                            orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEAT_FLOW_AIR_VENTILATION)
                        ), row=2, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["power_heating_doors_air_pos"],
                            name="Doors openings (air exchange)",
                            orientation='v', yaxis='y2',
                            marker=dict(color=COLOUR_HEAT_FLOW_AIR_DOORS)
                        ), row=2, col=1)

                        # electric powers

                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["electric_power_resistive_heating"],
                            name="Resistive heating",
                            orientation='v', yaxis='y3',
                            marker=dict(color=COLOUR_ELECTRIC_HEATING_RESISTIVE)
                        ), row=3, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["electric_power_heat_pumps_heating"],
                            name="Heat pump heating",
                            orientation='v', yaxis='y3',
                            marker=dict(color=COLOUR_ELECTRIC_POWER_HEAT_PUMP_HEATING)
                        ), row=3, col=1)
                        fig_heat_flows.add_trace(go.Bar(
                            x=df_heat_flow_annual["time"],
                            y=df_heat_flow_annual["electric_power_heat_pumps_cooling"],
                            name="Heat pump cooling",
                            orientation='v', yaxis='y3',
                            marker=dict(color=COLOUR_ELECTRIC_POWER_HEAT_PUMP_COOLING)
                        ), row=3, col=1)

                        tickvals = []
                        ticktext = []
                        for index, row in df_heat_flow_annual.iterrows():
                            if row["ticklabel"] != "":
                                tickvals.append(row["time"])
                                ticktext.append(row["ticklabel"])

                        fig_heat_flows.update_xaxes(
                            tickmode='array',
                            tickvals=tickvals,
                            ticktext=ticktext,
                            title_text="Month and Hour",
                            tickangle=0,
                            row=3, col=1,
                            range=[min(df_heat_flow_annual["time"].values)-1, max(df_heat_flow_annual["time"].values)+1]
                        )

                        # todo add correct trace name
                        # todo change (hover) displayed x coordinate
                        # todo add vertical lines between months
                        # todo make legend per subplot
                        fig_heat_flows.update_layout(
                            title_text="Annual Heat Flows for Single Vehicle",
                            height=700, # todo avoid fixed height
                            barmode='stack',
                            showlegend=True,
                            yaxis=dict(
                                title='Temperature [°C]'
                            ),
                            yaxis2 = dict(
                                title='Thermal power [kW]',
                                anchor='x',
                                side='left'
                            ),
                            yaxis3 = dict(
                                title='Electric power [kW]',
                                anchor='x',
                                side='left'
                            ),
                            yaxis4=dict(
                                title='Solar irradiation [W/m²]',
                                overlaying='y',
                                side='right'
                            )
                        )

                        # add vertical lines between months

                        # display plot
                        expander_heat_flow_annual.plotly_chart(fig_heat_flows)


    if not flag_plotted:
        tab.write("No data for plotting available after result calculation. "
                  "Change specification and then re-calculate results to generate plots.")


    tab.write("### Tables")
    flag_tabled = False

    if len(st.session_state["results"]["scenario_totals"]) > 0:
        flag_tabled = True

        expander_scenario_results = tab.expander("Scenario Totals", expanded=False)

        expander_scenario_results.dataframe(
            format_result_dataframes(
                st.session_state["results"]["scenario_totals"]),
            hide_index=True,
            column_config={
                "scenario_name": st.column_config.TextColumn(
                    "Scenario",
                    help="Scenario name"
                ),
                "electric_energy_scenario_total": st.column_config.NumberColumn(
                    "Electricity consumption total [kWh]",
                    help="Total electricity consumption"
                ),
                "electric_energy_scenario_heating_total": st.column_config.NumberColumn(
                    "Electricity consumption heating [kWh]",
                    help="Total electricity consumption for heating"
                ),
                "electric_energy_scenario_cooling_total": st.column_config.NumberColumn(
                    "Electricity consumption cooling [kWh]",
                    help="Total electricity consumption for cooling"
                ),
                "electricity_cost_scenario_total": st.column_config.NumberColumn(
                    f"Electricity cost [{CURRENCY}]",
                    help="Total cost for electricity consumption"
                ),
                "comparison_to_reference": st.column_config.NumberColumn(
                    f"Comparison with reference [%]",
                    help="Relative electricity consumption and cost compared to reference scenario"
                ),
                "reference_scenario": st.column_config.CheckboxColumn(
                    "Reference scenario",
                    help="Reference scenario for savings calculation"
                )
            }
        )

    if len(st.session_state["results"]["vehicle_operation_totals"]) > 0:
        flag_tabled = True

        expander_vehicle_operation_results = tab.expander("Vehicle Operation Totals", expanded=False)

        expander_vehicle_operation_results.dataframe(
            format_result_dataframes(st.session_state["results"]["vehicle_operation_totals"]),
            hide_index=True,
            column_config={
                "operation_schedule": st.column_config.TextColumn(
                    "Operation schedule",
                    help="Operation schedule name"
                ),
                "vehicle_name": st.column_config.TextColumn(
                    "Vehicle",
                    help="Vehicle type"
                ),
                "vehicle_version_parameter_set": st.column_config.TextColumn(
                    "Vehicle version parameter",
                    help="Vehicle version parameter set"
                ),
                "number_of_vehicles": st.column_config.NumberColumn(
                    "Number of vehicles",
                    help="Number of vehicles in operation"
                ),
                "electric_energy_vehicle_operation_total": st.column_config.NumberColumn(
                    "Electricity consumption [kWh]",
                    help="Total electricity consumption of single vehicle operation"
                ),
                "electric_energy_vehicle_operation_heating_total": st.column_config.NumberColumn(
                    "Electricity consumption heating [kWh]",
                    help="Total electricity consumption for heating of single vehicle operation"
                ),
                "electric_energy_vehicle_operation_cooling_total": st.column_config.NumberColumn(
                    "Electricity consumption cooling [kWh]",
                    help="Total electricity consumption for cooling of single vehicle operation"
                ),
                "electricity_cost_vehicle_operation_total": st.column_config.NumberColumn(
                    f"Electricity cost [{CURRENCY}]",
                    help="Total cost for electricity consumption of single vehicle operation"
                )
            }
        )

    if len(st.session_state["results"]["vehicles"]) > 0:
        flag_tabled = True

        expander_vehicle_results = tab.expander("Hourly Vehicle Heat Flows and Electricity Consumption",
                                                expanded=False)

        expander_vehicle_results.dataframe(
            format_result_dataframes(st.session_state["results"]["vehicles"]),
            hide_index=True,
            column_config={
                "operation_schedule": st.column_config.TextColumn(
                    "Operation schedule",
                    help="Operation schedule name"
                ),
                "vehicle_name": st.column_config.TextColumn(
                    "Vehicle",
                    help="Vehicle type"
                ),
                "vehicle_version_parameter_set": st.column_config.TextColumn(
                    "Vehicle version parameter",
                    help="Vehicle version parameter set"
                ),
                "month_name": st.column_config.TextColumn(
                    "Month",
                    help="Month"
                ),
                "hour": st.column_config.NumberColumn(
                    "Hour",
                    help="Hour"
                ),
                "electric_energy_vehicle_operation": st.column_config.NumberColumn(
                    "Electricity consumption [kWh]",
                    help="Total electricity (energy) consumption of single vehicle operation"
                ),
                "electric_energy_vehicle_operation_heating": st.column_config.NumberColumn(
                    "Electricity consumption heating [kWh]",
                    help="Total electricity (energy) consumption of single vehicle operation for heating"
                ),
                "electric_energy_vehicle_operation_cooling": st.column_config.NumberColumn(
                    "Electricity consumption cooling [kWh]",
                    help="Total electricity (energy) consumption of single vehicle operation for cooling"
                ),
                "electricity_cost_vehicle_operation": st.column_config.NumberColumn(
                    f"Electricity cost [{CURRENCY}]",
                    help="Total cost for electricity (energy) consumption of single vehicle operation"
                ),
                "electric_power_vehicle": st.column_config.NumberColumn(
                    "Electric power [kW]",
                    help="Electric power for vehicle heating and cooling"
                ),
                "electric_power_vehicle_heating": st.column_config.NumberColumn(
                    "Electric power [kW]",
                    help="Electric power for vehicle heating"
                ),
                "electric_power_vehicle_cooling": st.column_config.NumberColumn(
                    "Electric power cooling [kW]",
                    help="Electric power for vehicle cooling"
                ),
                "electric_power_resistive_heating": st.column_config.NumberColumn(
                    "Electric power resistive heater [kW]",
                    help="Electric power for resistive vehicle heaters"
                ),
                "electric_power_heat_pumps": st.column_config.TextColumn(
                    "Electric power heat pumps [kW]",
                    help="Electric power for heat pumps for vehicle heating and cooling"
                ),
                "power_demand_heating": st.column_config.NumberColumn(
                    "Heating demand [kW]",
                    help="Thermal power demand of vehicle heating"
                ),
                "power_demand_cooling": st.column_config.NumberColumn(
                    "Cooling demand [kW]",
                    help="Thermal power demand of vehicle cooling"
                ),
                "power_solar_absorption": st.column_config.NumberColumn(
                    "Solar heating [kW]",
                    help="Thermal power of solar heating (absorption)"
                ),
                "power_heating_passengers": st.column_config.NumberColumn(
                    "Passenger heating [kW]",
                    help="Thermal heating power of passengers"
                ),
                "power_heating_auxiliary": st.column_config.NumberColumn(
                    "Auxiliary device heating [kW]",
                    help="Thermal heating power of auxiliary devices"
                ),
                "power_heating_convection": st.column_config.NumberColumn(
                    "Convection heating [kW]",
                    help="Thermal heating power of convection through vehicle shell"
                ),
                "power_heating_ventilation_air": st.column_config.NumberColumn(
                    "Ventilation air exchange heating [kW]",
                    help="Thermal heating power of environmental air exchanged with the ventilation system"
                ),
                "power_heating_doors_air": st.column_config.NumberColumn(
                    "Door air exchange heating [kW]",
                    help="Thermal heating power of environmental air exchanged through the doors system"
                ),
                "operation_days": st.column_config.NumberColumn(
                    "Operation days",
                    help="Number of operation days in respective month"
                ),
                "operation_hours": st.column_config.NumberColumn(
                    "Time fraction",
                    help="Time fraction of operation during respective hour in respective month"
                ),
                "number_of_vehicles": st.column_config.NumberColumn(
                    "Number of vehicles",
                    help="Number of vehicles in operation"
                ),
                "unit_cost_electricity": st.column_config.NumberColumn(
                    f"Unit cost electricity [{CURRENCY}/kWh]",
                    help="Cost per unit of electric energy"
                ),
                "temperature_vehicle": st.column_config.NumberColumn(
                    "Vehicle temperature [°C]",
                    help="Temperature of vehicle cabin"
                ),
                "temperature_environment": st.column_config.NumberColumn(
                    "Environment temperature [°C]",
                    help="Temperature of the environment"
                ),
                "irradiation_direct_normal": st.column_config.NumberColumn(
                    "Solar irradiation [W/m²]",
                    help="Direct normal solar irradiation"
                )
            }
        )

    if not flag_tabled:
        tab.write("No data for tables available after result calculation. "
                  "Change specification and then re-calculate results to generate tables.")



# general


def generate()->None:
    setup()

    sidebar()

    st.write("# " + PAGE_TITLE)
    st.write("#### " + PAGE_SUBTITLE + f" by [Florian Schubert]({URL_LINKEDIN})")
    st.write("A user guide and legal information can be found in the sidebar (top left arrow). "
             + "By using this website, you agree to the terms of service.")

    tab_specification, tab_results = st.tabs(["Specification", "Results"])

    generate_specification_tab(tab_specification)
    generate_results_tab(tab_results)





##### COMMAND SEQUENCE #####

# generate session state dictionaries
if not "initiated" in st.session_state:
    st.session_state["initiated"] = True
    dh.create_session_state_dictionaries(st.session_state)

st.session_state["flag_stop"] = False

# generate the structure of the GUI
generate()

# stop after run (fixes segment errors)
if st.session_state["flag_stop"]:
    st.stop()