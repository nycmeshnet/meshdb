The Django admin leverages the same search logic for finding buildings 
- the search bar at /admin/meshapi/building/
- and the buildings dropdown on other pages like an install /admin/meshapi/install/245caf3c-685c-4f9b-9040-dc248c74ca14/change/

Django admin uses the search fields, search_vector, and RankedSearchMixin on the (BuildingAdmin model)[https://github.com/nycmeshnet/meshdb/blob/main/src/meshapi/admin/models/building.py#L66] to generate search results for both
- the search bar at /admin/meshapi/building/
- and the buildings dropdown on other pages like an install /admin/meshapi/install/245caf3c-685c-4f9b-9040-dc248c74ca14/change/

That is the buildings page and the buildings dropdown hit the same code to find buildings based on a search parameter.

That code generates two search queries
- one to find a page of the results against a search term
- one to find the total count of all the results

I believe they are slow because of a combination of the complexity of vectory search, missing indexes on some of the fields we are searching against, and searching against the notes column.

Easiest path forward to improve performance is to remove some of the fields we are searching against.

Next step might be adding indexes.

Customizing the queries to get better performance would probably be a lot more work and may require writing a custom view instead of using the admin functionality.

Here is the data for the various queries before I made any changes

Results search from the buildings page

```
SELECT DISTINCT ON ("rank",
                    "meshapi_building"."id") "meshapi_building"."id",
                   "meshapi_building"."bin",
                   "meshapi_building"."street_address",
                   "meshapi_building"."city",
                   "meshapi_building"."state",
                   "meshapi_building"."zip_code",
                   "meshapi_building"."address_truth_sources",
                   "meshapi_building"."latitude",
                   "meshapi_building"."longitude",
                   "meshapi_building"."altitude",
                   "meshapi_building"."notes",
                   "meshapi_building"."panoramas",
                   "meshapi_building"."primary_node_id",
                   ts_rank(((((((setweight(to_tsvector(COALESCE("meshapi_node"."name",)), A) || setweight(to_tsvector(COALESCE("meshapi_building"."street_address",)), A)) || setweight(to_tsvector(COALESCE("meshapi_building"."zip_code",)), A)) || setweight(to_tsvector(COALESCE(("meshapi_building"."bin")::text,)), A)) || setweight(to_tsvector(COALESCE(("meshapi_node"."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE(("meshapi_install"."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE("meshapi_building"."notes",)), D)), plainto_tsquery(444)) AS "rank",

  (SELECT ts_rank(((((((setweight(to_tsvector(COALESCE(U2."name",)), A) || setweight(to_tsvector(COALESCE(U0."street_address",)), A)) || setweight(to_tsvector(COALESCE(U0."zip_code",)), A)) || setweight(to_tsvector(COALESCE((U0."bin")::text,)), A)) || setweight(to_tsvector(COALESCE((U2."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE((U3."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE(U0."notes",)), D)), plainto_tsquery(444)) AS "rank"
   FROM "meshapi_building" U0
   LEFT OUTER JOIN "meshapi_building_nodes" U1 ON (U0."id" = U1."building_id")
   LEFT OUTER JOIN "meshapi_node" U2 ON (U1."node_id" = U2."id")
   LEFT OUTER JOIN "meshapi_install" U3 ON (U0."id" = U3."building_id")
   WHERE ((UPPER(U2."name"::text) LIKE UPPER(%444%)
           OR UPPER(U0."street_address"::text) LIKE UPPER(%444%)
           OR UPPER(U0."zip_code"::text) = UPPER(444)
           OR UPPER(U0."bin"::text) = UPPER(444)
           OR UPPER(U2."network_number"::text) = UPPER(444)
           OR UPPER(U3."install_number"::text) = UPPER(444)
           OR to_tsvector(COALESCE(U0."notes",)) @@ (plainto_tsquery(444)))
          AND U0."id" = ("meshapi_building"."id"))
   ORDER BY 1 DESC
   LIMIT 1) AS "highest_rank",
                   T5."id",
                   T5."network_number",
                   T5."name",
                   T5."status",
                   T5."type",
                   T5."latitude",
                   T5."longitude",
                   T5."altitude",
                   T5."install_date",
                   T5."abandon_date",
                   T5."placement",
                   T5."notes"
FROM "meshapi_building"
LEFT OUTER JOIN "meshapi_building_nodes" ON ("meshapi_building"."id" = "meshapi_building_nodes"."building_id")
LEFT OUTER JOIN "meshapi_node" ON ("meshapi_building_nodes"."node_id" = "meshapi_node"."id")
LEFT OUTER JOIN "meshapi_install" ON ("meshapi_building"."id" = "meshapi_install"."building_id")
LEFT OUTER JOIN "meshapi_node" T5 ON ("meshapi_building"."primary_node_id" = T5."id")
WHERE ((UPPER("meshapi_node"."name"::text) LIKE UPPER(%444%)
        OR UPPER("meshapi_building"."street_address"::text) LIKE UPPER(%444%)
        OR UPPER("meshapi_building"."zip_code"::text) = UPPER(444)
        OR UPPER("meshapi_building"."bin"::text) = UPPER(444)
        OR UPPER("meshapi_node"."network_number"::text) = UPPER(444)
        OR UPPER("meshapi_install"."install_number"::text) = UPPER(444)
        OR to_tsvector(COALESCE("meshapi_building"."notes",)) @@ (plainto_tsquery(444)))
       AND ts_rank(((((((setweight(to_tsvector(COALESCE("meshapi_node"."name",)), A) || setweight(to_tsvector(COALESCE("meshapi_building"."street_address",)), A)) || setweight(to_tsvector(COALESCE("meshapi_building"."zip_code",)), A)) || setweight(to_tsvector(COALESCE(("meshapi_building"."bin")::text,)), A)) || setweight(to_tsvector(COALESCE(("meshapi_node"."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE(("meshapi_install"."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE("meshapi_building"."notes",)), D)), plainto_tsquery(444)) =
         (SELECT ts_rank(((((((setweight(to_tsvector(COALESCE(U2."name",)), A) || setweight(to_tsvector(COALESCE(U0."street_address",)), A)) || setweight(to_tsvector(COALESCE(U0."zip_code",)), A)) || setweight(to_tsvector(COALESCE((U0."bin")::text,)), A)) || setweight(to_tsvector(COALESCE((U2."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE((U3."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE(U0."notes",)), D)), plainto_tsquery(444)) AS "rank"
          FROM "meshapi_building" U0
          LEFT OUTER JOIN "meshapi_building_nodes" U1 ON (U0."id" = U1."building_id")
          LEFT OUTER JOIN "meshapi_node" U2 ON (U1."node_id" = U2."id")
          LEFT OUTER JOIN "meshapi_install" U3 ON (U0."id" = U3."building_id")
          WHERE ((UPPER(U2."name"::text) LIKE UPPER(%444%)
                  OR UPPER(U0."street_address"::text) LIKE UPPER(%444%)
                  OR UPPER(U0."zip_code"::text) = UPPER(444)
                  OR UPPER(U0."bin"::text) = UPPER(444)
                  OR UPPER(U2."network_number"::text) = UPPER(444)
                  OR UPPER(U3."install_number"::text) = UPPER(444)
                  OR to_tsvector(COALESCE(U0."notes",)) @@ (plainto_tsquery(444)))
                 AND U0."id" = ("meshapi_building"."id"))
          ORDER BY 1 DESC
          LIMIT 1))
ORDER BY 14 DESC,
         "meshapi_building"."id" ASC


347.014ms
10 joins


Query Plan
Unique  (cost=2466.27..2466.33 rows=8 width=570)
  ->  Sort  (cost=2466.27..2466.29 rows=8 width=570)
        Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(meshapi_node.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(meshapi_building.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(meshapi_building.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_building.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_node.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((meshapi_install.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(meshapi_building.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC, meshapi_building.id
        ->  Nested Loop Left Join  (cost=838.63..2466.15 rows=8 width=570)
              ->  Hash Left Join  (cost=838.35..2192.52 rows=8 width=322)
                    Hash Cond: (meshapi_building_nodes.node_id = meshapi_node.id)
                    Filter: (((upper((meshapi_node.name)::text) ~~ '%444%'::text) OR (upper((meshapi_building.street_address)::text) ~~ '%444%'::text) OR (upper((meshapi_building.zip_code)::text) = '444'::text) OR (upper((meshapi_building.bin)::text) = '444'::text) OR (upper((meshapi_node.network_number)::text) = '444'::text) OR (upper((meshapi_install.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(meshapi_building.notes, ''::text)) @@ plainto_tsquery('444'::text))) AND (ts_rank(((((((setweight(to_tsvector((COALESCE(meshapi_node.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(meshapi_building.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(meshapi_building.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_building.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_node.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((meshapi_install.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(meshapi_building.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text)) = (SubPlan 2)))
                    ->  Hash Left Join  (cost=772.06..1637.43 rows=15582 width=322)
                          Hash Cond: (meshapi_building.id = meshapi_building_nodes.building_id)
                          ->  Hash Right Join  (cost=729.75..1479.48 rows=15582 width=306)
                                Hash Cond: (meshapi_install.building_id = meshapi_building.id)
                                ->  Seq Scan on meshapi_install  (cost=0.00..708.82 rows=15582 width=20)
                                ->  Hash  (cost=586.00..586.00 rows=11500 width=302)
                                      ->  Seq Scan on meshapi_building  (cost=0.00..586.00 rows=11500 width=302)
                          ->  Hash  (cost=25.47..25.47 rows=1347 width=32)
                                ->  Seq Scan on meshapi_building_nodes  (cost=0.00..25.47 rows=1347 width=32)
                    ->  Hash  (cost=51.13..51.13 rows=1213 width=32)
                          ->  Seq Scan on meshapi_node  (cost=0.00..51.13 rows=1213 width=32)
                    SubPlan 2
                      ->  Limit  (cost=31.84..31.84 rows=1 width=4)
                            ->  Sort  (cost=31.84..31.84 rows=1 width=4)
                                  Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(u2_1.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(u0_1.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(u0_1.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((u0_1.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((u2_1.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((u3_1.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(u0_1.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC
                                  ->  Nested Loop Left Join  (cost=1.12..31.83 rows=1 width=4)
                                        Filter: ((upper((u2_1.name)::text) ~~ '%444%'::text) OR (upper((u0_1.street_address)::text) ~~ '%444%'::text) OR (upper((u0_1.zip_code)::text) = '444'::text) OR (upper((u0_1.bin)::text) = '444'::text) OR (upper((u2_1.network_number)::text) = '444'::text) OR (upper((u3_1.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(u0_1.notes, ''::text)) @@ plainto_tsquery('444'::text)))
                                        ->  Nested Loop Left Join  (cost=0.85..20.92 rows=1 width=198)
                                              Join Filter: (u0_1.id = u3_1.building_id)
                                              ->  Nested Loop Left Join  (cost=0.56..12.61 rows=1 width=210)
                                                    Join Filter: (u0_1.id = u1_1.building_id)
                                                    ->  Index Scan using meshapi_building_pkey on meshapi_building u0_1  (cost=0.29..8.30 rows=1 width=194)
                                                          Index Cond: (id = meshapi_building.id)
                                                    ->  Index Only Scan using meshapi_building_nodes_building_id_node_id_7b8ad31c_uniq on meshapi_building_nodes u1_1  (cost=0.28..4.29 rows=1 width=32)
                                                          Index Cond: (building_id = meshapi_building.id)
                                              ->  Index Scan using meshapi_install_building_id_34417ad4 on meshapi_install u3_1  (cost=0.29..8.30 rows=1 width=20)
                                                    Index Cond: (building_id = meshapi_building.id)
                                        ->  Index Scan using meshapi_node_pkey on meshapi_node u2_1  (cost=0.28..8.29 rows=1 width=32)
                                              Index Cond: (id = u1_1.node_id)
              ->  Index Scan using meshapi_node_pkey on meshapi_node t5  (cost=0.28..0.31 rows=1 width=260)
                    Index Cond: (id = meshapi_building.primary_node_id)
              SubPlan 1
                ->  Limit  (cost=31.84..31.84 rows=1 width=4)
                      ->  Sort  (cost=31.84..31.84 rows=1 width=4)
                            Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(u2.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(u0.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(u0.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((u0.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((u2.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((u3.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(u0.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC
                            ->  Nested Loop Left Join  (cost=1.12..31.83 rows=1 width=4)
                                  Filter: ((upper((u2.name)::text) ~~ '%444%'::text) OR (upper((u0.street_address)::text) ~~ '%444%'::text) OR (upper((u0.zip_code)::text) = '444'::text) OR (upper((u0.bin)::text) = '444'::text) OR (upper((u2.network_number)::text) = '444'::text) OR (upper((u3.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(u0.notes, ''::text)) @@ plainto_tsquery('444'::text)))
                                  ->  Nested Loop Left Join  (cost=0.85..20.92 rows=1 width=198)
                                        Join Filter: (u0.id = u3.building_id)
                                        ->  Nested Loop Left Join  (cost=0.56..12.61 rows=1 width=210)
                                              Join Filter: (u0.id = u1.building_id)
                                              ->  Index Scan using meshapi_building_pkey on meshapi_building u0  (cost=0.29..8.30 rows=1 width=194)
                                                    Index Cond: (id = meshapi_building.id)
                                              ->  Index Only Scan using meshapi_building_nodes_building_id_node_id_7b8ad31c_uniq on meshapi_building_nodes u1  (cost=0.28..4.29 rows=1 width=32)
                                                    Index Cond: (building_id = meshapi_building.id)
                                        ->  Index Scan using meshapi_install_building_id_34417ad4 on meshapi_install u3  (cost=0.29..8.30 rows=1 width=20)
                                              Index Cond: (building_id = meshapi_building.id)
                                  ->  Index Scan using meshapi_node_pkey on meshapi_node u2  (cost=0.28..8.29 rows=1 width=32)
                                        Index Cond: (id = u1.node_id)
```

Results count from the buildings page

```
SELECT COUNT(*)
FROM
  (SELECT DISTINCT ON ("rank",
                       "meshapi_building"."id") "meshapi_building"."id" AS "col1",
                      "meshapi_building"."bin" AS "col2",
                      "meshapi_building"."street_address" AS "col3",
                      "meshapi_building"."city" AS "col4",
                      "meshapi_building"."state" AS "col5",
                      "meshapi_building"."zip_code" AS "col6",
                      "meshapi_building"."address_truth_sources" AS "col7",
                      "meshapi_building"."latitude" AS "col8",
                      "meshapi_building"."longitude" AS "col9",
                      "meshapi_building"."altitude" AS "col10",
                      "meshapi_building"."notes" AS "col11",
                      "meshapi_building"."panoramas" AS "col12",
                      "meshapi_building"."primary_node_id" AS "col13",
                      ts_rank(((((((setweight(to_tsvector(COALESCE("meshapi_node"."name",)), A) || setweight(to_tsvector(COALESCE("meshapi_building"."street_address",)), A)) || setweight(to_tsvector(COALESCE("meshapi_building"."zip_code",)), A)) || setweight(to_tsvector(COALESCE(("meshapi_building"."bin")::text,)), A)) || setweight(to_tsvector(COALESCE(("meshapi_node"."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE(("meshapi_install"."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE("meshapi_building"."notes",)), D)), plainto_tsquery(444)) AS "rank",

     (SELECT ts_rank(((((((setweight(to_tsvector(COALESCE(U2."name",)), A) || setweight(to_tsvector(COALESCE(U0."street_address",)), A)) || setweight(to_tsvector(COALESCE(U0."zip_code",)), A)) || setweight(to_tsvector(COALESCE((U0."bin")::text,)), A)) || setweight(to_tsvector(COALESCE((U2."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE((U3."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE(U0."notes",)), D)), plainto_tsquery(444)) AS "rank"
      FROM "meshapi_building" U0
      LEFT OUTER JOIN "meshapi_building_nodes" U1 ON (U0."id" = U1."building_id")
      LEFT OUTER JOIN "meshapi_node" U2 ON (U1."node_id" = U2."id")
      LEFT OUTER JOIN "meshapi_install" U3 ON (U0."id" = U3."building_id")
      WHERE ((UPPER(U2."name"::text) LIKE UPPER(%444%)
              OR UPPER(U0."street_address"::text) LIKE UPPER(%444%)
              OR UPPER(U0."zip_code"::text) = UPPER(444)
              OR UPPER(U0."bin"::text) = UPPER(444)
              OR UPPER(U2."network_number"::text) = UPPER(444)
              OR UPPER(U3."install_number"::text) = UPPER(444)
              OR to_tsvector(COALESCE(U0."notes",)) @@ (plainto_tsquery(444)))
             AND U0."id" = ("meshapi_building"."id"))
      ORDER BY 1 DESC
      LIMIT 1) AS "highest_rank"
   FROM "meshapi_building"
   LEFT OUTER JOIN "meshapi_building_nodes" ON ("meshapi_building"."id" = "meshapi_building_nodes"."building_id")
   LEFT OUTER JOIN "meshapi_node" ON ("meshapi_building_nodes"."node_id" = "meshapi_node"."id")
   LEFT OUTER JOIN "meshapi_install" ON ("meshapi_building"."id" = "meshapi_install"."building_id")
   WHERE ((UPPER("meshapi_node"."name"::text) LIKE UPPER(%444%)
           OR UPPER("meshapi_building"."street_address"::text) LIKE UPPER(%444%)
           OR UPPER("meshapi_building"."zip_code"::text) = UPPER(444)
           OR UPPER("meshapi_building"."bin"::text) = UPPER(444)
           OR UPPER("meshapi_node"."network_number"::text) = UPPER(444)
           OR UPPER("meshapi_install"."install_number"::text) = UPPER(444)
           OR to_tsvector(COALESCE("meshapi_building"."notes",)) @@ (plainto_tsquery(444)))
          AND ts_rank(((((((setweight(to_tsvector(COALESCE("meshapi_node"."name",)), A) || setweight(to_tsvector(COALESCE("meshapi_building"."street_address",)), A)) || setweight(to_tsvector(COALESCE("meshapi_building"."zip_code",)), A)) || setweight(to_tsvector(COALESCE(("meshapi_building"."bin")::text,)), A)) || setweight(to_tsvector(COALESCE(("meshapi_node"."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE(("meshapi_install"."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE("meshapi_building"."notes",)), D)), plainto_tsquery(444)) =
            (SELECT ts_rank(((((((setweight(to_tsvector(COALESCE(U2."name",)), A) || setweight(to_tsvector(COALESCE(U0."street_address",)), A)) || setweight(to_tsvector(COALESCE(U0."zip_code",)), A)) || setweight(to_tsvector(COALESCE((U0."bin")::text,)), A)) || setweight(to_tsvector(COALESCE((U2."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE((U3."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE(U0."notes",)), D)), plainto_tsquery(444)) AS "rank"
             FROM "meshapi_building" U0
             LEFT OUTER JOIN "meshapi_building_nodes" U1 ON (U0."id" = U1."building_id")
             LEFT OUTER JOIN "meshapi_node" U2 ON (U1."node_id" = U2."id")
             LEFT OUTER JOIN "meshapi_install" U3 ON (U0."id" = U3."building_id")
             WHERE ((UPPER(U2."name"::text) LIKE UPPER(%444%)
                     OR UPPER(U0."street_address"::text) LIKE UPPER(%444%)
                     OR UPPER(U0."zip_code"::text) = UPPER(444)
                     OR UPPER(U0."bin"::text) = UPPER(444)
                     OR UPPER(U2."network_number"::text) = UPPER(444)
                     OR UPPER(U3."install_number"::text) = UPPER(444)
                     OR to_tsvector(COALESCE(U0."notes",)) @@ (plainto_tsquery(444)))
                    AND U0."id" = ("meshapi_building"."id"))
             ORDER BY 1 DESC
             LIMIT 1))
   ORDER BY 14 DESC,
            "meshapi_building"."id" ASC) subquery


359.31800000000004ms
9 joins

Query Plan
Aggregate  (cost=2209.20..2209.21 rows=1 width=8)
  ->  Unique  (cost=2209.04..2209.10 rows=8 width=292)
        ->  Sort  (cost=2209.04..2209.06 rows=8 width=292)
              Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(meshapi_node.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(meshapi_building.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(meshapi_building.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_building.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_node.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((meshapi_install.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(meshapi_building.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC, meshapi_building.id
              ->  Hash Left Join  (cost=838.35..2208.92 rows=8 width=292)
                    Hash Cond: (meshapi_building_nodes.node_id = meshapi_node.id)
                    Filter: (((upper((meshapi_node.name)::text) ~~ '%444%'::text) OR (upper((meshapi_building.street_address)::text) ~~ '%444%'::text) OR (upper((meshapi_building.zip_code)::text) = '444'::text) OR (upper((meshapi_building.bin)::text) = '444'::text) OR (upper((meshapi_node.network_number)::text) = '444'::text) OR (upper((meshapi_install.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(meshapi_building.notes, ''::text)) @@ plainto_tsquery('444'::text))) AND (ts_rank(((((((setweight(to_tsvector((COALESCE(meshapi_node.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(meshapi_building.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(meshapi_building.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_building.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_node.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((meshapi_install.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(meshapi_building.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text)) = (SubPlan 1)))
                    ->  Hash Left Join  (cost=772.06..1637.43 rows=15582 width=214)
                          Hash Cond: (meshapi_building.id = meshapi_building_nodes.building_id)
                          ->  Hash Right Join  (cost=729.75..1479.48 rows=15582 width=198)
                                Hash Cond: (meshapi_install.building_id = meshapi_building.id)
                                ->  Seq Scan on meshapi_install  (cost=0.00..708.82 rows=15582 width=20)
                                ->  Hash  (cost=586.00..586.00 rows=11500 width=194)
                                      ->  Seq Scan on meshapi_building  (cost=0.00..586.00 rows=11500 width=194)
                          ->  Hash  (cost=25.47..25.47 rows=1347 width=32)
                                ->  Seq Scan on meshapi_building_nodes  (cost=0.00..25.47 rows=1347 width=32)
                    ->  Hash  (cost=51.13..51.13 rows=1213 width=32)
                          ->  Seq Scan on meshapi_node  (cost=0.00..51.13 rows=1213 width=32)
                    SubPlan 1
                      ->  Limit  (cost=31.84..31.84 rows=1 width=4)
                            ->  Sort  (cost=31.84..31.84 rows=1 width=4)
                                  Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(u2.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(u0.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(u0.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((u0.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((u2.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((u3.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(u0.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC
                                  ->  Nested Loop Left Join  (cost=1.12..31.83 rows=1 width=4)
                                        Filter: ((upper((u2.name)::text) ~~ '%444%'::text) OR (upper((u0.street_address)::text) ~~ '%444%'::text) OR (upper((u0.zip_code)::text) = '444'::text) OR (upper((u0.bin)::text) = '444'::text) OR (upper((u2.network_number)::text) = '444'::text) OR (upper((u3.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(u0.notes, ''::text)) @@ plainto_tsquery('444'::text)))
                                        ->  Nested Loop Left Join  (cost=0.85..20.92 rows=1 width=198)
                                              Join Filter: (u0.id = u3.building_id)
                                              ->  Nested Loop Left Join  (cost=0.56..12.61 rows=1 width=210)
                                                    Join Filter: (u0.id = u1.building_id)
                                                    ->  Index Scan using meshapi_building_pkey on meshapi_building u0  (cost=0.29..8.30 rows=1 width=194)
                                                          Index Cond: (id = meshapi_building.id)
                                                    ->  Index Only Scan using meshapi_building_nodes_building_id_node_id_7b8ad31c_uniq on meshapi_building_nodes u1  (cost=0.28..4.29 rows=1 width=32)
                                                          Index Cond: (building_id = meshapi_building.id)
                                              ->  Index Scan using meshapi_install_building_id_34417ad4 on meshapi_install u3  (cost=0.29..8.30 rows=1 width=20)
                                                    Index Cond: (building_id = meshapi_building.id)
                                        ->  Index Scan using meshapi_node_pkey on meshapi_node u2  (cost=0.28..8.29 rows=1 width=32)
                                              Index Cond: (id = u1.node_id)
```

Results search from the buildings dropdown

```
SELECT DISTINCT ON ("rank",
                    "meshapi_building"."id") "meshapi_building"."id",
                   "meshapi_building"."bin",
                   "meshapi_building"."street_address",
                   "meshapi_building"."city",
                   "meshapi_building"."state",
                   "meshapi_building"."zip_code",
                   "meshapi_building"."address_truth_sources",
                   "meshapi_building"."latitude",
                   "meshapi_building"."longitude",
                   "meshapi_building"."altitude",
                   "meshapi_building"."notes",
                   "meshapi_building"."panoramas",
                   "meshapi_building"."primary_node_id",
                   ts_rank(((((((setweight(to_tsvector(COALESCE("meshapi_node"."name",)), A) || setweight(to_tsvector(COALESCE("meshapi_building"."street_address",)), A)) || setweight(to_tsvector(COALESCE("meshapi_building"."zip_code",)), A)) || setweight(to_tsvector(COALESCE(("meshapi_building"."bin")::text,)), A)) || setweight(to_tsvector(COALESCE(("meshapi_node"."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE(("meshapi_install"."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE("meshapi_building"."notes",)), D)), plainto_tsquery(444)) AS "rank",

  (SELECT ts_rank(((((((setweight(to_tsvector(COALESCE(U2."name",)), A) || setweight(to_tsvector(COALESCE(U0."street_address",)), A)) || setweight(to_tsvector(COALESCE(U0."zip_code",)), A)) || setweight(to_tsvector(COALESCE((U0."bin")::text,)), A)) || setweight(to_tsvector(COALESCE((U2."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE((U3."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE(U0."notes",)), D)), plainto_tsquery(444)) AS "rank"
   FROM "meshapi_building" U0
   LEFT OUTER JOIN "meshapi_building_nodes" U1 ON (U0."id" = U1."building_id")
   LEFT OUTER JOIN "meshapi_node" U2 ON (U1."node_id" = U2."id")
   LEFT OUTER JOIN "meshapi_install" U3 ON (U0."id" = U3."building_id")
   WHERE ((UPPER(U2."name"::text) LIKE UPPER(%444%)
           OR UPPER(U0."street_address"::text) LIKE UPPER(%444%)
           OR UPPER(U0."zip_code"::text) = UPPER(444)
           OR UPPER(U0."bin"::text) = UPPER(444)
           OR UPPER(U2."network_number"::text) = UPPER(444)
           OR UPPER(U3."install_number"::text) = UPPER(444)
           OR to_tsvector(COALESCE(U0."notes",)) @@ (plainto_tsquery(444)))
          AND U0."id" = ("meshapi_building"."id"))
   ORDER BY 1 DESC
   LIMIT 1) AS "highest_rank"
FROM "meshapi_building"
LEFT OUTER JOIN "meshapi_building_nodes" ON ("meshapi_building"."id" = "meshapi_building_nodes"."building_id")
LEFT OUTER JOIN "meshapi_node" ON ("meshapi_building_nodes"."node_id" = "meshapi_node"."id")
LEFT OUTER JOIN "meshapi_install" ON ("meshapi_building"."id" = "meshapi_install"."building_id")
WHERE ((UPPER("meshapi_node"."name"::text) LIKE UPPER(%444%)
        OR UPPER("meshapi_building"."street_address"::text) LIKE UPPER(%444%)
        OR UPPER("meshapi_building"."zip_code"::text) = UPPER(444)
        OR UPPER("meshapi_building"."bin"::text) = UPPER(444)
        OR UPPER("meshapi_node"."network_number"::text) = UPPER(444)
        OR UPPER("meshapi_install"."install_number"::text) = UPPER(444)
        OR to_tsvector(COALESCE("meshapi_building"."notes",)) @@ (plainto_tsquery(444)))
       AND ts_rank(((((((setweight(to_tsvector(COALESCE("meshapi_node"."name",)), A) || setweight(to_tsvector(COALESCE("meshapi_building"."street_address",)), A)) || setweight(to_tsvector(COALESCE("meshapi_building"."zip_code",)), A)) || setweight(to_tsvector(COALESCE(("meshapi_building"."bin")::text,)), A)) || setweight(to_tsvector(COALESCE(("meshapi_node"."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE(("meshapi_install"."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE("meshapi_building"."notes",)), D)), plainto_tsquery(444)) =
         (SELECT ts_rank(((((((setweight(to_tsvector(COALESCE(U2."name",)), A) || setweight(to_tsvector(COALESCE(U0."street_address",)), A)) || setweight(to_tsvector(COALESCE(U0."zip_code",)), A)) || setweight(to_tsvector(COALESCE((U0."bin")::text,)), A)) || setweight(to_tsvector(COALESCE((U2."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE((U3."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE(U0."notes",)), D)), plainto_tsquery(444)) AS "rank"
          FROM "meshapi_building" U0
          LEFT OUTER JOIN "meshapi_building_nodes" U1 ON (U0."id" = U1."building_id")
          LEFT OUTER JOIN "meshapi_node" U2 ON (U1."node_id" = U2."id")
          LEFT OUTER JOIN "meshapi_install" U3 ON (U0."id" = U3."building_id")
          WHERE ((UPPER(U2."name"::text) LIKE UPPER(%444%)
                  OR UPPER(U0."street_address"::text) LIKE UPPER(%444%)
                  OR UPPER(U0."zip_code"::text) = UPPER(444)
                  OR UPPER(U0."bin"::text) = UPPER(444)
                  OR UPPER(U2."network_number"::text) = UPPER(444)
                  OR UPPER(U3."install_number"::text) = UPPER(444)
                  OR to_tsvector(COALESCE(U0."notes",)) @@ (plainto_tsquery(444)))
                 AND U0."id" = ("meshapi_building"."id"))
          ORDER BY 1 DESC
          LIMIT 1))
ORDER BY 14 DESC,
         "meshapi_building"."id" ASC
LIMIT 10


354.02ms
9 joins


Query Plan
Limit  (cost=2209.04..2480.32 rows=8 width=310)
  ->  Result  (cost=2209.04..2480.32 rows=8 width=310)
        ->  Unique  (cost=2209.04..2209.10 rows=8 width=306)
              ->  Sort  (cost=2209.04..2209.06 rows=8 width=306)
                    Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(meshapi_node.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(meshapi_building.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(meshapi_building.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_building.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_node.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((meshapi_install.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(meshapi_building.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC, meshapi_building.id
                    ->  Hash Left Join  (cost=838.35..2208.92 rows=8 width=306)
                          Hash Cond: (meshapi_building_nodes.node_id = meshapi_node.id)
                          Filter: (((upper((meshapi_node.name)::text) ~~ '%444%'::text) OR (upper((meshapi_building.street_address)::text) ~~ '%444%'::text) OR (upper((meshapi_building.zip_code)::text) = '444'::text) OR (upper((meshapi_building.bin)::text) = '444'::text) OR (upper((meshapi_node.network_number)::text) = '444'::text) OR (upper((meshapi_install.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(meshapi_building.notes, ''::text)) @@ plainto_tsquery('444'::text))) AND (ts_rank(((((((setweight(to_tsvector((COALESCE(meshapi_node.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(meshapi_building.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(meshapi_building.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_building.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_node.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((meshapi_install.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(meshapi_building.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text)) = (SubPlan 2)))
                          ->  Hash Left Join  (cost=772.06..1637.43 rows=15582 width=322)
                                Hash Cond: (meshapi_building.id = meshapi_building_nodes.building_id)
                                ->  Hash Right Join  (cost=729.75..1479.48 rows=15582 width=306)
                                      Hash Cond: (meshapi_install.building_id = meshapi_building.id)
                                      ->  Seq Scan on meshapi_install  (cost=0.00..708.82 rows=15582 width=20)
                                      ->  Hash  (cost=586.00..586.00 rows=11500 width=302)
                                            ->  Seq Scan on meshapi_building  (cost=0.00..586.00 rows=11500 width=302)
                                ->  Hash  (cost=25.47..25.47 rows=1347 width=32)
                                      ->  Seq Scan on meshapi_building_nodes  (cost=0.00..25.47 rows=1347 width=32)
                          ->  Hash  (cost=51.13..51.13 rows=1213 width=32)
                                ->  Seq Scan on meshapi_node  (cost=0.00..51.13 rows=1213 width=32)
                          SubPlan 2
                            ->  Limit  (cost=31.84..31.84 rows=1 width=4)
                                  ->  Sort  (cost=31.84..31.84 rows=1 width=4)
                                        Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(u2_1.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(u0_1.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(u0_1.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((u0_1.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((u2_1.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((u3_1.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(u0_1.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC
                                        ->  Nested Loop Left Join  (cost=1.12..31.83 rows=1 width=4)
                                              Filter: ((upper((u2_1.name)::text) ~~ '%444%'::text) OR (upper((u0_1.street_address)::text) ~~ '%444%'::text) OR (upper((u0_1.zip_code)::text) = '444'::text) OR (upper((u0_1.bin)::text) = '444'::text) OR (upper((u2_1.network_number)::text) = '444'::text) OR (upper((u3_1.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(u0_1.notes, ''::text)) @@ plainto_tsquery('444'::text)))
                                              ->  Nested Loop Left Join  (cost=0.85..20.92 rows=1 width=198)
                                                    Join Filter: (u0_1.id = u3_1.building_id)
                                                    ->  Nested Loop Left Join  (cost=0.56..12.61 rows=1 width=210)
                                                          Join Filter: (u0_1.id = u1_1.building_id)
                                                          ->  Index Scan using meshapi_building_pkey on meshapi_building u0_1  (cost=0.29..8.30 rows=1 width=194)
                                                                Index Cond: (id = meshapi_building.id)
                                                          ->  Index Only Scan using meshapi_building_nodes_building_id_node_id_7b8ad31c_uniq on meshapi_building_nodes u1_1  (cost=0.28..4.29 rows=1 width=32)
                                                                Index Cond: (building_id = meshapi_building.id)
                                                    ->  Index Scan using meshapi_install_building_id_34417ad4 on meshapi_install u3_1  (cost=0.29..8.30 rows=1 width=20)
                                                          Index Cond: (building_id = meshapi_building.id)
                                              ->  Index Scan using meshapi_node_pkey on meshapi_node u2_1  (cost=0.28..8.29 rows=1 width=32)
                                                    Index Cond: (id = u1_1.node_id)
        SubPlan 1
          ->  Limit  (cost=31.84..31.84 rows=1 width=4)
                ->  Sort  (cost=31.84..31.84 rows=1 width=4)
                      Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(u2.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(u0.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(u0.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((u0.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((u2.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((u3.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(u0.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC
                      ->  Nested Loop Left Join  (cost=1.12..31.83 rows=1 width=4)
                            Filter: ((upper((u2.name)::text) ~~ '%444%'::text) OR (upper((u0.street_address)::text) ~~ '%444%'::text) OR (upper((u0.zip_code)::text) = '444'::text) OR (upper((u0.bin)::text) = '444'::text) OR (upper((u2.network_number)::text) = '444'::text) OR (upper((u3.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(u0.notes, ''::text)) @@ plainto_tsquery('444'::text)))
                            ->  Nested Loop Left Join  (cost=0.85..20.92 rows=1 width=198)
                                  Join Filter: (u0.id = u3.building_id)
                                  ->  Nested Loop Left Join  (cost=0.56..12.61 rows=1 width=210)
                                        Join Filter: (u0.id = u1.building_id)
                                        ->  Index Scan using meshapi_building_pkey on meshapi_building u0  (cost=0.29..8.30 rows=1 width=194)
                                              Index Cond: (id = meshapi_building.id)
                                        ->  Index Only Scan using meshapi_building_nodes_building_id_node_id_7b8ad31c_uniq on meshapi_building_nodes u1  (cost=0.28..4.29 rows=1 width=32)
                                              Index Cond: (building_id = meshapi_building.id)
                                  ->  Index Scan using meshapi_install_building_id_34417ad4 on meshapi_install u3  (cost=0.29..8.30 rows=1 width=20)
                                        Index Cond: (building_id = meshapi_building.id)
                            ->  Index Scan using meshapi_node_pkey on meshapi_node u2  (cost=0.28..8.29 rows=1 width=32)
                                  Index Cond: (id = u1.node_id)
```

Results count from the buildings dropdown

```
SELECT COUNT(*)
FROM
  (SELECT DISTINCT ON ("rank",
                       "meshapi_building"."id") "meshapi_building"."id" AS "col1",
                      "meshapi_building"."bin" AS "col2",
                      "meshapi_building"."street_address" AS "col3",
                      "meshapi_building"."city" AS "col4",
                      "meshapi_building"."state" AS "col5",
                      "meshapi_building"."zip_code" AS "col6",
                      "meshapi_building"."address_truth_sources" AS "col7",
                      "meshapi_building"."latitude" AS "col8",
                      "meshapi_building"."longitude" AS "col9",
                      "meshapi_building"."altitude" AS "col10",
                      "meshapi_building"."notes" AS "col11",
                      "meshapi_building"."panoramas" AS "col12",
                      "meshapi_building"."primary_node_id" AS "col13",
                      ts_rank(((((((setweight(to_tsvector(COALESCE("meshapi_node"."name",)), A) || setweight(to_tsvector(COALESCE("meshapi_building"."street_address",)), A)) || setweight(to_tsvector(COALESCE("meshapi_building"."zip_code",)), A)) || setweight(to_tsvector(COALESCE(("meshapi_building"."bin")::text,)), A)) || setweight(to_tsvector(COALESCE(("meshapi_node"."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE(("meshapi_install"."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE("meshapi_building"."notes",)), D)), plainto_tsquery(444)) AS "rank",

     (SELECT ts_rank(((((((setweight(to_tsvector(COALESCE(U2."name",)), A) || setweight(to_tsvector(COALESCE(U0."street_address",)), A)) || setweight(to_tsvector(COALESCE(U0."zip_code",)), A)) || setweight(to_tsvector(COALESCE((U0."bin")::text,)), A)) || setweight(to_tsvector(COALESCE((U2."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE((U3."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE(U0."notes",)), D)), plainto_tsquery(444)) AS "rank"
      FROM "meshapi_building" U0
      LEFT OUTER JOIN "meshapi_building_nodes" U1 ON (U0."id" = U1."building_id")
      LEFT OUTER JOIN "meshapi_node" U2 ON (U1."node_id" = U2."id")
      LEFT OUTER JOIN "meshapi_install" U3 ON (U0."id" = U3."building_id")
      WHERE ((UPPER(U2."name"::text) LIKE UPPER(%444%)
              OR UPPER(U0."street_address"::text) LIKE UPPER(%444%)
              OR UPPER(U0."zip_code"::text) = UPPER(444)
              OR UPPER(U0."bin"::text) = UPPER(444)
              OR UPPER(U2."network_number"::text) = UPPER(444)
              OR UPPER(U3."install_number"::text) = UPPER(444)
              OR to_tsvector(COALESCE(U0."notes",)) @@ (plainto_tsquery(444)))
             AND U0."id" = ("meshapi_building"."id"))
      ORDER BY 1 DESC
      LIMIT 1) AS "highest_rank"
   FROM "meshapi_building"
   LEFT OUTER JOIN "meshapi_building_nodes" ON ("meshapi_building"."id" = "meshapi_building_nodes"."building_id")
   LEFT OUTER JOIN "meshapi_node" ON ("meshapi_building_nodes"."node_id" = "meshapi_node"."id")
   LEFT OUTER JOIN "meshapi_install" ON ("meshapi_building"."id" = "meshapi_install"."building_id")
   WHERE ((UPPER("meshapi_node"."name"::text) LIKE UPPER(%444%)
           OR UPPER("meshapi_building"."street_address"::text) LIKE UPPER(%444%)
           OR UPPER("meshapi_building"."zip_code"::text) = UPPER(444)
           OR UPPER("meshapi_building"."bin"::text) = UPPER(444)
           OR UPPER("meshapi_node"."network_number"::text) = UPPER(444)
           OR UPPER("meshapi_install"."install_number"::text) = UPPER(444)
           OR to_tsvector(COALESCE("meshapi_building"."notes",)) @@ (plainto_tsquery(444)))
          AND ts_rank(((((((setweight(to_tsvector(COALESCE("meshapi_node"."name",)), A) || setweight(to_tsvector(COALESCE("meshapi_building"."street_address",)), A)) || setweight(to_tsvector(COALESCE("meshapi_building"."zip_code",)), A)) || setweight(to_tsvector(COALESCE(("meshapi_building"."bin")::text,)), A)) || setweight(to_tsvector(COALESCE(("meshapi_node"."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE(("meshapi_install"."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE("meshapi_building"."notes",)), D)), plainto_tsquery(444)) =
            (SELECT ts_rank(((((((setweight(to_tsvector(COALESCE(U2."name",)), A) || setweight(to_tsvector(COALESCE(U0."street_address",)), A)) || setweight(to_tsvector(COALESCE(U0."zip_code",)), A)) || setweight(to_tsvector(COALESCE((U0."bin")::text,)), A)) || setweight(to_tsvector(COALESCE((U2."network_number")::text,)), B)) || setweight(to_tsvector(COALESCE((U3."install_number")::text,)), B)) || setweight(to_tsvector(COALESCE(U0."notes",)), D)), plainto_tsquery(444)) AS "rank"
             FROM "meshapi_building" U0
             LEFT OUTER JOIN "meshapi_building_nodes" U1 ON (U0."id" = U1."building_id")
             LEFT OUTER JOIN "meshapi_node" U2 ON (U1."node_id" = U2."id")
             LEFT OUTER JOIN "meshapi_install" U3 ON (U0."id" = U3."building_id")
             WHERE ((UPPER(U2."name"::text) LIKE UPPER(%444%)
                     OR UPPER(U0."street_address"::text) LIKE UPPER(%444%)
                     OR UPPER(U0."zip_code"::text) = UPPER(444)
                     OR UPPER(U0."bin"::text) = UPPER(444)
                     OR UPPER(U2."network_number"::text) = UPPER(444)
                     OR UPPER(U3."install_number"::text) = UPPER(444)
                     OR to_tsvector(COALESCE(U0."notes",)) @@ (plainto_tsquery(444)))
                    AND U0."id" = ("meshapi_building"."id"))
             ORDER BY 1 DESC
             LIMIT 1))
   ORDER BY 14 DESC,
            "meshapi_building"."id" ASC) subquery


382.351ms
9 joins



Query Plan
Aggregate  (cost=2209.20..2209.21 rows=1 width=8)
  ->  Unique  (cost=2209.04..2209.10 rows=8 width=292)
        ->  Sort  (cost=2209.04..2209.06 rows=8 width=292)
              Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(meshapi_node.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(meshapi_building.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(meshapi_building.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_building.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_node.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((meshapi_install.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(meshapi_building.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC, meshapi_building.id
              ->  Hash Left Join  (cost=838.35..2208.92 rows=8 width=292)
                    Hash Cond: (meshapi_building_nodes.node_id = meshapi_node.id)
                    Filter: (((upper((meshapi_node.name)::text) ~~ '%444%'::text) OR (upper((meshapi_building.street_address)::text) ~~ '%444%'::text) OR (upper((meshapi_building.zip_code)::text) = '444'::text) OR (upper((meshapi_building.bin)::text) = '444'::text) OR (upper((meshapi_node.network_number)::text) = '444'::text) OR (upper((meshapi_install.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(meshapi_building.notes, ''::text)) @@ plainto_tsquery('444'::text))) AND (ts_rank(((((((setweight(to_tsvector((COALESCE(meshapi_node.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(meshapi_building.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(meshapi_building.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_building.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((meshapi_node.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((meshapi_install.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(meshapi_building.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text)) = (SubPlan 1)))
                    ->  Hash Left Join  (cost=772.06..1637.43 rows=15582 width=214)
                          Hash Cond: (meshapi_building.id = meshapi_building_nodes.building_id)
                          ->  Hash Right Join  (cost=729.75..1479.48 rows=15582 width=198)
                                Hash Cond: (meshapi_install.building_id = meshapi_building.id)
                                ->  Seq Scan on meshapi_install  (cost=0.00..708.82 rows=15582 width=20)
                                ->  Hash  (cost=586.00..586.00 rows=11500 width=194)
                                      ->  Seq Scan on meshapi_building  (cost=0.00..586.00 rows=11500 width=194)
                          ->  Hash  (cost=25.47..25.47 rows=1347 width=32)
                                ->  Seq Scan on meshapi_building_nodes  (cost=0.00..25.47 rows=1347 width=32)
                    ->  Hash  (cost=51.13..51.13 rows=1213 width=32)
                          ->  Seq Scan on meshapi_node  (cost=0.00..51.13 rows=1213 width=32)
                    SubPlan 1
                      ->  Limit  (cost=31.84..31.84 rows=1 width=4)
                            ->  Sort  (cost=31.84..31.84 rows=1 width=4)
                                  Sort Key: (ts_rank(((((((setweight(to_tsvector((COALESCE(u2.name, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(u0.street_address, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector((COALESCE(u0.zip_code, ''::character varying))::text), 'A'::"char")) || setweight(to_tsvector(COALESCE((u0.bin)::text, ''::text)), 'A'::"char")) || setweight(to_tsvector(COALESCE((u2.network_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE((u3.install_number)::text, ''::text)), 'B'::"char")) || setweight(to_tsvector(COALESCE(u0.notes, ''::text)), 'D'::"char")), plainto_tsquery('444'::text))) DESC
                                  ->  Nested Loop Left Join  (cost=1.12..31.83 rows=1 width=4)
                                        Filter: ((upper((u2.name)::text) ~~ '%444%'::text) OR (upper((u0.street_address)::text) ~~ '%444%'::text) OR (upper((u0.zip_code)::text) = '444'::text) OR (upper((u0.bin)::text) = '444'::text) OR (upper((u2.network_number)::text) = '444'::text) OR (upper((u3.install_number)::text) = '444'::text) OR (to_tsvector(COALESCE(u0.notes, ''::text)) @@ plainto_tsquery('444'::text)))
                                        ->  Nested Loop Left Join  (cost=0.85..20.92 rows=1 width=198)
                                              Join Filter: (u0.id = u3.building_id)
                                              ->  Nested Loop Left Join  (cost=0.56..12.61 rows=1 width=210)
                                                    Join Filter: (u0.id = u1.building_id)
                                                    ->  Index Scan using meshapi_building_pkey on meshapi_building u0  (cost=0.29..8.30 rows=1 width=194)
                                                          Index Cond: (id = meshapi_building.id)
                                                    ->  Index Only Scan using meshapi_building_nodes_building_id_node_id_7b8ad31c_uniq on meshapi_building_nodes u1  (cost=0.28..4.29 rows=1 width=32)
                                                          Index Cond: (building_id = meshapi_building.id)
                                              ->  Index Scan using meshapi_install_building_id_34417ad4 on meshapi_install u3  (cost=0.29..8.30 rows=1 width=20)
                                                    Index Cond: (building_id = meshapi_building.id)
                                        ->  Index Scan using meshapi_node_pkey on meshapi_node u2  (cost=0.28..8.29 rows=1 width=32)
                                              Index Cond: (id = u1.node_id)
```