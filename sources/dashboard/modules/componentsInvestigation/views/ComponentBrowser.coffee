ComponentBrowserView = (facade) ->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  DefectSummaryView = backbone.View.extend({
    template: Handlebars.compile('<div class="cont">
      {{#if onlyCritical}}
        <div class="defect-summary"><div class="disk"><div title="{{formatNumber defectiveComponentsToCriticalRules.number "0,000"}}" class="value">{{formatNumber defectiveComponentsToCriticalRules.number "0a"}}</div><div class="label">{{t "Objects"}}</div></div></div>
        <div class="defect-summary violations"><div class="disk"><div title="{{formatNumber criticalViolations.number "0,000"}}" class="value">{{formatNumber criticalViolations.number "0a"}}</div><div class="label">{{t "Critical Violations"}}</div></div></div>
        <div class="defect-summary"><div class="disk"><div title="{{formatNumber violatedCriticalRulePatterns.number "0,000"}}" class="value">{{formatNumber violatedCriticalRulePatterns.number "0a"}}</div><div class="label">{{t "Rules"}}</div></div></div>
	    {{else}}
        <div class="defect-summary"><div class="disk"><div title="{{formatNumber defectiveComponents.number "0,000"}}" class="value">{{formatNumber defectiveComponents.number "0a"}}</div><div class="label">{{t "Objects"}}</div></div></div>
        <div class="defect-summary violations"><div class="disk"><div title="{{formatNumber violations.number "0,000"}}" class="value">{{formatNumber violations.number "0a"}}</div><div class="label">{{t "Violations"}}</div></div></div>
        <div class="defect-summary"><div class="disk"><div title="{{formatNumber violatedRulePatterns.number "0,000"}}" class="value">{{formatNumber violatedRulePatterns.number "0a"}}</div><div class="label">{{t "Rules"}}</div></div></div>
      {{/if}}
    </div>')

    initialize: (options)->
      @options = _.extend({}, options)
      @model = options.model

    render: ()->
      @template(_.extend({
          onlyCritical: facade.portal.getFilterSetting('criticalsOnly')
        }, @options.model.toJSON()))
  })

  backbone.View.extend({
    template: Handlebars.compile('<div class="component-browser-view">
        <h1>{{t "Application Browser"}}</h1>
        <div class="table-holder" id="tree-holder"></div>
        <footer id="defects-summary"></footer>
      </div>')

    initialize: (options)->
      @options = _.extend({}, options)
      @businessCriterion = "60017"
      @businessCriterion = "60016" if facade.context.get('isSecurity')
      @model = new facade.models.componentBrowserTree.ComponentRoot({snapshotId: facade.context.get('snapshot').getId()})
      facade.bus.on('component-selection', @renderDefectSummary, @)
      facade.bus.on('global-filter-change:criticalsOnly',this.updateFilterState,this)

    remove:()->
      facade.bus.off('global-filter-change:criticalsOnly',this.updateFilterState)

    updateFilterState: ()->
      $footer = this.$el.find('footer')
      defectSummaryView = new DefectSummaryView({model: @defectSummary})
      $footer.html(defectSummaryView.render())

    updateModel: (options)->

    updateViewState: (parameters)->
      componentSame = parameters.component? and @options.component == parameters.component
      businessFilterSame = @options.filterBusinessCriterion == parameters.filterBusinessCriterion
      return if componentSame and businessFilterSame

      @options.component = parameters.component
      @options.filterBusinessCriterion = parameters.filterBusinessCriterion
      @render() if parameters.isSearch == '1'

      unless componentSame
        if !@options.component? and !parameters.inZoom
          @render()
      else
        unless businessFilterSame
          @renderDefectSummary()
      return

    renderDefectSummary: ()->
      data = @selectedNode
      componentId = data.href.split('/')[2]
      if !@options.component? or @options.component != componentId
        facade.bus.emit('navigate',
          {page: "componentsInvestigation/" + componentId, replace: true})
      @defectSummary = new facade.models.componentBrowserTree.DefectsSummary({
        href: data.defectsSummary.href
        businessCriterion: @options.filterBusinessCriterion
      })
      view = @
      $footer = view.$el.find('footer')
      $footer.html('')
      facade.ui.spinner($footer)
      @defectSummary.getData({
        success: () ->
          view.updateFilterState()
          view.onLoadSelection = true
        error: ()->
          console.error arguments
      });
      return

    render: ()->
      view = @
      view.$el.html(view.template())
      if @options.component?
        selected = CENTRAL_DOMAIN + '/tree-nodes/' + @options.component +
          '/snapshots/' + facade.context.get('snapshot').getId()
      else
        selected = @model.getHref()

      options = {
        title: t('Object Name')
        roots: [
          @model.getHref()
        ]
        expand: 1
        selectedNode: selected
        startRow: 1
        nbRows: 100
      }

      tree = new facade.bootstrap.TreeExplorer(options);

      @onLoadSelection = !@options.component?
      tree.on('node:clicked', (data) ->
        view.selectedNode = data
        facade.bus.emit('component-selection', data)
      )

      view.$el.find('#tree-holder').html(tree.render())
      view.$el
  })
