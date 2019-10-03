(function() {
    var propTypesPlugin;

    propTypesPlugin = function(PropTypes) {
        return {
            id: 'propTypes',
            Facade: {
                propTypes: PropTypes,
            }
        };
    };

    if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
        define(['propTypes'], function(PropTypes) {
            return {PropTypes : propTypesPlugin(PropTypes).Facade.propTypes, id :'propTypes'};
        });
    } else if ((typeof window !== "undefined" && window !== null) && (window.stem != null)) {
        window.stem.plugins['propTypes'] = propTypesPlugin(window.PropTypes);
    }

}).call(this);
