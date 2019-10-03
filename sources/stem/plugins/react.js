(function() {
    var reactPlugin;

    reactPlugin = function(React) {
        return {
            id: 'react',
            Facade: {
                react: React,
            }
        };
    };

    if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
        define(['react'], function(React) {
            return {React : reactPlugin(React).Facade.react, id :'react'};
        });
    } else if ((typeof window !== "undefined" && window !== null) && (window.stem != null)) {
        window.stem.plugins['react'] = reactPlugin(window.React);
    }

}).call(this);
