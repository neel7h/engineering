ExclusionSummaryTile = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  Tile = backbone.View.extend({
    className:'exclusion-tile all-tile-evt'
    template:Handlebars.compile('<h2>{{title}}</h2>
        <div class="exclusion-container">
          <div class="active-summary risk-intro-evt">
            <h1>0</h1>
            <label>{{t "Active"}}</label>
            <p>{{t "Exclusions"}}</p>
          </div>
          <div class="scheduled-summary risk-intro-evt">
            <h1>0</h1>
            <label>{{t "Scheduled"}}</label>
            <p>{{t "Exclusions"}}</p>
          </div>
        </div>
    ')
    templateViolationCount:Handlebars.compile('{{formatNumber this "0,000"}}')

    events:
      'widget:resize':'updateRendering'
      'click .active-summary':'goToActiveExclusions'
      'click .scheduled-summary':'goToScheduledExclusions'

    goToActiveExclusions:()->
      facade.bus.emit('navigate', {page: "actionPlanOverview/" + "exclusions"})

    goToScheduledExclusions:()->
      facade.bus.emit('navigate', {page: "actionPlanOverview/" + "exclusions/scheduled"})

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
        facade.bus.emit('navigate', {page:'actionPlanOverview/exclusions'})
        return

      @clicked = null

    initialize:(options)->
      @options = _.extend({},options)
      @activeModel = new facade.models.exclusion.ActiveExclusionsSummary([], {href:facade.context.get('snapshot').get('href')})
      @scheduledModel = new facade.models.exclusion.ScheduledExclusionsSummary([], {href:facade.context.get('snapshot').get('href')})

    render:()->
      compactCol = @options.tile.get('sizex') == 1
      compactRow = @options.tile.get('sizey') == 1
      facade.ui.spinner(@$el)
      @$el.addClass('compact-col') if compactCol
      @$el.addClass('compact-row') if compactRow
      @activeModel.getData({
        success:()=>
          #To cleanup repeated code
          @scheduledModel.getData({
            success:()=>
              @$el.html(@template(_.extend({
                title:this.constructor.title
              }, @options.tile.toJSON())))
              @$el.find('.active-summary h1').html(this.templateViolationCount(@activeModel.computeSummary()))
              @$el.find('.scheduled-summary h1').html(this.templateViolationCount(@scheduledModel.computeSummary()))
            error:() =>
              @$el.html(@template(_.extend({
                title:this.constructor.title
              }, @options.tile.toJSON())))
              @$el.find('.active-summary h1').html(this.templateViolationCount(@activeModel.computeSummary()))
              @$el.find('.scheduled-summary h1').html(this.templateViolationCount('n/a'))
          })
        })
      @$el
  },{
    title:t('Exclusion')
  })

  return Tile
