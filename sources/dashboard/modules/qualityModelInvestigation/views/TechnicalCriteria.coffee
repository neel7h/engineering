TechnicalCriteriaView = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  numeral = facade.numeral
  _ = facade._
  t = facade.i18n.t

  backbone.View.extend({
    template: Handlebars.compile(' <div class="metric-page" id="technical-criteria">
        <div class="content-header">
          <h1>{{t "Technical Criteria"}}</h1>
        </div>
        <div class="content-actions">
          <a title="{{t "download all data as excel file"}}" class="download-file">{{t "Download Excel"}}</a>
        </div>
        <div id="table-holder" class="table-holder"></div>
       </div>')

    preTemplate:'<div class="loading"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    preRender:()->
      @rendered = false
      _.delay(()=>
        return if @rendered
        @$el.html(@preTemplate)
      , 500)

    events:
      'click .download-file':'downloadAsExcelFile'

    initialize: (options)->
      @options = _.extend({}, options)
      @options.business = facade.portal.getTQIifBCisFiltered(@options.business)
      facade.bus.on('global-filter-change:criticalsOnly', this.render, this)
      return unless @options.business?
      snapshot = facade.context.get('snapshot')
      lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds()
      module = facade.context.get('module')
      if module
        prevSnapshotModules = facade.context.get('modulesInPreviousSnapshot').pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(module.get('name'))
        lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds().splice('1') if isModuleAvailable < 0
      @model = new facade.models.TechnicalCriteriaResults({
        href:SELECTED_APPLICATION_HREF,
        businessCriterion:@options.business
        module:module
        technology:facade.context.get('technologies').getSelectedEncoded()
        snapshotId:snapshot.getId()
        lastTwoSnapshotIds: lastTwoSnapshotIds
      })

    downloadAsExcelFile:()->
      href = @downloadLinkUrl
      $.ajax('url': REST_URL + 'user', 'async': false)
        .success(()->
          window.location = href if href?
        )
      return false

    remove:()->
      facade.bus.off('global-filter-change:criticalsOnly', this.render)

    # FIXME remove update model (deprecated)
    updateModel:(parameters)->
      @updateViewState(parameters)

    updateRiskModel:(parameters)->
      snapshot = facade.context.get('snapshot')
      lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds()
      module = facade.context.get('module')
      if module
        prevSnapshotModules = facade.context.get('modulesInPreviousSnapshot').pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(module.get('name'))
        lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds().splice('1') if isModuleAvailable < 0

      @model = new facade.models.TechnicalCriteriaResults({
        href:SELECTED_APPLICATION_HREF
        businessCriterion:@options.business
        module:module
        technology:facade.context.get('technologies').getSelectedEncoded()
        snapshotId: snapshot.getId()
        lastTwoSnapshotIds: lastTwoSnapshotIds
      })
      @preRender()
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload technical criteria view', e)
      })

    updateViewState:(parameters)->
      # TODO update the way we handle module comparison
      sameModule = @model?.get('module')?.getId() == facade.context.get('module')?.getId()
      sameTechnology = @model?.get('technology') == facade.context.get('technologies').getSelectedEncoded()
      if sameModule and sameTechnology
        if @options.business == parameters.business and @options.risk == parameters.risk
          if @options.technical == parameters.technical
            return
          @options.technical = parameters.technical
          @table.select('technicalCriterion', @options.technical, true)
          return

      @options.business = parameters.business
      @options.risk = parameters.risk
      @options.technical = parameters.technical
      unless @options.business?
        @model = null
        return
      @updateRiskModel(parameters)
      return

    filterRows: (rows, risk) ->
      return rows if risk != 'risk'
      filteredResults = []
      for row in rows.models
        if(row.attributes.columns[0] or row.attributes.columns[1])
          filteredResults.push(row)
      rows.models = if filteredResults.length > 1 then filteredResults else []
      return rows

    render: ()->
      showCriticalsOnly = facade.portal.getFilterSetting('criticalsOnly')
      @rendered = true
      downloadLink = '#'
      if @model?._technicalCriteria?
        downloadLink = @model._technicalCriteria.exportUrl()
      @downloadLinkUrl = downloadLink
      @$el.html(@template())
      return @$el unless @model?
      data = @model?.asRows({
        selectCriterion:@options.technical
        criticalViolationsAsResults:showCriticalsOnly
      })
      t('All Rules...')
      data = @filterRows(data, @options.risk)
      gradeSortDirection = JSON.parse(localStorage.getItem('strength'))
      localStorage.removeItem('strength')
      if gradeSortDirection?
        data.comparator = (a,b)->
          return a.get("columns")[2] - b.get("columns")[2] if gradeSortDirection
          return b.get("columns")[2] - a.get("columns")[2]
          if Math.abs(a.get("columns")[0] - b.get("columns")[0]) < 0.01
            return -1 if a.get("columns")[2] < b.get("columns")[2]
            return 1

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
          {header: '<label>&#xe63a;</label>',title:t('Variation compares to previous snapshot'), align:'right nowrap', headerMin:'#xe63a;', length:3, sort:(a, b, increasing)->
            all = keepAllCRulesOnTop(a, b, increasing)
            return all if all?

            varA = a.columns[3]
            varB = b.columns[3]
            if increasing
              return 1 if isNaN(varA) and not isNaN(varB)
              return -1 if isNaN(varB) and not isNaN(varA)
            else
              return -1 if isNaN(varA) and not isNaN(varB)
              return 1 if isNaN(varB) and not isNaN(varA)
            return  varB - varA

          format:(value, group, row, model)->
            return facade.tableHelpers.formatVariation(value, model)
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
                if a.columns[4] < b.columns[4]
                  return 1
                if a.columns[4] > b.columns[4]
                  return -1
                return 0
          }
          {header:'<label>&#xe612;</label>', headerMin:'#xe612;',title:t('Weight'), align: 'right', length:3, sort:(a, b, increasing)->
            valA = a.columns[5]
            valB = b.columns[5]
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
              return b.columns[5] - a.columns[5]

          }
#          {header:'critical', format:(value)->
#            if value then 'yes' else 'no'
#          }
        ]
        selectOnClick:true
        click:true
        rows:data
      })
      @$el.find('#table-holder').html(@table.render())
      @$el.find('#table-holder').after("<div class='risk-table-message'><i>" + t('This displayed information is restricted to metrics with added and removed violations only linked to the Risk Introduced tile') + "</i></div>") if @options.risk == 'risk'
      @table.$el.addClass('contract compact')
      if !data.models.length
        critical = if showCriticalsOnly then t('No Technical Criteria found when filtering on critical violations') else t('No Technical Criteria found')
        @$el.find('.download-file').addClass('disabled')
        @$el.find('#table-holder').append('<div class="no-table-content">' + critical + '</div>')
      else
        @$el.find('#table-holder .no-table-content').remove()
      @table.on('row:clicked', @onTableSelection, @)
      setTimeout (->
        $(window).resize()
        ), 100
      @$el

    onTableSelection:(item)->
      return unless item?.extra?.technicalCriterion?
      facade.bus.emit('navigate', {page:"qualityInvestigation/#{@options.risk}/" + @options.business + "/" + item.extra.technicalCriterion})
  })
