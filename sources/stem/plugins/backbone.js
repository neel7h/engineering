(function() {
  var backbone;

  backbone = function(_, Backbone, Handlebars) {
    /*
      We override default backbone Model to provide an easier catch at multiple fetch we tend to have due to multiple
      url resources.
    */

    var BaseCollection, BaseModel,
      _this = this;
    BaseModel = Backbone.Model.extend({
      defaultOptions: {
        success: function() {
          var _ref;
          return (_ref = _this.success) != null ? _ref.apply(_this, arguments) : void 0;
        },
        error: function() {
          if (_this.error != null) {
            return _this.error.apply(_this, Array.prototype.slice.call(arguments));
          } else {
            console.error('Error during getData>fetch and no error method was defined', _this);
            return alert('Error during getData>fetch and no error method was defined\nsee log for more information');
          }
        }
      },
      getData: function(options) {
        var fullOptions;
        fullOptions = _.extend({
          success: this.success,
          error: this.error
        }, options);
        return this.fetch(fullOptions);
      }
    });
    BaseCollection = Backbone.Collection.extend({
      defaultOptions: {
        success: function() {
          var _ref;
          return (_ref = _this.success) != null ? _ref.apply(_this, arguments) : void 0;
        },
        error: function() {
          if (_this.error != null) {
            return _this.error.apply(_this, Array.prototype.slice.call(arguments));
          } else {
            console.error('Error during getData>fetch and no error method was defined', _this);
            return alert('Error during getData>fetch and no error method was defined\nsee log for more information');
          }
        }
      },
      getData: function(options) {
        var fullOptions;
        fullOptions = _.extend({
          success: this.success,
          error: this.error
        }, options);
        return this.fetch(fullOptions);
      }
    });
    return {
      id: 'backbone',
      Facade: {
        backbone: {
          Collection: BaseCollection,
          Model: BaseModel,
          View: Backbone.View
        },
        Handlebars: Handlebars
      }
    };
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['underscore', 'backbone', 'handlebars'], function(_, Backbone, Handlebars) {
      return backbone(_, Backbone, Handlebars);
    });
  } else if ((typeof window !== "undefined" && window !== null) && (window.stem != null)) {
    window.stem.plugins['backbone'] = backbone(window._, window.Backbone, window.Handlebars);
  }

}).call(this);
