# import libraries for building a Streamlit web app, 
# using pandas and numpy for handling data
import streamlit as st
import pandas as pd
import numpy as np

# execute R code using the Python to R data type conversion
import rpy2.robjects as rpy # to access R objects within Python
from rpy2.robjects.conversion import localconverter
from rpy2.robjects import default_converter, pandas2ri, numpy2ri

# activate R to Python conversion rules
with localconverter(default_converter):
    #load Rscript to load its function into R memory
    rpy.r["source"]("finalproj.R")

    #Retrieves the R function from R and bind them to python variable
    buildInitialTableau = rpy.globalenv["BuildInitialTableau"]
    simplex = rpy.globalenv["Simplex"]


#gas group list 
groups = ["Coal", "Natural Gas", "Geothermal", "Hydro", "Oil-based", "Solar", "Wind"]

#constraints, constant
timeblock = 6
demand = [6300,8600,11800,12300,14000, 10600]
capacity = [7000, 3300, 800,2500,1500, 2500, 400]

a_solar_t = [0, 0.10, 0.60, 0.55, 0.08, 0 ]
a_wind_t = [0.35, 0.30, 0.25,0.25, 0.30, 0.35]

coal_min = 2800
coalramp = 1500
hydrowater = 8000

emissions = [0.95, 0.40, 0.10, 0,0.75,0,0]

#dictionary: key = plant groups, value = list of operating cost on each timeblock
cgt = {"Coal":[3800,3838,3914,3990, 3952, 3876], 
       "Natural Gas":[6500,6565,6695,6825,6760, 6630], 
       "Geothermal": [1500, 1515, 1545, 1575, 1560, 1530], 
       "Oil-based": [14000, 14140, 14420, 14700,14560,14280]}

# tab title, layout formating, add icon
st.set_page_config(
    page_title = "Luzon Grid Dispatch and Price Simulator",
    layout = "wide",
    page_icon = "🔋"
)

# add background color and border radius to columns
st.markdown("""
<style>
/* font */
html, body { 
    font-size: 16px; 
}

h1 { 
    color: #0F7542; 
    font-size: 2.15rem !important; 
}

h2, h3 { 
    color: #163B29; 
    }

div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #F3F8F3;
    border: 1px solid #D6E5D8;
    border-radius: 10px;
    padding: 10px;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #064E2B 0%, #0F7542 100%);
}

section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label { 
    color: white !important; 
}

/* highlight the main cost and iteration metrics */
div[data-testid="stMetric"] {
    background-color: #E4F1E6;
    border: 1px solid #B8D4BE;
    border-radius: 10px;
    padding: 14px;
}

div[data-testid="stMetricLabel"] { 
    color: #245C3A; 
}

div[data-testid="stMetricValue"] { 
    color: #064E2B; 
    }
</style>
""", unsafe_allow_html=True)



#Web app title
st.title("Luzon Grid Dispatch and Price Simulator")


# Add a sidebar 
with st.sidebar:
    st.title("Luzon Grid Dispatch")
    st.write("Power generation • Minimum-cost dispatch • Electricity pricing")
    st.divider()
    st.markdown("**How to use**")
    st.markdown("1. Select the available plant groups.\n 2. Toggle the CO2 cap on or off. \n\n\t 2.a If toggle on, set the optional CO2 limit.\n3. Press **Solve** to run the simplex method.")
    st.divider()
    


#dictionary like API to set all plant checkboxes checked by default
for g in groups:
    if g not in st.session_state:
        st.session_state[g] = True

#CO2 constraint toggle disabled by default 
if "use_co2" not in st.session_state:
    st.session_state.use_co2 = False
#set the default maximum CO2 limit
if "co2_limit" not in st.session_state:
    st.session_state.co2_limit = 165000

#track the solver output
if "solved" not in st.session_state:
    st.session_state.solved = None
#
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(np.random.randn(20, 2), columns=["x", "y"])




#initialize an empty selected gas group list
selected_g = []

first_column, second_column = st.columns(2, border = True)

