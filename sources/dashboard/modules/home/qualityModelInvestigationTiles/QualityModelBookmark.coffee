# Create a tile view to avoid copy pasted code
QualityModelBookmark = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._

  Model = backbone.Collection.extend({

    url:()->
      REST_URL + SELECTED_APPLICATION_HREF + '/results?quality-indicators=(' + @indicator + ')&snapshots=(' + @snapshots +  ')'

    initialize:(options)->
      @indicator = options.business if options.business?
      @indicator = options.technical if options.technical?
      @indicator = options.rule if options.rule?
      @indicator = options.component if options.component?
      if options.trends then @snapshots = '$all' else @snapshots = '-2'

    hasResults:()->
      @length > 0

    getIndicator:()->
      @at(0).get('applicationResults')[0].reference.name

    getIndicatorShortName:()->
      @at(0).get('applicationResults')[0].reference.shortName

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

  QualityModelBookmark = backbone.View.extend({
    className:'value-tile bookmark'
    template:Handlebars.compile('

        <h2 title="{{title}}">{{ellipsis title 15 shortTitle}}</h2>
        <div class="indicator-grade">{{formatNumber grade "0.00"}}</div>
        {{#if gradeVariation}}<div class="indicator-grade-delta" title="{{t "Variation since last snapshot:"}} {{deltaSign}}{{formatNumber gradeVariation "0.0000000%"}}"><em>{{deltaSign}}{{formatNumber gradeVariation "0.0%"}}</em></div>{{/if}}
    ')
    templateEvolution:Handlebars.compile('

        <h2 title="{{title}}">{{ellipsis title 15 shortTitle}}</h2>
        <div class="chart"></div>
        {{#if gradeVariation}}<div class="indicator-grade-delta" title="{{t "Variation since last snapshot:"}} {{deltaSign}}{{formatNumber gradeVariation "0.0000000%"}}"><em>{{deltaSign}}{{formatNumber gradeVariation "0.0%"}}</em></div>{{/if}}
    ')
    noValuesTemplate:Handlebars.compile('
        <h2>{{t "No value"}}</h2>
        <h3>{{t "Indicator not available for snapshot or application"}}</h3>
    ')

    events:
      'mousedown':'clicking'
      'mouseup':'clicking'
      'click .close':'remove'
      'click':'drillInQualityModel'
      'widget:resize':'updateRendering'

    updateRendering:(event) ->
      $t = $(event.target)
      $c = $t.find('.chart')
      @chart?.setSize($c.width(), $c.height())

    remove:()->
      facade.bus.emit('bookmark:remove',{index:@options.tile.get('id')})

    clicking:(event)->
      return if 'close' == event.target.className
      if 'mousedown' == event.type
        @clicked = {
          x: event.pageX
          y: event.pageY
          when:new Date().getTime()
        }
      else
        @drillInQualityModel(event) # for charts blocking click event
      true

    drillInQualityModel:(event)->
      return if 'close' == event.target.className
      if @clicked?
        isNear = (Math.abs(event.pageX - @clicked.x) < 15 and Math.abs(event.pageY - @clicked.y) < 15)
        notTooLongAgo = (new Date().getTime() - @clicked.when) < 1000
        @clicked = null
        if isNear and notTooLongAgo
          page = "qualityInvestigation/0"
          if @options.business?
            page += '/' + @options.business
            if @options.technical?
              page += '/' + @options.technical
              if @options.rule?
                page += '/' + @options.rule
                if @options.component?
                  page += '/' + @options.component
          return facade.bus.emit('navigate', {page:page})

    initialize:(options)->
      @options = _.extend({},options)
      @model = new Model(options)

    render:()->
      color = '#fff'
      css =  facade.css.findLastCSSRule(@options.color)
      if css?
        color = css.style.color
      @model.getData({
        success:()=>
          if @model.hasResults()
            if @options.trends and @model.length > 1
              grades = @model.getGrades()
              grade = @model.getGrade()
              delta = @model.getGradeDelta()
              @$el.html(@templateEvolution({
                title:@model.getIndicator()
                shortTitle:@model.getIndicatorShortName()
                grade:grade
                gradeVariation:Math.abs(delta/@model.getPreviousGrade())
                deltaSign:if delta<0 then '-' else
                  if delta == 0 then '' else '+'
              }))
              @chart = new facade.Charts.Chart({
                credits:
                  enabled:false
                chart:
                  type: 'line'
                  backgroundColor: 'rgba(255,255,255,0)'
                  renderTo: @$el.find('.chart')[0]
                  zoomType: 'none'
                title:
                  text:null
                colors:[
                  color
                ]
                xAxis:
                  type: 'datetime'
                  gridLineWidth: 0
                  lineWidth:0
                  tickWidth:0
                  title:
                    text: null
                  labels:
                    enabled:false
                yAxis:
                  min: 1
                  max: 4
                  tickInterval: 1
                  gridLineWidth: 0.5
                  gridLineDashStyle: 'Dash'
                  gridLineColor: '#fff'
                  showFirstLabel: true
                  title:
                    text: null
                  labels:
                    enabled:true # label color is handled via css
                    style:
                      "font-size":'8px'
                    y: 2

                legend:
                  enabled: false
                plotOptions:
                  line:
                    lineWidth:2
                    marker:
                      enabled:false
                  spline:
                    lineWidth:2
                    marker:
                      enabled:false
                tooltip:
                  enabled:false
                series: [{
                  name: ''
                  data: grades
                }]
              })
            else
              grade = @model.getGrade()
              delta = @model.getGradeDelta()
              gradeVariation=Math.abs(delta/@model.getPreviousGrade())
              deltaSign = if delta<0 then '-' else
                if delta == 0 then '' else '+'
              if @model.length == 1
                delta = ''
                deltaSign = ''
                gradeVariation = null

              @$el.html(@template({
                title:@model.getIndicator()
                shortTitle:@model.getIndicatorShortName()
                grade:grade
                gradeVariation:gradeVariation
                deltaSign:deltaSign
              }))
          else
            @$el.html(@noValuesTemplate())
      })
      @$el
  },{
    processParameters:(parameters)->
      keys = ['business','technical','rule']
      parameters = parameters.metricIds.split(',')
      result = {
        trends: true
      }
      for i in [0..parameters.length-1]
        result[keys[i]] = parameters[i]
      result
  })

  return QualityModelBookmark
