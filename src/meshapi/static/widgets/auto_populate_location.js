$(document).ready(function($) {
    const sourceURLMap = {
        Node: "/api/v1/nodes/",
        Building: "/api/v1/buildings/",
        Address: "/api/v1/geography/nyc-geocode/v2/search"
    };

    let searchId = undefined;
    $('#id_node').on('change', function () {
        searchId = this.value;
        if (this.value) {
            $('#location_autocomplete_button').removeClass("disabled-button")
        } else {
            $('#location_autocomplete_button').addClass("disabled-button")
        }
    });

    $(document).change(function (e){
        if (e.target.id === "id_Building_nodes-0-building") {
            searchId = e.target.value;
            if (e.target.value) {
                $('#location_autocomplete_button').removeClass("disabled-button")
            } else {
                $('#location_autocomplete_button').addClass("disabled-button")
            }
        }
    })

    function buildAddressQuery(){
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
        searchId = `?street_address=${encodeURIComponent(streetAddr)}` +
            `&city=${encodeURIComponent(city)}` +
            `&state=${encodeURIComponent(state)}` +
            `&zip=${encodeURIComponent(zip)}`;

        $('#location_autocomplete_button').removeClass("disabled-button")
    }

    $('#id_street_address').on('change', buildAddressQuery);
    $('#id_city').on('change', buildAddressQuery);
    $('#id_state').on('change', buildAddressQuery);
    $('#id_zip_code').on('change', buildAddressQuery);
    buildAddressQuery();

    $('#location_autocomplete_button').on("click", function (event){
        event.preventDefault();
        $('#id_latitude').val("");
        $('#id_longitude').val("");
        $('#id_altitude').val("");
        $('#id_bin').val("");
        $('#geocode_error').addClass("hidden");

        if (searchId) {
            $.get(sourceURLMap[$(this).attr('autocompletesource')] + searchId)
                .done(function (data) {
                    if (data.BIN) $('#id_bin').val(data.BIN);
                    $('#id_latitude').val(data.latitude);
                    $('#id_longitude').val(data.longitude);
                    $('#id_altitude').val(data.altitude);
                }).fail(function(jqXHR) {
                    $('#geocode_error').text(
                        `Error encountered while trying to autocomplete: ${jqXHR.responseText}`
                    )
                    $('#geocode_error').removeClass("hidden");
                })
        }
    })
});
