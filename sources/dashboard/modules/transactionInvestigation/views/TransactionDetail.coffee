TransactionView = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  numeral = facade.numeral
  t = facade.i18n.t

  _objectNameTemplate = Handlebars.compile('<span>
    <em class="short-content" title="{{shortValue}} ({{value}})">{{ellipsisMiddle value 15 35}}</em>
    <em class="large-content" title="{{shortValue}} ({{value}})">{{ellipsisMiddle value 25 45}}</em>
    <em class="super-large-content" title="{{shortValue}} ({{value}})">{{value}}</em>
  </span>')

  ###

  ###
  backbone.View.extend({
    template: Handlebars.compile(' <div class="metric-page transaction-page" id="transaction-investigation">
          <div class="content-header">
            <h1>{{t "Transactions"}}</h1>

            <div id="business-selector" class="business-selector"><p>{{t "as business risk driver"}}</p></div>

          </div>
          <div class="content-actions">
            <div class="array-filter" id="filter"><input type="text" placeholder="{{t "Filter in loaded list"}}"/></div>
            <!--<a target="_blank" href="{{downloadLink}}" title="{{t "download all data as excel file"}}" class="download-file">{{t "Download Excel"}}</a>-->
          </div>
          <div id="table-holder" class="table-holder with-risk-factors">
            {{#unless hasContent}}<p class="no-content">{{t "No transactions available for the selected application."}}</p>{{/unless}}
          </div>
          {{#if showMore}}<button class="show-more">{{t "Show More"}}</button>{{/if}}
    </div>')
    preTemplate:'<div class="loading {{theme}}"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    events:{
      'input input':'onFilterChange'
      'click .risk-factors button':'updateRiskFactor'
      'click .show-more': 'showMore'
    }

    showMore: (event, done)->
      @options.startRow = @options.startRow + @options.nbRows
      @model.startRow = @options.startRow
      @model.getData({
        success: ()=>
          return unless @table?
          @table.$el.detach()
          @table.update({
            rows:@model.asRows({
              nbRows: @options.startRow + @options.nbRows
              transactionId: @options.transactionId
            }),
            resetRowSelector:false
          })
          @$el.find('#table-holder').append(@table.render())
          @table.delegateEvents()
          if this.model.hasMore
            done?.apply(this, arguments)
          else
            @$el.find('.show-more').hide()
          @onFilterChange()
      })

    showMoreUntilObjectIsAvailable:()->
      return unless @options.transactionId?
      model = @model.findWhere({id:@options.transactionId})
      if model?
          @scrollIfRequired(model)
      else
        @showMore(null, @showMoreUntilObjectIsAvailable)

    scrollIfRequired:()->
      setTimeout(()=>
        $tr = this.$el.find('table tbody tr[data-id="' + @options.transactionId + '"]')
        @$el.scrollTop($tr.position().top)
        this.trigger('scroll', $tr.position().top)
      , 500)

    updateRiskFactor:(event)->
      return if event.target.className.split(' ').indexOf('active')>=0
      facade.bus.emit('navigate', {page:"transactionInvestigation/"+event.target.id} )

    onFilterChange:()->
      # TODO add clean handling via model, only get the changes to update to avoid extra show/hide cost
      filter = @$el.find('#filter input').val().toLocaleLowerCase()
      visible = 0
      this.$el.find('table tbody tr').each((index, item)->
        if (item.children[0].innerText.toLocaleLowerCase().indexOf(filter) >= 0)
          visible++
          $(item).show()
        else $(item).hide()
      )
      @$el.find('.no-table-content').remove()
      if 0 == visible and filter.length > 0
        @$el.find('.table-holder').append('<div class="no-table-content">' + t('No Transactions found for current filter') + '</div>')

    preRender:()->
      @rendered = false
      _.delay(()=>
        return if @rendered
        @$el.find('#table-holder').html(@preTemplate)
        # @$el.html(@preTemplate)
      , 500)

    initialize: (options)->
      @options = _.extend({
        context:60017
        nbRows: 50
        startRow:1
      }, options)
      if facade.context.get('isSecurity')
        @isSecurity = true
        @options.context = 60016
      filterHealthFactor = facade.portal.get('configuration').filterHealthFactor or false
      @businessCriteriaModels = facade.context.get('snapshot').createBusinessCriteriaConfiguration({
        filterHealthFactor:filterHealthFactor
      })
      @model = new facade.models.transactions.TransactionsListing([],{
        href:SELECTED_APPLICATION_HREF
        module:facade.context.get('module') # useless as not available from API ?
        snapshotId: facade.context.get('snapshot').getId()
        context:@options.context
        nbRows:@options.nbRows
      })

    updateModel:(parameters)->
      @updateViewState(parameters)

    updateViewState:(parameters)->
      if parameters.context == @options.context
        if @options.transactionId == parameters.transactionId
          return
      @options.context = parameters.context if !@isSecurity
      @businessCriteriaSelector?.selectValue(@options.context)
      @options.transactionId = parameters.transactionId
      @options.startRow = 1
      @model = new facade.models.transactions.TransactionsListing([],{
        href:SELECTED_APPLICATION_HREF
        snapshotId: facade.context.get('snapshot').getId()
        context:@options.context
        nbRows:@options.nbRows
        startRow:@options.startRow
      })
      @preRender()
      @model.getData({
        success:()=>
          @renderTable()
        error:(e)->
          console.error('failed trying to reload transaction view', e)
      })
      return

    notify:()->
      return if @options.transactionId
      # console.log("transactionInvestigation/"+ @options.context + '/' +  @model.at(0).get('id'))
      facade.bus.emit('navigate', {page:"transactionInvestigation/"+ @options.context + '/' +  @model.at(0).get('id') } )

    configureTableColumns:()->
      triFormat = Handlebars.compile('<span title="Transaction Risk Index: {{formatNumber this "0,000"}}">{{formatNumber this "0,000"}}</span>')
      triTqiFormat = '<span title="Transaction Risk Index is not available">None</span>'
      columns = [
        {
          header: t('Transaction name')
          title:t('Transaction full name')
          align:'left'
          format:(value, columnId, rowId, item)->
            return _objectNameTemplate({value:value, shortValue:item.extra.shortName})
        },
        {
          header: t('Risk level')
          title:t('Transaction Risk Index')
          align:'left length-1'
          format:(value, group, row, model)->
            return ('none') if isNaN(value) or value < 0
            max = model.extra.maxRisk
            length = parseInt(value / max * 100)
            length = Math.max(1, length) if value > 0
            bar = '<div class="bar " title="' + facade.numeral(value).format('0,000') + '"><div class="weight object-pri" style="width:' + length + '%">' + facade.numeral(value).format('0,000') + '</div></div>'
            return bar
        }
      ]
      return columns


    render: ()->
      @$el.html(@template({
        hasContent:this.model.length > 0
        showMore:this.model.hasMore
      }))
      context = @options.context
      @businessCriteriaModels.getData({
        success:()=>
          result = []
          whiteList = ['60013','60014','60016']
          @businessCriteriaModels.each((model)->
            return true if whiteList.indexOf(model.get('key')) < 0
            result.push({
              label:model.get('name')
              value:model.get('key')
              selected: parseInt(model.get('key')) == parseInt(context)
            })
          )
          result[result.length] = {
            label:t('none')
            value:'60017'
            selected: 60017 == parseInt(context)
          }
          @businessCriteriaSelector = new facade.bootstrap.Selector({name: '', data: result, class: 'left', maxCharacters:20});
          @businessCriteriaSelector.on('selection', (item)=>
            @$el.find('#filter input').val("")
            @$el.find('.no-table-content').remove()
            return if @options.context == item
            facade.bus.emit('navigate', {page:"transactionInvestigation/"+item})
          )
          @businessCriteriaSelector.options.data.splice(1,1) if @isSecurity
          @$el.find('#business-selector').prepend(@businessCriteriaSelector.render())
          @$el?.find('#business-selector .cont .options').attr('data-before',t('Select business risk driver'))
          # @businessCriteriaSelector.selectValue(@options.context)
      })
      @renderTable()
      @$el

    renderTable:()->
      @rendered = true
      if @model.length == 0
        @$el.find('#table-holder .table').remove()
        @$el.find('#table-holder:first').addClass('no-content').text("No transactions available for the selected application.")
        @$el.find('.show-more').hide()
        @$el.find('#filter input[type="text"]').hide()
        return

      @$el.find('#filter input[type="text"]').show()
      @table = new facade.bootstrap.Table({
        columns:@configureTableColumns(),
        selectOnClick:true
        click:(item)=>
          @onTableSelection(item)
        rows:@model.asRows({transactionId:@options.transactionId})
      })
      @$el.find('#table-holder').html(@table.render())
      @table.$el.addClass('contract compact')
      @$el.find('.show-more').show() if this.model.hasMore
      @showMoreUntilObjectIsAvailable()
      @notify()
      setTimeout (->
        $(window).resize()
      ), 100


    onTableSelection:(item)->
      return if item.extra.transaction == @options.transactionId
      @options.transactionId = item.extra.transaction
      facade.bus.emit('navigate', {page:"transactionInvestigation/"+ @options.context + '/' +  item.id } )

  })
