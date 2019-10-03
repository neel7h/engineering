# FIXME more stuff should belong here !
plugin = (_, Backbone) ->

  searchAssessmentModel = (data, processedData, subString, filterContext, snapshotId)->
    results = []
    return results unless data?
    regexp = new RegExp(subString,'ig')
    baseURL = '#' + SELECTED_APPLICATION_HREF + '/snapshots/' + snapshotId + '/qualityInvestigation/0/'

    if filterContext?.business?
      filterPath = baseURL + filterContext.business
      filterPath += '/' + filterContext.technical if filterContext.technical?

    for name in data
      if name.match(regexp)
        dataSample = processedData[name]
        links = []
        key = dataSample.reference.key
        if dataSample.reference.gradeAggregators.length == 0
          links.push({url:baseURL + key, label:[name]})
        for aggregator in dataSample.reference.gradeAggregators
          secondLevelKey = aggregator.key + '/' + key
          secondLevelData = processedData[aggregator.key]
          continue unless secondLevelData?
          label = secondLevelData.reference.name
          if secondLevelData.reference.gradeAggregators.length == 0
            links.push({url:baseURL + secondLevelKey, label:[label]})
          for thirdLevelAggregator in secondLevelData.reference.gradeAggregators
            thirdLevelKey = thirdLevelAggregator.key + '/' + secondLevelKey
            thirdLevelData = processedData[thirdLevelAggregator.key]
            continue unless thirdLevelData?
            thirdLevelLabel = thirdLevelData.reference.shortName
            links.push({url:baseURL + thirdLevelKey, label:[thirdLevelLabel, label]})
        if filterPath?
          filteredLinks = []
          for link in links
            filteredLinks.push(link) if link.url.indexOf(filterPath) == 0 and link.url != filterPath
          links = filteredLinks
        results.push({
          name:name.replace(regexp,(matching)->
            '<em>' + matching + '</em>'
          )
          links:links
        }) if links.length > 0
    results


  aedUtils =
    id: 'aedUtils'
    Facade:
      utils:{
        searchAssessmentModel:searchAssessmentModel
      }
      navigation: {
        Router: Backbone.Router.extend({
          route: (route, name, callback) ->
            route = this._routeToRegExp(route) if (!_.isRegExp(route))
            if (_.isFunction(name))
              callback = name
              name = ''
            callback = this[name] if (!callback)
            router = this;
            Backbone.history.route(route, (fragment) ->
              args = router._extractParameters(route, fragment)
              Backbone.history.trigger('route:before', router, name, args)
              router.execute(callback, args)
              router.trigger.apply(router, ['route:' + name].concat(args))
              router.trigger('route', name, args)
              Backbone.history.trigger('route', router, name, args)
            )
            @
          })
        History:Backbone.history,
        startNavigation: ()->
          return Backbone.history.start()

      }

  aedUtils

# AMD support (use in require)
if define?.amd?
  define([
      'underscore'
      'backbone'
    ],
    (_, Backbone) ->
      return plugin(_, Backbone)
  )
# direct browser integration (src include)
else if window?
  window.stem = window.stem or {}
  window.stem.plugins = window.stem.plugins or {}
  window.stem.plugins.aedUtils = plugin(_, Backbone)
else if module?.exports?
  module.exports = plugin(_, Backbone)
