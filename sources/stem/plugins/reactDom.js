(function() {
    var reactDomPlugin;

    reactDomPlugin = function(ReactDOM) {
        return {
            id: 'reactDom',
            Facade: {
                reactDom: ReactDOM,

            }
        };
    };

    if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
        define(['reactDom'], function(ReactDOM) {
            return {ReactDOM : reactDomPlugin(ReactDOM).Facade.reactDom, id :'reactDom'};
        });
    } else if ((typeof window !== "undefined" && window !== null) && (window.stem != null)) {
        window.stem.plugins['reactDom'] = reactDomPlugin(window.ReactDOM);
    }

}).call(this);
