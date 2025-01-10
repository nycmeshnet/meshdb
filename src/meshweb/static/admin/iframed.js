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

// FIXME: Refreshes reset your location. Need to make sure that the iframe gets
// the refresh/forward/backward stuff. Check andrew's code.
// FIXME: Also need to make sure that admin/members/uuid directs you to this
// iframe setup properly
async function updateMapLocation() {
  const iframe_panel_url = document.getElementById("iframe_panel").contentWindow.location.href;

  const selectedNodes = await getNewSelectedNodes(iframe_panel_url);

  if (selectedNodes === null) {
    console.log("No node");
    return;
  }

  // MAP_BASE_URL comes from iframed.html
  document.getElementById("map_panel").contentWindow.postMessage({selectedNodes: selectedNodes}, MAP_BASE_URL);


  const map_panel_url = document.getElementById("map_panel").contentWindow.location.href;
  
  // Update the URL
  document.getElementById("admin_panel_url_bar").innerHTML = `${iframe_panel_url}`;
  document.getElementById("map_url_bar").innerHTML = `${map_panel_url}`;
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
            document.getElementById("iframe_panel").src = `panel/meshapi/node/${installJson.node.id}/change`;
        } else {
            document.getElementById("iframe_panel").src = `panel/meshapi/install/${installJson.id}/change`;
        }
    } else {
        if (nodeResponse.ok)  {
            const nodeJson = await nodeResponse.json();
            document.getElementById("iframe_panel").src = `panel/meshapi/node/${nodeJson.id}/change`;
        }
    }

    const map_panel_url = document.getElementById("map_panel").contentWindow.location.href;
    
    // Update the URL
    document.getElementById("admin_panel_url_bar").innerHTML = `${iframe_panel_url}`;
    document.getElementById("map_url_bar").innerHTML = `${map_panel_url}`;
}

window.addEventListener("message", ({ data, source }) => {
  updateAdminPanelLocation(data.selectedNodes);
});