with first_column:
    st.header("Select Power Plant Groups")
#for loop to access each plant groups and make a checkbox, if check append it into selected_g list 
    cols = st.columns(3)

    for i, g in enumerate(groups):
        with cols[i % 2]:
            if st.checkbox(g, key=g):
                selected_g.append(g)

    with cols[2]:
        #check all function
        def check_all():
            for g in groups:
                st.session_state[g] = True

        #reset all function
        def reset_all():
            for g in groups:
                st.session_state[g] = False

            st.session_state.use_co2 = False
            st.session_state.co2_limit = 165000
            st.session_state.solved = None

        #check all button
        st.button("Check All:",on_click = check_all)

        #reset button
        st.button("Reset", on_click = reset_all)
st.divider()

with second_column:
    st.header("CO2 Cap Toggle On")

    #toggle switch to turn CO2 emission limit on or off
    use_co2 = st.toggle("Enable CO2 emission limit", key="use_co2")

#show number input if CO2 is enabled
    if use_co2:
        co2_limit = st.number_input("Limit daily CO2 emissions (tons/day)", min_value=1,step=5000,key="co2_limit")
    else:
        co2_limit = st.session_state.co2_limit

# solve button to validate inputs and save user selection
if st.button("Solve", type="primary", width="stretch"):
    if len(selected_g) == 0:
        st.error("Please select at least one power plant.")
    
    elif use_co2 and co2_limit <= 0:
        st.error("CO2 limit must be greater than zero.")

    else:
        st.session_state.solved = {"groups": selected_g.copy(),"use_co2": use_co2,"co2_limit": co2_limit}
        st.success("Your response have been save!")

st.divider()

# only run optimization if at least one power plant is selected
#if len(selected_g) > 0:
   
st.header("Optimization")
rows = []
row_labels = []

for t in range(1, timeblock + 1):
    row = []
    for g in selected_g:
        for block in range(1, timeblock+1):
            if block == t:
                row.append(1)
            else:
                row.append(0)
    row.append(demand[t-1])
    rows.append(row)
    row_labels.append(f"Demand_{t}")


 #Capacity
for g in selected_g:
    gas_index = groups.index(g)
    for t in range(1, timeblock + 1):
        row = []
        for selected in selected_g:  
            for block in range(1, timeblock + 1):
                if selected == g and block == t:
                    row.append(-1)
                else:
                    row.append(0)

        if (g == "Solar"):
            max_capacity = capacity[gas_index] * -1 * a_solar_t[t-1]
        elif (g == "Wind"):
            max_capacity = capacity[gas_index] * -1 * a_wind_t[t-1]
        else:
            max_capacity = capacity[gas_index] * -1
            
        row.append(max_capacity)  
        rows.append(row)
        row_labels.append(f"Capacity_{g},{t}") 

#Coal Minimum
if "Coal" in selected_g:
    for t in range(1, timeblock + 1):
        row = []
        for g in selected_g:
            for block in range(1, timeblock + 1):
                if g == "Coal" and block == t:
                    row.append(1)
                else:
                    row.append(0)
       
        row.append(coal_min)
        rows.append(row)
        row_labels.append(f"CoalMin_t{t}")

if "Coal" in selected_g:
    for t in range(1, timeblock):
        row_rise = []
        for g in selected_g:
            for block in range(1, timeblock + 1):
                if g == "Coal" and block == t:
                    row_rise.append(1)

                elif g == "Coal" and block == t + 1:
                    row_rise.append(-1)

                else:
                    row_rise.append(0)

        row_rise.append(coalramp * -1)
        rows.append(row_rise)
        row_labels.append(f"CoalRampRise_t{t}")

        # Ramp fall
        row_fall = []

        for g in selected_g:
            for block in range(1, timeblock + 1):
                if g == "Coal" and block == t:
                    row_fall.append(-1)
                elif g == "Coal" and block == t + 1:
                    row_fall.append(1)

                else:
                    row_fall.append(0)
        row_fall.append(coalramp * -1)
        rows.append(row_fall)
        row_labels.append(f"CoalRampFall_t{t}")

