###
  Defines the application main content -> Quality model investigation.
###
define [], ->

  QualityModule = (facade) ->

    backbone = facade.backbone
    t = facade.i18n.t

    ComponentModel = backbone.Model.extend({
      url:()->
        REST_URL + CENTRAL_DOMAIN + '/components/' + @params.component + '/snapshots/' + @params.snapshotId

      initialize:(options)->
        @params = options
    })

    BreadcrumbModel = backbone.Model.extend({
      sortMap:
        '':0
        'business-criteria':1
        'technical-criteria':2
        'quality-rules':3
        'quality-measures':3
        'quality-distributions':3

      initialize:(options)->
        @options = facade._.extend({},options)
        @qualitymodel = new facade.models.breadcrumb.QualityModelInformation(_.extend(options, {criteria:@get('criteria').slice(0,3)}))
        if 3 < @get('criteria').length
          @componentModel = new ComponentModel({component:@get('criteria')[3],snapshotId:facade.context.get('snapshot').getId()})
        facade.context.on('change',@updateUrlsWithFilters,@)

      updateUrlsWithFilters:()->
        @moduleId = facade.context.get('module')?.getId()
        # TODO missing implementation ?

      getAvailableTechnologies:()->
        return [] if 3 < @get('criteria').length
        return @qualitymodel.availableTechnologies()

      getAvailableModules:()->
        return [] if 3 < @get('criteria').length
        return @qualitymodel.availableModules()

      getData:(options)->
        return options.success.apply(this, arguments) if 0 == @get('criteria').length
        deferred = []
        deferred.push(@qualitymodel.fetch()) if @qualitymodel?
        deferred.push(@componentModel.fetch()) if @componentModel?
        if deferred.length > 0
          $.when.apply(this, deferred).then(() ->
            options.success()
          ,()->
            options.error?()
          )
        else
          options.success()

      getHref:(type)->
        snapshotId = facade.context.get('snapshot').getId()
        @moduleId = facade.context.get('module')?.getId()
        rootHREF = '#' + SELECTED_APPLICATION_HREF
        rootHREF += '/modules/' + @moduleId if @moduleId?
        rootHREF += '/snapshots/' + snapshotId
        rootHREF += '/business/' + @options.filterBusinessCriterion if @options.filterBusinessCriterion?
        rootHREF += '/qualityInvestigation/'+ @options.risk + '/'
        switch type
          when 'business-criteria' then rootHREF + @get('criteria')[0]
          when 'technical-criteria' then rootHREF + @get('criteria')[0] + '/' + @get('criteria')[1]
          when 'quality-rules' then rootHREF + @get('criteria')[0] + '/' + @get('criteria')[1] + '/' + @get('criteria')[2]
          when 'quality-measures' then rootHREF + @get('criteria')[0] + '/' + @get('criteria')[1] + '/' + @get('criteria')[2]
          when 'quality-distributions' then rootHREF + @get('criteria')[0] + '/' + @get('criteria')[1] + '/' + @get('criteria')[2]
          when 'object-violations' then rootHREF + @get('criteria')[0] + '/' + @get('criteria')[1] + '/' + @get('criteria')[2] + '/' + @get('criteria')[3]
          else rootHREF

      asBreadcrumb:()->
        results = []
        hasModule = @qualitymodel.hasModule()
        data = @qualitymodel.get('0')

        results = @qualitymodel.listResults()
        for result in results
          result.href = @getHref(result.type)
        if @componentModel?
          breadcrumb = {
            name: @componentModel.get('name')
            href: @getHref('object-violations')
          }
          results.push(breadcrumb)

        results.sort((item1, item2)=>
          @sortMap[item1.type] - @sortMap[item2.type]
        )
        results
    })

    Controller = Controller(facade)

    module = {
      initialize: (options) ->
        facade.bus.emit('menu:add-item',{
          "className": "quality-investigation",
          "text": t('Risk investigation'),
          "route": "qualityInvestigation/0"
        })
        controller = new Controller({el: options.el});
        facade.bus.on('show', controller.control, controller)
        facade.bus.on('show', @processBreadcrumb, @)

        facade.bus.emit('tile:register',{
          type:'NewViolationsForQualityRules'
          TileView:NewViolationsForQualityRules(facade)
        })
        facade.bus.emit('tile:register',{
          type:'Technologies'
          TileView: TechnologyTile(facade)
        })
        facade.bus.emit('tile:register',{
          type:'AddedViolations'
          TileView:AddedViolations(facade)
        })

      processBreadcrumb:(parameters)->
        switch parameters.pageId
          when 'quality-investigation'
            facade.bus.emit('header', {criticalFilter:'enable'})
            facade.bus.emit('theme', {theme:'quality-investigation'})
            business = facade.portal.getTQIifBCisFiltered(parameters.business)
            technical = parameters.technical
            rule = parameters.rule
            component = parameters.component
            criteria = []
            criteria.push(business) if business?
            criteria.push(technical) if technical?
            criteria.push(rule) if rule?
            criteria.push(component) if component? and 'none' != component

            module = facade.context.get('module')
            technology = facade.context.get('technologies').getSelected()

            # FIXME getHref everywhere, no getHREF
            breadCrumb = new BreadcrumbModel(_.extend({}, parameters, {
              module:module?.getHREF(),
              technology:technology,
              criteria:criteria,
              queryString:parameters.queryString
            }))
            breadCrumb.getData({
              success:()->
                facade.bus.emit('breadcrumb', {
                  path:breadCrumb.asBreadcrumb(),
                  pageId:parameters.pageId
                  activateModuleSelector:true,
                  availableModules:breadCrumb.getAvailableModules()
                  availableTechnologies:breadCrumb.getAvailableTechnologies()
                })

              error:()->
                console.error 'error', arguments
            })
          else return
      destroy: () ->
        @view.remove()
    }
    return module

  return QualityModule
