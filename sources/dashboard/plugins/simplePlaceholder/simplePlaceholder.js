(function() {
  var plugin;

  plugin = function(simplePlaceholder) {
    simplePlaceholder = {
      id: 'simplePlaceholder'
    };
    return simplePlaceholder;
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['simplePlaceholder'], function(simplePlaceholder) {
      return plugin(simplePlaceholder);
    });
  } else if (typeof window !== "undefined" && window !== null) {
    window.stem = window.stem || {};
    window.stem.plugins = window.stem.plugins || {};
    window.stem.plugins.simplePlaceholder = plugin(simplePlaceholder);
  } else if ((typeof module !== "undefined" && module !== null ? module.exports : void 0) != null) {
    module.exports = plugin(simplePlaceholder);
  }

}).call(this);
