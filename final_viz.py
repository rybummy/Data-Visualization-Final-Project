
import itertools
import sketchingpy
import sketchingpy.geo
import pandas as pd
import math
import time
import shapely

FONT = 'PublicSans-Regular.otf'
WIDTH = 1200
HEIGHT = 800
BACKGROUND_COL = '#F0F0F0'

state_to_abbrev = {
    'Alabama': 'AL',
    'Alaska': 'AK',
    'American Samoa': 'AS',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'District of Columbia': 'DC',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Guam': 'GU',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Pennsylvania': 'PA',
    'Puerto Rico': 'PR',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'United States Virgin Islands': 'VI',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virginia': 'VA',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY',
    'Commonwealth of the Northern Mariana Islands': 'MP'
}

#Energy Production Data
renewables = 'Total renewables-Table 1.csv'
renewables_df = pd.read_csv(renewables)

total_energy = 'Total primary energy-Table 1.csv' 
total_df = pd.read_csv(total_energy)

#Energy Consumption Data

consumption_coal = 'CONSUMPTION Coal-Table 1.csv'
consumption_naturalgas = 'CONSUMPTION Natural gas-Table 1.csv'
consumption_nuclear ='CONSUMPTION Nuclear-Table 1.csv'
consumption_petroleum = 'CONSUMPTION Petroleum-Table 1.csv'
consumption_renewable = 'CONSUMPTION Total renewable energy-Table 1.csv'

consumption_coal_df = pd.read_csv(consumption_coal)
consumption_naturalgas_df = pd.read_csv(consumption_naturalgas)
consumption_nuclear_df = pd.read_csv(consumption_nuclear)
consumption_petroleum_df = pd.read_csv(consumption_petroleum)
consumption_renewable_df = pd.read_csv(consumption_renewable)


def data_clean(df, df_name='blank'):
    df = df.iloc[1:].reset_index(drop=True)
    df.columns = df.iloc[0]              
    df = df.drop(df.index[0]).reset_index(drop=True)
    years = [c for c in df.columns if c!='State']
    
    df[years] = (
        df[years]
        .replace({',':''}, regex=True)
        .apply(pd.to_numeric, errors='coerce')
    )

    df_long = df.melt( 
        id_vars='State',
        value_vars=years,
        var_name='Year',
        value_name = df_name
    )

    return df_long

#Specific Cleaning for Energy Production Data
renewables_df = data_clean(renewables_df, 'Renewable Prod')
total_df = data_clean(total_df, 'Total Prod')

joined_df = total_df.merge(renewables_df, on = ['State', 'Year'], how='inner').dropna()
joined_df['Year'] = joined_df['Year'].astype('int64')

joined_df['Proportion'] = (joined_df['Renewable Prod'] / joined_df['Total Prod']).clip(upper=1.0)
print(len(joined_df[joined_df['Proportion'] >= 1.0]))

#Specific Cleaning for Energy Consumption Data
c_coal_df = data_clean(consumption_coal_df)
c_naturalgas_df = data_clean(consumption_naturalgas_df)
c_nuclear_df = data_clean(consumption_nuclear_df)
c_petroleum_df = data_clean(consumption_petroleum_df)
c_renewable_df = data_clean(consumption_renewable_df)

"""
Including Nuclear:

total_consumption_df = pd.concat(
    [c_coal_df, c_naturalgas_df, c_nuclear_df, c_petroleum_df, c_renewable_df]
    ).drop_duplicates().reset_index(drop=True)"""

#Excluding nuclear
total_consumption_df = pd.concat(
    [c_coal_df, c_naturalgas_df, c_petroleum_df, c_renewable_df]
    ).drop_duplicates().reset_index(drop=True)

total_consumption_df = total_consumption_df.groupby(['State', 'Year']).sum()

#print(total_consumption_df.head())

consumption_joined_df = total_consumption_df.merge(c_renewable_df, on = ['State', 'Year'], how='inner').dropna()
consumption_joined_df['Year'] = consumption_joined_df['Year'].astype('int64')
consumption_joined_df['Proportion'] = (consumption_joined_df['blank_y'] / consumption_joined_df['blank_x']).clip(upper=1.0)
consumption_joined_df.rename(columns={
    'blank_x': 'Total Consumption',
    'blank_y': 'Renewable Consumption'}, inplace=True)


consumption_joined_df['Altered Proportion'] = consumption_joined_df['Proportion'].map(
    lambda x: x / max(consumption_joined_df['Proportion']))

print((consumption_joined_df.head()))
print((joined_df.head()))
#print(consumption_joined_df['Proportion'])

#print(joined_df[joined_df['Proportion'] > 0.95].head(40))


