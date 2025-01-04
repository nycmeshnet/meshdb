function extractUUIDs(inputString) {
    // Regular expression to match UUIDs
    const uuidRegex = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g;
    // Find all matches in the input string
    const matches = inputString.match(uuidRegex);
    // Return the matches or an empty array if none found
    return matches || [];
}

function extractModel(inputString) {
  const relevantModels = ["member", "building", "install", "node", "device", "sector", "link"];
  return relevantModels.find(element => inputString.includes(element));
}


function getCurrentTarget(url){
    let path = url.replace(/^\/admin\/meshapi\//, "");
    path = path.replace(/\/$/, "");

    const [type, id, action] = path.split("/");
    return [type, id, action];
}

// XXX (wdn): This function is plural, but it's actually just one node?
async function getNewSelectedNodes(url){
    //const [type, id, action] = getCurrentTarget(url);

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
        nodeId = install.install_number;
    } else if (type === "node") {
        if (!id) return null;
        const nodeResponse = await fetch(`/api/v1/nodes/${id}/`);
        if (!nodeResponse.ok) return null;
        const node = await nodeResponse.json();
        if (node.network_number) {
            nodeId = node.network_number;
        } else {
            nodeId = node.installs[0].install_number;
        }
    } else if (type === "building") {
        if (!id) return null;
        const buildingResponse = await fetch(`/api/v1/buildings/${id}/`);
        if (!buildingResponse.ok) return null;
        const building = await buildingResponse.json();
        if (building.primary_node && building.primary_node.network_number) {
            nodeId = building.primary_node.network_number;
        } else if (building.installs) {
            nodeId = building.installs[0].install_number;
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
        nodeId = member.installs.map(install => install.install_number).join("-");
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
            b1NodeId = building1.installs[0].install_number;
        }

        let b2NodeId = null;
        const buildingResponse2 = await fetch(`/api/v1/buildings/${los.to_building.id}/`);
        if (!buildingResponse2.ok) return null;
        const building2 = await buildingResponse2.json();
        if (building2.primary_node && building2.primary_node.network_number) {
            b2NodeId = building2.primary_node.network_number;
        } else if (building2.installs) {
            b2NodeId = building2.installs[0].install_number;
        }

        if (b1NodeId && b2NodeId)  nodeId = `${b1NodeId}-${b2NodeId}`;
    }

    return nodeId ? `${nodeId}` : null;
}


// FIXME: Refreshes reset your location. Need to make sure that the iframe gets the refresh/forward/backward stuff. Check andrew's code.
// FIXME: Also need to make sure that admin/members/uuid directs you to this iframe setup properly
async function adminPanelLoaded() {
  const iframe_panel_url = document.getElementById("iframe_panel").contentWindow.location.href;

  const selectedNodes = await getNewSelectedNodes(iframe_panel_url);

  document.getElementById("iframe_url").innerHTML = `${iframe_panel_url} ---> Selected Nodes: ${selectedNodes}`;

  if (selectedNodes === null) {
    console.log("No node");
    return;
  }

  console.log(`Got node: ${selectedNodes}`);

  //const selectedEvent = new Event("setMapNode");//, {detail: {selectedNodes: selectedNodes}});
  //selectedEvent.selectedNodes = selectedNodes;
    document.getElementById("map_panel").contentWindow.postMessage({selectedNodes: selectedNodes}, "http://127.0.0.1:3001");
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
    if (installResponse.ok){
        const installJson = await installResponse.json();
        if (installJson.node && installJson.node.network_number)  {
            const newAdminPanelURL = new URL(`/admin/panel/meshapi/node/${installJson.node.id}/change`, document.location);
            document.getElementById("iframe_panel").src = `panel/meshapi/node/${installJson.node.id}/change`;
            //updateMapForLocation(installJson.node.network_number.toString());
        } else {
            const newAdminPanelURL = new URL(`/admin/panel/meshapi/install/${installJson.id}/change`, document.location);
            document.getElementById("iframe_panel").src = `panel/meshapi/install/${installJson.id}/change`;
        }
    } else {
        if (nodeResponse.ok)  {
            const nodeJson = await nodeResponse.json();
            const newAdminPanelURL = new URL(`/admin/panel/meshapi/node/${nodeJson.id}/change`, document.location);
            document.getElementById("iframe_panel").src = `panel/meshapi/node/${nodeJson.id}/change`;
        }
    }
}

window.addEventListener("message", ({ data, source }) => {
        console.log(`Admin Panel got event: ${JSON.stringify(data)}`);
        // Check if we have the correct data
        // look up the id of the node
        // replace admin panel window location
        //this.updateSelected.bind(this)(data.selectedNodes, false);
        updateAdminPanelLocation(data.selectedNodes);
    }
);
