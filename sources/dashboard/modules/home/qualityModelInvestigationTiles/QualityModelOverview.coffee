QualityModelOverview = (facade) ->

  Handlebars = facade.Handlebars

  QualityModel = facade.backbone.Model.extend({
    url:()->
      snapshotId = facade.context.get('snapshot').getId()
      REST_URL + SELECTED_APPLICATION_HREF + '/results?quality-indicators=(quality-rules,quality-distributions,quality-measures)&snapshot-ids=(' + snapshotId + ')'

    parse:(data)->
      snapshotData = data[0]
      results = {
        criticalRules:0
        measures:0
        distributions:0
        qualityRules:0
      }
      for result in snapshotData.applicationResults
        if parseInt(result.reference.key) > 1000000
          results.qualityRules++
          results.criticalRules++ if 'quality-rules' == result.type and result.reference.critical
        else
          switch result.type
            when 'quality-rules'
                results.qualityRules++
                results.criticalRules++ if result.reference.critical
            when 'quality-measures' then results.measures++
            when 'quality-distributions' then results.distributions++
      return results
  })

  QualitySizingMeasure = facade.backbone.Model.extend({
    url:()->
      snapshotId = facade.context.get('snapshot').getId()
      REST_URL + SELECTED_APPLICATION_HREF + '/results?sizing-measures=(' + @get('measureKey') + ')&snapshot-ids=(' + snapshotId + ')'

    parse:(data)->
      snapshotData = data[0]
      results = {}
      for result in snapshotData.applicationResults
        results[result.reference.key] = result.result.value
      results

  })

  return facade.backbone.View.extend({
    className:'tile-content all-tile-evt'
    template:Handlebars.compile('
        <div class="title">
          <h2>{{t "Risk model"}}</h2>
        </div>
        <div id="critical-violations" class="tile-block important title-block-1 {{#unless showCriticalsOnly}}hide{{/unless}}">
          <div id="NUM_CRITICAL_VIOLATIONS" class="value">-</div>
          <div class="label critical">{{t "Critical Violations"}}</div>
        </div>
        <div id="all-violations" class="tile-block important title-block-1 {{#if showCriticalsOnly}}hide{{/if}}">
          <div id="NUM_VIOLATIONS" class="value">-</div>
          <div class="label">{{t "Violations"}}</div>
        </div>
        <div class="tile-block title-block-2" title="">
          <div id="qualityRules" class="value">-</div>
          <div class="label">{{t "All Rules"}}</div>
        </div>
        <div class="tile-block title-block-3" title="">
          <div id="criticalRules" class="value">-</div>
          <div class="label">{{t "Critical Rules"}}</div>
        </div>
    ')

    events:
      'mousedown':'clicking'
      'click':'drillInQualityModel'
      'widget:resize':'updateRendering'

    updateRendering:(event) ->
      if @$el.width() < 260
        @$el.addClass('compact-col') unless @$el.hasClass('compact-col')
      else
        @$el.removeClass('compact-col') if @$el.hasClass('compact-col')
      if @$el.height() < 260
        @$el.addClass('compact-row') unless @$el.hasClass('compact-row')
      else
        @$el.removeClass('compact-row') if @$el.hasClass('compact-row')
      @$el

    clicking:(event)->
      @clicked = {
        x: event.pageX
        y: event.pageY
      }
      true

    drillInQualityModel:(event)->
      if @clicked? and Math.abs(event.pageX - @clicked.x) < 15 and Math.abs(event.pageY - @clicked.y) < 15
        @clicked = null
        facade.bus.emit('navigate', {page:'qualityInvestigation/0'})
        return
      @clicked = null

    initialize:(options)->
      @options = _.extend({},options)
      @model = new QualityModel()
      @measureModel = new QualitySizingMeasure({measureKey:'67011,67211'})
      facade.bus.on('global-filter-change:criticalsOnly', this.filterCriticity, this)

    filterCriticity: ()->
      if facade.portal.getFilterSetting('criticalsOnly')
        @$el.find('#critical-violations').removeClass('hide')
        @$el.find('#all-violations').addClass('hide')
      else
        @$el.find('#critical-violations').addClass('hide')
        @$el.find('#all-violations').removeClass('hide')

    violationMeasure: (ID) ->
      switch ID
        when '67011' then return 'NUM_CRITICAL_VIOLATIONS'
        when '67211' then return 'NUM_VIOLATIONS'
      return undefined

    render:()->
      showCriticalsOnly = facade.portal.getFilterSetting('criticalsOnly')
      compactCol = @options.tile.get('sizex') == 1
      compactRow = @options.tile.get('sizey') == 1
      facade.ui.spinner(@$el)
      @$el.addClass('compact-col') if compactCol
      @$el.addClass('compact-row') if compactRow
      $.when(@model.fetch(), @measureModel.fetch()).done(()=>
        @$el.html(@template({showCriticalsOnly:showCriticalsOnly}))
        data = @model.toJSON()
        for key of data
          formatNumber = formatNumberTitle = facade.numeral(data[key]).format('0,000')
          @$el.find('#' + key).html(formatNumber).attr('title',formatNumberTitle)

        measureData = @measureModel.toJSON()
        formatNumber = 0
        for key of measureData
          $criticalViolations = @$el.find('#' + @violationMeasure(key))
          value = measureData[key]
          if ['67011','67211'].indexOf(key) >= 0
            $criticalViolations.addClass('largest') if 1000000 > value >= 10000
            $criticalViolations.addClass('large') if 10000 > value >= 1000
          formatNumber = formatNumberTitle = facade.numeral(value).format('0,000')
          formatNumber = facade.numeral(value).format('0.0a') if value>= 100000
          $criticalViolations.html(formatNumber).attr('title', formatNumberTitle)

      )

      @$el
  })