# Setup sketch
sketch = sketchingpy.Sketch2D(WIDTH, HEIGHT)
sketch.clear(BACKGROUND_COL)

# Determine where to draw
center_longitude = -100
center_latitude = 40
center_x = 500
center_y = 375
map_scale = 1

# Create a geo transformation that ties pixel to geo coordinates
sketch.set_map_pan(center_longitude, center_latitude) # Geographic center
sketch.set_map_zoom(map_scale)  # How much zoom
sketch.set_map_placement(center_x, center_y)  # Pixels center

# Make and convert points
data_layer = sketch.get_data_layer()
geojson = data_layer.get_json('states.geojson')
geo_polgyons = sketch.parse_geojson(geojson)

# Utility function to determine the number of shapes in a feature where our
# geojson has one feature per census region.
get_num_shapes_in_feature = lambda x: len(x['geometry']['coordinates'])

mouse = sketch.get_mouse()
keyboard = sketch.get_keyboard()
press_states = {
    'left': False,
    'right': False
}
year = 1980
#print([feature['properties']['NAME'] for feature in geojson['features']])


ENERGY_PROD_COLOR = '#8300C4'   
ENERGY_CONSUMP_COLOR = '#DB4C00'

def interpolate_color(proportion, end_hex=ENERGY_PROD_COLOR):
    if end_hex.startswith('#'):
        end_hex = end_hex[1:]
    
    if not (0 <= proportion <= 1):
        raise ValueError("Proportion must be between 0 and 1.")
    
    if len(end_hex) != 6:
        raise ValueError("Hex color must be 6 characters long.")
    
    # convert hex to rgb
    r_target = int(end_hex[0:2], 16)
    g_target = int(end_hex[2:4], 16)
    b_target = int(end_hex[4:6], 16)

    # blend with white
    r = round(255 * (1 - proportion) + r_target * proportion)
    g = round(255 * (1 - proportion) + g_target * proportion)
    b = round(255 * (1 - proportion) + b_target * proportion)

    #convert back to hex
    return f"#{r:02x}{g:02x}{b:02x}"


#print("Entries with larger than 0 prop: " +  str(joined_df[joined_df['Proportion'] > 1.0]))



joined_df['Color'] = joined_df['Proportion'].map(interpolate_color)
consumption_joined_df['Color'] = consumption_joined_df['Proportion'].map(interpolate_color)
consumption_joined_df['Color 2'] = consumption_joined_df['Altered Proportion'].map(lambda x: interpolate_color(x, ENERGY_CONSUMP_COLOR))

#global variable to indicate if the viz. is currently showing Energy Consumption or Production.
consumption_setting = True

"""
#create map of states & their min/max coordinates (for bounding box point detection)
state_shapes = []
for feature in geojson['features']:
    state_name = feature['properties']['NAME']  
    geom = shapely.geometry.shape(feature['geometry'])
    state_shapes.append((state_name, geom))

#print([x[0] for x in state_shapes])
def find_state_containing_point(lon, lat):
    point = shapely.geometry.Point(lon, lat)
    for state_name, geom in state_shapes:
        if geom.contains(point):
            return state_name
    return None  # Not found
"""

territories = [
    'American Samoa',
    'Guam',
    'Commonwealth of the Northern Mariana Islands',
    'Puerto Rico',
    'United States Virgin Islands',
]

state_shapes = []
for feature in geojson['features']:
    state_name = feature['properties']['NAME']  
    if not(state_name in territories):
        geom = shapely.geometry.shape(feature['geometry'])
        state_shapes.append((state_name, geom))

state_centers = {}
for state_name, geom in state_shapes:
    centroid = geom.centroid  # returns a Shapely Point
    lon, lat = centroid.x, centroid.y
    x, y = sketch.convert_geo_to_pixel(lon, lat)
    state_centers[(x, y)] = state_name


def find_closest_coordinate(input_coord, state_centers=state_centers):


    closest_state = min(
        state_centers.keys(),
        key=lambda state: math.dist(input_coord, state)
    )

    return state_centers[closest_state]
