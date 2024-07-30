

let currentSplit = 60;

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
        if (building.primary_network_number) {
            nodeId = building.primary_network_number;
        } else if (building.installs) {
            nodeId = building.installs[0];
        }
    } else if (["device", "sector"].indexOf(type) !== -1) {
        if (!id) return null;
        const deviceResponse = await fetch(`/api/v1/devices/${id}/`);
        if (!deviceResponse.ok) return null;
        const device = await deviceResponse.json();
        nodeId = device.network_number;
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

        nodeId = `${device1.network_number}-${device2.network_number}`;
    } else if (type === "los") {
        if (!id) return null;
        const losResponse = await fetch(`/api/v1/loses/${id}/`);
        if (!losResponse.ok) return null;
        const los = await losResponse.json();

        let b1NodeId = null;
        const buildingResponse1 = await fetch(`/api/v1/buildings/${los.from_building}/`);
        if (!buildingResponse1.ok) return null;
        const building1 = await buildingResponse1.json();
        if (building1.primary_network_number) {
            b1NodeId = building1.primary_network_number;
        } else if (building1.installs) {
            b1NodeId = building1.installs[0];
        }

        let b2NodeId = null;
        const buildingResponse2 = await fetch(`/api/v1/buildings/${los.to_building}/`);
        if (!buildingResponse2.ok) return null;
        const building2 = await buildingResponse2.json();
        if (building2.primary_network_number) {
            b2NodeId = building2.primary_network_number;
        } else if (building2.installs) {
            b2NodeId = building2.installs[0];
        }

        if (b1NodeId && b2NodeId)  nodeId = `${b1NodeId}-${b2NodeId}`;
    }

    return nodeId ? `${nodeId}` : null;
}

async function updateMapForLocation(selectedNodes) {
    const selectedEvent = new Event("setMapNode");//, {detail: {selectedNodes: selectedNodes}});
    if (!selectedNodes) selectedNodes = await getNewSelectedNodes()
    selectedEvent.selectedNodes = selectedNodes;
    window.dispatchEvent(selectedEvent);
}

async function loadScripts(scripts, destination) {
    const scriptsArray = [];
    for (const script of scripts){
        scriptsArray.push(script);
    }

    for (const script of scriptsArray) {
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
            script.remove();

            // onload will never fire for in-lined scripts since they don't fetch(), so resolve the
            // promise right away
            if (!script.src) resolve();
        });
        await scriptLoadPromise;
    }
}

async function updateAdminContent(newUrl, updateHistory = true) {
    const response = await fetch(newUrl);
    if (!response.ok) {
        throw new Error("Error loading new contents for page: " + response.status + " " + response.statusText);
    }

    if (updateHistory) window.history.pushState(null, '', newUrl);

    const current_map = document.getElementById("map");

    const text = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, "text/html");

    doc.getElementById("map").replaceWith(current_map);

    // Keep the elements Google Maps injected in the header, otherwise the map breaks
    const headerElementsToKeep = [];
    for (const el of document.getElementsByTagName("head")[0].getElementsByTagName("script")){
        if (el.src && el.src.startsWith("https://maps.googleapis.com/")) headerElementsToKeep.push(el);
    }
    for (const el of document.getElementsByTagName("head")[0].getElementsByTagName("style")){
        if (el.textContent.indexOf(".gm") !== -1) headerElementsToKeep.push(el);
    }

    for (const el of headerElementsToKeep){
        doc.getElementsByTagName("head")[0].appendChild(el);
    }

    // Replace the whole page with the new one
    const newHTML = doc.getElementsByTagName("html")[0];
    document.getElementsByTagName("html")[0].replaceWith(newHTML);

    setMapProportions(currentSplit);

    // Re-run other javascript to make page happy
    if (window.DateTimeShortcuts) window.removeEventListener('load', window.DateTimeShortcuts.init);

    const scriptsToReload = [];
    for (const script of document.head.querySelectorAll('script')){
        if (!script.src || !script.src.startsWith("https://maps.googleapis.com/")) scriptsToReload.push(script);
    }
    await loadScripts(scriptsToReload, document.head);

    dispatchEvent(new Event('load'));
}


function shouldNotIntercept(target) {
    const url = new URL(target);

    if (!url.pathname.startsWith("/admin/")) return true;
    if (url.pathname.startsWith("/admin/login")) return true;
    if (url.pathname.startsWith("/admin/logout")) return true;
    if (url.host !== location.host) return true;

    return false;
}

