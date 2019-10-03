(function() {
  var plugin;

  plugin = function(animo) {
    animo = {
      id: 'animo'
    };
    return animo;
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['animo'], function(animo) {
      return plugin(animo);
    });
  } else if (typeof window !== "undefined" && window !== null) {
    window.stem = window.stem || {};
    window.stem.plugins = window.stem.plugins || {};
    window.stem.plugins.animo = plugin(animo);
  } else if ((typeof module !== "undefined" && module !== null ? module.exports : void 0) != null) {
    module.exports = plugin(animo);
  }

}).call(this);
