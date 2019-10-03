ContinuousImprovementTile = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  Tile = backbone.View.extend({
    className:'improvement-tile all-tile-evt'
    template:Handlebars.compile('<h2>{{title}}</h2>
        <div class="improvement-container">
          <div class="removed-summary risk-intro-evt">
            <h1>0</h1>
            <label>{{t "Removed"}}</label>
            <p>{{t "Violations"}}</p>
          </div>
          <div class="added-summary risk-intro-evt">
            <h1>0</h1>
            <label>{{t "Added"}}</label>
            <p>{{t "Violations"}}</p>
          </div>
        </div>
    ')
    templateViolationCount:Handlebars.compile('{{formatNumber this "0,000"}}')

    events:
      'widget:resize':'updateRendering'
      'click .removed-summary':'goToRemovedViolation'
      'click .added-summary':'goToaddedViolation'

    goToRemovedViolation:()->
      facade.bus.emit('navigate', {page: "educationOverview/improvement/removed"})

    goToaddedViolation:()->
      facade.bus.emit('navigate', {page: "educationOverview/improvement/added"})

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
        facade.bus.emit('navigate', {page:'educationOverview/improvement'})
        return

      @clicked = null

    initialize:(options)->
      @options = _.extend({},options)
      @educatedRules = new facade.models.education.EducationSummary([], {href:facade.context.get('snapshot').get('href')})

    NoValueAvailable:()->
      @$el.find('.removed-summary h1').html(this.templateViolationCount('n/a'))
      @$el.find('.added-summary h1').html(this.templateViolationCount('n/a'))
      @$el.find('.improvement-container').addClass('disabled')

    render:()->
      compactCol = @options.tile.get('sizex') == 1
      compactRow = @options.tile.get('sizey') == 1
      facade.ui.spinner(@$el)
      @$el.addClass('compact-col') if compactCol
      @$el.addClass('compact-row') if compactRow
      @educatedRules.getData({
        success:(result)=>
#To cleanup repeated code
          @educatedRuleIds =_.map(_.filter(result.models,(rule) -> return rule if rule.get('active') == false), (rules) -> return rules.get('rulePattern').href.split('/')[2])
          @addedRemovedViolations = new facade.models.education.EducationViolationsCount([], { ruleIds: @educatedRuleIds, href: facade.context.get('application').get('href'), snapshotId: facade.context.get('snapshot').get('href').split('/')[4]})
          @addedRemovedViolations.getData({
            success:(data)=>
              result = @addedRemovedViolations.addedRemovedViolationsCount(data)
              @$el.html(@template(_.extend({
                title:this.constructor.title
              }, @options.tile.toJSON())))
              @$el.find('.removed-summary h1').html(this.templateViolationCount(result.removedViolationsCount))
              @$el.find('.added-summary h1').html(this.templateViolationCount(result.addedViolationsCount))
              @NoValueAvailable() if data.rules == 0

            error:() =>
              @$el.html(@template(_.extend({
                title:this.constructor.title
              }, @options.tile.toJSON())))
              @NoValueAvailable()
          })
        error:() =>
          @$el.html(@template(_.extend({
            title:this.constructor.title
          }, @options.tile.toJSON())))
          @NoValueAvailable()
      })
      @$el
  },{
    title:t('Continuous Improvement')
  })

  return Tile
