const ADMIN_PANEL_HOME = "/admin/"
const MESHDB_LAST_PAGE_VISITED = "MESHDB_LAST_PAGE_VISITED"
const adminPanelIframe = document.getElementById("admin_panel_iframe");

let currentSplit = parseFloat(localStorage.getItem("MESHDB_MAP_SIZE"));
if (isNaN(currentSplit)) {
    currentSplit = 60;
}

// Navigation Stuff

// Gets the UUID of the object the Admin Panel is currently viewing
function extractUUIDs(url) {
    // Regular expression to match UUIDs
    const uuidRegex = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g;
    // Find all matches in the input string
    const matches = url.match(uuidRegex);
    // Return the matches or an empty array if none found
    return matches || [];
}

// Checks what model the Admin Panel is looking at
function extractModel(url) {
    const relevantModels = [
        "member",
        "building",
        "install",
        "node",
        "device",
        "sector",
        "accesspoint",
        "link",
        "los"
    ];
    return relevantModels.find(element => url.includes(element));
}

// Based on the current URL of the Admin Panel, figures out what node the map
// should focus on
async function getNewSelectedNodes(url) {
    const objectUUIDs = extractUUIDs(url);
    const type = extractModel(url);

    // Guard against looking up an empty UUID
    if (objectUUIDs.length == 0) {
        console.log("[Admin Panel] Found no UUID")
        return null;
    }
    const id = objectUUIDs[0];

    let nodeId = null;

    if (type === "install") {
        if (!id) return null;
        const installResponse = await fetch(`/api/v1/installs/${id}/`);
        if (!installResponse.ok) return null;
        const install = await installResponse.json();
        if (install.status !== "Closed" && install.status !== "NN Reassigned") {
            nodeId = install.install_number;
        }
    } else if (type === "node") {
        if (!id) return null;
        const nodeResponse = await fetch(`/api/v1/nodes/${id}/`);
        if (!nodeResponse.ok) return null;
        const node = await nodeResponse.json();
        if (node.network_number) {
            nodeId = node.network_number;
        } else {
            for (const install of node.installs) {
                if (install.status !== "Closed" && install.status !== "NN Reassigned") {
                    nodeId = install.install_number;
                    break;
                }
            }
        }
    } else if (type === "building") {
        if (!id) return null;
        const buildingResponse = await fetch(`/api/v1/buildings/${id}/`);
        if (!buildingResponse.ok) return null;
        const building = await buildingResponse.json();
        if (building.primary_node && building.primary_node.network_number) {
            nodeId = building.primary_node.network_number;
        } else if (building.installs) {
            const installResponses = await Promise.all(
                building.installs.map(install => fetch(`/api/v1/installs/${install.id}/`))
            );
            for (const installResponse of installResponses) {
                if (installResponse.ok) {
                    const install = await installResponse.json();
                    if (install.status !== "Closed" && install.status !== "NN Reassigned") {
                        nodeId = install.install_number;
                        break;
                    }
                }
            }
        }
    } else if (["device", "sector", "accesspoint"].indexOf(type) !== -1) {
        if (!id) return null;
        const deviceResponse = await fetch(`/api/v1/devices/${id}/`);
        if (!deviceResponse.ok) return null;
        const device = await deviceResponse.json();
        nodeId = device.node.network_number;
    } else if (type === "member") {
        if (!id) return null;
        const memberResponse = await fetch(`/api/v1/members/${id}/`);
        if (!memberResponse.ok) return null;
        const member = await memberResponse.json();

        const installResponses = await Promise.all(
            member.installs.map(install => fetch(`/api/v1/installs/${install.id}/`))
        );

        nodeId = (await Promise.all(installResponses
            .filter(installResponse => installResponse.ok)
            .map(installResponse => installResponse.json())))
            .filter(install => install.status !== "Closed" && install.status !== "NN Reassigned")
            .map(install => install.install_number).join("-");
    } else if (type === "link") {
        if (!id) return null;
        const linkResponse = await fetch(`/api/v1/links/${id}/`);
        if (!linkResponse.ok) return null;
        const link = await linkResponse.json();

        const device1Response = await fetch(`/api/v1/devices/${link.from_device.id}/`);
        if (!device1Response.ok) return null;
        const device1 = await device1Response.json();

        const device2Response = await fetch(`/api/v1/devices/${link.to_device.id}/`);
        if (!device2Response.ok) return null;
        const device2 = await device2Response.json();

        if (device1.node.network_number && device2.node.network_number) {
            nodeId = `${device1.node.network_number}-${device2.node.network_number}`;
        }
    } else if (type === "los") {
        if (!id) return null;
        const losResponse = await fetch(`/api/v1/loses/${id}/`);
        if (!losResponse.ok) return null;
        const los = await losResponse.json();

        let b1NodeId = null;
        const buildingResponse1 = await fetch(`/api/v1/buildings/${los.from_building.id}/`);
        if (!buildingResponse1.ok) return null;
        const building1 = await buildingResponse1.json();
        if (building1.primary_node && building1.primary_node.network_number) {
            b1NodeId = building1.primary_node.network_number;
        } else if (building1.installs) {
            const installResponses = await Promise.all(
                building1.installs.map(install => fetch(`/api/v1/installs/${install.id}/`))
            );
            for (const installResponse of installResponses) {
                if (installResponse.ok) {
                    const install = await installResponse.json();
                    if (install.status !== "Closed" && install.status !== "NN Reassigned") {
                        b1NodeId = install.install_number;
                        break;
                    }
                }
            }
        }

        let b2NodeId = null;
        const buildingResponse2 = await fetch(`/api/v1/buildings/${los.to_building.id}/`);
        if (!buildingResponse2.ok) return null;
        const building2 = await buildingResponse2.json();
        if (building2.primary_node && building2.primary_node.network_number) {
            b2NodeId = building2.primary_node.network_number;
        } else if (building2.installs) {
            const installResponses = await Promise.all(
                building2.installs.map(install => fetch(`/api/v1/installs/${install.id}/`))
            );
            for (const installResponse of installResponses) {
                if (installResponse.ok) {
                    const install = await installResponse.json();
                    if (install.status !== "Closed" && install.status !== "NN Reassigned") {
                        b2NodeId = install.install_number;
                        break;
                    }
                }
            }
        }

        if (b1NodeId && b2NodeId) nodeId = `${b1NodeId}-${b2NodeId}`;
    }

    return nodeId ? `${nodeId}` : null;
}