print(find_closest_coordinate((280, 540)))
features = geojson['features']
print([x['properties']['NAME'] for x in features])
def draw_map(sketch):


    #assign each shape in region to associated color
    features = geojson['features']
    colors_full = []
    geopolygon_names = []

    for feature in features:
        name = feature['properties']['NAME']
        if name in state_to_abbrev:
            initials = state_to_abbrev[name]

            if consumption_setting == False:
                filtered = joined_df[(joined_df['State'] == initials) & (joined_df['Year'] == year)]['Color']
            else:
                filtered = consumption_joined_df[(consumption_joined_df['State'] == initials) & (consumption_joined_df['Year'] == year)]['Color 2']

            if filtered.empty:
                color_for_feature = "#000000"
            else:
                color_for_feature = filtered.iloc[0]
        else:
            color_for_feature = "#000000" 
        
        num_shapes = get_num_shapes_in_feature(feature)
        color_per_shape = [color_for_feature] * num_shapes
        colors_full.extend(color_per_shape)
        name_per_shape = [name] * num_shapes
        geopolygon_names.extend(name_per_shape)

    # combine
    geo_polgyons_with_colors = zip(geo_polgyons, colors_full, geopolygon_names)

    sketch.set_stroke('#333333')

    # draw each shape (state)
    for (geo_polygon, color, name) in geo_polgyons_with_colors:
        

        shape = geo_polygon.to_shape()
        
        # Draw
        sketch.set_fill(color)

        #move Alaska and Hawaii closer:
        
        if name == 'Alaska':
            sketch.push_transform()
            sketch.translate(100, 350)
            sketch.scale(0.4)
            sketch.draw_shape(shape)
            sketch.pop_transform()
        elif name == 'Hawaii':
            sketch.push_transform()
            sketch.translate(350, -675)
            sketch.scale(2)

            sketch.draw_shape(shape)
            sketch.pop_transform()
        elif name == 'Puerto Rico':
            continue
            #NEED TO FIX CRASHING WHERE HOVER OVER TERRITORIES --> CRASH
        else:
            sketch.draw_shape(shape)

