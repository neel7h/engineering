(function() {
  var bootstrapPlugin;

  bootstrapPlugin = function(bootstrap) {
    return {
      id: 'bootstrap',
      Facade: {
        bootstrap: bootstrap
      }
    };
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['cast.bootstrap'], function(bootstrap) {
      return bootstrapPlugin(bootstrap);
    });
  } else if ((typeof window !== "undefined" && window !== null) && (window.stem != null)) {
    window.stem.plugins['bootstrap'] = bootstrapPlugin(bootstrap);
  }

}).call(this);
