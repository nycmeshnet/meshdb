// Used to check if a user has accessed the PANEL_URL directly, and adjusts the 
// URL for them
// This file is meant to be loaded from iframe.html where that variable is defined
function checkForPanelURL() {
  const entryPath = new URL(window.location.href).pathname;
  if (entryPath.includes(PANEL_URL)) {
    window.history.pushState("MeshDB Admin Panel", "", entryPath.replace(PANEL_URL, "/admin/"));
  }
}

checkForPanelURL();
