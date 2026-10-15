"""UK-DALE converter (.dat family, UK households).

Raw layout mirrors REDD: house_<n>/channel_<m>.dat (watts) plus
labels.dat. Channels 1-2 are the mains legs (apparent power); UK
wall-clock seconds in Europe/London.
"""
from __future__ import annotations

from oed.converters.dat_family import DatFamilyConverter

DATASET_ID = "ukdale"
SOURCE_URL = "https://data.ukedc.rl.ac.uk/browse/edc/efficiency/residential/EnergyConsumption/Domestic/UK-DC"
SOURCE_LICENSE = "Academic research use; redistribution restricted (see project page)"
CITATION = (
    "Jack Kelly and William Knottenbelt. The UK-DALE dataset, Domestic "
    "Appliance-Level Electricity Demand and Whole-House Demand from Five UK "
    "Homes. Scientific Data 2, 150007, 2015."
)

APPLIANCE_TYPES = {
    "boiler": "electric boiler",
    "solar": "PV inverter",
    "mains": "distribution board",
    "freezer": "fridge-freezer",
    "fridge_freezer": "fridge-freezer",
    "kettle": "electric kettle",
    "dish_washer": "dish washer",
    "washing_machine": "washing machine",
    "washer_dryer": "washer dryer",
    "tv": "television",
    "audio": "hifi",
    "lamp": "light",
    "light": "light",
    "laptop": "laptop computer",
    "computer": "desktop computer",
    "router": "network equipment",
    "server": "server",
    "monitor": "computer monitor",
    "oven": "electric oven",
    "microwave": "microwave oven",
    "toaster": "toaster",
    "breadmaker": "breadmaker",
    "fan": "electric fan",
    "heater": "electric space heater",
    "electric_heater": "electric space heater",
    "hair_dryer": "hair dryer",
    "vacuum": "vacuum cleaner",
    "iron": "iron",
    "pond_pump": "pump",
    "electric_bike": "electric bike charger",
    "hybrid_car": "EV charger",
    "sub_meter": "distribution board",
}


class UkdaleConverter(DatFamilyConverter):
    dataset_id = DATASET_ID
    source_url = SOURCE_URL
    source_license = SOURCE_LICENSE
    citation = CITATION
    timezone = "Europe/London"
    name = "ukdale-oed"
    description = "UK-DALE converted to the OpenEnergyData unified format"
    creators = ["Kelly, Jack", "Knottenbelt, William"]
    date_published = "2015-03-31"
    keywords = ["energy", "nilm", "disaggregation", "uk-dale", "oed"]
    n_site_meters = 2
    site_meter_ac_type = "apparent"
    appliance_types = APPLIANCE_TYPES
    geo = {"country": "GB", "locality": "London area",
           "latitude": 51.5074, "longitude": -0.1278}
