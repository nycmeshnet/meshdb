
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

function getCurrentTarget(){
    let path = location.pathname.replace(/^\/admin\/meshapi\//, "");
    path = path.replace(/\/$/, "");

    const [type, id, action] = path.split("/");
    return [type, id, action];
}

async function getNewSelectedNodes(){
    const [type, id, action] = getCurrentTarget();

    let nodeId = null;
    if (["node", "install"].indexOf(type) !== -1) nodeId = id;

    if (type === "building") {
        if (!id) return null;
        const buildingResponse = await fetch(`/api/v1/buildings/${id}/`);
        if (!buildingResponse.ok) return null;
        const building = await buildingResponse.json();
        if (building.primary_node) {
            nodeId = building.primary_node;
        } else if (building.installs) {
            nodeId = building.installs[0];
        }
    } else if (["device", "sector"].indexOf(type) !== -1) {
        if (!id) return null;
        const deviceResponse = await fetch(`/api/v1/devices/${id}/`);
        if (!deviceResponse.ok) return null;
        const device = await deviceResponse.json();
        nodeId = device.node;
    } else if (type === "member") {
        if (!id) return null;
        const memberResponse = await fetch(`/api/v1/members/${id}/`);
        if (!memberResponse.ok) return null;
        const member = await memberResponse.json();
        nodeId = member.installs.join("-");
    } else if (type === "link") {
        if (!id) return null;
        const linkResponse = await fetch(`/api/v1/links/${id}/`);
        if (!linkResponse.ok) return null;
        const link = await linkResponse.json();

        const device1Response = await fetch(`/api/v1/devices/${link.from_device}/`);
        if (!device1Response.ok) return null;
        const device1 = await device1Response.json();

        const device2Response = await fetch(`/api/v1/devices/${link.to_device}/`);
        if (!device2Response.ok) return null;
        const device2 = await device2Response.json();

        nodeId = `${device1.node}-${device2.node}`;
    }

    console.log(`${type} ${id} -> ${nodeId}`)


    return nodeId ? `${nodeId}` : null;
}

async function updateMapForRoute() {
    const selectedEvent = new Event("setMapNode");//, {detail: {selectedNodes: selectedNodes}});
    selectedEvent.selectedNodes = await getNewSelectedNodes();
    window.dispatchEvent(selectedEvent);
}

async function loadScripts(scripts, destination) {
    for (const script of scripts) {
        const scriptLoadPromise = new Promise((resolve, reject) => {
            const scriptElement = document.createElement('script');
            if (script.src) {
                scriptElement.src = script.src;
            } else {
                scriptElement.innerText = script.innerText;
            }
            scriptElement.onload = resolve;
            scriptElement.onerror = reject;
            destination.appendChild(scriptElement);

            // onload will never fire for in-lined scripts since they don't fetch(), so resolve the
            // promise right away
            if (!script.src) resolve();
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
    await loadScripts(document.head.querySelectorAll('script'), document.head);

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

async function nodeSelectedOnMap(selectedNodes) {
    if (!selectedNodes) return;
    if (selectedNodes.indexOf("-") !== -1) return;

    const nodeResponse = await fetch(`/api/v1/nodes/${selectedNodes}/`);
    if (nodeResponse.ok)  {
        window.location = `/admin/meshapi/node/${selectedNodes}/change`;
    } else {
        window.location = `/admin/meshapi/install/${selectedNodes}/change`;
    }
}

function listenForMapNavigation() {
    window.addEventListener("nodeSelectedOnMap", (event) => {
        nodeSelectedOnMap(event.selectedNodes);
    })
}

async function load_map() {
    const map_host = MAP_BASE_URL;
    const response = await fetch(`${map_host}/index.html`);
    if (!response.ok) {
        throw new Error("Error loading map index: " + response.status + " " + response.statusText);
    }

    const parser = new DOMParser();
    const text = await response.text();
    const remote_map_doc = parser.parseFromString(text, "text/html");

    const map_scripts_div = document.getElementById("map-scripts");

    for (const el of remote_map_doc.querySelectorAll('script')){
        let src = el.getAttribute("src") ?? "";
        if (src) {
            if (!src.match(/https?:\/\//)){
                el.src = map_host + src;
            }
        }
    }

    for (const el of remote_map_doc.querySelectorAll('link')){
        let href = el.getAttribute("href") ?? "";
        if (!href.match(/https?:\/\//)){
            el.href = map_host + href
        }
    }

    for (const el of remote_map_doc.querySelectorAll('link')){
        map_scripts_div.appendChild(el);
    }

    await loadScripts(remote_map_doc.querySelectorAll('script'), map_scripts_div);
}

async function start() {
    await load_map();
    updateMapForRoute();
    interceptLinks();
    listenForMapNavigation();
}

start();