def draw_interactive(sketch):
    global year
    global running_animation
    already_clicked = False
    sketch.clear("#F0F0F0")
    draw_map(sketch)

    sketch.push_transform()
    sketch.translate(0, 450)

    sketch.push_style()
    sketch.set_fill("#000000")
    x_coord, y_coord = mouse.get_pointer_x(), mouse.get_pointer_y()

    sketch.push_style()
    sketch.set_text_font(FONT, 22)
    sketch.set_stroke_weight(0)

    #sketch.draw_ellipse(100, 200, 50, 60)
    if press_states['left'] == True:
        if year > 1960:
            year = year - 1
        press_states['left'] = False
        already_clicked = True

    elif press_states['right'] == True:
        if year < 2022:
            year = year + 1
        press_states['right'] = False
        already_clicked = True
    
    pressed_list = list(keyboard.get_keys_pressed())
    pressed_list_str = [x.get_name() for x in pressed_list]
    #print(pressed_list)
    if "left" in pressed_list_str and already_clicked == False:
        if year > 1960:
            year = year - 1
    elif "right" in pressed_list_str and already_clicked == False:
        if year < 2022:
            year = year + 1

    
    sketch.set_text_font(FONT, 12)
    sketch.draw_text(WIDTH / 2 - 450, 160, 'Mouse Position: ' + str(x_coord) + ", " + str(y_coord))
    closest_state = find_closest_coordinate((x_coord, y_coord))
    sketch.set_text_font(FONT, 16)
    sketch.draw_text(WIDTH/2 - 450, 135, 'Closest State to Mouse Pos: ' + closest_state)

    #500, 200
    #draw proportion bar charts for current hover
    #corners: Left and top coordinates followed by right and bottom coordinates.
    sketch.push_style()

    sketch.set_rect_mode('corners')
    sketch.set_fill('#000000')
    production_row = joined_df[(joined_df['State'] == state_to_abbrev[closest_state]) & (joined_df['Year'] == year)]
    consumption_row = consumption_joined_df[(consumption_joined_df['State'] == state_to_abbrev[closest_state]) & (consumption_joined_df['Year'] == year)]
    
    production_prop = production_row['Proportion'].iloc[0]
    consumption_prop = consumption_row['Proportion'].iloc[0]

    production_total = production_row['Total Prod'].iloc[0]
    production_renewable = production_row['Renewable Prod'].iloc[0]

    consumption_total = consumption_row['Total Consumption'].iloc[0]
    consumption_renewable = consumption_row['Renewable Consumption'].iloc[0]


    sketch.set_text_font(FONT, 14)
    sketch.draw_text(500, 160, closest_state + ' ' + str(year) + ' : Renewable Production (P), Consumption (C)')
    
    
    if consumption_setting:
        sketch.draw_text(100, 200, "Total Energy Consumption:              "+str(consumption_total)[:-2])
        sketch.draw_text(100, 220, "Renewable Energy Consumption: "+str(consumption_renewable)[:-2])
    else:
        sketch.draw_text(100, 200, "Total Energy Production:              "+str(production_total)[:-2])
        sketch.draw_text(100, 220, "Renewable Energy Production: "+str(production_renewable)[:-2])
    sketch.set_text_font(FONT, 12)
    sketch.draw_text(310, 180, 'Billion Btu')
    sketch.draw_text(650, 270, 'Proportion')

    sketch.draw_rect(500, 180, 500 + 300 * production_prop, 200)
    sketch.draw_text(500 - 20, 195, 'P')

    sketch.draw_rect(500 + 300 * consumption_prop, 210, 500, 230)
    sketch.draw_text(500 - 20, 225, 'C')
    
    for i in range(6):
        sketch.set_stroke_weight(0)
        sketch.draw_text(500 + 300 * i/5, 250, str(i/5))

        if i > 0:
            sketch.set_stroke_weight(2)
            sketch.set_stroke(BACKGROUND_COL)
            sketch.draw_line(500 + 300 * i/5, 260, 500 + 300 * i/5, 175)

    #sketch.draw_rect()

    sketch.pop_style()
    mode = ""

    sketch.push_style()
    sketch.set_text_font(FONT, 12)

    sketch.push_transform()
    sketch.translate(0, -50)

    height_offset = 600
    if consumption_setting:
        mode = 'Renewable Consumption Share'
        for i in range(201):
            sketch.set_fill(interpolate_color(i/200, end_hex=ENERGY_CONSUMP_COLOR))
            sketch.draw_rect((WIDTH / 2) + 400, HEIGHT - height_offset - 2 * i, 20, 1)

            if i % 40 == 0:
                sketch.set_fill('#000000')
                sketch.draw_text((WIDTH / 2) + 400 - 30, HEIGHT - height_offset - 2 * i, str(i/(200*(10/4))))

                sketch.set_stroke_weight(1)
                sketch.draw_line((WIDTH / 2) + 400 - 5, HEIGHT - height_offset - 2 * i, (WIDTH / 2) + 400 + 5, HEIGHT - height_offset - 2 * i )
                sketch.set_stroke_weight(0)

    else:
        mode = 'Renewable Production Share'
        for i in range(201):
            sketch.set_fill(interpolate_color(i/200))
            sketch.draw_rect((WIDTH / 2) + 400, HEIGHT - height_offset - 2 * i, 20, 1)

            if i % 40 == 0:
                sketch.set_fill('#000000')
                sketch.draw_text((WIDTH / 2) + 400 - 30, HEIGHT - height_offset - 2 * i, str(i/200))

                sketch.set_stroke_weight(1)
                sketch.draw_line((WIDTH / 2) + 400 - 5, HEIGHT - height_offset - 2 * i, (WIDTH / 2) + 400 + 5, HEIGHT - height_offset  - 2 * i )
                sketch.set_stroke_weight(0)
    
    sketch.pop_transform()

    sketch.pop_style()
    sketch.pop_transform()
    sketch.set_text_font(FONT, 22)
    sketch.draw_text(100, 200, "Current Display: " + mode)
    sketch.set_text_font(FONT, 16)
    sketch.draw_text(100, 225, "Press 'C' to switch")

    sketch.set_text_font(FONT, 22)
    sketch.draw_text(WIDTH/2 + 100, 200, 'Year: ' + str(year))
    sketch.set_text_font(FONT, 12)
    sketch.draw_text(WIDTH/2 + 100, 225, 'Arrow Keys (L), (R) to Change Year')
    sketch.draw_text(WIDTH/2 + 100, 235, "Press 'P' for autoplay ")

    sketch.set_text_font(FONT, 24)
    sketch.draw_text(100, 45, 'Data Visualization Final Project: A Look At Renewable Energy Trends in U.S States')
    sketch.set_text_font(FONT, 20)
    sketch.draw_text(100, 75, 'Renewable Proportion (Share) of Total Energy Consumption/Production (1960-2022)')
    sketch.set_text_font(FONT, 12)
    sketch.draw_text(100, 95, '**Note: U.S Territories not represented (i.e American Samoa, Guam, etc.) due to missing data')



    sketch.pop_style()

    if running_animation:
        year = year + 1
        time.sleep(0.2)
    
    if running_animation and year == 2022:
        running_animation = not running_animation
    

running_animation = False
def run_interactive():
    
    def handle_press(button):
        global consumption_setting
        global year
        global running_animation
        #if button is left click
        #print(button.get_name())
        if button.get_name() == 'c':
            print('switched')
            consumption_setting = not consumption_setting
        
        if button.get_name() == 'p' and not running_animation:
            if year == 2022:
                year = 1960
            running_animation = True

            print('done')
        elif button.get_name() == 'p' and running_animation:
            running_animation = False
        
        press_states[button.get_name()] = True



    mouse.on_button_press(handle_press)
    keyboard.on_key_press(handle_press)
    sketch.on_step(draw_interactive)


sketch.set_fps(100)

draw_map(sketch)
run_interactive()
sketch.show()