BusinessCriteriaView = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  numeral = facade.numeral
  t = facade.i18n.t

  ###
    Business Criteria view provides a listing of the business criteria.
    Note that the business criteria are filtered to display only health-factors.
  ###
  QualityIndicatorsView = backbone.View.extend({
    template: Handlebars.compile(' <div class="metric-page transaction-page" id="business-criteria">
          <div class="content-header">
            <h1>{{t "Health Measures"}}</h1>
          </div>
          <div class="content-actions">
            <!--<a target="_blank" href="{{downloadLink}}" title="{{t "download all data as excel file"}}" class="download-file">{{t "Download Excel"}}</a>-->
          </div>
          <div id="table-holder" class="table-holder">
            {{#unless hasContent}}<p class="no-content">{{t "No Data Available for selected transaction in current snapshot."}}</p>{{/unless}}
          </div>
          <div class="filter-description">{{#if hasContent}}<p>{{t "Critical violation filter is currently activated. As Transaction Risk index is based on all violations identification, if you want to get full violation visibility, update the global filter in the header to all violations."}}</p>{{/if}}</div>
          <div id="doc-60017" class="description"><h2>{{t "Total Quality index"}}</h2><p>{{{t "Total Quality index measures the global structural quality level of the application based on all existing technical criteria that are based on our 5 health measures. Sometimes rules are linked to multiple technical criteria so that sum of critical violations of TQI is not the same than the sum of critical violations for all health measure."}}}</p></div>
          <div id="doc-60013" class="description"><h2>{{t "Robustness"}}</h2><p>{{{t "Robustness is focusing on engineering flaws and practices that can have an impact on the runtime stability of the application."}}}</p></div>
          <div id="doc-60014" class="description"><h2>{{t "Efficiency"}}</h2><p>{{{t "Efficiency is focusing on potential bottlenecks and potential future scalability issues linked to coding practices."}}}</p></div>
          <div id="doc-60016" class="description"><h2>{{t "Security"}}</h2><p>{{{t "Security measures the risk of potential security breaches due to poor coding and architectural practices."}}}</p></div>
          <div id="doc-60012" class="description"><h2>{{t "Changeability"}}</h2><p>{{{t "Changeability is highlighting difficulties to modified in order to implement new features, correct errors or change the application environment."}}}</p></div>
          <div id="doc-60011" class="description"><h2>{{t "Transferability"}}</h2><p>{{{t "Transferability  is about difficulties to move across teams, lock in to specific resources."}}}</p></div>
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
      @filterHealthFactor  = facade.portal.get('configuration')?.filterHealthFactor
      @filterHealthFactor = true unless @filterHealthFactor?
      facade.bus.on('global-filter-change:criticalsOnly', this.render,this)
      return unless options.transactionId?
      @model = new facade.models.transactions.TransactionResultsForBusinessCriteria([], {
        snapshotId:facade.context.get('snapshot').getId()
        transactionId:@options.transactionId
      })

    remove:()->
      facade.bus.off('global-filter-change:criticalsOnly', this.render)

    # TODO remove once controller v3.0 is done
    updateModel:(parameters)->
      @updateViewState(parameters)

    updateViewState:(parameters)->
      return if (!parameters.context? and !parameters.transactionId?)
      # @table?.select('businessCriterion', parameters.business, true)
      if (!parameters.business)
        @table?.select('businessCriterion', parameters.business, true)
        @updateDocumentation(parameters.business)

      if parameters.transactionId == @options.transactionId
        return
      @options.transactionId = parameters.transactionId
      if !@options.transactionId
        @model = null
        @$el.find('#table-holder .table').remove()
        @$el.find('.filter-description').remove()
        if parameters.context == '60017'
          @$el.find('.table-holder:last').addClass('no-content').text('No Data Available for selected transaction in current snapshot.')
        return

      @options.business = parameters.business
      snapshot = facade.context.get('snapshot')
      snapshotIds = snapshot.getLastTwoSnapshotIds()
      snapshotIds.unshift(snapshot.getFirstSnapshot().getId())
      @model = new facade.models.transactions.TransactionResultsForBusinessCriteria([], {
        snapshotId:facade.context.get('snapshot').getId()
        transactionId:@options.transactionId
      })
      @preRender()
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload technical criteria view', e)
      })
      return

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
          header:t('Health measure')
          title:t('Criteria Name')
          align:'left'
          format:(value, group, row, model)->
            return facade.tableHelpers.formatName(value,model)
        }
      ]
      return columns

    render: ()->
      showCriticalsOnly = facade.portal.getFilterSetting('criticalsOnly')
      @rendered = true
      if @model?
        rows = @model.asRows({
          selectCriterion:@options.business
          filter:@filterHealthFactor
          criticalViolationsAsResults:showCriticalsOnly
        })
      else
        rows = []
      @$el.html(@template({
        isHealthFactors:@filterHealthFactor
        hasContent:rows.length > 0
        # downloadLink:@model.downloadUrl(@filterHealthFactor)
      }))
      return @$el unless @model?
      if rows.length > 0
        @table = new facade.bootstrap.Table({
          columns:@configureTableColumns(showCriticalsOnly),
          selectOnClick:true
          click:(item)=>
            @onTableSelection(item)
          rows:rows
        })
        @$el.find('#table-holder').html(@table.render())
        @table.$el.addClass('contract compact')# compact by default
      setTimeout (->
        $(window).resize()
        ), 100
      @updateDocumentation(@options.business)
      @updateFilterDescription(showCriticalsOnly)
      @$el

    updateFilterDescription:(critical)->
      @$el.find('.filter-description').hide() if !critical

    updateDocumentation:(business)->
      @$el.find('.description').hide()
      @$el.find('#doc-' + business).css('display', 'block')

    onTableSelection:(item)->
      criterion = item?.extra?.businessCriterion
      return unless criterion?
      return if criterion == window.location.hash.split('/').pop() && criterion == @options.business
      @updateDocumentation(criterion)
      facade.bus.emit('navigate', {page:"transactionInvestigation/"+ @options.context + '/' +  @options.transactionId + '/' + criterion} )
  })

  return QualityIndicatorsView
