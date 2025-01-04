function extractUUIDs(inputString) {
    // Regular expression to match UUIDs
    const uuidRegex = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g;
    // Find all matches in the input string
    const matches = inputString.match(uuidRegex);
    // Return the matches or an empty array if none found
    return matches || [];
}

function extractModel(inputString) {
  const relevantModels = ["member", "building", "install", "node", "device", "sector"];
  return relevantModels.find(element => inputString.includes(element));
}


// FIXME: Refreshes reset your location. Need to make sure that the iframe gets the refresh/forward/backward stuff. Check andrew's code.
// FIXME: Also need to make sure that admin/members/uuid directs you to this iframe setup properly
async function adminPanelLoaded() {
  const iframe_panel_url = document.getElementById("iframe_panel").contentWindow.location.href;

  const objectUUIDs = extractUUIDs(iframe_panel_url)
  const objectModel = extractModel(iframe_panel_url)

  document.getElementById("iframe_url").innerHTML = iframe_panel_url + " ---> " + objectModel + " || " + objectUUIDs;

  // Guard against looking up an empty UUID
  if (objectUUIDs.length == 0) {
    console.log("No UUID");
    return;
  }

  console.log(objectUUIDs[0]);
  // This is a dev token
  const token = "";

  let rqHeaders = new Headers();
  rqHeaders.append("Content-Type", "application/json");
  rqHeaders.append("Authorization", `Bearer ${token}`);

  const objectInfo = await fetch(`http://127.0.0.1:8000/api/v1/${objectModel}s/${objectUUIDs[0]}/`, {
    headers: rqHeaders 
  });

  const objectInfoJson = await objectInfo.json();
  console.log(objectInfoJson);
}

