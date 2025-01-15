const PANEL_URL = "/admin/panel/";

async function checkIframed() {
  // Check if we're in an iframe
  const inIframe = window.self !== window.top;
  
  // If not, do nothing
  if (inIframe) {
    return;
  }

  // If we're not in an iframe, then we'll want to swap the user to the iframed 
  // view
  try {
    response = await fetch(PANEL_URL);
    if (!response.ok) {
      throw new Error(
        `Error loading new contents for page: ${response.status} ${response.statusText}`
      );
    }
  } catch (e) {
    console.error(`Error during page nav to %s`, PANEL_URL, e)
    const mapWrapper = document.getElementById("container");

    const pageLink = document.createElement("a");
    pageLink.className = "capture-exclude";
    pageLink.href = PANEL_URL;
    pageLink.textContent = PANEL_URL;

    const errorNotice = document.createElement("p");
    errorNotice.className = "error-box";
    errorNotice.innerHTML = `<b>Error loading page</b>: ${pageLink.outerHTML}<br>${e}`

    mapWrapper.parentNode.insertBefore(
        errorNotice,
        mapWrapper
    );
    return;
  }
  
  document.open();
  document.write(await response.text());
  document.close();
}

checkIframed();