#Hydrowater Constraints
if "Hydro" in selected_g:
    row = []
    for g in selected_g:
        for t in range(1, timeblock + 1):
            if g == "Hydro":
                row.append(-4)
            else:
                row.append(0)

    row.append(hydrowater *-1)
    rows.append(row)
    row_labels.append("HydroWater")

#CO2 cap toggle on constraints
if use_co2:
    row = []
    for g in selected_g:
        for t in range(1, timeblock + 1):
            emission_index = groups.index(g)

            row.append(-1 *4 * emissions[emission_index])
    row.append(co2_limit*-1)
    rows.append(row)
    row_labels.append("CO2 toggle")

#linear objective function
h = 4
row = []
for g in selected_g:
    gas_index = groups.index(g)
    for t in range(1, timeblock + 1):
        if g == "Solar":
            cost = h * 40
        elif g == "Wind":
            cost = h*60
        elif g == 'Hydro':
            cost = h *300
        elif g in cgt:
            idx = min(t - 1, len(cgt[g]) - 1)
            cost = h * cgt[g][idx]
        else:
            cost = h * 1000
        row.append(cost)       
    
row.append(1)
rows.append(row)
row_labels.append("Linear Objective Function")


# Build column headers
col_headers = []
for g in selected_g:
    for t in range(1, timeblock + 1):
        col_headers.append(f"x_{g},{t}")
col_headers.append("Solution")

matrix_df = pd.DataFrame(
    rows, 
    columns=col_headers, 
    index=row_labels)

st.subheader("Primal Tableau")
st.dataframe(matrix_df, width="stretch")


converter = default_converter + pandas2ri.converter + numpy2ri.converter

