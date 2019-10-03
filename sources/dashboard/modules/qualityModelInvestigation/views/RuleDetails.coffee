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

  DistributionSection = DistributionSection(facade)
  DocumentationSection = DocumentationSection(facade)
  ComputingDetailsSection = ComputingDetailsSection(facade)

  backbone.SectionContainerView.extend({
    bus: facade.bus
    localId: 'qi_'
    initialize:(options)->
      options.facade = facade
      localStorage.removeItem('filterViolationsByStatus') if options.APDrillDown == "_ap"
      localStorage.setItem('selectedTag','All Tags') if localStorage.getItem('selectedTag') != 'All Tags'
      @sections= [
        {
          id: 'violations'
          title:t('Violations')
          notifications:
            value:(options, callback)->
              moduleHref = facade.context.get('module')?.getHREF()
              model = new facade.models.QualityRuleComputingDetail({
                applicationHref: SELECTED_APPLICATION_HREF
                moduleHref:moduleHref
                snapshotId: facade.context.get('snapshot').getId()
                qualityRuleId: options.rule
                technology:facade.context.get('technologies')?.getSelectedEncoded()
              })
              model.getData({
                success:()->
                  violationRatio = model.getViolationRatio()
                  if violationRatio?
                    callback(violationRatio.failedChecks)
              })
          selected: if options.APDrillDown == "_edu" then false else true
          openedByDefault: if options.APDrillDown == "_edu" then false else true
          View: facade.backbone.ViolationDetailView.ObjectViolationSectionView.extend({
          title: t('Violations')
          theme:'background-orange'
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
            @model = new facade.models.violations.Violations([], {
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
            if options.APDrillDown == '_ap' then rows = @nbRows else rows = @nbRows + 1
            @model = new facade.models.violations.Violations([], {
              applicationHref: window.SELECTED_APPLICATION_HREF
              moduleHref:facade.context.get('module')?.getHREF()
              snapshotId: facade.context.get('snapshot').getId()
              technology:facade.context.get('technologies').getSelectedEncoded()
              qualityRuleId: @rule
              businessCriterionId: @options.business
              nbRows: rows
              startRow: @startRow
              status:@status
            })

          getViolationAndRenderShowMore:(options)->
            el = @$el if @$el?
            options = @options
            moduleHref = facade.context.get('module')?.getHREF()
            model = new facade.models.QualityRuleComputingDetail({
              applicationHref: SELECTED_APPLICATION_HREF
              moduleHref:moduleHref
              snapshotId: facade.context.get('snapshot').getId()
              qualityRuleId: @options.rule
              technology:facade.context.get('technologies')?.getSelectedEncoded()
              selectedStatus: @status
            })
            that = this
            model.getData({
              success:()->
                violationRatio = model.getViolationSummary()
                that._renderShowMoreSelector(el,violationRatio, that.nbRows)
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

          adjustScroll:(el, itemId)->
            setTimeout(()=>
              selected = el.find('#table-holder table tbody tr[data-id="' + itemId + '"]')
              selected.closest('.sections-content').scrollTop((selected or selected[0]).offsetTop)
            , 500)

          onViolationSelection: (item)->
            el = @$el
            @tableViewState()
            @adjustScroll(el,item.id) if item.id
            @selectedRow = item
            @options.component = item.extra.componentId
            facade.bus.emit('navigate', {page: "qualityInvestigation/#{@options.risk}/" + @options.business + "/" + @options.technical + '/' + @rule + '/' + item.extra.componentId})

          componentSelection: ()->
            facade.bus.emit('navigate', {page: "qualityInvestigation/#{@options.risk}/" + @options.business + "/" + @options.technical + '/' + @rule + '/none'})

          generateMessage: ()->
            return ''
          })
          ClosedView: facade.backbone.ViolationDetailView.ObjectViolationCloseView
          filters:['quality-rules']
        }
        {
          id: 'distributions'
          title: t('Distributions')
          selected: true
          View: DistributionSection.DistributionSectionView
          filters:['quality-distributions']
        }
        {
          id: 'computing-details'
          title: t('Computing details')
          View: ComputingDetailsSection.ComputingDetailSectionVIew
          ClosedView:ComputingDetailsSection.ComputingDetailCloseVIew
          filters:['quality-rules','quality-measures']
        }
        {
          id: 'documentation'
          openedByDefault: true if options.APDrillDown == "_edu"
          selected: true if options.APDrillDown == "_edu"
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
      backbone.SectionContainerView.prototype.initialize.apply(this, arguments)
      facade.bus.on('display:documentation', ()->
        this.navigateToSection('documentation')
        this.openSection(@localId + 'documentation')
      , this)
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
