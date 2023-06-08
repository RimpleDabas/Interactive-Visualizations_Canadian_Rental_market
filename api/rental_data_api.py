import numpy as np
import pandas as pd
from pprint import pprint
from pymongo import MongoClient
from flask import Flask, jsonify

#################################################
# Database Setup
#################################################
mongo = MongoClient(port=27017)

db = mongo['rental_data']
rental_information = db['canadian_rental_market']

#################################################
# Flask Setup
#################################################
app = Flask(__name__)

#################################################
# Flask Routes
#################################################
@app.route("/")
def index():
    return (
        f"Welcome to the Rental Data Analysis API!<br/>"
        f"Available Routes:<br/>"
        f"===============================================================<br/>"
        f"Filter Endpoints</br>"
        f"===============================================================<br/>"
        f"/api/v1.0/location_filter/provinces<br/>"
        f"/api/v1.0/location_filter/centers/&lt;province&gt;<br/>"
        f"/api/v1.0/location_filter/zones/&lt;province&gt;/&lt;center&gt;<br/>"
        f"/api/v1.0/location_filter/neighbourhoods/&lt;province&gt;/&lt;center&gt;/&lt;zone&gt;<br/>"
        f"/api/v1.0/location_filter/years<br/>"
        f"/api/v1.0/location_filter/dwellingtypes<br/>"
        f"===============================================================<br/>"
        f"Endpoint to get rental information for unqiue province + center combinations<br/>"
        f"===============================================================<br/>"
        f"/api/v1.0/province_centers<br/>"
        f"===============================================================<br/>"
        f"Endpoint to get rental information based on selected parameters<br/>"
        f"<br/>"
        f"*NOTE: For following routes pass 'na' for cases where you wan to skip<br/>"
        f"any filter that comes before the one you want to filter for<br/></br>"
        f"Example: if you want to filter on year, use /api/v1.0/rental_data/na/na/na/na/2018<br/>"
        f"===============================================================<br/>"
        f"/api/v1.0/rental_data/&lt;province&gt;<br/>"
        f"/api/v1.0/rental_data/&lt;province&gt;/&lt;center&gt;<br/>"
        f"/api/v1.0/rental_data/&lt;province&gt;/&lt;center&gt;/&lt;zone&gt;<br/>"
        f"/api/v1.0/rental_data/&lt;province&gt;/&lt;center&gt;/&lt;zone&gt;/&lt;neighbourhood&gt;/&lt;year&gt;<br/>"
        f"/api/v1.0/rental_data/&lt;province&gt;/&lt;center&gt;/&lt;zone&gt;/&lt;neighbourhood&gt;/&lt;year&gt;/&lt;dwellingtype&gt;"
    )

@app.route("/api/v1.0/rental_data/<p>" , defaults={'c': None, 'z': None, 'n': None, 'y': None, 'dt': None })
@app.route("/api/v1.0/rental_data/<p>/<c>" , defaults={'z': None, 'n': None, 'y': None, 'dt': None })
@app.route("/api/v1.0/rental_data/<p>/<c>/<z>" , defaults={'n': None, 'y': None, 'dt': None })
@app.route("/api/v1.0/rental_data/<p>/<c>/<z>/<n>" , defaults={'y': None, 'dt': None })
@app.route("/api/v1.0/rental_data/<p>/<c>/<z>/<n>/<y>" , defaults={'dt': None })
@app.route("/api/v1.0/rental_data/<p>/<c>/<z>/<n>/<y>/<dt>")
def get_rental_information(p, c, z, n, y, dt):

    output = get_rental_data(p, c, z, n, y, dt)

    return jsonify(output)

@app.route("/api/v1.0/province_centers")
def get_province_centers():
    rental_data = []

    query = rental_information.aggregate( 
                [
                    {"$group": { "_id": { "Province": "$Location.Province", "Center": "$Location.Center" } } }
                ]
            )
    
    df = pd.json_normalize(query)

    for index, row in df.iterrows():
         rental_data.append(get_rental_data(row["_id.Province"], row["_id.Center"], 'na', 'na', 'na', 'na', True))

    return jsonify(rental_data)

@app.route("/api/v1.0/location_filter/provinces")
def get_province():
    provinces = list(rental_information.find().distinct("Location.Province"))
    return jsonify(provinces)

@app.route("/api/v1.0/location_filter/centers/<province>")
def get_center(province):
    query = { "Location.Province": province }
    centers = list(rental_information.find(query).distinct("Location.Center"))
    return jsonify(centers)

@app.route("/api/v1.0/location_filter/zones/<province>/<center>")
def get_zones(province, center):
    query = { "Location.Province": province, "Location.Center": center }
    zones = list(rental_information.find(query).distinct("Location.Zone"))
    return jsonify(zones)

