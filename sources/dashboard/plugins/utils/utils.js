(function() {
  var plugin;

  plugin = function(_, Backbone) {
    var aedUtils, searchAssessmentModel;
    searchAssessmentModel = function(data, processedData, subString, filterContext) {
      var aggregator, baseURL, dataSample, filterPath, filteredLinks, key, label, link, links, name, regexp, results, secondLevelData, secondLevelKey, thirdLevelAggregator, thirdLevelData, thirdLevelKey, thirdLevelLabel, _i, _j, _k, _l, _len, _len1, _len2, _len3, _ref, _ref1;
      results = [];
      if (data == null) {
        return results;
      }
      regexp = new RegExp(subString, 'ig');
      baseURL = '#' + SELECTED_APPLICATION_HREF + '/qualityInvestigation/';
      if ((filterContext != null ? filterContext.business : void 0) != null) {
        filterPath = baseURL + filterContext.business;
        if (filterContext.technical != null) {
          filterPath += '/' + filterContext.technical;
        }
      }
      for (_i = 0, _len = data.length; _i < _len; _i++) {
        name = data[_i];
        if (name.match(regexp)) {
          dataSample = processedData[name];
          links = [];
          key = dataSample.reference.key;
          if (dataSample.reference.gradeAggregators.length === 0) {
            links.push({
              url: baseURL + key,
              label: [name]
            });
          }
          _ref = dataSample.reference.gradeAggregators;
          for (_j = 0, _len1 = _ref.length; _j < _len1; _j++) {
            aggregator = _ref[_j];
            secondLevelKey = aggregator.key + '/' + key;
            secondLevelData = processedData[aggregator.key];
            if (secondLevelData == null) {
              continue;
            }
            label = secondLevelData.reference.name;
            if (secondLevelData.reference.gradeAggregators.length === 0) {
              links.push({
                url: baseURL + secondLevelKey,
                label: [label]
              });
            }
            _ref1 = secondLevelData.reference.gradeAggregators;
            for (_k = 0, _len2 = _ref1.length; _k < _len2; _k++) {
              thirdLevelAggregator = _ref1[_k];
              thirdLevelKey = thirdLevelAggregator.key + '/' + secondLevelKey;
              thirdLevelData = processedData[thirdLevelAggregator.key];
              if (thirdLevelData == null) {
                continue;
              }
              thirdLevelLabel = thirdLevelData.reference.shortName;
              links.push({
                url: baseURL + thirdLevelKey,
                label: [thirdLevelLabel, label]
              });
            }
          }
          if (filterPath != null) {
            filteredLinks = [];
            for (_l = 0, _len3 = links.length; _l < _len3; _l++) {
              link = links[_l];
              if (link.url.indexOf(filterPath) === 0 && link.url !== filterPath) {
                filteredLinks.push(link);
              }
            }
            links = filteredLinks;
          }
          if (links.length > 0) {
            results.push({
              name: name.replace(regexp, function(matching) {
                return '<em>' + matching + '</em>';
              }),
              links: links
            });
          }
        }
      }
      return results;
    };
    aedUtils = {
      id: 'aedUtils',
      Facade: {
        utils: {
          searchAssessmentModel: searchAssessmentModel
        },
        navigation: {
          Router: Backbone.Router.extend({
            route: function(route, name, callback) {
              var router;
              if (!_.isRegExp(route)) {
                route = this._routeToRegExp(route);
              }
              if (_.isFunction(name)) {
                callback = name;
                name = '';
              }
              if (!callback) {
                callback = this[name];
              }
              router = this;
              Backbone.history.route(route, function(fragment) {
                var args;
                args = router._extractParameters(route, fragment);
                Backbone.history.trigger('route:before', router, name, args);
                router.execute(callback, args);
                router.trigger.apply(router, ['route:' + name].concat(args));
                router.trigger('route', name, args);
                return Backbone.history.trigger('route', router, name, args);
              });
              return this;
            }
          }),
          History: Backbone.history,
          startNavigation: function() {
            return Backbone.history.start();
          }
        }
      }
    };
    return aedUtils;
  };

  if ((typeof define !== "undefined" && define !== null ? define.amd : void 0) != null) {
    define(['underscore', 'backbone'], function(_, Backbone) {
      return plugin(_, Backbone);
    });
  } else if (typeof window !== "undefined" && window !== null) {
    window.stem = window.stem || {};
    window.stem.plugins = window.stem.plugins || {};
    window.stem.plugins.aedUtils = plugin(_, Backbone);
  } else if ((typeof module !== "undefined" && module !== null ? module.exports : void 0) != null) {
    module.exports = plugin(_, Backbone);
  }

}).call(this);
