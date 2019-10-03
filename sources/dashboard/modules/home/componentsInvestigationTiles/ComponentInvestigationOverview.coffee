ComponentInvestigationOverview = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  QualitySizingMeasure = facade.backbone.Model.extend({
    url:()->
      REST_URL + SELECTED_APPLICATION_HREF + "/results?sizing-measures=(" + @get('metricId') + ")&snapshots=(-1)"

    parse:(data)->
      snapshotData = data[0]
      results = {}
      for result in snapshotData.applicationResults
        results[result.reference.key] = result.result.value
      results
  })

  ComponentInvestigation = backbone.Collection.extend({
    initialize:()->
      @modules = facade.context.get('modules')
      @treeRoot = new facade.models.componentBrowserTree.ComponentRoot({snapshotId:facade.context.get('snapshot').getId()})
      @applicationSize = new QualitySizingMeasure({metricId:'10151'})

    getData:(options)->
      _arguments = arguments
      that = @
      fullOptions = _.extend({success:@defaultOptions.success, error:@defaultOptions.error}, options)
      $.when(@applicationSize.fetch(), @treeRoot.fetch()).done(()=>
        @defectsSummary = new facade.models.componentBrowserTree.DefectsSummary({href:@treeRoot.getDefectsSummaryHref()})
        $.when(@defectsSummary.fetch()).then(()->
          fullOptions.success.apply(that, _arguments)
        , ()->
          fullOptions.error.apply(that, _arguments)
        )
      ).fail(()->
        fullOptions.error.apply(that, _arguments)
      )

    getLinesOfCode:()->
      @applicationSize.get('10151')

    modulesCount:()->
      @modules.length
  })

  _Modules = facade.backbone.Collection.extend({
    url:()->
      REST_URL + SELECTED_APPLICATION_HREF + '/modules'
  })

  DefectSummaryView = backbone.View.extend({
    template:Handlebars.compile('
      {{#if onlyCritical}}
        <div class="defect-summary"><div class="value">{{formatNumber defectiveComponentsToCriticalRules.number "0a"}}</div><div class="label">{{t "Involved Objects"}}</div></div>
        <div class="defect-summary violations critical-defects-summary"><div class="value">{{formatNumber criticalViolations.number "0a"}}</div><div class="label">{{t "Critical Violations"}}</div></div>
        <div class="defect-summary"><div class="value">{{formatNumber violatedCriticalRulePatterns.number "0a"}}</div><div class="label">{{t "Violated Rules"}}</div></div>
        <div class="trop-de-la-barre"></div>
      {{else}}
        <div class="defect-summary"><div class="value">{{formatNumber defectiveComponents.number "0a"}}</div><div class="label">{{t "Involved Objects"}}</div></div>
        <div class="defect-summary violations"><div class="value">{{formatNumber violations.number "0a"}}</div><div class="label">{{t "Violations"}}</div></div>
        <div class="defect-summary"><div class="value">{{formatNumber violatedRulePatterns.number "0a"}}</div><div class="label">{{t "Violated Rules"}}</div></div>
        <div class="trop-de-la-barre"></div>
      {{/if}}
    ')

    initialize:(options)->
      @options = _.extend({},options)

    render:()->
      @template(_.extend({
        onlyCritical: facade.portal.getFilterSetting('criticalsOnly')
        }, @model.toJSON()))
  })

  return backbone.View.extend({
    className:'modules-tile all-tile-evt'
    template:Handlebars.compile('
        <h2 class="modules">{{title}}</h2>
        <div class="module-count-block">
          <div class="value modules-count">{{formatNumber moduleCount "0,000"}}</div>
          <div class="label modules-count-label">{{#if plural}}{{t "Modules"}}{{else}}{{t "Module"}}{{/if}}</div>
        </div>
        <div class="application-size-block">
          <div id="LOC" class="value line-of-code"  title="{{formatNumber lineOfCode "0,000"}}">{{formatNumber lineOfCode "0.0a"}}</div>
          <div class="label application-size-label">{{t "lines of code"}}</div>
        </div>
        <div class="defect-summaries"></div>
    ')

    events:
      'mousedown':'clicking'
      'click':'drillInComponentInvestigation'
      'widget:resize':'updateRendering'

    clicking:(event)->
      @clicked = {
        x: event.pageX
        y: event.pageY
      }
      true

    updateRendering:(event)->
      if @$el.width() < 260
        @$el.addClass('compact-col') unless @$el.hasClass('compact-col')
      else
        @$el.removeClass('compact-col') if @$el.hasClass('compact-col')
      if @$el.height() < 260
        @$el.addClass('compact-row') unless @$el.hasClass('compact-row')
      else
        @$el.removeClass('compact-row') if @$el.hasClass('compact-row')
      @$el

    updateFilterState: ()->
      defectSummaryView = new DefectSummaryView({model:@model.defectsSummary})
      $ds = @$el.find('.defect-summaries')
      $ds.html(defectSummaryView.render())

    drillInComponentInvestigation:(event)->
      if @clicked? and Math.abs(event.pageX - @clicked.x) < 15 and Math.abs(event.pageY - @clicked.y) < 15
        @clicked = null
        facade.bus.emit('navigate', {page:'componentsInvestigation'})
        return
      @clicked = null

    initialize:(options)->
      @options = _.extend({},options)
      @model = new ComponentInvestigation()
      facade.bus.on('global-filter-change:criticalsOnly', this.updateFilterState, this)

    remove:->
      facade.bus.off('global-filter-change:criticalsOnly', this.updateFilterState)

    render:()->
      compactCol = @options.tile.get('sizex') == 1
      compactRow = @options.tile.get('sizey') == 1
      facade.ui.spinner(@$el)

      @$el.addClass('compact-col') if compactCol
      @$el.addClass('compact-row') if compactRow
      @model.getData({
        success:()=>
          @$el.html(@template({
            moduleCount:@model.length
            plural:@model.length != 1
          }))
          count = @model.modulesCount()
          @$el.html(@template({
              title:this.constructor.title
              moduleCount:count
              plural:count != 1
              lineOfCode:@model.getLinesOfCode()
            }))

          @updateFilterState()
        error:(e)->
          console.error('failed to load module count for Application Components', e)
      })
      @$el
  },{
    requiresLastSnapshot:true,
    title:t('Application components')
  })
