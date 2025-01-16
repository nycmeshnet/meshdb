// Used to check if a user has accessed the PANEL_URL directly, and adjusts the 
// URL for them
// This file is meant to be loaded from iframe.html where that variable is defined
function checkForPanelURL() {
  if (entryPath.contains(PANEL_URL)) {
    const entryPath = new URL(window.location.href).pathname;
    window.history.pushState("MeshDB Admin Panel", "", entryPath.replace(PANEL_URL, "/admin/"));
  }
}

checkForPanelURL();
