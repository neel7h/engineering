ActionPlanSummaryTile = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._


  Tile = backbone.View.extend({
    className:'action-plan-tile all-tile-evt'
    template:Handlebars.compile('<h2>{{t "Action plan"}}</h2>
          <div class="summary">
            <h1>0</h1>
            <label>{{t "Violations"}}</label>
            <p>{{t "for Action Plan"}}</p>
          </div>
          <div class="summary-detail"></div>
    ')
    templateViolationCount:Handlebars.compile('{{formatNumber this "0,000"}}')

    detailTemplate:Handlebars.compile('
      <div class="action-plan-detail"><div class="value">{{formatNumber addedIssues "0a"}}</div><div class="label">{{t "New"}}</div></div>
      <div class="action-plan-detail"><div class="value">{{formatNumber pendingIssues "0a"}}</div><div class="label">{{t "Pending"}}</div></div>
      <div class="action-plan-detail"><div class="value">{{formatNumber solvedIssues "0a"}}</div><div class="label">{{t "Solved"}}</div></div>
    ')

    events:
      'mousedown':'clicking'
      'click':'drillInBusinessCriteria'
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

    drillInBusinessCriteria:(event)->
      if @clicked? and Math.abs(event.pageX - @clicked.x) < 15 and Math.abs(event.pageY - @clicked.y) < 15
        @clicked = null
        facade.bus.emit('navigate', {page:'actionPlanOverview/0'})
        return

      @clicked = null

    initialize:(options)->
      @options = _.extend({},options)
      @model = new facade.models.actionPlan.ActionPlanSummary([], {href:facade.context.get('snapshot').get('href')})

    render:()->
      compactCol = @options.tile.get('sizex') == 1
      compactRow = @options.tile.get('sizey') == 1
      facade.ui.spinner(@$el)
      @$el.addClass('compact-col') if compactCol
      @$el.addClass('compact-row') if compactRow
      @model.getData({
        success:()=>
          @$el.html(@template())
          summaryData = @model.computeSummary()
          @$el.find('.summary h1').html(this.templateViolationCount(summaryData.totalIssues))
          $sd = @$el.find('.summary-detail')
          $sd.html(@detailTemplate(summaryData))
      })

      @$el
  })

  return Tile
