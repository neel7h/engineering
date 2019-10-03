###
  Defines the application main content -> Quality model investigation.
###
define [], ->

  TransactionModule = (facade) ->

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
        if @options.transactionId
          @transactionmodel = new facade.models.transactions.Transaction(options)
        if @options.business?
          criteria = []
          criteria.push( @options.business)
          criteria.push( @options.technical) if  @options.technical?
          criteria.push( @options.rule) if  @options.rule?
          criteria.push( @options.component) if  @options.component? and 'none' !=  @options.component
          @qualitymodel = new facade.models.breadcrumb.QualityModelInformation(_.extend(options, {
            criteria:criteria
          }))
        if @options.component?
          @componentModel = new ComponentModel(@options)

      getData:(options)->
        return options.success.apply(this, arguments) unless @transactionmodel?
        deferred = []
        deferred.push(@qualitymodel.fetch()) if @qualitymodel?
        deferred.push(@transactionmodel.fetch()) if @transactionmodel?
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
        rootHREF += '/transactionInvestigation/'
        rootHREF += + @options.context + '/' + @options.transactionId
        return rootHREF if 'transaction' == type
        rootHREF += '/' + @options.business
        return rootHREF if 'business-criteria' == type
        rootHREF += '/' + @options.technical
        return rootHREF if 'technical-criteria' == type
        rootHREF += '/' + @options.rule
        return rootHREF if ['quality-rules','quality-measures','quality-distributions'].indexOf(type) >= 0
        rootHREF += '/' + @options.component
        return rootHREF

      asBreadcrumb:()->
        results = []
        if @transactionmodel?
          results.push({
            name:@transactionmodel.get('name')
            href:@getHref('transaction')
          })
        if @qualitymodel?
          qualityResults = @qualitymodel.listResults().sort((a,b)->
            return -1 if a.type == 'business-criteria'
            return 1 if b.type == 'business-criteria'
            return -1 if a.type == 'technical-criteria'
            return 1 if b.type == 'technical-criteria'
            return 0
          )
          for result in qualityResults
            results.push({
              href: @getHref(result.type)
              name: result.name
              shortName: result.shortName
            })
        if @componentModel?
          results.push({
            name: @componentModel.get('name')
            href: @getHref('object-violations')
          })
        results.sort((item1, item2)=>
          @sortMap[item1.type] - @sortMap[item2.type]
        )
        results
    })

    Controller = Controller(facade)

    ExtendedRoute = facade.navigation.Router.extend(
      routes:
        ':domain/applications/:id(/modules/:moduleId)(/technology/:technology)(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)/transactionInvestigation(/:context)(/:transactionId)(/:business)(/:technical)(/:rule)(/:component)(?*queryString)':'transactionInvestigation'

      transactionInvestigation: (domain, id, moduleId, technologyId, snapshotId, filterBusinessCriterion = '60017', context = '60013',transactionId, business, technical, rule, component, queryString)->

        facade.bus.emit('show', {
          pageId:'transaction-investigation' ,
          route:'transactionInvestigation',
          business:business,
          technical:technical,
          rule:rule,
          context:context
          transactionId:transactionId
          component:component,
          moduleId:moduleId,
          snapshotId:snapshotId,
          filterBusinessCriterion:filterBusinessCriterion
          technology:technologyId
          queryString:queryString
        })
    )

    module = {
      initialize: (options) ->
        facade.bus.emit('menu:add-item',{
          "className": "transaction-investigation",
          "text": t('Transaction investigation'),
          "route": "transactionInvestigation"
        })
        controller = new Controller({el: options.el});
        facade.bus.on('show', controller.control, controller)
        facade.bus.on('show', @processBreadcrumb, @)
        #
        facade.bus.emit('tile:register',{
          type:'TopRiskiestTransactions'
          TileView:TopRiskiestTransactions(facade)
        })
      postInitialize:(options)->
        router = new ExtendedRoute() # in the post initialize to make sure *other route still comes last

      processBreadcrumb:(parameters)->
        switch parameters.pageId
          when 'transaction-investigation'
            facade.bus.emit('theme', {theme:'transaction-investigation'})
            breadCrumb = new BreadcrumbModel(_.extend({}, parameters))
            breadCrumb.getData({
              success:()->
                facade.bus.emit('header',{criticalFilter:'enable'})
                facade.bus.emit('breadcrumb', {
                  path:breadCrumb.asBreadcrumb(),
                  pageId:parameters.pageId

                })

              error:()->
                console.error 'error', arguments
            })
          else return
      destroy: () ->
        @view.remove()
    }
    return module

  return TransactionModule
