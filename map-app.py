import streamlit as st
from streamlit_folium import folium_static
import pandas as pd
import matplotlib
import matplotlib.cm as cm
import geopandas as gpd
import pyproj
import folium
import os.path
import json

from PIL import Image


from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


st.title("Bike Hire in Edinburgh")
st.subheader(
    "Exploring bike hire trends, station availability and usage through socioeconomic lens")
st.subheader(
    "To select a different month or year, open the sidebar on the left and use the sliders.")
st.markdown("This interactive webpage uses Just Eat bike hire data in Edinburgh. Two types of data sets were used 1) a general one, which shows _all_ stations in Edinburgh, 2) and a collection of monthly datasets from 2018 to 2021, which show the usage of bike hire stations and is used in the interactive map (further down in the page). ")


# @st.cache(persist=True, allow_output_mutation=True)
def load_and_merge_data():
    """
    This function loads the boundary and deprivation data and merges them.
    """

    # loading the boundary data
    boundaries_gdf = gpd.read_file("simd2020_withgeog/sc_dz_11.zip")
    boundaries_gdf.to_crs(pyproj.CRS.from_epsg(4326), inplace=True)

    # loading the deprivation data
    deprivation_df = pd.read_excel("simd2020_withgeog/simd2020_withinds.xlsx",
                                   sheet_name="Data")
    deprivation_df.rename(columns={'Data_Zone': 'DataZone'}, inplace=True)

    # merging the two datasets and storing them in boundaries_and_depri_gf
    boundaries_and_depri_gdf = boundaries_gdf.merge(deprivation_df)

    # The line of code below filters the data to only display the City of Edinburgh.
    boundaries_and_depri_gdf = boundaries_and_depri_gdf[boundaries_and_depri_gdf[
        "Council_area"] == "City of Edinburgh"]

    return boundaries_and_depri_gdf


def create_hire_df(bike_df):
    """
    This function counts the number of times that each station was used as a starting point for a hire.
    The count is measured in density.
    This is to help to apply gradient colours to markers to show high density vs low density.
    This creates a new dataframe/table, with added columns 'density'.
    """

    # hire_density is a dictionary
    hire_density = {}

    # creating a for loop, which iterates through each row of the raw bike hire data.
    # Iterrows - gets the index and the content of the row.
    # The row value can be accessed by using the column name, eg. "start_station_id"
    for _, bike_row in bike_df.iterrows():
        # checking if the value of the row under 'start_station_id' is already in the dictionary
        # if it is in, then we add 1 to density.
        if bike_row["start_station_id"] in hire_density:
            hire_density[bike_row["start_station_id"]]['density'] += 1
        # if it doesn't exist, a new row is created with the station information
        else:
            # creating a dictionary called row
            row = {}
            row["start_station_name"] = bike_row["start_station_name"]
            row["start_station_latitude"] = bike_row["start_station_latitude"]
            row["start_station_longitude"] = bike_row["start_station_longitude"]
            # setting density to 1, because it's the first time the station is accessed
            row["density"] = 1
            # storing the dictionary 'row' as a value in the dictionary 'hire density'
            hire_density[bike_row["start_station_id"]] = row
    # converting dictionary into a dataframe, to view it as table. Transposing the axes.
    return pd.DataFrame.from_dict(hire_density).T


def generate_color_from_density(hire_density_df):
    """
    This function generates and maps a color to the station based on the density of number of hires
    """
    # getting min and max values from hire_density["density"]
    max_density = hire_density_df["density"].max()
    min_density = hire_density_df["density"].min()

    # colors is a list that will store all the colors
    colors = []
    for _, row in hire_density_df.iterrows():
        # normalise density - normalise numbers to be between 0 and 1 so that they can be mapped to a color
        normalised_density = (
            (row["density"] - min_density) / (max_density - min_density))
        # appending the list with converted HEX values for colors
        colors.append(matplotlib.colors.rgb2hex(
            cm.gist_heat(normalised_density)))
    # create new column colors and assign the HEX values
    hire_density_df["color"] = colors


# load stations info
with open('station_information.json') as f:
    stations_dict = json.load(f)

# build dataframe from station_dict
stations_df = pd.DataFrame.from_dict(stations_dict["data"]["stations"])

st.markdown(
    "Below is a table which contains general data about all Just Eat bike hire stations in Edinburgh, dated July 2021.")
stations_df


# calling the load and merge function
boundaries_and_depri_gdf = load_and_merge_data()

