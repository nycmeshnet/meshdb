async function checkIframed() {
  // Check if we're in an iframe
  const inIframe = window.self !== window.top;
  
  // If we are, do nothing
  if (inIframe) {
    return;
  }

  // Also do nothing if we're not in the admin panel proper (eg not logged in)
  const escURLs = ["login", "password_reset"]
  const currentURL = window.location.href;

  var shouldEscape = escURLs.some(url => currentURL.includes(url));
  if (shouldEscape) {
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
  
  // FIXME (wdn): This might not totally clear the state after all, since the variables
  // from /admin are still hanging around
  document.open(); // Clears the screen
  document.write(await response.text());
  document.close();
}

checkIframed();