function interceptLinks() {
    interceptClicks(function(event, el) {
        // Exit early if this navigation shouldn't be intercepted,
        // e.g. if the navigation is cross-origin, or a download request
        if (shouldNotIntercept(el.href)) return;
        async function handler() {
            await updateAdminContent(el.href);
            updateMapForLocation();
        }
        handler()
        // console.log("Intercepting " + el.href)
        event.preventDefault()
    });

    window.addEventListener('popstate', function(event) {
         async function handler() {
            await updateAdminContent(location.href, false);
            updateMapForLocation();
        }
        handler()
        // console.log(location.href);
        event.preventDefault()
    }, false)
}

async function nodeSelectedOnMap(selectedNodes) {
    if (!selectedNodes) return;
    if (selectedNodes.indexOf("-") !== -1) return;

    let selectedNodeInt = parseInt(selectedNodes);
    if (selectedNodeInt >= 1000000) {
        selectedNodeInt -= 1000000;
        /* Hack for APs to show correctly */
        updateAdminContent(new URL(`/admin/meshapi/device/${selectedNodeInt}/change`, document.location).href);
        return;
    }

    const installResponse = await fetch(`/api/v1/installs/${selectedNodes}/`);
    const nodeResponse = await fetch(`/api/v1/nodes/${selectedNodes}/`);
    if (installResponse.ok){
        const installJson = await installResponse.json();
        if (installJson.network_number)  {
            await updateAdminContent(new URL(`/admin/meshapi/node/${installJson.network_number}/change`, document.location).href);
            updateMapForLocation(installJson.network_number.toString());
        } else {
            updateAdminContent(new URL(`/admin/meshapi/install/${selectedNodes}/change`, document.location).href);
        }
    } else {
        if (nodeResponse.ok)  {
            updateAdminContent(new URL(`/admin/meshapi/node/${selectedNodes}/change`, document.location).href);
        }
    }

}

function listenForMapNavigation() {
    window.addEventListener("nodeSelectedOnMap", (event) => {
        nodeSelectedOnMap(event.selectedNodes);
    })
}

function listenForRecenterClick() {
    const recenterButton = document.querySelector("#map_recenter_button");

    function onRecenterClick(event) {
        console.log("recenterclick");
        updateMapForLocation();
        event.preventDefault();
    }

    recenterButton.addEventListener("click", onRecenterClick, false);
}

async function load_map() {
    const map_host = MAP_BASE_URL;

    if (!map_host) {
        document.getElementById("map-inner").innerHTML = "Cannot load map due to missing environment " +
            "variable ADMIN_MAP_BASE_URL. Make sure this is set in your .env file and reload the django server";
        document.getElementById("map-inner").style = "text-align: center; align-items: center;"
        return;
    }


    const map_url = `${map_host}/index.html`;
    let response;
    try {
        response = await fetch(map_url);
    } catch (e) {
        document.getElementById("map-inner").innerHTML = `<p>Error loading map from <a href="${map_url}">${map_url}</a>. ` +
            "Is this host up, and serving CORS headers that allow a request from this domain?</p>";
        document.getElementById("map-inner").style = "text-align: center; align-items: center;"
        return;
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

function setMapProportions(leftWidth){
    // Apply new widths to left and right divs
    const leftDiv = document.getElementById('main');
    const rightDiv = document.getElementById('map');

    currentSplit = leftWidth;
    leftDiv.style.width = `${leftWidth}%`;
    rightDiv.style.width = `${100 - leftWidth}%`;
}


function allowMapResize() {
    // Event listener for mouse down on handle
    const handle = document.getElementById('handle');
    handle.addEventListener('mousedown', function(e) {
        e.preventDefault();
        window.addEventListener('mousemove', resize);
        window.addEventListener('mouseup', stopResize);
    });

    // Function to resize divs
    function resize(e) {
        // Get elements
        const container = document.getElementById('map-wrapper');

        const rect = container.getBoundingClientRect();
        const containerLeft = rect.left;
        const containerWidth = rect.width;

        // Calculate new width of left div
        let leftWidth = ((e.clientX - containerLeft) / containerWidth) * 100;

        // Ensure left div doesn't become too small or too large
        leftWidth = Math.min(Math.max(leftWidth, 10), 90);

        setMapProportions(leftWidth);
    }

    // Event listener for mouse up to stop resizing
    function stopResize() {
        window.removeEventListener('mousemove', resize);
    }

    setMapProportions(currentSplit);
}

async function start() {
    allowMapResize();
    await load_map();
    updateMapForLocation();
    interceptLinks();
    listenForMapNavigation();
    listenForRecenterClick();
}

start();
