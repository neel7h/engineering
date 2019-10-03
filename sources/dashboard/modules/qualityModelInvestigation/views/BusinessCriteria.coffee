BusinessCriteriaView = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  numeral = facade.numeral
  t = facade.i18n.t

  ###
    Business Criteria view provides a listing of the business criteria.
    Note that the business criteria are filtered to display only health-factors.
  ###
  backbone.View.extend({
    template: Handlebars.compile(' <div class="metric-page" id="business-criteria">
          <div class="content-header">
            <h1>{{t "Health Measures"}}</h1>
          </div>
          <div class="content-actions">
            <a title="{{t "download all data as excel file"}}" class="download-file">{{t "Download Excel"}}</a>
          </div>
          <div id="table-holder" class="table-holder"></div>
          {{#if hasContent}}
          <div id="doc-60017" class="description"><h2>{{t "Total Quality index"}}</h2><p>{{{t "Total Quality index measures the global structural quality level of the application based on all existing technical criteria that are based on our 5 health measures. Sometimes rules are linked to multiple technical criteria so that sum of critical violations of TQI is not the same than the sum of critical violations for all health measure."}}}</p></div>
          <div id="doc-60013" class="description"><h2>{{t "Robustness"}}</h2><p>{{{t "Robustness is focusing on engineering flaws and practices that can have an impact on the runtime stability of the application."}}}</p></div>
          <div id="doc-60014" class="description"><h2>{{t "Efficiency"}}</h2><p>{{{t "Efficiency is focusing on potential bottlenecks and potential future scalability issues linked to coding practices."}}}</p></div>
          <div id="doc-60016" class="description"><h2>{{t "Security"}}</h2><p>{{{t "Security measures the risk of potential security breaches due to poor coding and architectural practices."}}}</p></div>
          <div id="doc-60012" class="description"><h2>{{t "Changeability"}}</h2><p>{{{t "Changeability is highlighting difficulties to modified in order to implement new features, correct errors or change the application environment."}}}</p></div>
          <div id="doc-60011" class="description"><h2>{{t "Transferability"}}</h2><p>{{{t "Transferability  is about difficulties to move across teams, lock in to specific resources."}}}</p></div>
          {{/if}}
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
      @businessCriteria = "60017"
      @businessCriteria = "60016" if facade.context.get('isSecurity')
      @options.business = facade.portal.getTQIifBCisFiltered(@options.business)
      @filterHealthFactor = facade.portal.filterHealthFactors()
      snapshot = facade.context.get('snapshot')
      module = facade.context.get('module')
      lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds()
      if module
        prevSnapshotModules = facade.context.get('modulesInPreviousSnapshot').pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(module.get('name'))
        lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds().splice('1') if isModuleAvailable < 0

      @model = new facade.models.BusinessCriteriaResults({
        href:SELECTED_APPLICATION_HREF
        module:module
        technology:facade.context.get('technologies').getSelectedEncoded()
        snapshotId: snapshot.getId()
        lastTwoSnapshotIds: lastTwoSnapshotIds
      })
      facade.bus.on('global-filter-change:criticalsOnly', this.render,this)

    downloadAsExcelFile:()->
      href = @downloadLinkUrl
      $.ajax('url': REST_URL + 'user', 'async': false)
        .success(()->
          window.location = href if href?
        )
      return false

    remove:()->
      facade.bus.off('global-filter-change:criticalsOnly', this.render)

    # TODO remove once controller v3.0 is done
    updateModel:(parameters)->
      @updateViewState(parameters)

    updateRiskModel :(parameters)->
      lastTwoSnapshotIds = facade.context.get('snapshot').getLastTwoSnapshotIds()
      if facade.context.get('module')
        prevSnapshotModules = facade.context.get('modulesInPreviousSnapshot').pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(facade.context.get('module').get('name'))
        lastTwoSnapshotIds = facade.context.get('snapshot').getLastTwoSnapshotIds().splice('1')if isModuleAvailable < 0
      snapshot = facade.context.get('snapshot')
      @model = new facade.models.BusinessCriteriaResults({
        href:SELECTED_APPLICATION_HREF
        module:facade.context.get('module')
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
      sameModule = @model.get('module')?.getId() == facade.context.get('module')?.getId()
      sameTechnology = @model.get('technology') == facade.context.get('technologies').getSelectedEncoded()
      if sameModule and sameTechnology
        return if parameters.business? and @options.business == parameters.business and @options.risk == parameters.risk
        @options.business = parameters.business
        @options.risk = parameters.risk
        @table?.select('businessCriterion', @options.business, true)
        if !parameters.inZoom
          @updateRiskModel(parameters)
      else
        @updateRiskModel(parameters)
      return

    notify:()->
      if @options.business?
        unless @model.isAvailable(@options.business, @filterHealthFactor)
          facade.bus.emit('navigate', {page:"qualityInvestigation/#{@options.risk}/#{@businessCriteria}"})
      if !@options.business? and !@options.inZoom
        facade.bus.emit('navigate', {page:"qualityInvestigation/#{@options.risk}/"+@model.getCriterionWithHigherCriticalViolations(@filterHealthFactor), replace:true} )

    configureTableColumns:(showCriticalsOnly)->
      columns = [
        {
          header:if showCriticalsOnly then '<label>&#xe809;</label>' else '<label>&#xe618;</label>',
          headerMin:if showCriticalsOnly then '#xe809;' else '#xe618;',
          title:if showCriticalsOnly then t('Added Critical violations count') else t('Added violations count'),
          align:'critical-count-label new right', length:4,
          format:(value, group, row, model)->
            return '<span class="critical-count" title="'+value+'">'+value+'</span>' if value == 0 or value == 'n/a'
            return '<span class="critical-count added" title="'+numeral(value).format('0,000')+'">+ '+numeral(value).format('0,000')+'</span>'
        }
        {
          header:if showCriticalsOnly then '<label>&#xe809;</label>' else '<label>&#xe618;</label>',
          headerMin:if showCriticalsOnly then '#xe809;' else '#xe618;',
          title:if showCriticalsOnly then t('Removed Critical violations count') else t('Removed violations count'),
          align:'critical-count-label fix right', length:4,
          format:(value, group, row, model)->
            return '<span class="critical-count" title="'+value+'">'+value+'</span>' if value == 0 or value == 'n/a'
            return '<span class="critical-count removed" title="'+numeral(value).format('0,000')+'">- '+numeral(value).format('0,000')+'</span>'
        }
        {
          header:if showCriticalsOnly then '<label>&#xe809;</label>' else '<label>&#xe618;</label>',
          headerMin:if showCriticalsOnly then '#xe809;' else '#xe618;',
          title:if showCriticalsOnly then t('Critical violations count') else t('Violations count'),
          align:'right', length:4,
          format:(value, group, row, model)->
            return facade.tableHelpers.formatViolation(value,model)
        }
        {
          header:'<label>&#xe63a;</label>', title:t('Variation compares to previous snapshot'), align:'right nowrap',headerMin:'#xe63a;', length:4,
          format:(value, group, row, model)->
            return facade.tableHelpers.formatVariation(value,model)
        }
        # {
        #   header:t('baseline'), labelIcon:'#xe63b;', title:t('Variation compares to first snapshot'), align:'right nowrap',headerMin:'#xe63b;',length:4,
        #   format:(value, group, row, model)->
        #     return facade.tableHelpers.formatVariation(value,model)
        # }
        {
          header: t('Health measure')
          title:t('Criteria Name')
          align:'left'
          format:(value, group, row, model)->
            return facade.tableHelpers.formatName(value,model)
        }
      ]
      return columns

    filterRows: (rows, risk) ->
      return rows if risk != 'risk'
      filteredResults = []
      for row in rows.models
        if(row.attributes.columns[0] or row.attributes.columns[1])
          filteredResults.push(row)
      rows.models = filteredResults
      return rows

    render: ()->
      showCriticalsOnly = facade.portal.getFilterSetting('criticalsOnly')
      @rendered = true
      @downloadLinkUrl = @model.downloadUrl(@filterHealthFactor)
      rows = @model?.asRows({
        selectCriterion: @options.business
        filter:@filterHealthFactor
        criticalViolationsAsResults:showCriticalsOnly
      })
      @table = new facade.bootstrap.Table({
        columns:@configureTableColumns(showCriticalsOnly),
        selectOnClick:true
        click:(item)=>
          @onTableSelection(item)
        rows: @filterRows(rows, @options.risk)
      })
      @$el.html(@template({
        isHealthFactors:@filterHealthFactor
        hasContent: rows.models.length
#        applicationName:facade.context.get('application').get('name')
      }))
      @$el.find('#table-holder').html(@table.render())
      @$el.find('#table-holder').after("<div class='risk-table-message'><i>" + t('This displayed information is restricted to metrics with added and removed violations only linked to the Risk Introduced tile') + "</i></div>") if @options.risk == 'risk'
      @table.$el.addClass('contract compact')
      @notify()
      if !rows.models.length
        critical = if showCriticalsOnly then t('No Health Measure found when filtering on critical violations') else t('No Health Measure found')
        @$el.find('.download-file').addClass('disabled')
        @$el.find('#table-holder .description').css('display', 'none')
        @$el.find('#table-holder').append('<div class="no-table-content">' + critical + '</div>')
      else
        @$el.find('#table-holder .no-table-content').remove()
      setTimeout (->
        $(window).resize()
        ), 100
      selectedBusiness = @options.business
      selectedBusinessExist = _.find(rows.models,(model)-> return true if model.get('extra').businessCriterion == selectedBusiness)
      if !selectedBusinessExist
        facade.bus.emit('navigate', {page:"qualityInvestigation/#{@options.risk}/"+@model.getCriterionWithHigherCriticalViolations(@filterHealthFactor), replace:true} )
      @updateDocumentation(@options.business)
      @$el

    updateDocumentation:(business)->
      @$el.find('.description').hide()
      @$el.find('#doc-' + business).show()

    onTableSelection:(item)->
      return unless item?.extra?.businessCriterion?
      return if item.extra.businessCriterion == @options.business
      @updateDocumentation(item.extra.businessCriterion)
      facade.bus.emit('navigate', {page:"qualityInvestigation/#{@options.risk}/" +item.extra.businessCriterion} )

  })
