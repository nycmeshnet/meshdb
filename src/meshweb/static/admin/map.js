const ADMIN_PANEL_HOME = "/admin/"
const MESHDB_LAST_PAGE_VISITED = "MESHDB_LAST_PAGE_VISITED"
const admin_panel_iframe = document.getElementById("admin_panel_iframe");

let currentSplit = parseFloat(localStorage.getItem("MESHDB_MAP_SIZE"));
if (isNaN(currentSplit)) {
    currentSplit = 60;
}

// Taken from: https://stackoverflow.com/a/11381730
const mobileCheck = function() {
  let check = false;
  (function(a){if(/(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows ce|xda|xiino/i.test(a)||/1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(a.substr(0,4))) check = true;})(navigator.userAgent||navigator.vendor||window.opera);
  return check;
};

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
  const relevantModels = ["member", "building", "install", "node", "device", "sector", "link"];
  return relevantModels.find(element => url.includes(element));
}

// Based on the current URL of the Admin Panel, figures out what node the map
// should focus on
async function getNewSelectedNodes(url){
    const objectUUIDs = extractUUIDs(url);
    const type = extractModel(url);

    // Guard against looking up an empty UUID
    if (objectUUIDs.length == 0) {
      console.log("Found no UUID")
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
                if (installResponse.ok){
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
                if (installResponse.ok){
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
                if (installResponse.ok){
                    const install = await installResponse.json();
                    if (install.status !== "Closed" && install.status !== "NN Reassigned") {
                        b2NodeId = install.install_number;
                        break;
                    }
                }
            }
        }

        if (b1NodeId && b2NodeId)  nodeId = `${b1NodeId}-${b2NodeId}`;
    }

    return nodeId ? `${nodeId}` : null;
}


async function updateAdminPanelLocation(selectedNodes) {
    if (!selectedNodes) return;
    console.log(`[Admin Panel] Updating admin panel location: ${selectedNodes}`);
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

    if (installResponse.ok){
        const installJson = await installResponse.json();
        if (installJson.node && installJson.node.network_number)  {
            admin_panel_iframe.src = `/admin/meshapi/node/${installJson.node.id}/change`;
        } else {
            admin_panel_iframe.src = `/admin/meshapi/install/${installJson.id}/change`;
        }
    } else {
        if (nodeResponse.ok)  {
            const nodeJson = await nodeResponse.json();
            admin_panel_iframe.src = `/admin/meshapi/node/${nodeJson.id}/change`;
        }
    }

    console.log(`Admin Panel src set to: ${admin_panel_iframe.src}`);

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
  document.getElementById("map_panel").contentWindow.postMessage({selectedNodes: selectedNodes}, MAP_BASE_URL);
}

// Helper function to wrap everything that needs to happen when the admin panel
// loads
async function onAdminPanelLoad() {
    const adminPanelIframeUrl = admin_panel_iframe.contentWindow.location.href;

    // Save the new admin location. We do this here because it means that the admin panel has
    // recently reloaded.
    const adminPanelIframeLastPageVisited = new URL(adminPanelIframeUrl).pathname;
    localStorage.setItem(MESHDB_LAST_PAGE_VISITED, adminPanelIframeLastPageVisited);

    // Update the URL bar in the browser for viz
    window.history.pushState("MeshDB Admin Panel", "", adminPanelIframeLastPageVisited.replace("/admin", "/admin/panel"));

    // Finally, update the map view
    updateMapLocation(adminPanelIframeUrl);
}

// Configures the listener that updates the map based on admin panel activity
async function listenForAdminPanelLoad() {
    admin_panel_iframe.addEventListener("load", onAdminPanelLoad);
}

// See above
async function dontListenForAdminPanelLoad() {
    admin_panel_iframe.removeEventListener("load", onAdminPanelLoad);
}

// Checks local storage for the last page the user navigated to, and directs them
// there
async function adminPanelRestoreLastVisited() {
    // If the window's URL has more than just /admin/, then we wanna
    // override our stored page and replace it with that.
    const entryPath = new URL(window.location.href).pathname;
    console.log(`Entry Path: ${entryPath}`);
    const entrypointRegex = /^(\/?admin\/panel\/?)$/;
    if (!entryPath.match(entrypointRegex)) {
      const newEntryPath = entryPath.replace("admin/panel", "admin");
      document.getElementById("admin_panel_iframe").src = newEntryPath;
      localStorage.setItem(MESHDB_LAST_PAGE_VISITED, newEntryPath);
      return;
    }

    let lastVisitedUrl = localStorage.getItem(MESHDB_LAST_PAGE_VISITED);
    console.log(`Last Visited: ${lastVisitedUrl}`);

    // Check for corruption in lastVisited

    // If the URL doesn't contain "panel," then something broke, and the safest
    // thing is to just default back home
    if (!lastVisitedUrl.startsWith("/admin/panel/")) {
        localStorage.setItem(MESHDB_LAST_PAGE_VISITED, ADMIN_PANEL_HOME);
        lastVisitedUrl = ADMIN_PANEL_HOME;
        console.error("MESHDB_LAST_PAGE_VISITED was somehow corrupted. It's probably @willard's fault.");
    }

    // Make sure it loads. If it doesn't, reset.
    const isGoodLastVisited = await fetch(lastVisitedUrl);
    if (!isGoodLastVisited.ok) {
        localStorage.setItem(MESHDB_LAST_PAGE_VISITED, ADMIN_PANEL_HOME);
        lastVisitedUrl = ADMIN_PANEL_HOME;
        console.error("MESHDB_LAST_PAGE_VISITED was somehow corrupted. It's probably @willard's fault.")
    }

    admin_panel_iframe.src = lastVisitedUrl;
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
            admin_panel_iframe.src = location.href;
        }
        handler()
        // console.log(location.href);
        event.preventDefault()
    }, false);
}

function setMapProportions(leftWidth){
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
        //document.getElementById('main').classList.remove("flex");

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
    } else {
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
    adminPanelRestoreLastVisited();
    if (hideMapIfAppropriate()) {
        return;
    }
    allowMapResize();
    interceptLinks();
    listenForAdminPanelLoad();
    listenForMapClick();
    listenForRecenterClick();

}

start();
