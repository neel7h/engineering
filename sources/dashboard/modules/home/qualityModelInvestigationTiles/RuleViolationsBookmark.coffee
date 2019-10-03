# FIXME relocate in adequate module
RuleViolationsModelBookmark = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._

  Model = backbone.Collection.extend({

    url:()->
      lastTwoSnapshotIds = facade.context.get('snapshot').getLastTwoSnapshotIds()
      rootURL = REST_URL + SELECTED_APPLICATION_HREF + '/results?select=(violationRatio)&quality-indicators=(' + @rule + ',' + @business + ')&snapshot-ids=('+lastTwoSnapshotIds+')'
      rootURL

    initialize:(options)->
      @rule = options.rule
      @business = options.business

    parse:(data)->
      for result in data
        result.applicationResults.sort((a, b)=> if a.type > b.type then return -1 else return 1)
      return data

    hasResults:()->
      return false if @length == 0
      results = @at(0).get('applicationResults')
      return false unless results?
      return results.length == 2

    getRuleName:()->
      @at(0).get('applicationResults')[0].reference.name

    getRuleShortName:()->
      @at(0).get('applicationResults')[0].reference.shortName

    getBusinessCriteriaName:()->
      @at(0).get('applicationResults')[1].reference.name

    getBusinessCriteriaShortName:()->
      @at(0).get('applicationResults')[1].reference.shortName

    getViolations:() ->
      violations = @at(0).get('applicationResults')?[0].result.violationRatio?.failedChecks
      return violations if violations?
      return 'n/a'

    getPreviousViolations:() ->
      violations = @at(1)?.get('applicationResults')?[0].result.violationRatio?.failedChecks
      return violations if violations?
      return @getViolations()

    getAllViolations:() ->
      results = []
      for data in @models
        snapshotDate = data.get('date').time
        result = data.get('applicationResults')?[0].result.violationRatio?.failedChecks
        results.push([snapshotDate, result]) if result?
      results.sort((a,b)->a[0]-b[0])
      results

    getViolationsDelta:()->
      currentViolations = @at(0).get('applicationResults')[0].result.violationRatio?.failedChecks or 0
      previousViolations = @at(1)?.get('applicationResults')?[0].result.violationRatio?.failedChecks or 0
      currentViolations - previousViolations

    getGrade:()->
      @at(0).get('applicationResults')?[0].result.grade

    getPreviousGrade:()->
      grade = @at(1)?.get('applicationResults')?[0].result.grade
      return grade if grade?
      return @getGrade()

    getGrades:()->
      results = []
      for data in @models
        snapshotDate = data.get('date').time
        result = data.get('applicationResults')?[0].result.grade
        results.push([snapshotDate, result]) if result?
      results.sort((a,b)->a[0]-b[0])
      results

    getGradeDelta:()->
      currentGrade = @at(0).get('applicationResults')[0].result.grade
      previousGrade = @at(1)?.get('applicationResults')?[0].result.grade or 0
      currentGrade - previousGrade

  })

  RuleViolationsModelBookmark = backbone.View.extend({
    className:'value-tile bookmark'
    template:Handlebars.compile('

        <h3 title="{{indicator}}">{{indicator}}</h3>
        <div class="quality-rule"></div>
        {{#if critical}}<h4>{{t "Critical"}}</h4>{{/if}}
        {{#if hasViolations}}
          <div class="indicator-violations" title="{{formatNumber violations "0,000"}}">{{#if largeNumberViolations}}
                                                {{formatNumber violations "0,000a"}}
                                            {{else}}{{formatNumber violations "0,000"}}{{/if}}</div>
          {{#if variation}}
          <div class="indicator-violations-delta" title="{{t "Variation since last snapshot:"}} {{deltaSign}}{{formatNumber violationsVariation "0.0000000%"}}">
            <span>{{deltaSign}}{{formatNumber violationsVariation violationVariationFormat}}</span>
            <em>{{t "violations"}}</em>
          </div>
          {{/if}}
        {{/if}}
    ')
    qualityRuleTemplate:Handlebars.compile('<h2 title="{{title}}">{{ellipsisMiddle title charBefore charAfter}}</h2>')
    noValuesTemplate:Handlebars.compile('
        <h2>{{t "No value"}}</h2>
        <h3>{{t "Indicator not available for snapshot or application"}}</h3>
    ')

    events:
      'mousedown':'clicking'
      'click .close':'remove'
      'click':'drillInQualityModel'
      'widget:resize':'updateRendering'

    clicking:(event)->
      @clicked = {
        x: event.pageX
        y: event.pageY
      }
      true

    updateRendering:(event) ->
      $t = $(event.target)
      if $t.width() < 168 and $t.height() < 168
        charBefore = 20
        charAfter = 35
      else
        charBefore = 60
        charAfter = 60

      $qualityRule = @$el.find('.quality-rule')
      $qualityRule.html(@qualityRuleTemplate({title:@model.getRuleName(),charBefore:charBefore, charAfter:charAfter}))
      @$el

    remove:()->
      facade.bus.emit('bookmark:remove',{index:@options.tile.get('id')})

    drillInQualityModel:(event)->
      if @clicked? and Math.abs(event.pageX - @clicked.x) < 15 and Math.abs(event.pageY - @clicked.y) < 15
        @clicked = null
        return if @$el.hasClass('no-value')
        return if 'close' == event.target.className
        page = "qualityInvestigation/0"
        if @options.business?
          page += '/' + @options.business
          if @options.technical?
            page += '/' + @options.technical
            if @options.rule?
              page += '/' + @options.rule
        return facade.bus.emit('navigate', {page:page})
      @clicked = null

    initialize:(options)->
      @options = _.extend({},options)
      @model = new Model(options)
      snapshot = facade.context.get('snapshot')
      lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds()
      if facade.context.get('module')
        prevSnapshotModules = facade.context.get('modulesInPreviousSnapshot').pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(facade.context.get('module').get('name'))
        lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds().splice('1') if isModuleAvailable < 0

      @qualityRuleModel = new facade.models.QualityRulesResults({
        href:SELECTED_APPLICATION_HREF,
        technicalCriterion: @options.technical
        business:@options.business
        module:facade.context.get('module')
        snapshotId:snapshot.getId()
        lastTwoSnapshotIds:lastTwoSnapshotIds
      })

    render:()->
      compactCol = @options.tile.get('sizex') == 1
      compactRow = @options.tile.get('sizey') == 1
      if compactCol and compactRow
        charBefore = 35
        charAfter = 20
      else
        charBefore = 60
        charAfter = 60
      facade.ui.spinner(@$el)
      @model.getData({
        success:()=>
          if @model.hasResults()
            @$el.removeClass('no-value')
            violations = @model.getViolations()
            delta = @model.getViolationsDelta()
            violationsVariation = 0
            violationsVariation=Math.abs(delta/@model.getPreviousViolations()) if @model.getPreviousViolations()? && @model.getPreviousViolations() != 0
            variation = true
            deltaSign = if delta<0 then '-' else
              if delta == 0 then '' else '+'

            if @model.length == 1
              delta = ''
              deltaSign = ''
              violationsVariation = null
              variation = false


            @qualityRuleModel.getData({
              success:()=>
                contributors = @qualityRuleModel._contribution?.get('gradeContributors')
                critical = false
                if contributors?
                  for contributor in contributors
                    if (contributor.key == @options.rule)
                      critical = contributor.critical
                      break
                @$el.html(@template({
                  shortTitle:@model.getRuleShortName()
                  indicator:@model.getBusinessCriteriaName()
                  critical:critical
                  violations:violations
                  hasViolations:'n/a' != violations
                  violationsVariation:violationsVariation
                  violationVariationFormat:if violationsVariation < 0.01 then '0.00%' else '0%'
                  deltaSign:deltaSign
                  variation:variation
                  largeNumberViolations: violations >= 1000
                }))
                $qualityRule = @$el.find('.quality-rule')
                $qualityRule.html(@qualityRuleTemplate({title:@model.getRuleName(),charBefore:charBefore, charAfter:charAfter}))
              error:(e)->
                console.error('failed trying to reload technical criteria view', e)
            })

          else
            @$el.addClass('no-value')
            @$el.html(@noValuesTemplate())
      })
      @$el
  },{
    processParameters:(parameters)->
      return {
        rule:parameters.rule
        business:parameters.business
        technical:parameters.technical
        critical:parameters.critical
      }
  })

  return RuleViolationsModelBookmark
