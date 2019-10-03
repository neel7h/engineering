RuleDetails = (facade) ->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  DocumentationSection = DocumentationSection(facade)

  backbone.SectionContainerView.extend({
    bus: facade.bus
    viewId:'Rule details'
    localId: 'ci_'
    initialize:(options)->
      options.facade = facade
      backbone.SectionContainerView.prototype.initialize.apply(this, arguments)
      facade.bus.on('display:documentation', ()->
        this.navigateToSection('documentation')
        this.openSection(@localId + 'documentation')
      , this)
    sections: [
      {
        id: 'violations'
        title: t('Violations')
        notifications:
          value:(options, callback)->
            # TODO SUB-OPTIMAL, try and improve when api provide parameter to get only one rule at a time
            selectedNode = REST_URL + CENTRAL_DOMAIN + '/tree-nodes/' + options.component +
              '/snapshots/' + facade.context.get('snapshot').getId()
            model = new facade.models.QualityRuleWithViolationForComponent([],{
              selectedNode:selectedNode
              businessCriterion: if facade.context.get('isSecurity') then "60016" else options.filterBusinessCriterion
            })
            model.getData({
              success:()->
                ruleHRef = CENTRAL_DOMAIN + '/rule-patterns/' + options.rule
                for violatedRule in model.models
                  if violatedRule.get('rulePattern').href == ruleHRef
                    value = violatedRule.get('violations').number
                    return callback(value)
                callback('-')
            })
        selected: true
        openedByDefault:true
        View: facade.backbone.ViolationDetailView.ObjectViolationSectionView.extend({
        title: t('Violations')
        theme:'background-pink'
        events:
          'click .export':'downloadAsExcelFile'
          'click .educate':'goToEducation'

        callModel: (options)->
          @model = new facade.models.violations.ComponentViolations([], {
            applicationHref: window.SELECTED_APPLICATION_HREF
            snapshotId: facade.context.get('snapshot').getId()
            component: @options.rootComponent
            qualityRuleId: @rule
            businessCriterionId: if @businessCriterion == "60016" then "60016" else @options.filterBusinessCriterion
            nbRows: @startRow + @nbRows
            startRow: 1
            status: @status
          })

        updateModel:(options)->
          @options = _.extend({}, options)
          @options.rootComponent = options.component # to avoid confusion between browser component and violated component in the table
          @component = options.ruleComponent
          @startRow = 1
          @rule = @options.rule
          @model = new facade.models.violations.ComponentViolations([], {
            applicationHref: window.SELECTED_APPLICATION_HREF
            snapshotId: facade.context.get('snapshot').getId()
            component: @options.rootComponent
            qualityRuleId: @rule
            businessCriterionId: if @businessCriterion == "60016" then "60016" else @options.filterBusinessCriterion
            nbRows: @nbRows + 1
            startRow: @startRow
            status:@status
          })

        getViolationAndRenderShowMore:(options)->
          el = @$el if @$el?
          options = @options
          selectedNode = REST_URL + CENTRAL_DOMAIN + '/tree-nodes/' + options.component +
            '/snapshots/' + facade.context.get('snapshot').getId()
          model = new facade.models.QualityRuleWithViolationForComponent([],{
            selectedNode:selectedNode
            rulePattern: options.rule
            selectedStatus: @status
          })
          that = this
          selectedStatus = @status
          model.getData({
            success:()->
              violationRatio = model.models[0].get('totalViolations').number if selectedStatus == null
              violationRatio = model.models[0].get('addedViolations').number if selectedStatus == "added"
              violationRatio = model.models[0].get('updatedViolations').number if selectedStatus == "updated"
              violationRatio = model.models[0].get('unchangedViolations').number if selectedStatus == "unchanged"
              that._renderShowMoreSelector(el, violationRatio, that.nbRows)
          })

        updateUrl:()->
          data = _.find(@table.options.rows.models, (model)=>
            if model.get('extra').componentId == @options.ruleComponent
              return model)
          if data == undefined and @options.ruleComponent?
            @preRender()
            @showMore(1000000)

        tableViewState:() ->
          @table?.select('componentId', @options.ruleComponent, true)

        onViolationSelection: (item)->
          @tableViewState()
          @selectedRow = item
          facade.bus.emit('navigate', {page:"componentsInvestigation/" + @options.rootComponent + "/0/" + @options.rule + '/' + item.extra.componentId})

        componentSelection: ()->
          facade.bus.emit('navigate', {page: "componentsInvestigation/" + @options.rootComponent + '/0/' + @rule + '/none'})

        generateMessage: ()->
          return  @_SelectedObjectTemplate({title: @title, name: @selectedRow.columns[1]}) if @selectedRow and @options.pageId == 'components-investigation'
          return ''
        })
      }
      {
        id: 'documentation'
        title: t('Documentation')
        View: DocumentationSection.DocumentationSectionView
        ClosedView:DocumentationSection.DocumentationClosedSectionView
      }
#      {
#        id: 'notes'
#        View: MockSectionDetailsView.extend({
#          title: 'Notes'
#        })
#      }
    ]

    updateSubviewState:(options)->
      if @options.filterBusinessCriterion == options.filterBusinessCriterion
        if @options.component == options.component
          if @options.rule == options.rule
            return if @options.ruleComponent == options.ruleComponent
            @options.ruleComponent = options.ruleComponent
            for section in @sections
              if section.sectionId == "ci_violations" and section.view?
                section.view.updateSelection(options)
                break;
            return
      @options = _.extend({}, @options, options)
      return unless @options.rule?

      for section in @sections
        if section.view?
          section.view.updateViewState?(options)
        if section.closedView?
          section.closedView.updateViewState?(options)
  })
