function checkIframed() {
  // Check if we're in an iframe
  const inIframe = window.self !== window.top;
  
  // If not, show button
  if (!inIframe) {
    const panelViewButton = document.getElementById("navigate_to_panel_view");
    panelViewButton.classList.toggle("hidden");

    let panelURL = window.location.href;
    console.log(panelURL);
    panelURL = panelURL.replace("/admin", "/admin/panel");
    console.log(panelURL);
    panelViewButton.href = panelURL;
  }
}

checkIframed();
