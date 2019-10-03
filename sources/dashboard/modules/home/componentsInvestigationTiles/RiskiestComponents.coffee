RiskiestComponents = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  RISKIEST_COMPONENTS_BUSINESS = 'riskiest-components-business'

  RiskiestCompponentsPerHealthFactor = backbone.Collection.extend({
    url:()->
      indicator = @business or '60013'
      nbRows = @nbRows or 20
      REST_URL + facade.context.get('snapshot').get('href') + '/components/' + indicator + '?nbRows=' + nbRows

    initialize:(options)->
      @business = options.business
      @nbRows = options.nbRows

    toCloud:()->
      result = []
      for model in @models
        shortName = model.get('shortName')
        result.push({
          text:shortName
          weight:model.get('propagationRiskIndex')
          title:t('test')
          fullName: model.get('name')
        })
      result
  })

  RiskiestComponentsView = backbone.View.extend({
    className:'riskiest-components-tile'
    template:Handlebars.compile('
      <div class="business-criteria icon-{{parameters.business}}">
        <h2>{{title}}</h2>
        <h3 class="">{{t "for"}}</h3><div id="business-selector" class="business-selector"></div>
      </div>
      <div class="cloud-container" ></div>')
    loadingTemplate:'<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    initialize:(options)->
      @options = _.extend({},options)
      @business = @options.tile.get('parameters').business or '60013'
      @nbRows = @options.tile.get('parameters').nbRows
      filterHealthFactor = facade.portal.get('configuration').filterHealthFactor or false
      @businessCriteriaModels = facade.context.get('snapshot').createBusinessCriteriaConfiguration({
        filterHealthFactor:filterHealthFactor
      })
      @model = new RiskiestCompponentsPerHealthFactor({business:@business, nbRows:@nbRows})

    events:
      'widget:resize':'updateRendering'
      'mouseup span':'clicking'
      'mousedown':'mouseDown' # deactivate drag'n drop on tile when clicking span

    updateRendering:(event) ->
      $(window).trigger('resize')

    mouseDown:(event)->
      if 'SPAN' != event.target.nodeName
        @onSpan = false
        return true
      @onSpan = true
      return false

    clicking:(event)->
      return true if 'SPAN' != event.target.nodeName
      return true unless @onSpan
      @onSpan = false
      ids = event.target.id.split('_')
      index = parseInt(ids[ids.length-1])
      return false if isNaN(index)
      model = @model.at(index)
      treeNodes = new facade.models.componentBrowserTree.TreeNodes({href:model.get('treeNodes').href})
      treeNodes.getData({
        success:()->
          node = treeNodes.getFirstNodeId()
          facade.context.get('scope').set('businessCriterion',model.collection.business)
          if node == ''
            facade.bus.emit('navigate', {page:'componentsInvestigation'})
          else
            facade.bus.emit('navigate', {page:'componentsInvestigation/' + treeNodes.getFirstNodeId()})
      })
      return false

    _dataRender:(business)->
      @model = new RiskiestCompponentsPerHealthFactor({
        business:business
        nbRows:@nbRows
      })
      @model.getData({
        success:()=>
          localStorage.setItem(@persistentKey, business)
          @$el.find('.cloud-container').remove()
          @$el.append('<div class="cloud-container" ></div>')
          facade.advancedUI.cloud(@$el.find('.cloud-container'), @model.toCloud())
      })

    render:()->
      @$el.html(@template(_.extend({
          title:this.constructor.title
        }, @options.tile.toJSON())))
      @businessCriteriaModels.getData({
        success:()=>
          result = []
          @businessCriteriaModels.each((model)->
            return true if model.get('key') == '60017'
            result.push({
              label:model.get('name')
              value:model.get('key')
              selected: parseInt(model.get('key')) == parseInt(@business)
            })
          )
          @businessCriteriaSelector = new facade.bootstrap.Selector({name: '', data: result, class: 'left', maxCharacters:20});
          @businessCriteriaSelector.on('selection', (item)=>
            oldBusiness = @business
            @business = item
            if oldBusiness? and oldBusiness != @business
              @$el.find('.business-criteria').addClass('icon-'+@business).removeClass('icon-'+oldBusiness)
            @$el.find('.cloud-container').html(@loadingTemplate)
            @_dataRender(item)
            @options.tile.get('parameters').business = item
            @options.tile.collection.trigger('grid-update')
          )
          @$el.find('#business-selector').html(@businessCriteriaSelector.render())
          @$el?.find('#business-selector .cont .options').attr('data-before',t('Select health measure'))
          @businessCriteriaSelector.selectValue(@business)
      })
      @$el
  },{
    requiresLastSnapshot:true,
    title:t('Top riskiest components')
  })
  return RiskiestComponentsView
