"""REDD converter (thin wrapper around the .dat family base)."""
from __future__ import annotations

from oed.converters.dat_family import DatFamilyConverter

DATASET_ID = "redd"
SOURCE_URL = "http://redd.csail.mit.edu"
SOURCE_LICENSE = "Free for academic research use (see REDD project page)"
CITATION = (
    "J. Zico Kolter and Matthew J. Johnson. REDD: A public data set for "
    "energy disaggregation research. SustKDD workshop, 2011."
)

APPLIANCE_TYPES = {
    "oven": "electric oven",
    "refrigerator": "fridge",
    "dishwaser": "dish washer",  # upstream label is misspelled in REDD
    "dish_washer": "dish washer",
    "dishwasher": "dish washer",
    "kitchen_outlets": "sockets",
    "bathroom_gfi": "sockets",
    "lighting": "light",
    "lights": "light",
    "washer_dryer": "washer dryer",
    "microwave": "microwave oven",
    "furnace": "electric furnace",
    "well_pump": "pump",
    "electronics": "consumer electronics",
    "subpanel": "distribution board",
    "smoke_alarm": "smoke alarm",
    "stove": "electric stove",
    "air_conditioning": "air conditioner",
    "miscellaeneous": "sockets",
    "electric_heat": "electric space heater",
}


class ReddConverter(DatFamilyConverter):
    dataset_id = DATASET_ID
    source_url = SOURCE_URL
    source_license = SOURCE_LICENSE
    citation = CITATION
    timezone = "America/New_York"
    name = "redd-oed"
    description = "REDD converted to the OpenEnergyData unified format"
    creators = ["Kolter, Zico", "Johnson, Matthew"]
    date_published = "2011-04-18"
    keywords = ["energy", "nilm", "disaggregation", "redd", "oed"]
    n_site_meters = 2
    site_meter_ac_type = "apparent"
    appliance_types = APPLIANCE_TYPES
    geo = {"country": "US", "locality": "Massachusetts",
           "latitude": 42.360091, "longitude": -71.09416}
