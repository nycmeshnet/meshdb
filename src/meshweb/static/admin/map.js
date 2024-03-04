
function updateMapForRoute() {
    document.getElementById("map").getElementsByTagName("p")[0].innerHTML = location.pathname + location.search;
}

async function loadScripts(scripts) {
    for (const script of scripts) {
        const scriptLoadPromise = new Promise((resolve, reject) => {
            const scriptElement = document.createElement('script');
            scriptElement.src = script.src;
            scriptElement.onload = resolve;
            scriptElement.onerror = reject;
            document.head.appendChild(scriptElement);
        });
        await scriptLoadPromise;
    }
}

async function updateAdminContent() {
  let currentPathname = location.pathname;

    const response = await fetch(location.pathname + location.search);
    if (!response.ok) {
      throw new Error("Error loading page");
    }
    // if (response.redirected) {
    //   window.location = response.url;
    //   return;
    // }
    const current_map = document.getElementById("map");

    const text = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, "text/html");
    doc.getElementById("map").replaceWith(current_map);


  if (location.pathname != currentPathname) {
    return
  }


  const newHTML = doc.getElementsByTagName("html")[0];
  document.getElementsByTagName("html")[0].replaceWith(newHTML);

  if (window.DateTimeShortcuts) window.removeEventListener('load', window.DateTimeShortcuts.init);
  await loadScripts(document.head.querySelectorAll('script'));

  console.log("Simulating window load...")
  dispatchEvent(new Event('load'));

  //window.scrollTo(0, 0);
}


function shouldNotIntercept(event) {
    const url = new URL(event.destination.url);

    if (event.downloadRequest) return true;
    if (!url.pathname.startsWith("/admin/")) return true;
    if (url.pathname.startsWith("/admin/login")) return true;
    if (url.pathname.startsWith("/admin/logout")) return true;
    if (url.host !== location.host) return true;

    return false;
}

function interceptLinks() {
    navigation.addEventListener("navigate", (event) => {
      // Exit early if this navigation shouldn't be intercepted,
      // e.g. if the navigation is cross-origin, or a download request
      if (shouldNotIntercept(event)) return;

      const url = event.destination.url;
      event.intercept({
          async handler() {
              console.log("Caught navigation to " + url)

                updateMapForRoute();
                updateAdminContent();
          },
        });
    });
}

function start() {
  updateMapForRoute();
  interceptLinks();
}

start();