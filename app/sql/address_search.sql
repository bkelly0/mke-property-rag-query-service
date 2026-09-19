DECLARE search_string STRING DEFAULT UPPER(@search_string);
DECLARE search_len INT64 DEFAULT CHARACTER_LENGTH(search_string);


WITH search_results AS (
  SELECT 
  taxkey,
  formatted_address, 
  EDIT_DISTANCE(formatted_address, search_string) AS distance
  FROM `bkelly-portfolio.mke_rag_demo.property_address_search`
  WHERE 
    CHARACTER_LENGTH(formatted_address) BETWEEN (search_len - 3) 
                                            AND (search_len + 3)
  AND EDIT_DISTANCE(formatted_address, search_string, max_distance => 4) <= 3
  ORDER BY distance ASC
  LIMIT 5
)
SELECT
search_results.taxkey,
search_results.formatted_address,
search_results.distance,
IF(
  locations.centroid IS NULL,
  NULL,
  STRUCT(
    ST_Y(locations.centroid) AS latitude,
    ST_X(locations.centroid) AS longitude
  )
) AS centroid
from search_results
JOIN `bkelly-portfolio.mke_rag_demo.property_locations` locations
  ON search_results.taxkey = locations.taxkey
ORDER BY search_results.distance ASC;