async function updateAdminPanelLocation(selectedNodes) {
    if (!selectedNodes) return;
    if (selectedNodes.indexOf("-") !== -1) return;

    let selectedNodeInt = parseInt(selectedNodes);
    if (selectedNodeInt >= 1000000) {
        /* Hack for APs to not break things. We unfortantely can't do a lot better than this without much pain*/
        return;
    }
    const installResponse = await fetch(`/api/v1/installs/${selectedNodes}/`);
    const nodeResponse = await fetch(`/api/v1/nodes/${selectedNodes}/`);

    // Disable onLoad for Admin Panel while we navigate to a new page
    dontListenForAdminPanelLoad();

    if (installResponse.ok) {
        const installJson = await installResponse.json();
        if (installJson.node && installJson.node.network_number) {
            adminPanelIframe.src = `/admin/meshapi/node/${installJson.node.id}/change`;
        } else {
            adminPanelIframe.src = `/admin/meshapi/install/${installJson.id}/change`;
        }
    } else {
        if (nodeResponse.ok) {
            const nodeJson = await nodeResponse.json();
            adminPanelIframe.src = `/admin/meshapi/node/${nodeJson.id}/change`;
        }
    }

    // Restore the listener
    listenForAdminPanelLoad();
}

// Configures the listener that updates the admin panel based on map activity
async function listenForMapClick() {
    window.addEventListener("message", ({ data, source }) => {
        updateAdminPanelLocation(data.selectedNodes);
    });
}

// Prompts the map to change its view to focus on whatever
// node the admin panel is currently viewing.
async function updateMapLocation(url) {
    const selectedNodes = await getNewSelectedNodes(url);

    if (selectedNodes === null) {
        console.log("[Admin Panel] No node is selected.");
        return;
    }

    console.debug(`[Admin Panel] Updating map location: ${selectedNodes}`);

    // MAP_BASE_URL comes from iframed.html
    document.getElementById("map_panel").contentWindow.postMessage({ selectedNodes: selectedNodes }, MAP_BASE_URL);
}

async function onAdminPanelLoadWithMapClosed() {
    const adminPanelIframeUrl = new URL(adminPanelIframe.contentWindow.location.href);

    // Update the URL bar in the browser for viz
    window.history.pushState("MeshDB Admin Panel", "", adminPanelIframeUrl.pathname);
}

// Helper function to wrap everything that needs to happen when the admin panel
// loads
async function onAdminPanelLoad() {
    const adminPanelIframeUrl = new URL(adminPanelIframe.contentWindow.location.href);

    // If the admin panel iframe leaves the admin panel (by logging out, going to homescreen, etc)
    // we should leave this iframed view and go there.
    const escURLs = ["login", "password_reset"]
    var shouldEscape = escURLs.some(url => adminPanelIframeUrl.pathname.includes(url));
    if (!adminPanelIframeUrl.pathname.includes("admin") || shouldEscape) {
        window.location.href = adminPanelIframeUrl;
    }

    // Save the new admin location. We do this here because it means that the admin panel has
    // recently reloaded.
    localStorage.setItem(MESHDB_LAST_PAGE_VISITED, adminPanelIframeUrl.pathname);

    // Update the URL bar in the browser for viz
    window.history.pushState("MeshDB Admin Panel", "", adminPanelIframeUrl.pathname);

    // Finally, update the map view
    updateMapLocation(adminPanelIframeUrl.toString());
}