if st.session_state.solved is not None:
    config = st.session_state.solved
    
    # To call the buildInitialTableau function in the Rfile
    with localconverter(converter):
        initialTableau = buildInitialTableau(matrix_df.to_numpy(dtype=float))

    #shows initial Tableau
     # x_g,t label follows the selected plant groups and timeblock
    tableau_columns = (
    [f"S{i}" for i in range(1, matrix_df.shape[0])]
    + [f"x_{g},{t}" for g in selected_g for t in range(1, timeblock + 1)]
    + ["Z", "Solution"]
)


    st.subheader("Primal Tableau")
    # Display the initial tableau
    st.dataframe(
        pd.DataFrame(initialTableau, columns=tableau_columns),
        width="stretch"
    )


    with localconverter(converter):
        result = simplex(initialTableau, False)

    # handle infeasibility before displaying optimal-solution outputs
    if "status" in result.keys():
        status = str(result["status"][0])
    else:
        status = "optimal"

    iterations = int(np.array(result["iteration"]).item())
        
    if "infeasible" in status:
        st.error("The problem is infeasible.")
        st.metric(label= "Number of Iterations", value = iterations)
    else:
        st.success("Optimal solution found")
        final_tableau = np.array(result["finalTableau"])
        basic_solution = np.array(result["basicSolution"])
    
        # st.write("Final tableau:", final_tableau)
        # st.write("Basic solution:", basic_solution)

        st.divider()

        st.header("Optimization Results")

        results_tab, tableau_tab, chart_tab = st.tabs(["Results", "Simplex Tableau", "Chart"])

        with results_tab:

            column1, column2, column3 = st.columns(3, border=True)

            with column1:
                st.subheader("Selected Power Plants")
                st.write(", ".join(config["groups"]))

            with column3:
                st.subheader("CO2 Constraint")

                if config["use_co2"]:
                    st.write( f"Enabled — {config['co2_limit']:,} tons/day")
                else:
                    st.write("Disabled")

            with column2:
                st.subheader("Number Selected Plant Groups")
                st.subheader(len(selected_g))
                

            z_value = float(np.array(result["Z"]).item())
            iterations = int(np.array(result["iteration"]).item())

            col1, col2 = st.columns(2, border=True)
            with col1:
                st.metric(label="Total Minimum Cost (Z)", value=f"₱{z_value:,.2f}")
            with col2:
                st.metric(label="Iterations", value=iterations)


            summary1, summary2 = st.columns(2, border = True)

            with summary1:
                st.metric("Number of Unknowns", len(config["groups"]* timeblock))

            with summary2:
                st.metric("Number of Constraints", len(row_labels)-1)

            st.subheader("Unknowns (MW)")

            # Get the values of x_gt from the final tableau
            start = len(rows) - 1
            end = start + len(config["groups"]) * timeblock
            unknowns = final_tableau[-1, start:end]
            unknows_df = pd.DataFrame(
                unknowns.reshape(len(config["groups"]), timeblock),
                columns=['B1', 'B2', 'B3', 'B4', 'B5', 'B6']
                
            )
            unknowns = final_tableau[-1, start:end]

            #insert the plant groups names
            unknows_df.insert(0, "Parameter", config["groups"])
        
            st.dataframe(
                unknows_df,
                width="stretch",
                hide_index=True)

            #diaplaying the prices of the demand Constraints
            st.subheader("Prices of the demand constraints")
            
            prices = []

            for t in range(timeblock):

                column = final_tableau[:, t]

                if np.count_nonzero(column) == 1 and 1 in column:
                    index = np.where(column == 1)[0][0]
                    price = final_tableau[index, -1] / 4
                else:
                    price = 0

                prices.append(price)

            df = pd.DataFrame({
                "Parameter": ["Price = St / 4 (₱/MWh)"],
                "B1": [prices[0]],
                "B2": [prices[1]],
                "B3": [prices[2]],
                "B4": [prices[3]],
                "B5": [prices[4]],
                "B6": [prices[5]]
            })

            st.dataframe(df, width="stretch", hide_index=True)

        with tableau_tab:
        
            st.subheader("Simplex Iteration History")

            st.write(
                "The tableau and Basic Solution for every iteration will appear "
                "here after connecting the R solver."
            )
        
            # to input data 
            for i, (_, step_data) in enumerate(result["history"].items()):
                with st.expander(f"Iteration {i}"): #uses expander
                    st.write("### Tableau")

                    #column names
                    tableau_columns = (
                        [f"S{x}" for x in range(1, matrix_df.shape[0])]
                        + [f"x_{g},{t}" for g in selected_g
                        for t in range(1, timeblock + 1)]
                        + ["Z", "Solution"]
                    )

                    st.dataframe(pd.DataFrame(np.array(step_data["finalTableau"]), 
                        columns = tableau_columns),
                          width="stretch")

                    st.write("### Basic Solution")

                    basic_columns = tableau_columns[:-1]

                    st.dataframe(pd.DataFrame(np.array(step_data["basicSolution"]), columns = basic_columns),width="stretch")

        with chart_tab:

            col1, col2 = st.columns(2)

            with col1:
                # Unknowns Table 
                st.subheader("Generation Dispatch by Time Block (MW)")
                # Transpose unknowns_df so Time Blocks (B1–B6) are on the X-axis and Plants are stacked
                dispatch_chart_df = df.set_index("Parameter").T
                st.bar_chart(
                    dispatch_chart_df,
                    x_label="Time Block",
                    y_label="Generation Output (MW)",
                    width="stretch"
                )

            with col2:
                st.subheader("Marginal Cost of Demand Across Time Blocks (₱/MWh)")
                # Build a DataFrame for the 6 block prices
                price_chart_df = pd.DataFrame({
                    "Time Block": ["B1", "B2", "B3", "B4", "B5", "B6"],
                    "Marginal Price (₱/MWh)": prices
                }).set_index("Time Block")

                st.line_chart(
                    price_chart_df,
                    x_label="Time Block",
                    y_label="Price (₱/MWh)",
                    width="stretch"
                )

        
#"st.session_state object: ", st.session_state






# References:
# https://docs.streamlit.io/get-started
# https://www.youtube.com/watch?v=o8p7uQCGD0U
    
        


