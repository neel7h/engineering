RuleDetails = (facade) ->
  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  TreeNodeCollection = backbone.Collection.extend({

    url:()->
      REST_URL + @href

    initialize:(nodes,options)->
      @href = options.href

  })

  RuleType = backbone.Model.extend({
    url: ()->
      REST_URL + CENTRAL_DOMAIN + '/quality-indicators/' + @get('rule') + '/snapshots/' + facade.context.get('snapshot').getId()
  })

  DocumentationSection = DocumentationSection(facade)

  backbone.SectionContainerView.extend({
    bus: facade.bus
    localId: 'qi_'
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
        title:t('Violations')
        notifications:
          value:(options, callback)->
            transactionViolationModel = new facade.models.violations.TransactionViolationsRatio([], {
              transactionId:options.transactionId
              snapshotId: facade.context.get('snapshot').getId()
              qualityRuleId: options.rule
            })
            transactionViolationModel.getData({
              success:()=>
                violationRatio = transactionViolationModel.getAllViolationsCount()
                if violationRatio?
                  callback(violationRatio)
            })
        selected: true
        openedByDefault:true
        View: facade.backbone.ViolationDetailView.ObjectViolationSectionView.extend({
        title: t('Violations')
        theme:'background-purple'
        events:
          'click .export':'downloadAsExcelFile'
          'click .educate':'goToEducation'
          'click .link-to-component-browser':'goToComponent'

        goToComponent:(event)->
          $t = $(event.target)
          return if !facade.context.get('snapshot').isLatest()
          return unless @selectedRow?

          treeNodeHref = @selectedRow.extra?.model?.get('component')?.treeNodes?.href
          treeNodes = new TreeNodeCollection([],{href:treeNodeHref}, @)
          that = @

          treeNodes.getData({
            success:()->
              return if treeNodes.length == 0
              hrefParts = treeNodes.at(0).get('href').split('/')
              facade.context.get('scope').set('businessCriterion', that.options.business)
              facade.bus.emit('navigate', {page: "componentsInvestigation/" + hrefParts[2]})
          })

        callModel: (options)->
          @model = new facade.models.violations.TransactionViolations([], {
            transactionId:@options.transactionId
            applicationHref: window.SELECTED_APPLICATION_HREF
            moduleHref:facade.context.get('module')?.getHREF()
            snapshotId: facade.context.get('snapshot').getId()
            technology:facade.context.get('technologies').getSelectedEncoded()
            qualityRuleId: @rule
            businessCriterionId: @options.business
            nbRows: @startRow + @nbRows
            startRow: 1
            status: @status
          })

        updateModel: (options)->
          @options = _.extend({}, options)
          @startRow = 1
          @businessCriterion = @options.business
          @technicalCriterion = @options.technical
          @rule = @options.rule
          @component = @options.component
          @model = new facade.models.violations.TransactionViolations([], {
            transactionId:@options.transactionId
            applicationHref: window.SELECTED_APPLICATION_HREF
            moduleHref:facade.context.get('module')?.getHREF()
            snapshotId: facade.context.get('snapshot').getId()
            technology:facade.context.get('technologies').getSelectedEncoded()
            qualityRuleId: @rule
            businessCriterionId: @options.business
            nbRows: @nbRows + 1
            startRow: @startRow
            status:@status
          })

        getViolationAndRenderShowMore:(options)->
          el = @$el if @$el?
          options = @options
          model = new facade.models.violations.TransactionViolationsRatio([], {
            transactionId:options.transactionId
            snapshotId: facade.context.get('snapshot').getId()
            qualityRuleId: options.rule
            selectedStatus: @status
          })
          that = this
          model.getData({
            success:()=>
              violationRatio = model.getViolationSummary()
              that._renderShowMoreSelector(el, violationRatio, that.nbRows)
          })

        updateUrl:()->
          data = _.find(@table.options.rows.models, (model)=>
            if model.get('extra').componentId == @options.component
              return model)
          if data == undefined and @options.component?
            @preRender()
            @showMore(1000000)

        tableViewState:()->
          @table?.select('componentId', @options.component, true)

        onViolationSelection: (item)->
          @tableViewState()
          @selectedRow = item
          @options.component = item.extra.componentId
          facade.bus.emit('navigate', {page:"transactionInvestigation/"+ @options.context + '/' +  @options.transactionId + '/' + @options.business + '/' + @options.technical + '/' + @rule + '/' + item.extra.componentId})

        componentSelection: ()->
          facade.bus.emit('navigate', {page:"transactionInvestigation/"+ @options.context + '/' +  @options.transactionId + '/' + @options.business + '/' + @options.technical + '/' + @rule + '/none'})

        generateMessage: ()->
          return ''
        })
        ClosedView: facade.backbone.ViolationDetailView.ObjectViolationCloseView
        filters:['quality-rules']
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
    loadFilter:(parameters)->
      deferred = $.Deferred()
      ruleType = new RuleType(parameters)
      ruleType.getData({
        success:()->
          deferred.resolve(ruleType.get('type'))
      })
      deferred
    updateSubviewState:(options)->
      if @options.moduleId == options.moduleId and @options.technology == options.technology
        if @options.rule == options.rule and @options.business == options.business
          return if @options.component == options.component
          @options.component = options.component
          for section in @sections
            if section.sectionId == "qi_violations" and section.view?
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