# creating a map using folium
# specifying Edinburgh coordinates
m = folium.Map(location=[55.9533, -3.1883],
               zoom_start=12, tiles='CartoDB positron')

# slider for month
month = st.sidebar.slider(label="Select Month", min_value=1,
                          max_value=12, step=1, value=4)
# slider for year
year = st.sidebar.slider(label="Select Year", min_value=2018,
                         max_value=2021, step=1, value=2020)
# getting file name from the slider outputs using f string
filename = f"bike_data/{year}{month:02}.csv"

# checking if file exists
if os.path.isfile(filename):
    # loading the file selected by the slider
    bike_df = pd.read_csv(f"{filename}")
    # plotting the table
    st.markdown(
        "The table below shows the raw bike hire data for the month and year that has been selected.")
    bike_df

    # creating the hire density dataframe (passing in the file that we loaded to the create_hire_df function)
    hire_density_df = create_hire_df(bike_df)
    # generating the color from density using the hire_density_df dataframe
    generate_color_from_density(hire_density_df)

    # plotting the table
    st.markdown(
        "The table below is the amended table of the bike hire data above. X axis has the station name, start station latitute and longitude, number of bikes that were rented from that station, and corresponding color code for density. This is then used for the map (see below).")
    st.markdown(
        "Y axis has the station ID. The stations are sorted in a descending order by number of hires.")
    sorted_hire_density_df = hire_density_df.sort_values(
        by=['density'], ascending=False)
    sorted_hire_density_df
    # plotting the boundaries of the map

    folium.Choropleth(
        # geo_data = geometry data for boundaries
        geo_data=boundaries_and_depri_gdf,
        # name="choropleth",
        # data = choropleth colour data for differences in deprivation
        data=boundaries_and_depri_gdf,
        # id and information that will color the map
        columns=["DataZone", "SIMD2020v2_Decile"],
        # matches the 'geo_data' to the the 'data'
        # need to use the 'feature.properties' as it uses the GeoJSON format
        key_on="feature.properties.DataZone",
        fill_color="RdYlBu",
        fill_opacity=0.7,
        line_opacity=0.2,
        line_color="Black",
        bins=9,
        legend_name="Level of Deprivation",
    ).add_to(m)

    # The colour data is applied to each marker.
    for _, row in hire_density_df.iterrows():
        # this information is used later on in the popup
        station_name = row["start_station_name"]
        density = row["density"]
        # plotting the markers on the map
        folium.CircleMarker(
            location=[row['start_station_latitude'],
                      row['start_station_longitude']],
            radius=5,
            # applying color data to color the marker
            color=row["color"],
            fill=True,
            fill_color=row["color"],
            fill_opacity=0.9,
            popup=f"{station_name}\nDensity: {density}"
        ).add_to(m)

    # displaying the map
    st.markdown("The map below displays the total level of deprivation (lighter green is higher deprivation, darker is more affluent) from 1-10.")
    st.markdown("Deprivation scores include income domain, employment domain, health domain, education/skills domain, housing domain, geographic access domain, crime rank.")
    st.markdown("The Scottish Index of Multiple Deprivation (2020) and its data were used to map out the levels of deprivation throughout Edinburgh. For more information about SIMD, head to this website: https://www.gov.scot/collections/scottish-index-of-multiple-deprivation-2020/?utm_source=redirect&utm_medium=shorturl&utm_campaign=simd ")
    st.markdown("The markers show where bikes were rented from (start stations) in a form of heat plotting. The lighter the colour of the marker (eg. white), the more a particular station was used. A colour closer to black would mean that the station was rarely used.")
    st.markdown("Clicking a marker will produce a pop up, which shows the name of the station and how many times a bike was rented from it.")
    folium_static(m)
    st.markdown(
        "This data tells a two-part story: 1) where the bike hire stations are located 2) bike rental trends for the month and year that was selected.")
    st.markdown("It is natural, that the bike hire stations are located closer to the city centre, but a high number of stations are also located in areas of mid-to-high level of affluence.")
    st.markdown("Most striking is the complete absence (or near complete)  of stations in Granton, Muirhouse, Craigmillar, Niddrie, and West of Edinburgh (Gorgie, Saughton, Slateford). A further investigation (below), will show that the level of deprivation of an area plays a big role in station placement throughout Edinburgh.")

    st.markdown("While it would be interesting to look at how bike hire trends were affected by the COVID-19 pandemic, this was not explored.")

    # adding number of stations in each area
    column_num_stations = {}
    for ind_location, row_locations in boundaries_and_depri_gdf.iterrows():
        column_num_stations[ind_location] = 0
        try:
            polygon = Polygon(row_locations["geometry"])

            for ind_hire, row_hire in stations_df.iterrows():

                point = Point(row_hire["lon"],
                              row_hire["lat"])
                if polygon.contains(point):
                    column_num_stations[ind_location] += 1
        except NotImplementedError:
            pass
    boundaries_and_depri_gdf["num_stations"] = column_num_stations.values()

    # boundaries_and_depri_gdf

    # computing deprivation for each station
    column_depri = []
    for _, row_hire in stations_df.iterrows():
        point = Point(row_hire["lon"],
                      row_hire["lat"])
        flag = False
        for ind_location, row_locations in boundaries_and_depri_gdf.iterrows():
            # st.markdown(ind_location)
            try:
                polygon = Polygon(row_locations["geometry"])
                if polygon.contains(point):
                    column_depri.append(row_locations["SIMD2020v2_Decile"])
                    flag = True
            except NotImplementedError:
                pass
        if flag == False:
            column_depri.append(-1)
    stations_df["deprivation"] = column_depri

    # removing the -1 deprivation areas
    # stations_df
    stations_df.loc[1, 'deprivation'] = 4
    stations_df.loc[2, 'deprivation'] = 5
    stations_df.loc[23, 'deprivation'] = 6
    stations_df.loc[42, 'deprivation'] = 10
    stations_df.loc[52, 'deprivation'] = 10
    stations_df.loc[73, 'deprivation'] = 9
    stations_df.loc[79, 'deprivation'] = 5

    # stations_df.set_value('deprivation', '1', '4')
    st.markdown("")
    st.markdown("Below is a table of all available Just Eat bike hire stations (general data). The last column, named 'deprivation' shows which level of deprivation the station is located in. Level 1 is the area with highest level of deprivation, whereas level 10 is the most 'affluent'.")

    stations_df

    # st.markdown(
    #     "The table below shows the 'cleaned' data with the missing deprivation levels removed")
    # stations_df_clean = stations_df[stations_df['deprivation'] != -1]

    # stations_df_clean

    # finding out how many stations there are per each level of deprivation
    depri_num_of_stations = {}
    for ind_location, row_locations in boundaries_and_depri_gdf.iterrows():
        depri = row_locations["SIMD2020v2_Decile"]
        if depri not in depri_num_of_stations:
            depri_num_of_stations[depri] = row_locations["num_stations"]
        else:
            depri_num_of_stations[depri] += row_locations["num_stations"]

    # st.markdown(depri_num_of_stations)

    # diction = {"1": 0, "2": 2, "3": 1, "4": 9, "5": 9,
    #            "6": 6, "7": 8, "8": 5, "9": 11, "10": 28}

    dictdata_df = pd.DataFrame.from_dict(
        depri_num_of_stations, orient='index', columns=['number of stations'])

    # correcting station numbers in each deprivation area due to boundary error
    dictdata_df.loc[10, 'number of stations'] = 30
    dictdata_df.loc[5, 'number of stations'] = 11
    dictdata_df.loc[4, 'number of stations'] = 10
    dictdata_df.loc[6, 'number of stations'] = 7
    dictdata_df.loc[9, 'number of stations'] = 10
    # dictdata_df
    dictdata_df.plot.bar(
        y='number of stations', rot=0)
    st.markdown(
        "Below is a bar graph showing the number of stations per each deprivation level. _X_ axis shows the number of stations, and _Y_ axis is the level of deprivation from 1 to 10.")
    st.bar_chart(dictdata_df, height=400)
    dictdata_df.reset_index(inplace=True)
    dictdata_df.rename(
        columns={'index': 'level of deprivation'}, inplace=True)
    st.markdown("A summary table of the number of stations and level of deprivation is available below. Clicking on column names will sort the table by ascending or descending order.")
    dictdata_df
    st.markdown("A correlation between the number of stations and deprivation level was conducted. Below is a correlation matrix. There is a strong relationship (0.7208) between number of stations and level of deprivation. While correlation does not equal causation, these findings still show that there is a relationship between deprivation and where stations are located in Edinburgh. More affluent areas have a higher number of stations, allowing the residents or visitors to those areas to have better access to green transport. ")
    st.write(dictdata_df.corr(method='pearson', min_periods=1))

else:
    # if the file does not exist, display the message that another file should be selected
    st.markdown(
        f"File at month {month} and year {year} does not exist. Select a different month and year")
