ImprovementSection = (facade) ->

  Handlebars = facade.Handlebars
  _ = facade._
  Backbone = facade.backbone
  Highcharts = facade.Charts
  t = facade.i18n.t

  _objectNameTemplate = Handlebars.compile('<span>
    <em class="short-content" ({{value}})">{{ellipsisMiddle value 20 30}}</em>
    <em class="large-content" ({{value}})">{{ellipsisMiddle value 40 60}}</em>
    <em class="super-large-content" ({{value}})">{{value}}</em>
  </span>')

  ImprovementSectionView = Backbone.View.extend({

    template: Handlebars.compile(' <div class="improvement-view" id="improvement-view"></div>')

    summaryTemplate: Handlebars.compile(' <div class="improvement-overview" id="improvement-overview">
      <div id="exclusion-selector"></div>
      <h1 class="overview-text">{{t "Continuous Improvement Summary"}}</h1>
      <div class="improvement-summary-outer"></div>
      <div id="improvement-details"></div>
    </div>')

    violationsTemplate: Handlebars.compile('<div class="improvement-summary">
        {{#equals type value="added"}}
          <div class="current-snapshot-info">
            <h1>{{data.currentViolations}}</h1>
            <p>{{{t "Violations added in the </br> current snapshot"}}}</p>
          </div>
          <div class="since-initial-snapshot-info">
            <h1>{{data.initialViolations}}</h1>
            <p>{{{t "Violations added since </br> initial snapshot"}}}</p>
          </div>
        {{/equals}}
        {{#equals type value="removed"}}
          <div class="current-snapshot-info">
            <h1>{{data.currentViolations}}</h1>
            <p>{{{t "Violations removed in the </br> current snapshot"}}}</p>
          </div>
          <div class="since-initial-snapshot-info">
            <h1>{{data.initialViolations}}</h1>
            <p>{{{t "Violations removed since </br> initial snapshot"}}}</p>
          </div>
        {{/equals}}
        {{#equals type value="total"}}
          <div class="current-snapshot-info">
            <h1>{{data.currentViolations}}</h1>
            <p>{{{t "Violations in</br> current snapshot"}}}</p>
          </div>
          <div class="initial-percentage-snapshot-info">
            {{#if data.noDifference}}
                <h1>{{t "N/A"}}</h1>
            {{else}}
                <h1>{{data.initialViolationsPercentage}}% ({{data.initialCountDifference}})</h1>
            {{/if}}
            <p>{{#if data.noDifference}}
                {{t "Violations"}}
               {{else}}
                {{#if data.initialCountDifferenceWithSign}} {{#positive data.initialCountDifferenceWithSign }} {{t "Increased"}} {{else}} {{t "Decreased"}} {{/positive}} {{else}} {{t "No Change"}} {{/if}}
               {{/if}}
              {{{t " since </br> initial snapshot"}}}</p>
          </div>
          <div class="previous-percentage-snapshot-info">
            {{#if data.noDifference}}
                <h1>{{t "N/A"}}</h1>
            {{else}}
                <h1>{{data.previousViolationsPercentage}}% ({{data.previousCountDifference}})</h1>
            {{/if}}
            <p>{{#if data.noDifference}}
                {{t "Violations"}}
               {{else}}
                {{#if data.previousCountDifferenceWithSign}} {{#positive data.previousCountDifferenceWithSign }} {{t "Increased"}} {{else}} {{t "Decreased"}} {{/positive}} {{else}} {{t "No Change"}}  {{/if}}
               {{/if}}
               {{{t " since </br> previous snapshot"}}}</p>
          </div>
        {{/equals}}
      </div>')

    graphTemplate: Handlebars.compile('<div class="improvement-graph" id="improvement-graph">
      </div>')

    monitorTemplate: Handlebars.compile('<div class="monitor-overview" id="monitor-overview">
      <div class="monitor-header">
        <h1 class="overview-text"> {{t "Monitor rules marked for Improvement"}}</h1>
        <a title="{{t "Download data as excel file"}}" class="download-file monitor-rules pos">{{t "Download Excel"}}</a>
      </div>
      <div class="rule-details"></div>
      <hr>
      <div class="violations-details">
        <h1 class="overview-text">{{t "Violations status"}}</h1>
          <input class="violation-type" type="radio" name="violationsType" value="removed"> {{t "Removed"}}</br>
          <input class="violation-type" type="radio" name="violationsType" value="added"> {{t "Added"}}</br>
          <input class="violation-type" type="radio" name="violationsType" value="total"> {{t "Total"}}</br>
      </div>
    </div>')

    unavailableTemplate: Handlebars.compile('<div class="improvement-not-available"><h1>{{{t "No rules are marked for education"}}}</h1><p>{{{t "Please add rules to check."}}}</p></div>')

    noTemplateForPreviousSnapshot: Handlebars.compile('<div class="investigation-not-available"><h1>{{{t "Education not available in past snapshot"}}}</h1><p>{{{t "You may only be able to investigate this data in the latest snapshot."}}}</p></div>')

    loadingTemplate: '<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    events:
      'click .monitor-rules': 'downloadMonitorRulesAsExcelFile'

    preRender:()->
      @$el.find('.improvement-summary-outer').html(@loadingTemplate)

    initialize: (options) ->
      @options = _.extend({},options)
      @educationRules = new facade.models.education.EducationSummary([], {href:facade.context.get('snapshot').get('href')})
      @qualityAutomationManager = facade.context.get('user').get('qualityAutomationManager')
      @selectedRulesId = []
      @activeViolationsType = if options.violationType then options.violationType else 'removed'

    downloadMonitorRulesAsExcelFile:()->
      href = @monitorRulesDownloadLink
      $.ajax('url': REST_URL + 'user', 'async': false)
        .success(()->
        window.location = href if href?
      )
      return false

    fetchEducationRules:(callback)->
      @educationRules.getData({
        success: (result)=>
          @educationRuleIds = _.map(_.filter(result.models, (rule) ->
            return rule if rule.get('active') == false
          ), (rules)->
            return rules.get('rulePattern').href.split('/')[2]
          )

          @monitorRulesDownloadLink = REST_URL + facade.context.get('snapshot').get('href') + '/results?quality-indicators=(' + @educationRuleIds + \
            ')&select=(evolutionSummary,violationRatio)&unselect=(grade)&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

          callback() if @educationRuleIds.length == 0

          rows = @educationRules.asRows(improvementSection: true)
          columns = [
            {
              header:t('Select All'),title:t('Select All'), align: 'left stretch', format: (value)->
                return _objectNameTemplate({value: value})
            }
          ]
          @rulesTable = new facade.bootstrap.Table({
            rowSelector: true
            columns: columns
            rows: rows
          })
          callback()
        error:() =>
          if !facade.context.get('snapshot').isLatest()
            $('#improvement-holder').html(@noTemplateForPreviousSnapshot)
            @$el.find('.investigation-not-available h1').addClass('no-snapshot-text')
      })

    getTooltipData:(snapshotsData)->
      tooltipData = []
      _.map(snapshotsData, (snapshotData) =>
        tooltipData.push({
          x: new Date(snapshotData.date).getTime()
          y: snapshotData.violations
          version: _.find(facade.context.get('snapshots').models, (snapshot) => return snapshot.get('annotation').date.time == snapshotData.time ).get('annotation').version
          violationsType: @activeViolationsType
        })
      )
      return tooltipData

    fetchViolationsCount:(callback)->
      result = {}
      if @selectedRulesId.length == 0
        result.currentViolations = 'N/A'
        if @activeViolationsType != 'total' then result.initialViolations = 'N/A' else result.noDifference = true
        callback(result)
      else
        if @activeViolationsType != 'total'
          @educationViolations = new facade.models.education.EducationViolationsCount([], {
            ruleIds: @selectedRulesId
            href: facade.context.get('application').get('href'),
            type: @activeViolationsType
          })

          @educationViolations.getData({
            success: (data)=>
              snapshotsData = @educationViolations.getSnapshotsData(data).reverse()
              result.snapshotsData =  @getTooltipData(snapshotsData)
              result.currentViolations = @educationViolations.getViolationsCount(data, '0')
              result.initialViolations = if result.snapshotsData.length != 1 then @educationViolations.getInitialViolationsCount(data) else 'N/A'
              callback(result)
          })
        else
          @educationViolations = new facade.models.education.EducationTotalViolationsCount([], {
            ruleIds: @selectedRulesId
            href: facade.context.get('application').get('href'),
            type: @activeViolationsType
          })

          @educationViolations.getData({
            success: (data)=>
              snapshotsData = @educationViolations.getSnapshotsData(data).reverse()
              result.snapshotsData = @getTooltipData(snapshotsData)
              if result.snapshotsData.length == 1
                result.currentViolations = @educationViolations.getViolationsCount(data, '0')
                result.noDifference = true
              else
                result = _.extend(result, @educationViolations.getViolations(data))
              callback(result)
          })

    updateGraph:(snapshotData)->
      @chart.series[0].setData(snapshotData)

    renderGraph:(result)->
      @$el.find('.improvement-summary-outer').append(@graphTemplate())
      @chart = new Highcharts.Chart({
        title:
          text: null
        chart:
          type: 'areaspline'
          renderTo: 'improvement-graph'
          height: 350
        xAxis:
          title:
            text: 'Snapshots'
            style:
              fontWeight: 'bold'
            margin: 25
          type: 'datetime'
        yAxis:
          title:
            text: 'Violations'
            style:
              fontWeight: 'bold'
            margin: 35
          labels:
            formatter:()->
              if this.value > 1000
                return this.value/1000 + 'k'
              else
                return this.value
          plotLines:[
            value: 0,
            width: 1,
            color: '#808080'
          ]
          allowDecimals: false
        plotOptions:
          series:
            fillOpacity: 0.1
        legend:
          enabled: false
        tooltip:
          useHTML: true
          style:
            color: '#fff'
          backgroundColor: '#36383a'
          borderColor: '#36383a'
          borderWidth: 0
          borderRadius: 10
          shadow: false
          formatter: (a, b, c) ->
              formatDate = new Date(this.point.x).toDateString()
              return '<div class="graph-tooltip">' +
                        '<div class="tooltip-header">' +
                          '<p class="graph-violations-count">' + this.point.y + '</p>' +
                          '<span class="graph-violations-type">' + this.point.violationsType + ' violations</span>' +
                        '</div>' +
                        '<div class="graph-snapshot">' +
                          '<p>Snapshot Version: <b>' + this.point.version + '</b></p>' +
                          '<p>Snapshot Date: <b>' + formatDate.slice(0,formatDate.length - 5) + ', ' + formatDate.slice(formatDate.length - 5)  + '</b></p>' +
                        '</div>' +
                     '</div>'
        series: [{
          data: result.snapshotsData,
          color: '#1b1ba9'
        }]
      })

    onRuleSelection: ()->
      selectedRules = @rulesTable.getSelectedRows()
      @selectedRulesId = []
      for rule in selectedRules
        @selectedRulesId.push(rule.get('ruleId'))
      if selectedRules.length == @educationRules._collection.length
        @$el.find('table thead tr .row-selector input[type="checkbox"]').prop('checked', true)
      @fetchViolationsCount((result)=>
        @$el.find('.improvement-summary-outer .loading').remove()
        if @chart?
          @$el.find('.improvement-summary').remove()
          @$el.find('.improvement-graph').before(@violationsTemplate( type: @activeViolationsType , data:result))
          @updateGraph(result.snapshotsData)
        else
          @$el.find('.improvement-summary-outer').append(@violationsTemplate( type: @activeViolationsType , data:result))
          @renderGraph(result)
      )

    onViolationsTypeSelection: ()->
      @activeViolationsType = $('input[type="radio"]:checked').val()
      facade.bus.emit('navigate', {page: "educationOverview/improvement/" + @activeViolationsType, updateViolationsType:true})
      @fetchViolationsCount((result)=>
        @$el.find('.improvement-summary').remove()
        @$el.find('.improvement-graph').before(@violationsTemplate( type: @activeViolationsType , data:result))
        @updateGraph(result.snapshotsData)
      )

    render:() ->
      @fetchEducationRules(()=>
        @$el.html(@template())
        @$el.find('#improvement-view').append(@summaryTemplate)
        @$el.find('#improvement-view').append(@monitorTemplate())
        if @educationRuleIds.length == 0
          @$el.html(@unavailableTemplate())
          @$el.find('.monitor-rules').addClass('disabled')
          return
        @$el.find('#monitor-overview .rule-details').html(@rulesTable.render())
        @preRender()
        @rulesTable.on('update:row-selector', @onRuleSelection, @)
        @$el.find('table tbody tr[data-index="0"] .row-selector input[type="checkbox"]').prop('checked', true)
        @$el.find('table tbody tr[data-index="0"] .row-selector label').trigger('click');
        if @activeViolationsType == "removed"
          $('input[type="radio"]:first').prop('checked', true)
        else  if @activeViolationsType == "added"
          $('input[type="radio"]:eq(1)').prop('checked', true)
        else
          $('input[type="radio"]:eq(2)').prop('checked', true)
        $('input[type="radio"]').on('change', @onViolationsTypeSelection.bind(@))
        @view = new  @options.ViolationsSection({el:'#improvement-holder', educatedRules: @educationRules})
        @view.render()
      )
  })

  return ImprovementSectionView
