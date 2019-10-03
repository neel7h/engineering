TechnicalCriteriaView = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  numeral = facade.numeral
  _ = facade._
  t = facade.i18n.t

  backbone.View.extend({
    template: Handlebars.compile(' <div class="metric-page transaction-page" id="technical-criteria">
        <div class="content-header">
          <h1>{{t "Technical Criteria"}}</h1>
        </div>
        <div class="content-actions"></div>
        <div id="table-holder" class="table-holder"></div>
       </div>')

    preTemplate:'<div class="loading {{theme}}"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    preRender:()->
      @rendered = false
      _.delay(()=>
        return if @rendered
        @$el.html(@preTemplate)
        @$el.find('.loading').addClass(@options.theme)
      , 500)

    initialize: (options)->
      @options = _.extend({}, options)
      facade.bus.on('global-filter-change:criticalsOnly', this.render, this)
      return unless options.business?
      snapshot = facade.context.get('snapshot')
      @model = new facade.models.transactions.TransactionResultsForTechnicalCriteria([], {
        snapshotId:facade.context.get('snapshot').getId()
        transactionId:@options.transactionId
        businessCriterion:options.business
      })

    remove:()->
      facade.bus.off('global-filter-change:criticalsOnly', this.render)

    # FIXME remove update model (deprecated)
    updateModel:(parameters)->
      @updateViewState(parameters)

    updateViewState:(parameters)->
      if @options.transactionId == parameters.transactionId
        return if @options.business == parameters.business and @options.technical == parameters.technical
      @options.transactionId = parameters.transactionId
      @options.business = parameters.business
      @options.technical = parameters.technical
      unless @options.business?
        @model = null
        return
      snapshot = facade.context.get('snapshot')
      @model = new facade.models.transactions.TransactionResultsForTechnicalCriteria([], {
        snapshotId:facade.context.get('snapshot').getId()
        transactionId:@options.transactionId
        businessCriterion:@options.business
      })
      @preRender()
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload technical criteria view', e)
      })
      return

    render: ()->
      showCriticalsOnly = facade.portal.getFilterSetting('criticalsOnly')
      @rendered = true
      @$el.html(@template({}))
      return @$el unless @model?
      data = @model.asRows({
        selectCriterion:@options.technical
        criticalViolationsAsResults:showCriticalsOnly
      })

      gradeSortDirection = JSON.parse(localStorage.getItem('strength'))
      localStorage.removeItem('strength')
      if gradeSortDirection?
        data.comparator = (a,b)->
          if Math.abs(a.get("columns")[0] - b.get("columns")[0]) < 0.01
            return -1 if a.get("columns")[2] < b.get("columns")[2]
            return 1

          return a.get("columns")[0] - b.get("columns")[0] if gradeSortDirection
          return b.get("columns")[0] - a.get("columns")[0]
        data.sort()

      keepAllCRulesOnTop=(a, b, increasing)->
        if isNaN(a.extra.technicalCriterion)
          return -1 if increasing
          return 1
        if isNaN(b.extra.technicalCriterion)
          return 1 if increasing
          return -1

      # FIXME see what can be done to extract table configuration to an external configuration source (e.g. ced.json or other json)
      @table = new facade.bootstrap.Table({
        columns:[
          {header:if showCriticalsOnly then '<label>&#xe809;</label>' else '<label>&#xe618;</label>',
          headerMin:if showCriticalsOnly then '#xe809;' else '#xe618;',
          title:if showCriticalsOnly then t('Added Critical violations count') else t('Added violations count'),
          align:'critical-count-label new right', length:4, sort:(a, b, increasing)->
            all = keepAllCRulesOnTop(a, b, increasing)
            return all if all?
            valA = a.columns[0]
            valB = b.columns[0]
            return 0 if valA == valB
            if increasing
              return -1 if isNaN(valA)
              return 1 if isNaN(valB)
            else
              return 1 if isNaN(valA)
              return -1 if isNaN(valB)
            return valB - valA

          format:(value, group, row, model)->
            return '<span class="critical-count" title="'+value+'">'+value+'</span>' if value == 0 or  value == 'n/a'
            return '<span class="critical-count added" title="'+numeral(value).format('0,000')+'">+ '+numeral(value).format('0,000')+'</span>'
          }
          {header:if showCriticalsOnly then '<label>&#xe809;</label>' else '<label>&#xe618;</label>',
          headerMin:if showCriticalsOnly then '#xe809;' else '#xe618;',
          title:if showCriticalsOnly then t('Removed Critical violations count') else t('Removed violations count'),
          align:'critical-count-label fix right', length:4, sort:(a, b, increasing)->
            all = keepAllCRulesOnTop(a, b, increasing)
            return all if all?
            valA = a.columns[1]
            valB = b.columns[1]
            return 0 if valA == valB
            if increasing
              return -1 if isNaN(valA)
              return 1 if isNaN(valB)
            else
              return 1 if isNaN(valA)
              return -1 if isNaN(valB)
            return valB - valA

          format:(value, group, row, model)->
            return '<span class="critical-count" title="'+value+'">'+value+'</span>' if value == 0 or  value == 'n/a'
            return '<span class="critical-count removed" title="'+numeral(value).format('0,000')+'">- '+numeral(value).format('0,000')+'</span>'
          }
          {header:if showCriticalsOnly then '<label>&#xe809;</label>' else '<label>&#xe618;</label>',
          headerMin:if showCriticalsOnly then '#xe809;' else '#xe618;',
          title:if showCriticalsOnly then t('Critical violations count') else t('Violations count'),
          align:'right', length:4, sort:(a, b, increasing)->
            all = keepAllCRulesOnTop(a, b, increasing)
            return all if all?
            valA = a.columns[2]
            valB = b.columns[2]
            return 0 if valA == valB
            if increasing
              return -1 if isNaN(valA)
              return 1 if isNaN(valB)
            else
              return 1 if isNaN(valA)
              return -1 if isNaN(valB)
            return valB - valA
          format:(value, group, row, model)->
              return facade.tableHelpers.formatViolation(value,model)
          }
          {
            header:t('Technical criterion')
            title:t('Criteria Name')
            align: 'left'
            format:(value, group, row, model)->
              return facade.tableHelpers.formatTechnicalName(t(value), model)
            sort:(a, b, increasing)->
                all = keepAllCRulesOnTop(a, b, increasing)
                return all if all?
                if a.columns[3] < b.columns[3]
                  return 1
                if a.columns[3] > b.columns[3]
                  return -1
                return 0
          }
          {header:'<label>&#xe612;</label>', headerMin:'#xe612;',title:t('Weight'), align: 'right', length:3, sort:(a, b, increasing)->
            valA = a.columns[4]
            valB = b.columns[4]
            return 0 if valA == valB
            if increasing
              return 1 if isNaN(valA)
              return -1 if isNaN(valB)
            else
              return -1 if isNaN(valA)
              return 1 if isNaN(valB)
            return valB - valA
          format:(value, group, row, model)->
            return facade.tableHelpers.formatWeight(value, model)
          sort:(a, b, increasing)->
              all = keepAllCRulesOnTop(a, b, increasing)
              return all if all?
              return b.columns[4] - a.columns[4]
          }
        ]
        selectOnClick:true
        click:true
        rows:data
      })
      @$el.find('#table-holder').html(@table.render())
      @table.$el.addClass('contract compact')
      @table.on('row:clicked', @onTableSelection, @)
      setTimeout (->
          $(window).resize()
      ), 100
      @$el

    onTableSelection:(item)->
      return unless item?.extra?.technicalCriterion?
      facade.bus.emit('navigate', {page:"transactionInvestigation/"+ @options.context + '/' +  @options.transactionId + '/' + @options.business + '/' + item.extra.technicalCriterion} )
  })
