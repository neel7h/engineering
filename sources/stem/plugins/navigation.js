(function() {
  var navigation;

  navigation = function(Backbone) {
    return {
      id: 'navigation',
      Facade: {
        navigation: {
          Router: Backbone.Router,
          startNavigation: function() {
            return Backbone.history.start();
          }
        }
      }
    };
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['backbone'], function(Backbone) {
      return navigation(Backbone);
    });
  } else if ((typeof window !== "undefined" && window !== null) && (window.stem != null)) {
    window.stem.plugins['navigation'] = navigation(window.Backbone);
  }

}).call(this);
