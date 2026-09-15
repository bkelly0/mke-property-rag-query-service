prompt = """
Base table: mprop_master (alias: m)

Available fields:

- house_number_low: low/start house number
- house_number_high: high/end house number; use when the address represents a range
- house_number_suffix: house-number suffix, such as A or 1/2
- street_direction: street directional prefix, such as N, S, E, or W
- street_name: street name
- street_type: street type or suffix, such as St, Ave, Rd, or Blvd
- building_type_desc: building type description
- convey_type_desc: conveyance type description
- num_stories: number of stories
- has_basement: whether the property has a basement
- has_attic: whether the property has an attic
- has_fireplace: whether the property has a fireplace
- num_rooms: total number of rooms
- num_bedrooms: number of bedrooms
- num_baths: number of full bathrooms
- num_half_bath: number of half bathrooms
- year_built: year the building was built
- building_area: building area
- lot_area: lot area
- historic_code: historic designation code
- historic_desc: historic designation description
- zoning: zoning code
- zip: ZIP code
- taxkey: unique property tax key
- assessment_class: assessment class code
- assessment_class_desc: assessment class description
- assessed_total: current total assessed value
- assessed_land: current assessed land value
- assessed_improvement: current assessed improvement value
- prev_assessed_total: previous total assessed value
- prev_assessed_land: previous assessed land value
- prev_assessed_improvement: previous assessed improvement value
- assessment_year: assessment year
- land_use_description: land-use description
- land_use_category_description: land-use category description
- zoning_district_name: zoning district name
- owner_name_1: primary owner name
- owner_name_2: secondary owner name
- owner_name_3: tertiary owner name
- owner_address: owner mailing address
- last_ownership_change: most recent ownership-change date
- neighborhood: neighborhood name
- current_excemption_code: current exemption code
- current_excemption_type_desc: current exemption type description
- alderman_dist: aldermanic district
- police_dist: police district
- fire_dist: fire district
- num_units: number of dwelling units

Available relationships:
- building_type: building type descriptions
- conveyance_type: conveyance type descriptions
- assessment_class: assessment class descriptions
- land_use: land-use descriptions and categories
- zoning_district: zoning district names
- property_location: neighborhood names
- exemption_type: exemption type descriptions

Choose required_relationships only when a requested field requires it.
"""

ALLOWED_FIELDS = {
    "house_number_low": "m.house_nr_lo",
    "house_number_high": "m.house_nr_hi",
    "house_number_suffix": "m.house_nr_sfx",
    "street_direction": "m.sdir",
    "street_name": "m.street",
    "street_type": "m.sttype",
    "building_type_desc": "bt.description",
    "convey_type_desc": "ct.description",
    "num_stories": "ROUND(m.nr_stories, 2)",
    "has_basement": "m.basement = 'Y'",
    "has_attic": "m.attic = 'Y'",
    "has_fireplace": "m.fireplace = '1'",
    "num_rooms": "m.nr_rooms",
    "num_bedrooms": "m.bedrooms",
    "num_baths": "m.baths",
    "num_half_bath": "m.powder_rooms",
    "year_built": "m.yr_built",
    "building_area": "ROUND(m.bldg_area, 3)",
    "lot_area": "ROUND(m.lot_area, 3)",
    "historic_code": "m.hist_code",
    "historic_desc": """CASE
        WHEN m.hist_code = "1" THEN "National Register of Historic Places and locally designated."
        WHEN m.hist_code = "2" THEN "National Register of Historic Places, but no local designation."
        WHEN m.hist_code = "3" THEN "Eligible for National Register of Historic Places and locally designated."
        WHEN m.hist_code = "4" THEN "Eligible for National Register of Historic Places, but no designation."
        WHEN m.hist_code = "5" THEN "Not on National Register of Historic Places, but locally designated."
        WHEN m.hist_code = "7" THEN "On National Register of Historic Places, and Historic Local Easement."
        ELSE ""
    END""",
    "zoning": "m.zoning",
    "zip": "m.geo_zip_code",
    "taxkey": "m.taxkey",
    "assessment_class": "m.c_a_class",
    "assessment_class_desc": 'IFNULL(ac1.description, "unknown")',
    "assessed_total": "m.c_a_total",
    "assessed_land": "m.c_a_land",
    "assessed_improvement": "m.c_a_imprv",
    "prev_assessed_total": "m.p_a_total",
    "prev_assessed_land": "m.p_a_land",
    "prev_assessed_improvement": "m.p_a_imprv",
    "assessment_year": "m.yr_assmt",
    "land_use_description": "lu.land_use_description",
    "land_use_category_description": "lu.land_use_category_description",
    "zoning_district_name": "zc.district_name",
    "owner_name_1": "m.owner_name_1",
    "owner_name_2": "m.owner_name_2",
    "owner_name_3": "m.owner_name_3",
    "owner_address": """TRIM(CONCAT(
        IFNULL(m.owner_mail_addr, ""), " ",
        IFNULL(m.owner_city_state, ""), " ",
        IFNULL(SUBSTRING(m.owner_zip, 0, 5), "")
    ))""",
    "last_ownership_change": "m.last_name_chg",
    "neighborhood": "loc.neighborhood_name",
    "current_excemption_code": "m.c_a_exm_type",
    "current_excemption_type_desc": "ex.description",
    "alderman_dist": "m.geo_alder",
    "police_dist": "m.geo_police",
    "fire_dist": "m.geo_fire",
    "num_units": "m.nr_units",
}

ALLOWED_JOINS = {
    "building_type": (
        "LEFT OUTER JOIN `mke_rag_demo.building_types` bt "
        "ON bt.code = m.bldg_type"
    ),
    "conveyance_type": (
        "LEFT OUTER JOIN `mke_rag_demo.conveyance_types` ct "
        "ON ct.code = m.convey_type"
    ),
    "assessment_class": (
        "LEFT OUTER JOIN `mke_rag_demo.assessment_classes` ac1 "
        "ON ac1.code = m.c_a_class"
    ),
    "land_use": (
        "LEFT OUTER JOIN `mke_rag_demo.land_use` lu "
        "ON lu.land_use_code = m.land_use"
    ),
    "zoning_district": (
        "LEFT OUTER JOIN `mke_rag_demo.zoning_codes` zc "
        "ON zc.map_indicator_value = m.zoning"
    ),
    "property_location": (
        "LEFT OUTER JOIN `mke_rag_demo.property_locations` loc "
        "ON loc.taxkey = m.taxkey"
    ),
    "exemption_type": (
        "LEFT OUTER JOIN `mke_rag_demo.exemption_types` ex "
        "ON ex.code = m.c_a_exm_type"
    ),
}