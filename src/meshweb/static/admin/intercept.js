// Copied from https://www.npmjs.com/package/intercept-link-clicks v1.1.0


/**
 * Intercepts clicks on a given element
 */
var Interceptor = function interceptClicks (el, opts, cb) {
  // Options and element are optional
  if (typeof el === 'function') {
    cb = el
    opts = {}
    el = window
  } else if (typeof opts === 'function') {
    cb = opts
    opts = {}
    // Duck-typing here because you can bind events to the window just fine
    // also, it might be good to bind to synthetic objects
    // to be able to mimic dom events
    if (typeof el.addEventListener !== 'function') {
      opts = el
      el = window
    }
  }

  // cb and el are required
  if (typeof cb !== 'function' || !el) {
    return
  }

  // Create click callback
  var clickCb = Interceptor.onClick(opts, cb)

  // Bind the event
  el.addEventListener('click', clickCb, false)

  // Returns the off function
  return function () {
    el.removeEventListener('click', clickCb, false)
  }
}

/**
 * On click handler that intercepts clicks based on options
 *
 * @function onClick
 * @param {Event} e
 */
Interceptor.onClick = function (opts, cb) {
  // Options are optional
  if (typeof opts === 'function') {
    cb = opts
    opts = {}
  }

  // cb is required and must be a function
  if (typeof cb !== 'function') {
    return
  }

  // Default options to true
  [
    'modifierKeys',
    'download',
    'target',
    'hash',
    'mailTo',
    'sameOrigin',
    'shadowDom'
  ].forEach(function (key) {
    opts[key] = typeof opts[key] !== 'undefined' ? opts[key] : true
  })

  // Return the event handler
  return function (e) {
    // Cross browser event
    e = e || window.event

    // Check if we are a click we should ignore
    if (opts.modifierKeys && (Interceptor.which(e) !== 1 || e.metaKey || e.ctrlKey || e.shiftKey || e.defaultPrevented)) {
      return
    }

    // Find link up the dom tree
    var el = Interceptor.isLink(e.target)

    // Support for links in shadow dom
    if (opts.shadowDom && !el && e.composedPath) {
      el = Interceptor.isLink(e.composedPath()[0])
    }

    //
    // Ignore if tag has
    //

    // 1. Not a link
    if (!el) {
      return
    }

    // 2. "download" attribute
    if (opts.download && el.getAttribute('download') !== null) {
      return
    }

    // 3. rel="external" attribute
    if (opts.checkExternal && el.getAttribute('rel') === 'external') {
      return
    }

    // 4. target attribute
    if (opts.target && (el.target && el.target !== '_self')) {
      return
    }

    // Get the link href
    var link = el.getAttribute('href')

    // ensure this is not a hash for the same path
    if (opts.hash && el.pathname === window.location.pathname && (el.hash || link === '#')) {
      return
    }

    // Check for mailto: in the href
    if (opts.mailTo && link && link.indexOf('mailto:') > -1) {
      return
    }

    // Only for same origin
    if (opts.sameOrigin && !Interceptor.sameOrigin(link)) {
      return
    }

    // All tests passed, intercept the link
    cb(e, el)
  }
}

Interceptor.isLink = function (el) {
  while (el && el.nodeName !== 'A') {
    el = el.parentNode
  }
  if (!el || el.nodeName !== 'A') {
    return
  }
  return el
}

/**
 * Get the pressed button
 */
Interceptor.which = function (e) {
  return e.which === null ? e.button : e.which
}

/**
 * Internal request
 */
Interceptor.isInternal = new RegExp('^(?:(?:http[s]?:)?//' + window.location.host.replace(/\./g, '\\.') + ')?(?:/[^/]|#|(?!(?:http[s]?:)?//).*$)', 'i')
Interceptor.sameOrigin = function (url) {
  return !!Interceptor.isInternal.test(url)
}

var interceptClicks = Interceptor;