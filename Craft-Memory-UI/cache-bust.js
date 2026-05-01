(function () {
  var CB = String(Date.now());
  function bust(url) {
    if (typeof url === 'string' && url.indexOf('.jsx') !== -1) {
      return url.split('?')[0] + '?_cb=' + CB;
    }
    return url;
  }
  var _xo = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m, u) { return _xo.call(this, m, bust(u)); };
  var _f = window.fetch;
  window.fetch = function (i, o) { return _f.call(window, typeof i === 'string' ? bust(i) : i, o); };
  console.log('[cm] cache-bust active CB=' + CB);
})();
