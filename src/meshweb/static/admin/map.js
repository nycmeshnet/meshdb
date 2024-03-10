
const mapStyles = [
  {
    "featureType": "administrative.land_parcel",
    "elementType": "labels",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "poi",
    "elementType": "labels.text",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "poi.attraction",
    "elementType": "labels",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "poi.business",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "poi.medical",
    "elementType": "labels",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "poi.park",
    "elementType": "labels",
    "stylers": [
      {
        "visibility": "on"
      }
    ]
  },
  {
    "featureType": "poi.park",
    "elementType": "labels.icon",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "poi.school",
    "elementType": "labels.icon",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "poi.sports_complex",
    "elementType": "labels.icon",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "road.highway",
    "elementType": "geometry.fill",
    "stylers": [
      {
        "color": "#ffffff"
      },
      {
        "saturation": -40
      }
    ]
  },
  {
    "featureType": "road.highway",
    "elementType": "geometry.stroke",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "road.highway.controlled_access",
    "elementType": "labels.icon",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  },
  {
    "featureType": "transit.station",
    "stylers": [
      {
        "visibility": "off"
      }
    ]
  }
];

let map;

function getCurrentTarget(){
    let path = location.pathname.replace(/^\/admin\/meshapi\//, "");
    path = path.replace(/\/$/, "");

    const [type, id, action] = path.split("/");
    return [type, id, action];
}

async function updateMapForRoute() {
    const [type, id, action] = getCurrentTarget();

    if (["building"].indexOf(type) === -1) return;
    if (!id) return;

    const buildingResponse = await fetch(`/api/v1/buildings/${id}/`);
    if (!buildingResponse.ok) return;
    const building = await buildingResponse.json();
    console.log(building);

    map.setCenter(new google.maps.LatLng(building.latitude, building.longitude))
    map.setZoom(18);

    document.getElementById("map").getElementsByTagName("p")[0].innerHTML = [type,id];
}

async function loadScripts(scripts) {
    for (const script of scripts) {
        const scriptLoadPromise = new Promise((resolve, reject) => {
            const scriptElement = document.createElement('script');
            scriptElement.src = script.src;
            scriptElement.onload = resolve;
            scriptElement.onerror = reject;
            document.head.appendChild(scriptElement);
        });
        await scriptLoadPromise;
    }
}

async function updateAdminContent() {
    let currentPathname = location.pathname;

    const response = await fetch(location.pathname + location.search);
    if (!response.ok) {
        throw new Error("Error loading new contents for page: " + response.status + " " + response.statusText);
    }

    const current_map = document.getElementById("map");

    const text = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, "text/html");
    doc.getElementById("map").replaceWith(current_map);


    // Bail if the user clicked an additional link while we could load/parse the first one
    if (location.pathname !== currentPathname) {
        return
    }

    // Replace the whole page with the new one
    const newHTML = doc.getElementsByTagName("html")[0];
    document.getElementsByTagName("html")[0].replaceWith(newHTML);

    // Re-run other javascript to make page happy
    if (window.DateTimeShortcuts) window.removeEventListener('load', window.DateTimeShortcuts.init);
    await loadScripts(document.head.querySelectorAll('script'));

    console.log("Simulating window load...")
    dispatchEvent(new Event('load'));
}


function shouldNotIntercept(event) {
    const url = new URL(event.destination.url);

    if (event.downloadRequest) return true;
    if (!url.pathname.startsWith("/admin/")) return true;
    if (url.pathname.startsWith("/admin/login")) return true;
    if (url.pathname.startsWith("/admin/logout")) return true;
    if (url.host !== location.host) return true;

    return false;
}

function interceptLinks() {
    navigation.addEventListener("navigate", (event) => {
        // Exit early if this navigation shouldn't be intercepted,
        // e.g. if the navigation is cross-origin, or a download request
        if (shouldNotIntercept(event)) return;

        const url = event.destination.url;
        event.intercept({
            async handler() {
                console.log("Caught navigation to " + url)

                updateMapForRoute();
                updateAdminContent();
            },
        });
    });
}

function start() {
    updateMapForRoute();
    interceptLinks();
}

async function initMap() {
    const {Map} = await google.maps.importLibrary("maps");

    map = new Map(document.getElementById("map-inner"), {
        center: {lat: 40.7211997, lng: -73.9927221},
        zoom: 11.7,
        styles: mapStyles,
        streetViewControl: false,
    });

    google.maps.event.addListenerOnce( map, 'idle', function() {
        start();
    });
}

initMap();
