###
  Defines the application navigation urls and control the components.
###
define [], ->

  RouterModule = (facade) ->

    _ = facade._

    parseQueryParameter = (queryString)->
      params = {};
      if(queryString)
        _.each(
          _.map(decodeURI(queryString).split(/&/g),(el,i)->
            aux = el.split('=')
            o = {};
            if(aux.length >= 1)
              val = aux.slice(1, aux.length).join('=')
              o[aux[0]] = val;
            return o;
          ),
          (o)->
            _.extend(params,o);
        )
      return params;

    ApplicationRoutes = facade.navigation.Router.extend(
      queryParameters:{}
      routes:
        ':domain/applications/:id(/modules/:moduleId)(/technology/:technology)(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)(/home)(/)(?*queryString)':'home'
        ':domain/applications/:id(/modules/:moduleId)(/technology/:technology)(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)/qualityInvestigation(/:risk)(/:business)(/:technical)(/:rule)(/:componentId)(/:APDrillDown)(?*queryString)':'qualityInvestigation'
        ':domain/applications/:id(/modules/:moduleId)(/technology/:technology)(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)/componentsInvestigation(/:browserComponent)(/:isSearch)(/:rule)(/:ruleComponent)(?*queryString)':'componentsInvestigation'
        ':domain/applications/:id(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)(/search)(?*queryString)':'advanceSearch'
        ':domain/applications/:id(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)(/report)(?*queryString)':'reportGenerator'
        ':domain/applications/:id(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)/actionPlanOverView/:exclusions':'actionPlanOverview'
        '*others(?*queryString)':'applicationSelection'

      routeUtils:
        idPatterns: ['modules','snapshots','business','technology']

      initialize:(options)->
        facade.navigation.History.on('route:before', (router, page, parameters)=>
          return if parameters.length < 2
          if SELECTED_APPLICATION_HREF != parameters[0] + '/applications/' + parameters[1]
            facade.navigation.History.stop()
            window.location.reload(true);
          if page != 'advanceSearch' and page != 'reportGenerator'
            if parameters[4] and facade.context.get('snapshot').get('href') != SELECTED_APPLICATION_HREF + '/snapshots/' + parameters[4]
              facade.navigation.History.stop()
              window.location.reload(true);
          @persistPageState()
        )

      applicationSelection: ()->
        facade.bus.emit('require:application-selection')

      processModule:(domain, moduleId)->
        return unless moduleId?
        module = facade.context.get('modules').findWhere({href:domain + '/modules/' + moduleId})
        return unless module?
        facade.context.set('module', module)

      # Some navigation cases does not go through navigate; as designed filtering cannot work unless we store
      # the page state
      persistPageState:()->
        fragments = window.location.hash
        fragments = fragments.split('/').slice(3) # remove application id
        while @routeUtils.idPatterns.indexOf(fragments[0]) >=0
          fragments = fragments.slice(2) # remove pattern id
        @routeUtils.page = fragments.join('/')

      processQueryParameters :(queryString)->
        query = parseQueryParameter(queryString)
        oldQueryString = facade.base64.encode(JSON.stringify(@queryParameters))
        newQueryString = facade.base64.encode(JSON.stringify(query._p or {}))

        _.extend(@queryParameters, @queryParameters, JSON.parse(facade.base64.decode(query._p)))
        if oldQueryString != newQueryString and !_.isEmpty(@queryParameters)
          hash = window.location.hash.split('?')[0]
          @navigate(hash + '?_p=' + facade.base64.encode(JSON.stringify(@queryParameters)), {trigger: false, replace:true})

      home: (domain, id, moduleId, technologyId, snapshotId, filterBusinessCriterion, queryString)->
        @processQueryParameters(queryString)
        facade.bus.emit('show', {
          pageId:'home',
          route:'home',
          queryString:@queryParameters
          technology:technologyId
        })

      componentsInvestigation:(domain, id, moduleId, technologyId, snapshotId, filterBusinessCriterion = '60017', browserComponent, isSearch, rule, ruleComponent, queryString)->
        @processQueryParameters(queryString)
        facade.bus.emit('show', {
          pageId:'components-investigation',
          route:'componentsInvestigation',
          component:browserComponent,
          rule:rule,
          ruleComponent:ruleComponent,
          queryString:@queryParameters
          filterBusinessCriterion:filterBusinessCriterion
          technology:technologyId
          isSearch: isSearch
        })

      qualityInvestigation:(domain, id, moduleId, technologyId, snapshotId, filterBusinessCriterion = '60017', risk, business, technical, rule, componentId, APDrillDown, queryString)->
        @processQueryParameters(queryString)
        facade.bus.emit('show', {
          pageId:'quality-investigation' ,
          route:'qualityInvestigation',
          business:business,
          risk:risk,
          technical:technical,
          rule:rule,
          component:if componentId == "0" then null else componentId,
          moduleId:moduleId,
          snapshotId:snapshotId,
          queryString:@queryParameters
          filterBusinessCriterion:filterBusinessCriterion
          technology:technologyId,
          APDrillDown: APDrillDown
        })

      advanceSearch:(domain, id, snapshotId, filterBusinessCriterion = '60017', search, queryString) ->
        @processQueryParameters(queryString)
        facade.bus.emit('show', {
          pageId: 'advanceSearch',
          route: 'search',
          snapshotId:snapshotId,
          queryString:@queryParameters
          filterBusinessCriterion:filterBusinessCriterion
        })

      reportGenerator:(domain, id, snapshotId, filterBusinessCriterion = '60017', report, queryString) ->
        @processQueryParameters(queryString)
        facade.bus.emit('show', {
          pageId: 'reportGenerator',
          route: 'report',
          snapshotId:snapshotId,
          queryString:@queryParameters
          filterBusinessCriterion:filterBusinessCriterion
        })
    )

    module = {
      initialize: ->
        @router = new ApplicationRoutes()
        facade.bus.on('navigate', @navigate, this)
        facade.bus.on('filter',@updateFilters, @)
        facade.bus.on('update:url', @updateURL, this)
        facade.bus.on('add:route', @addRoute, @)

      postInitialize:(options)->
        facade.navigation.startNavigation()

      addRoute:(options)->
        @router.route(options.page, options.method)

      updateURL:(options) ->
        _.extend(@router.queryParameters, @router.queryParameters, options)
        for parameter of @router.queryParameters
          unless @router.queryParameters[parameter]
            delete @router.queryParameters[parameter]
        hash = null
        if @currentPage
          hash = '#' + SELECTED_APPLICATION_HREF + '/' + @currentPage
        else
          hash = window.location.hash.split('?')[0]
        if !_.isEmpty(@router.queryParameters)
          hash += '?_p=' + facade.base64.encode(JSON.stringify(@router.queryParameters))
        @router.processQueryParameters(hash)

      navigate: (options) ->
        page = options.page
        replace = if options.replace? then options.replace else false
        rootURL = '#' + SELECTED_APPLICATION_HREF
        module = facade.context.get('module')
        rootURL +=  '/modules/' + module.getId() if module?
        technology = facade.context.get('technologies').getSelected()
        rootURL +=  '/technology/' + encodeURIComponent(technology) if technology?
        snapshotId = facade.context.get('snapshot').getId()
        rootURL +=  '/snapshots/' + snapshotId
        businessFilter = facade.context.get('scope').get('businessCriterion')
        rootURL +=  '/business/' + businessFilter
        @router.navigate  rootURL + '/' + page,
          trigger: if options.updateViolationsType then false else true
          replace: replace

      updateFilters:(options)->
        parameterUpdated = false
        if options.module?
          currentModule = facade.context.get('module')
          if options.module == -1
            unless currentModule == null
              facade.context.set('module', null)
              parameterUpdated = true
          else
            unless currentModule?.get('href') == options.module
              facade.context.set('module', facade.context.get('modules').findWhere({href:options.module}))
              parameterUpdated = true
        if options.business
          previousBusiness = facade.context.get('scope').get('businessCriterion')
          unless previousBusiness == options.business
            facade.context.get('scope').set('businessCriterion', options.business)
            parameterUpdated = true
        if options.technology?
          technologies = facade.context.get('technologies')
          previousTechnology = technologies.getSelected()
          unless previousTechnology == options.technology
            technologies.pickTechnology(options.technology)
            newTechnology = technologies.getSelected()
            parameterUpdated = newTechnology != previousTechnology
        facade.bus.emit('filter:updated')
        @navigate({page:@router.routeUtils.page,replace:true}) if parameterUpdated
    }
    return module

  return RouterModule
