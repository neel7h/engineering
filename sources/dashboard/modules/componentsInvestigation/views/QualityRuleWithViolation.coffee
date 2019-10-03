# FIXME remove table helpers (create clean backbone views or handlebars helpers)
QualityRuleWithViolationView = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  TechnicalContexts = TechnicalContext(facade)

  QualityRulesSection = backbone.MetricView.extend({
    title: t('Rules')
    template: Handlebars.compile('
        <div class="detail-header">
          <div class="close-section"></div>
          <h2>{{title}}</h2>
        </div>
        <div class="table-violations" id="table-holder">
        </div>
        <footer></footer>')

    preTemplate: Handlebars.compile('
        <div class="detail-header">
          <div class="close-section"></div>
          <h2>{{title}}</h2>
        </div>
        <div class="table-violations" id="table-holder">
          <div class="loading {{theme}}"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div></div>
        </div>
        <footer></footer>')

    preRender:()->
      @rendered = false
      _.delay(()=>
        return if @rendered
        @$el.html(@preTemplate({
          title: @title
        }))
      , 10)

    initialize: (options)->
      @options = _.extend({},options)
      facade.bus.on('global-filter-change:criticalsOnly',this.onFilterUpdate,this)
      @educationModel = new facade.models.education.EducationSummary([],{
        href:facade.context.get('snapshot').get('href')
      })
      @educationModel.getData({async: false})
      @isSecurity = facade.context.get('isSecurity')
      @businessCriterion = "60017"
      @businessCriterion = "60016" if facade.context.get('isSecurity')
      return unless @options.component?
      selectedNode = REST_URL + CENTRAL_DOMAIN + '/tree-nodes/' + @options.component +
          '/snapshots/' + facade.context.get('snapshot').getId()
      @model = new facade.models.QualityRulesWithViolations({
        selectedNode:selectedNode
        businessCriterion: @options.filterBusinessCriterion
        domain:CENTRAL_DOMAIN
        snapshotId:facade.context.get('snapshot').getId()
      })

    onFilterUpdate:()->
      @selectionChanged = true
      @filterCriticity()
      @selectionChanged = false

    remove:()->
      facade.bus.off('global-filter-change:criticalsOnly',this.onFilterUpdate)

    updateViewState:(parameters)->
      return unless parameters.component?
      selectedNode = REST_URL + CENTRAL_DOMAIN + '/tree-nodes/' + parameters.component +
          '/snapshots/' + facade.context.get('snapshot').getId()
      sameNode = selectedNode == @model?.get('selectedNode')
      sameBusinessFilter =  @options.filterBusinessCriterion == parameters.filterBusinessCriterion
      if sameNode and sameBusinessFilter
        return if parameters.pageId == 'components-investigation'
        this.table.selectRow() unless parameters.rule?
        @filterCriticity({silent:true})
      else
        @filterCriticity()

      @options = _.extend({},parameters)
      @model = new facade.models.QualityRulesWithViolations({
        selectedNode:selectedNode
        businessCriterion: @options.filterBusinessCriterion
        domain:CENTRAL_DOMAIN
        snapshotId:facade.context.get('snapshot').getId()
      })
      @preRender()
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload rule with violations view', e)
      })
      return

    _filterCriticityCriticals:(options={})->
      selectedItemBecomesInvisible = @$el.find('tr.selected[data-criticity="0"]').length > 0 # if filter hides visible items
      silent = options.sorting or options.silent or false
      if selectedItemBecomesInvisible and !@selectionChanged
        facade.bus.emit('notification:message',{
          message:t('Critical rule filtering has been temporarily changed so that you can access the selected Rules. The default filter hides non-critical rules.')
          title: t('Filter update')
          type:'log'
        }) unless silent
        facade.portal.get('configuration').parameters?.filterCriticity = 0
        return @_filterCriticityShowAll(options)

      visible = @$el.find('tr[data-criticity="1"]').show().length
      @$el.find('tr[data-criticity="0"]').hide()
      if 0 == visible
        @$el.find('#table-holder').append('<div class="no-contents">' + t('No Rules found when filtering on critical violations') + '</div>')
      @$el.find('#table-holder li[data-ref="1"]').addClass('selected')
      if selectedItemBecomesInvisible and @selectionChanged
        if 0 == @$el.find('tr[data-criticity="1"] td').length
          facade.bus.emit('navigate', {page:"componentsInvestigation/" + @options.component})# navigate up one page
        $(@$el.find('tr[data-criticity="1"] td')[0]).click()

    _filterCriticityNonCriticals:(options={})->
      selectedItemBecomesInvisible = @$el.find('tr.selected[data-criticity="1"]').length > 0 # if filter hides visible items
      silent = options.sorting or options.silent or false
      if selectedItemBecomesInvisible and !@selectionChanged
        if !options.silent
          facade.bus.emit('notification:message',{
            message:t('Critical rule filtering was temporally changed so that you could access the selected rules. Default filters hides non critical rules.')
            title: t('Filter update')
            type:'log'
          }) unless silent
          facade.portal.get('configuration').parameters?.filterCriticity = 0
          @_filterCriticityShowAll(options)
          return

      visible = @$el.find('tr[data-criticity="0"]').show().length
      @$el.find('tr[data-criticity="1"]').hide()
      if 0 == visible then @$el.find('#table-holder').append('<div class="no-contents">' + t('No Rules found when filtering on non critical violations') + '</div>')
      @$el.find('#table-holder li[data-ref="2"]').addClass('selected')
      if selectedItemBecomesInvisible and @selectionChanged
        $(@$el.find('tr[data-criticity="0"] td')[0]).click()

    _filterCriticityShowAll:()->
      visible = 0
      visible = @$el.find('tr[data-criticity="1"]').show().length
      visible += @$el.find('tr[data-criticity="0"]').show().length
      if 0 == visible then @$el.find('#table-holder').append('<div class="no-contents">'+ t('No Rules found') + '</div>')
      @$el.find('#table-holder li[data-ref="0"]').addClass('selected')

    filterCriticity:(options = {})->
      @$el.find('#table-holder li').removeClass('selected')
      @$el.find('#table-holder .no-contents').remove()
      if facade.portal.getFilterSetting('criticalsOnly')
        @_filterCriticityCriticals(options)
      else
        @_filterCriticityShowAll(options)

    filterEducatedRules: (isSort)->
      @educationModel.getData({async: false}) if isSort?.sorting
      for rule in @educationModel.models
        ruleNameSpan = @$el.find(".rule-name[data-ruleid*='#{rule.get('rulePattern').href.split('/')[2]}']")
        if rule.get('active') then ruleNameSpan?.addClass("educate-icon") else ruleNameSpan?.addClass("educate-icon disabled")

    _render: ()->
      @preRender()
      _.delay(()=>
        @rendered = true
        @$el.html(@template({title: @title}))
        return @$el unless @options.component?
        maxWeight = 0
        rows = @model.asRows({
          selectCriterion:@options.rule
          onlyViolations:true
          })

        state = -1
        @table = new facade.bootstrap.Table({
          columns:[
            {header:t('name'), title:t('Name'), align: 'left', length:10, format:(value, group, row, item)->
              return "<span class='rule-name' data-ruleid = #{item.extra.qualityRule}> #{value} </span>"
            }
            {header:t('#VIOLATIONS'), headerMin:'#xe618;', title:t('Number Of Violations'), align:'right' ,length:5, format:(value)->
              return '<span class="violation">' + facade.numeral(value).format('0,000') + '</span>'
            }
            {header: t('weight'), headerMin:'#xe612;', title:t('Weight'), length: 2, align:'right',format:(value, columnId, rowId, item) ->
              return facade.tableHelpers.formatWeight(value, item)
            }
            {header: '<label>&#xe616;</label>', headerMin:'#xe616;',title:t('Critical Rule'), length: 3, align:'right', format:(value, group, row, item)->
              return facade.tableHelpers.formatCritical(value,item)
            }
          ],
          rows:rows
          click:true
          selectOnClick:true
        })
        @$el.find('#table-holder').html(@table.render())
        @filterEducatedRules()
        @filterCriticity(options?)
        @table.on('row:clicked', @onTableSelection, @)
        @table.on('sorted', ()=>
          @filterCriticity({sorting:true})
          @filterEducatedRules({sorting:true})
        , @)
        setTimeout (->
          $(window).resize()
          ), 100
        @$el
      , 300)

    onTableSelection:(item) ->
      return unless item?.extra?.qualityRule?
      @filterEducatedRules({sorting:true})
      facade.bus.emit('navigate', {page:"componentsInvestigation/" + @options.component + "/0/" + item.extra.qualityRule})
  })

  QualityRulesCloseSection = backbone.MetricView.extend({
    title: t('Rules')
    template:Handlebars.compile('<h2 class="close">{{{title}}}</h2><footer></footer>')

    initialize: (options)->
      @options = _.extend({},options)

    _render: ()->
      @rendered = true
      @$el.html(@template({title: @title}))
  })

  backbone.SectionContainerView.extend({
    bus: facade.bus
    localId: 'qi_'
    initialize:(options)->
      backbone.SectionContainerView.prototype.initialize.apply(this, arguments)

    sections: [
      {
        id: 'qm-violations'
        title:t('Rules')
        selected: true
        openedByDefault:true
        View: QualityRulesSection
        ClosedView: QualityRulesCloseSection
      }
      {
        id: 'technical-content'
        title:t('Technical properties')
        openedByDefault:true
        View: TechnicalContexts.TechnicalContextDetailSection
        ClosedView:TechnicalContexts.TechnicalContextCloseSection
      }
    ]

    updateSubviewState:(options)->
      @options.component = options.component
      for section in @sections
        if section.view?
          section.view.updateViewState?(options)
        if section.closedView?
          section.closedView.updateViewState?(options)
  })
