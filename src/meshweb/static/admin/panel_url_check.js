// Used to check if a user has accessed /admin/panel directly, and adjusts the 
// URL for them
function checkForPanelURL() {
  if (entryPath.contains("/admin/panel/")) {
    const entryPath = new URL(window.location.href).pathname;
    window.history.pushState("MeshDB Admin Panel", "", entryPath.replace("/admin/panel/", "/admin/"));
  }
}

checkForPanelURL();
