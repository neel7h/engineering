TopRiskiestTransactions = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  RiskiestComponentsView = backbone.View.extend({
    className:'riskiest-transactions-tile'
    template:Handlebars.compile('
      <div class="business-criteria icon-{{parameters.business}}">
        <h2>{{title}}</h2>
        <h3 class="">{{t "for"}}</h3><div id="business-selector" class="business-selector transactioncontentText"></div>
      </div>
      <div class="cloud-container" ></div>')
    transactionTooltipTemplate:Handlebars.compile('{{text}} {{t "has a transaction risk index of "}} {{formatNumber weight "0,000"}}')
    loadingTemplate:'<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'
    emptyTemplate:Handlebars.compile('<div class="empty-transactions-cloud" >{{t "No transactions available"}}</div>')

    initialize:(options)->
      @options = _.extend({},options)
      @business = @options.tile.get('parameters').business or "60013"
      @business = "60016" if facade.context.get('isSecurity')
      @nbRows = @options.tile.get('parameters').nbRows or 30
      filterHealthFactor = facade.portal.get('configuration').filterHealthFactor or false
      @businessCriteriaModels = facade.context.get('snapshot').createBusinessCriteriaConfiguration({
        filterHealthFactor:filterHealthFactor
      })
      @model = new facade.models.transactions.TransactionsListing([], {
        href:SELECTED_APPLICATION_HREF
        context:@business
        snapshotId:facade.context.get('snapshot').getId()
        nbRows:@nbRows
      })

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
      facade.bus.emit('navigate', {page:"transactionInvestigation/"+ @business + '/' +  model.get('id') + '/' + @business} )
      return false

    _dataRender:(business)->
      @model = new facade.models.transactions.TransactionsListing([], {
        href:SELECTED_APPLICATION_HREF
        context:business
        snapshotId:facade.context.get('snapshot').getId()
        nbRows:@nbRows
      })
      @model.getData({
        success:()=>
          localStorage.setItem(@persistentKey, business)
          @$el.find('.cloud-container').remove()
          @$el.append('<div class="cloud-container"></div>')
          $cc = @$el.find('.cloud-container')
          cloudData =  @model.asCloud().map((transaction)=>
            transaction.fullName = @transactionTooltipTemplate(transaction)
            return transaction
          )
          if cloudData.length == 0
            $cc.html(@emptyTemplate())
          else
            facade.advancedUI.cloud($cc,cloudData)
      })

    render:()->
      @$el.html(@template(_.extend({
          title:this.constructor.title
        }, @options.tile.toJSON())))
      @businessCriteriaModels.getData({
        success:()=>
          result = []
          whiteList = ['60013','60014','60016']
          @businessCriteriaModels.each((model)->
            return true if whiteList.indexOf(model.get('key')) < 0
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
          @$el?.find('#business-selector .cont .options').attr('data-before',t('Select business risk driver'))

          @businessCriteriaSelector.selectValue(@business)
      })
      @$el
  },{
    requiresLastSnapshot:false,
    title:t('Top riskiest transactions')
  })
  return RiskiestComponentsView
