$(document).ready(function($) {
    const sourceURLMap = {
        Node: "/api/v1/nodes/",
        Building: "/api/v1/buildings/",
        Address: "https://geosearch.planninglabs.nyc/v2/search?size=1&text="
    };
    const ALTITUDE_DATA_URL = "https://data.cityofnewyork.us/resource/qb5r-6dgf.json";


    let searchId = undefined;
    $('#id_node').on('change', function () {
        searchId = this.value;
        if (this.value) {
            $('#location_autocomplete_button').removeClass("disabled-button")
        } else {
            $('#location_autocomplete_button').addClass("disabled-button")
        }
    });

    $('#id_Building_nodes-0-building_id').on('change', function () {
        searchId = this.value;
        if (this.value) {
            $('#location_autocomplete_button').removeClass("disabled-button")
        } else {
            $('#location_autocomplete_button').addClass("disabled-button")
        }
    });

    function buildAddress(){
        console.log("BUILD ADDR")
        const streetAddr = $('#id_street_address').val();
        const city = $('#id_city').val();
        const state = $('#id_state').val();
        const zip = $('#id_zip_code').val();
        if (!streetAddr) {
            searchId = undefined;
            $('#location_autocomplete_button').addClass("disabled-button")
            return;
        }
        if (!city) {
            searchId = undefined;
            $('#location_autocomplete_button').addClass("disabled-button")
            return;
        }
        if (!state) {
            searchId = undefined;
            $('#location_autocomplete_button').addClass("disabled-button")
            return;
        }
        if (!zip) {
            searchId = undefined;
            $('#location_autocomplete_button').addClass("disabled-button")
            return;
        }
        searchId = encodeURIComponent(`${streetAddr}, ${city}, ${state} ${zip}`)
        $('#location_autocomplete_button').removeClass("disabled-button")
    }

    $('#id_street_address').on('change', buildAddress);
    $('#id_city').on('change', buildAddress);
    $('#id_state').on('change', buildAddress);
    $('#id_zip_code').on('change', buildAddress);
    buildAddress();

    $('#location_autocomplete_button').on("click", function (event){
        event.preventDefault();
        $('#id_latitude').val("");
        $('#id_longitude').val("");
        $('#id_altitude').val("");
        $('#id_bin').val("");

        if (searchId) {
            $.get(sourceURLMap[$(this).attr('autocompletesource')] + searchId, function (data, status) {
                if (data.features) {
                    // We are talking to the NYC geocoding API,
                    // build a special data object to replicate the meshDB api response
                    let bin = data.features[0].properties.addendum.pad.bin ?? "";
                    if (parseInt(bin) % 1000000 === 0) bin = "";

                    if (bin) {
                        $('#id_bin').val(bin);
                        const altitudeParams = {
                           "$where": `bin=${bin}`,
                            "$select": "heightroof,groundelev",
                            "$limit": "1",
                        };
                        $.get(ALTITUDE_DATA_URL + "?" + $.param(altitudeParams), function (data, status) {
                            const absoluteAltitudeMeters = (parseFloat(data[0]["heightroof"]) + parseFloat(data[0]["groundelev"])) / 3.28084;
                            $('#id_altitude').val(absoluteAltitudeMeters.toFixed(1));
                        })
                    }

                    data = {
                        latitude: data.features[0].geometry.coordinates[1],
                        longitude: data.features[0].geometry.coordinates[0],
                        altitude: ""
                    }
                }

                $('#id_latitude').val(data.latitude);
                $('#id_longitude').val(data.longitude);
                $('#id_altitude').val(data.altitude);
            })
        }
    })
});
