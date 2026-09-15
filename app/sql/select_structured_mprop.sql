SELECT
    CONCAT(IF(m.house_nr_lo = m.house_nr_hi, CAST(m.house_nr_lo AS STRING), CONCAT(m.house_nr_lo, "-", m.house_nr_hi)),
      " ", IFNULL(m.house_nr_sfx, ''), " ", IFNULL(m.sdir, ''), " ", IFNULL(m.street, ''), " ", IFNULL(m.sttype, '')) AS address,
    bt.description AS building_type_desc,
    ct.description AS convey_type_desc,
    ROUND(m.nr_stories, 2) AS num_stories,
    m.basement = 'Y' AS has_basement,
    m.attic = 'Y' AS has_attic,
    m.fireplace = '1' AS has_fireplace,
    m.nr_rooms AS num_rooms,
    m.bedrooms AS num_bedrooms,
    m.baths AS num_baths,
    m.powder_rooms AS num_half_bath,
    m.yr_built AS year_built,
    ROUND(m.bldg_area, 3) AS building_area,
    ROUND(m.lot_area, 3) AS lot_area,
    m.hist_code as historic_code,
    CASE
      WHEN m.hist_code = "1" THEN "National Register of Historic Places and locally designated. "
      WHEN m.hist_code = "2" THEN "National Register of Historic Places, but no local designation. "
      WHEN m.hist_code = "3" THEN "Eligible for National Register of Historic Places and locally designated. "
      WHEN m.hist_code = "4" THEN "Eligible for National Register of Historic Places, but no designation. "
      WHEN m.hist_code = "5" THEN "Not on National Register of Historic Places, but locally designated. "
      WHEN m.hist_code = "7" THEN "On National Register of Historic Places, and Historic Local Easement. "
      ELSE ""
    END AS historic_desc,
    m.zoning AS zoning,
    m.geo_zip_code AS zip,
    m.taxkey AS taxkey,
    m.c_a_class AS assessment_class,
    IFNULL(ac1.description, "unknown") AS assessment_class_desc,
    m.c_a_total AS assessed_total,
    m.c_a_land AS assessed_land,
    m.c_a_imprv AS assessed_improvement,
    m.p_a_total AS prev_assessed_total,
    m.p_a_land AS prev_assessed_land,
    m.p_a_imprv AS prev_assessed_improvement,
    m.yr_assmt AS assessment_year,
    lu.land_use_description AS land_use_description,
    lu.land_use_category_description AS land_use_category_description,
    zc.district_name AS zoning_district_name,
    m.owner_name_1 AS owner_name_1,
    m.owner_name_2 AS owner_name_2,
    m.owner_name_3 AS owner_name_3,
    TRIM(CONCAT(IFNULL(m.owner_mail_addr,"") , " ", IFNULL(m.owner_city_state, ""), " ", IFNULL(SUBSTRING(m.owner_zip, 0, 5), ""))) AS owner_address,
    m.last_name_chg AS last_ownership_change,
    loc.neighborhood_name AS neighborhood,
    m.c_a_exm_type AS current_excemption_code,
    ex.description AS current_excemption_type_desc,
    m.geo_alder as alderman_dist,
    m.geo_police as police_dist,
    m.geo_fire as fire_dist,
    m.nr_units as num_units
  FROM `mke_rag_demo.mprop_master` m
  LEFT OUTER JOIN `mke_rag_demo.building_types` bt ON bt.code = m.bldg_type
  LEFT OUTER JOIN `mke_rag_demo.conveyance_types` ct ON ct.code = m.convey_type
  LEFT OUTER JOIN `mke_rag_demo.assessment_classes` ac1 ON ac1.code = m.c_a_class
  LEFT OUTER JOIN `mke_rag_demo.land_use` lu ON lu.land_use_code = m.land_use
  LEFT OUTER JOIN `mke_rag_demo.zoning_codes` zc ON zc.map_indicator_value = m.zoning
  LEFT OUTER JOIN `mke_rag_demo.property_locations` loc ON loc.taxkey = m.taxkey
  LEFT OUTER JOIN `mke_rag_demo.exemption_types` ex ON ex.code = m.c_a_exm_type
WHERE CAST(m.taxkey AS STRING) IN UNNEST(@taxkeys);