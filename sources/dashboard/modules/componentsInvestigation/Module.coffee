###
  Defines the application main content -> Quality model investigation.
###
define [], ->

  QualityModule = (facade) ->
    t = facade.i18n.t
    Handlebars = facade.Handlebars

    # FIXME extract BreadcrumbModel to another file like Controller for enhanced readability and code exploration
    BreadcrumbModel = facade.backbone.Model.extend({

      initialize:(options)->
        @options = facade._.extend({},options)
        snapshotId = facade.context.get('snapshot').getId()
        if options.component?
          @componentModel = new facade.backbone.Model()
          @componentModel.url = REST_URL + CENTRAL_DOMAIN + '/tree-nodes/' + options.component +
              '/snapshots/' + snapshotId
        if options.rule?
          @ruleModel = new facade.backbone.Model()
          @ruleModel.url =  REST_URL + CENTRAL_DOMAIN + '/quality-indicators/' + @options.rule + '/snapshots/' + snapshotId
        if options.ruleComponent? and 'none' != options.ruleComponent
          @ruleComponentModel = new facade.backbone.Model()
          @ruleComponentModel.url = REST_URL + CENTRAL_DOMAIN + '/components/' + @options.ruleComponent + '/snapshots/' + snapshotId

      getData:(options)->
        deferred = []
        deferred.push(@componentModel.fetch()) if @componentModel?
        deferred.push(@ruleModel.fetch()) if @ruleModel?
        deferred.push(@ruleComponentModel.fetch()) if @ruleComponentModel?
        if deferred.length > 0
          $.when.apply(this, deferred).then(() ->
            options.success()
          ,()->
            options.error?()
          )
        else
          options.success()

      getAvailableHealthFactors:()->
        result = []
        aggregators = @ruleModel?.get('gradeAggregators')
        if aggregators?
          for aggregator in aggregators
            _aggregators = aggregator.gradeAggregators if aggregator.gradeAggregators?.length != 0 # from technical to business
            for _aggregator in _aggregators
              result.push(_aggregator.key) if result.indexOf(_aggregator.key) == -1
        return result


      getHrefRoot:()->
        snapshotId = facade.context.get('snapshot').getId()
        @moduleId = facade.context.get('module')?.getId()
        rootHREF = '#' + SELECTED_APPLICATION_HREF
        rootHREF += '/modules/' + @moduleId if @moduleId?
        rootHREF += '/snapshots/' + snapshotId
        rootHREF += '/business/' + @options.filterBusinessCriterion if @options.filterBusinessCriterion?
        rootHREF += '/componentsInvestigation/'

      asBreadcrumb:()->
        results = []
        if @options.component?
          breadcrumb = {
            name:@componentModel.get('name')
            type:''
            href: @getHrefRoot() + @options.component  + '/0'       }
          results.push(breadcrumb)
        if @options.rule?
          breadcrumb = {
            name:@ruleModel.get('name')
            type:''
            href:@getHrefRoot() + @options.component + '/0/' + @options.rule}
          results.push(breadcrumb)
        if @options.ruleComponent? and 'none' != @options.ruleComponent
          breadcrumb = {
            name:@ruleComponentModel.get('name')
            type:''
            href:@getHrefRoot() + @options.component + '/0/' + @options.rule +  '/' + @options.ruleComponent}
          results.push(breadcrumb)

        results
    })


    Controller = Controller(facade)

    UnavailableView = facade.backbone.View.extend({
      template: Handlebars.compile('<div class="investigation-not-available">
          <h1>{{t "Content not available in past snapshot"}}</h1>
          <p>{{t "Investigation through the modules and objects is not available on this snapshot."}}</p>
          <p>{{t "You may only be able to investigate this data in the latest snapshot."}}</p>
        </div>')
      render:()->
        @$el.html(@template)
    })

    module = {
      initialize: (options) ->
        facade.bus.emit('menu:add-item',{
          "className": "component-investigation",
          "text": t('Application investigation'),
          "route": 'componentsInvestigation'
        })
        if facade.context.get('snapshot').isLatest()
          @initializeInRegularCase(options)
        else
          @initializeOnPastSnapshots(options)
        facade.bus.emit('tile:register',{
          type:'TopCriticalModules'
          TileView:TopCriticalModules(facade)
        })

      initializeInRegularCase:(options)->
        controller = new Controller({el: options.el, hasSelectedObjectInfo:true});
        facade.bus.on('component-selection', controller.selectComponent, controller)
        facade.bus.on('show', controller.control, controller)
        facade.bus.on('show', @processBreadcrumb, @)

      initializeOnPastSnapshots:(options)->
        facade.bus.on('show', (parameters)->
          if 'components-investigation' == parameters.pageId
            view = new UnavailableView({el:options.el});
            view.render();
            facade.bus.emit('theme', {theme:'components-investigation'})
            facade.bus.emit('header', {criticalFilter:'enable'})
            facade.bus.emit('breadcrumb', {
              path:[{name: t('not available for selected snapshot'),type:'',href: '#' + SELECTED_APPLICATION_HREF + '/snapshots/' + facade.context.get('snapshot').getId()}],
              pageId:parameters.pageId
            })
        , this)

      processBreadcrumb:(parameters)->
        if 'components-investigation' == parameters.pageId
          facade.bus.emit('header', {criticalFilter:'enable'})
          facade.bus.emit('theme', {theme:'components-investigation'})
          breadCrumb = new BreadcrumbModel(parameters)
          breadCrumb.getData({
            success:()->
              facade.bus.emit('breadcrumb', {
                path:breadCrumb.asBreadcrumb(),
                activateBusinessCriteriaSelector:true
                pageId:parameters.pageId
                availableHealthFactors:breadCrumb.getAvailableHealthFactors()
              })
          })

      destroy: () ->
        @view.remove()
    }
    return module

  return QualityModule
