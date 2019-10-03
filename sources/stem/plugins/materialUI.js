(function() {
    var materialUIPlugin;

    materialUIPlugin = function(MaterialUI) {
        return {
            id: 'materialUI',
            Facade: {
                materialUI: MaterialUI,
            }
        };
    };

    if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
        define(['materialUI'], function(MaterialUI) {
            return {materialUI : materialUIPlugin(MaterialUI).Facade.materialUI, id :'materialUI'};
        });
    } else if ((typeof window !== "undefined" && window !== null) && (window.stem != null)) {
        window.stem.plugins['materialUI'] = materialUIPlugin( window.MaterialUI);
    }

}).call(this);
