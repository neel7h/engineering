(function() {
  var i18n;

  i18n = function(i18next) {
    return {
      id: 'i18n',
      Facade: {
        i18n: {
          init: function(options, callback) {
            return i18next.init(options, callback);
          },
          translate: function(key) {
            return i18next.t(key);
          }
        }
      }
    };
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['i18next'], function(i18next) {
      return i18n(i18next);
    });
  } else if ((typeof window !== "undefined" && window !== null) && (window.stem != null)) {
    window.stem.plugins['i18n'] = i18n(i18next);
  }

}).call(this);
