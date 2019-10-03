(function() {
  var plugin;

  plugin = function() {
    var codeHighlighter;
    codeHighlighter = {
      id: 'codeHighlighter',
      Facade: {
        codeHighlighter: {
          processLanguages: function($selector) {
            return $selector.find('pre code').each(function(i, item) {
              return hljs.highlightBlock(item);
            });
          }
        }
      }
    };
    return codeHighlighter;
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['highlight'], function() {
      return plugin();
    });
  } else if (typeof window !== "undefined" && window !== null) {
    window.stem = window.stem || {};
    window.stem.plugins = window.stem.plugins || {};
    window.stem.plugins.codeHighlighter = plugin();
  } else if ((typeof module !== "undefined" && module !== null ? module.exports : void 0) != null) {
    module.exports = plugin();
  }

}).call(this);