@app.route("/api/v1.0/location_filter/neighbourhoods/<province>/<center>/<zone>")
def get_neighbourhood(province, center, zone):
    query = { "Location.Province": province, "Location.Center": center, "Location.Zone": zone }
    neighbourhood = list(rental_information.find(query).distinct("Location.Neighbourhood"))
    return jsonify(neighbourhood)

@app.route("/api/v1.0/location_filter/years")
def get_years():
    years = list(rental_information.find().distinct("Year"))
    return jsonify(years)

@app.route("/api/v1.0/location_filter/dwellingtypes")
def get_dwellingtypes():
    dwellingtypes = list(rental_information.find().distinct("DwellingType"))
    return jsonify(dwellingtypes)

def get_query(p, c, z, n, y, dt):
    query = {}

    if(p is not None and p != "na"):
        query["Location.Province"] = p

    if(c is not None and c != "na"):
        query["Location.Center"] = c

    if(z is not None and z != "na"):
            query["Location.Zone"] = z

    if(n is not None and n != "na"):
            query["Location.Neighbourhood"] = n

    if(y is not None and y != "na"):
            query["Year"] = int(y)

    if(dt is not None and dt != "na"):
            query["DwellingType"] = dt

    return query

def get_rental_data(p, c, z, n, y, dt, geo = False):
     # Create query based on parameter
    query = get_query(p, c, z, n, y, dt)

    df = pd.json_normalize(rental_information.find(query))

    output = {}

    #location rent
    filter_dict = {}
    filter_dict["Province"] = p
    filter_dict["Center"] = c
    filter_dict["Zone"] = z
    filter_dict["Neighbourhood"] = n
    filter_dict["Year"] = y
    filter_dict["DwellingType"] = dt

    output["Filter"] = filter_dict

    if(len(df.index) > 0):

        if(geo):
            geo_dict = {}
            geo_dict["Lat"] = df["Location.CenterGeo.lat"].iloc[0]
            geo_dict["Lon"] = df["Location.CenterGeo.lon"].iloc[0]
            output["Filter"]["CenterGeo"] = geo_dict

        #avearage rent
        ar_dict = {}
        ar_dict["Bachelor"] = df.loc[df["RentalInformation.AverageRent.Bachelor"] != 0, "RentalInformation.AverageRent.Bachelor"].mean()
        ar_dict["1br"] = df.loc[df["RentalInformation.AverageRent.1br"] != 0, "RentalInformation.AverageRent.1br"].mean()
        ar_dict["2br"] = df.loc[df["RentalInformation.AverageRent.2br"] != 0, "RentalInformation.AverageRent.2br"].mean()
        ar_dict["3br+"] = df.loc[df["RentalInformation.AverageRent.3br+"] != 0, "RentalInformation.AverageRent.3br+"].mean()
        ar_dict["Total"] = df.loc[df["RentalInformation.AverageRent.Total"] != 0, "RentalInformation.AverageRent.Total"].mean()

        #vacancy rate
        vr_dict = {}
        vr_dict["Bachelor"] = df.loc[df["RentalInformation.VacancyRate.Bachelor"] != 0, "RentalInformation.VacancyRate.Bachelor"].mean()
        vr_dict["1br"] = df.loc[df["RentalInformation.VacancyRate.1br"] != 0, "RentalInformation.VacancyRate.1br"].mean()
        vr_dict["2br"] = df.loc[df["RentalInformation.VacancyRate.2br"] != 0, "RentalInformation.VacancyRate.2br"].mean()
        vr_dict["3br+"] = df.loc[df["RentalInformation.VacancyRate.3br+"] != 0, "RentalInformation.VacancyRate.3br+"].mean()
        vr_dict["Total"] = df.loc[df["RentalInformation.VacancyRate.Total"] != 0, "RentalInformation.VacancyRate.Total"].mean()

        #total number of units
        nu_dict = {}
        nu_dict["Bachelor"] = df.loc[df["RentalInformation.NumberofUnits.Bachelor"] != 0, "RentalInformation.NumberofUnits.Bachelor"].sum()
        nu_dict["1br"] = df.loc[df["RentalInformation.NumberofUnits.1br"] != 0, "RentalInformation.NumberofUnits.1br"].sum()
        nu_dict["2br"] = df.loc[df["RentalInformation.NumberofUnits.2br"] != 0, "RentalInformation.NumberofUnits.2br"].sum()
        nu_dict["3br+"] = df.loc[df["RentalInformation.NumberofUnits.3br+"] != 0, "RentalInformation.NumberofUnits.3br+"].sum()
        nu_dict["Total"] = df.loc[df["RentalInformation.NumberofUnits.Total"] != 0, "RentalInformation.NumberofUnits.Total"].sum()

        output["AverageRents"] = ar_dict
        output["AvearageVacancytRate"] = vr_dict
        output["TotalNumberOfUnits"] = nu_dict

    return output

if __name__ == '__main__':
    app.run(debug=True)