// Configures the listener that updates the map based on admin panel activity
async function listenForAdminPanelLoad() {
    adminPanelIframe.addEventListener("load", onAdminPanelLoad);
}

// See above
async function dontListenForAdminPanelLoad() {
    adminPanelIframe.removeEventListener("load", onAdminPanelLoad);
}

// Checks local storage for the last page the user navigated to, and directs them
// there
async function readURLBar() {
    // If the window's URL has more than just /admin/, then we wanna
    // override our stored page and replace it with that.
    const entryPath = new URL(window.location.href).pathname;
    const entrypointRegex = /^(\/?admin\/?)$/;
    if (!entryPath.match(entrypointRegex)) {
        const newEntryPath = entryPath.replace(PANEL_URL, "admin");
        adminPanelIframe.src = newEntryPath;
        localStorage.setItem(MESHDB_LAST_PAGE_VISITED, newEntryPath);
    }
}

// Interface Stuff

function listenForRecenterClick() {
    const recenterButton = document.querySelector("#map_recenter_button");

    function onRecenterClick(event) {
        console.log("recenterclick");
        updateMapLocation();
        event.preventDefault();
    }

    recenterButton.addEventListener("click", onRecenterClick, false);
}

function interceptLinks() {
    // Browser back
    window.addEventListener('popstate', function(event) {
        async function handler() {
            adminPanelIframe.src = location.href;
        }
        handler()
        event.preventDefault()
    }, false);
}

function setMapProportions(leftWidth) {
    // Apply new widths to left and right divs
    const leftDiv = document.getElementById('admin_panel_div');
    const rightDiv = document.getElementById('map_panel_div');

    currentSplit = leftWidth;
    leftDiv.style.width = `${leftWidth}%`;
    rightDiv.style.width = `${100 - leftWidth}%`;

    localStorage.setItem("MESHDB_MAP_SIZE", leftWidth.toString());
}

function toggleIframeInteractivity() {
    const handle = document.getElementById('handle');
    handle.classList.toggle("bigBar");

    const handlebar = document.getElementById('handlebar');
    handlebar.classList.toggle("hidden");

    const substituteHandle = document.getElementById('substituteHandle');
    substituteHandle.classList.toggle("hidden");
}

function allowMapResize() {
    // Event listener for mouse down on handle
    const handle = document.getElementById('handle');
    handle.addEventListener('mousedown', function(e) {
        e.preventDefault();
        window.addEventListener('mousemove', resize);
        window.addEventListener('mouseup', stopResize);
        toggleIframeInteractivity();
    });

    // Function to resize divs
    function resize(e) {
        // Get elements
        const container = document.getElementById('page_container');

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
        window.removeEventListener('mouseup', stopResize);
        toggleIframeInteractivity();
    }

    setMapProportions(currentSplit);
}

// Checks for mobile/manual map hiding and configures the admin panel interface as appropriate
function hideMapIfAppropriate() {
    const isMobile = mobileCheck();

    const mapDisabled = localStorage.getItem("MESHDB_MAP_DISABLED") === "true" || isMobile;
    if (mapDisabled) {
        document.getElementById('map_panel_div').classList.add("hidden");
        document.getElementById('map_controls').classList.add("hidden");

        if (!isMobile) {
            const showMapButton = document.getElementById('show_map_button');
            function onShowMapClick(event) {
                localStorage.setItem("MESHDB_MAP_DISABLED", "false");
                window.location.reload(); // Unpleasant but this action should be very infrequent
                event.preventDefault();
            }

            showMapButton.classList.remove("hidden");
            showMapButton.addEventListener("click", onShowMapClick, false);
        }

        // Make sure the URL bar still updates
        adminPanelIframe.addEventListener("load", onAdminPanelLoadWithMapClosed);
    } else {
        // Hide the show map button
        const showMapButton = document.getElementById('show_map_button');
        showMapButton.classList.toggle("hidden");

        const hideMapButton = document.getElementById("map_hide_button");

        function onHideMapClick(event) {
            localStorage.setItem("MESHDB_MAP_DISABLED", "true");
            window.location.reload(); // Unpleasant but this action should be very infrequent
            event.preventDefault();
        }

        hideMapButton.addEventListener("click", onHideMapClick, false);
    }

    return mapDisabled;
}

function start() {
    readURLBar();
    interceptLinks();
    if (hideMapIfAppropriate()) {
        return;
    }
    allowMapResize();
    listenForAdminPanelLoad();
    listenForMapClick();
    listenForRecenterClick();

}

start();
