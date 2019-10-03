QualityRulesView = (facade)->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  numeral = facade.numeral
  t = facade.i18n.t

  loadTitle=(type)->
    switch type
      when 'quality-measures'
        t('This is a Quality Measure. It will not provide objects in violations but give you information about specific situation at module level. Please see official documentation to understand how a grade is calculated on a quality measure.')
      when 'quality-distributions'
        t('This is a Quality Distribution. It will not provide objects in violations but give you information about how are categorized your objects. Please see official documentation to understand how a grade is calculated on a quality distribution.')
      else null

  templateRuleName = Handlebars.compile(
      '<span class="{{grey}} rule-name" data-ruleid = {{ruleId}} {{#if deactiveRuleInfo}}title="{{t "This rule is no more activated for this snapshot. it can be due to Risk Model configuration or modification in the source code that remove the scope of object identified by the rule."}}"{{/if}}>{{name}}</span>
      {{#if informationTitle}}<span title="{{informationTitle}}" class="information-icon {{grey}}"></span>{{/if}}'
    )

  formatRuleName = (value, model) ->
    templateRuleName({
      grey: facade.tableHelpers.isGreyScore4(model),
      ruleId: model.extra.qualityRule
      name: value,
      informationTitle: loadTitle(model.extra.type),
      deactiveRuleInfo: model.extra.isGone
    })


  backbone.View.extend({
    template: Handlebars.compile('<div class="metric-page transaction-page" id="quality-rules">
          <div class="content-header">
            <h1>{{t "Rules..."}}</h1>
          </div>
          <div class="content-actions">
            <!--<a target="_blank" href="{{downloadLink}}" title="{{t "download all data as excel file"}}" class="download-file">{{t "Download Excel"}}</a>-->
            <!--<a id="bookmark-icon" title="{{t "add bookmark to the homepage"}}" class="{{#if bookmarkDisabled}}inactive{{/if}}
                {{#if bookmarked}}icon-bookmark-on{{else}}icon-bookmark-off{{/if}}"></a>-->
          </div>
          <div id="table-holder" class="table-holder"></div>
        </div>')

    preTemplate:'<div class="loading {{theme}}"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    preRender:()->
      @rendered = false
      _.delay(()=>
        return if @rendered
        @$el.html(@preTemplate)
        @$el.find('.loading').addClass(@options.theme)
      , 500)

    events:
      'click #bookmark-icon.icon-bookmark-off': 'addBookmark'
      'click #bookmark-icon.icon-bookmark-on': 'removeBookmark'

    initialize: (options)->
      @options = _.extend({}, options)
      snapshot = facade.context.get('snapshot')
      @model = new facade.models.transactions.TransactionResultsForQualityRules([], {
        snapshotId:facade.context.get('snapshot').getId()
        transactionId:@options.transactionId
        businessCriterion:options.business
        technicalCriterion:options.technical
      })
      @educationModel = new facade.models.education.EducationSummary([],{
        href:facade.context.get('snapshot').get('href')
      })
      @educationModel.getData({async: false})
      facade.bus.on('global-filter-change:criticalsOnly', this.onFilterUpdate, this)

    onFilterUpdate:()->
      @selectionChanged = true # FIXME try and simplify this mechanism
      @filterCriticity()
      @selectionChanged = false

    remove:()->
      facade.bus.off('global-filter-change:criticalsOnly', this.onFilterUpdate)

    removeBookmark:(event)->
      return unless @options.rule?
      facade.bus.emit('bookmark:remove',{
        type:'RuleViolationsModelBookmark'
        findInTiles:(tiles)=>
          results = []
          for tile in tiles
            tileParameters = tile.get('parameters')
            continue unless tileParameters.rule == @options.rule
            continue unless tileParameters.technical == @options.technical
            continue unless tileParameters.business == @options.business
            results.push(tile)
          return results
      })

      $target = $(event.target)
      $target.removeClass('icon-bookmark-on')
      $target.addClass('icon-bookmark-off')

    addBookmark:(event)->
      return unless @options.rule?
      businessCriterion = facade.context.get('scope').businessCriterionList
      contributors = @model._contribution?.get('gradeContributors')
      critical = false
      if contributors?
        for contributor in contributors
          if (contributor.key == @options.rule)
            critical = contributor.critical
      facade.bus.emit('bookmark:add', {
        type:'RuleViolationsModelBookmark'
        rule:@options.rule
        business:@options.business
        technical:@options.technical
        critical:critical
        color:'grey-light'
      })

      $target = $(event.target)
      $target.removeClass('icon-bookmark-off')
      $target.addClass('icon-bookmark-on')

    updateViewState:(parameters)->
      if @options.transactionId == parameters.transactionId
        if @options.business == parameters.business and @options.technical == parameters.technical
          if @options.rule == parameters.rule
            return if parameters.component?
            @filterCriticity({silent:true})
            return
          @options.rule = parameters.rule
          @table.select('qualityRule', @options.rule, true)
          if !@options.rule?
            @$el.find('#bookmark-icon').addClass('inactive')
            @$el.find('#bookmark-icon').removeClass('icon-bookmark-on')
            @$el.find('#bookmark-icon').addClass('icon-bookmark-off')
          else
            @filterCriticity()
          return
      @options.transactionId = parameters.transactionId
      @options.business = parameters.business
      @options.technical = parameters.technical
      @options.rule = parameters.rule
      return unless @options.technical?
      snapshot = facade.context.get('snapshot')
      @model = new facade.models.transactions.TransactionResultsForQualityRules([], {
        snapshotId:facade.context.get('snapshot').getId()
        transactionId:@options.transactionId
        businessCriterion:@options.business
        technicalCriterion:@options.technical
      })
      @preRender()
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload technical criteria view', e)
      })
      return

    _generateColumnHeaders:()->
      headers = {
        # score:{header:'score', headerMin:'#xe610;',title:'Score', length: 3, format:(value, group, row, model)->
        #   return facade.tableHelpers.formatRuleScore(value,model)
        # }
        # scoreVariation:{header:'% evolution',title:'Score evolution since previous snapshot', align:'right nowrap', headerMin:'#xe610;#xe63a;', length: 3, format:(value, group, row, model)->
        #   return facade.tableHelpers.formatVariation(value,model)
        # }
        addedCriticalViolationCount:{header:'<label>&#xe618;</label>', headerMin:'#xe618;',title:t('Added violations count'), align:'critical-count-label new right', length:4, format:(value, group, row, model)->
          return '<span class="critical-count" title="'+value+'">'+value+'</span>' if value == 0 or value == 'n/a'
          return '<span class="critical-count added" title="'+numeral(value).format('0,000')+'">+ '+numeral(value).format('0,000')+'</span>'
        sort:(a, b, increasing)->
          valA = a.columns[0]
          valB = b.columns[0]
          return 0 if valA == valB
          if increasing
            return 1 if isNaN(valA)
            return -1 if isNaN(valB)
          else
            return -1 if isNaN(valA)
            return 1 if isNaN(valB)
          return valB - valA
        }
        removedCriticalViolatioCount:{header:'<label>&#xe618;</label>', headerMin:'#xe618;',title:t('Removed violations count'), align:'critical-count-label fix right', length:4, format:(value, group, row, model)->
          return '<span class="critical-count" title="'+value+'">'+value+'</span>' if value == 0 or value == 'n/a'
          return '<span class="critical-count removed" title="'+numeral(value).format('0,000')+'">- '+numeral(value).format('0,000')+'</span>'
        sort:(a, b, increasing)->
          valA = a.columns[1]
          valB = b.columns[1]
          return 0 if valA == valB
          if increasing
            return 1 if isNaN(valA)
            return -1 if isNaN(valB)
          else
            return -1 if isNaN(valA)
            return 1 if isNaN(valB)
          return valB - valA
        }
        qualityRuleName:{header:t('Name'), align: 'left',title:t('Rule Name'), format:(value, group, row, model)->
          return formatRuleName(value, model)
        }
        violationsCount:{header:'<label>&#xe618;</label>', headerMin:'#xe618;', title:t('Number Of Violations'), align: 'right', length: 3, sort:(a, b, increasing)->
          valA = a.columns[2]
          valB = b.columns[2]
          return 0 if valA == valB
          if increasing
            return 1 if isNaN(valA)
            return -1 if isNaN(valB)
          else
            return -1 if isNaN(valA)
            return 1 if isNaN(valB)
          return valB - valA
        format:(value, group, row, model)->
          return facade.tableHelpers.formatViolation(value,model)
        }
        violationsVariation: {header:t('% evolution'), headerMin:'#xe618;#xe63a;', title:t('Violation evolution since previous snapshot'), align: 'right', length: 3, sort:(a, b, increasing)->
          valA = a.columns[3]
          valB = b.columns[3]
          return 0 if valA == valB
          if increasing
            return 1 if isNaN(valA)
            return -1 if isNaN(valB)
          else
            return -1 if isNaN(valA)
            return 1 if isNaN(valB)
          return valB - valA
        format:(value, group, row, model)->
          return facade.tableHelpers.formatVariation(value, model)
        }
        weight:{header:'<label>&#xe612;</label>', headerMin:'#xe612;', title:t('Weight'), align: 'right', length: 3, format:(value, group, row, model)->
          return facade.tableHelpers.formatWeight(value, model)
        }
        critical:{header:'&#xe616;', headerMin:'#xe616;',title:t('Critical Rule'), length: 3, align: 'right status icon',
        format:(value, group, row, model)->
          return facade.tableHelpers.formatCritical(value,model)
        sort:(a, b, increasing)->
           return 0 if a.columns[6] == b.columns[6]
           return 1 if b.columns[6]
           return -1
        }
      }
      return [headers.addedCriticalViolationCount, headers.removedCriticalViolatioCount,headers.violationsCount, headers.qualityRuleName, headers.weight, headers.critical]

    _filterCriticityCriticals:(options={})->
      selectedItemBecomesInvisible = @$el.find('tr.selected[data-criticity="0"]').length > 0 # if filter hides visible items
      silent = options.sorting or options.silent or false
      if selectedItemBecomesInvisible and !@selectionChanged
          facade.bus.emit('notification:message',{
            message:t('Critical rule filtering has been temporarily changed so that you can access the selected rule. The default filter hides non-critical rules.')
            title: t('Filter update')
            type:'log'
          }) unless silent
          facade.portal.get('configuration').parameters?.filterCriticity = 0
          return @_filterCriticityShowAll(options)

      visible = @$el.find('tr[data-criticity="1"]').show().length
      @$el.find('tr[data-criticity="0"]').hide()
      if 0 == visible
        @$el.find('#table-holder').append('<div class="no-table-content">' + t('No Rules found when filtering on critical violations') + '</div>')
        @$el.find('#bookmark-icon').addClass('inactive')
      @$el.find('#table-holder li[data-ref="1"]').addClass('selected')
      if selectedItemBecomesInvisible and @selectionChanged
        if 0 == @$el.find('tr[data-criticity="1"] td').length
          facade.bus.emit('navigate', {page:"transactionInvestigation/"+ @options.context + '/' +  @options.transactionId + '/' + @options.business + '/' + @options.technical} )
        $(@$el.find('tr[data-criticity="1"] td')[0]).click()

    _filterCriticityNonCriticals:(options={})->
      selectedItemBecomesInvisible = @$el.find('tr.selected[data-criticity="1"]').length > 0 # if filter hides visible items
      silent = options.sorting or options.silent or false
      if selectedItemBecomesInvisible and !@selectionChanged
        if !options.silent
          facade.bus.emit('notification:message',{
            message:t('Critical rule filtering was temporally changed so that you could access the selected rule. Default filters hides non critical rules.')
            title: t('Filter update')
            type:'log'
          }) unless silent
          facade.portal.get('configuration').parameters?.filterCriticity = 0
          @_filterCriticityShowAll(options)
          return

      visible = @$el.find('tr[data-criticity="0"]').show().length
      @$el.find('tr[data-criticity="1"]').hide()
      if 0 == visible then @$el.find('#table-holder').append('<div class="no-table-content">' + t('No Rules found when filtering on non critical violations') + '</div>')
      @$el.find('#table-holder li[data-ref="2"]').addClass('selected')
      if selectedItemBecomesInvisible and @selectionChanged
        $(@$el.find('tr[data-criticity="0"] td')[0]).click()

    _filterCriticityShowAll:()->
        visible = 0
        visible = @$el.find('tr[data-criticity="1"]').show().length
        visible += @$el.find('tr[data-criticity="0"]').show().length
        if 0 == visible then @$el.find('#table-holder').append('<div class="no-table-content">'+ t('No Rules found') + '</div>')
        @$el.find('#table-holder li[data-ref="0"]').addClass('selected')
        @$el.find('#bookmark-icon').removeClass('inactive')

    filterCriticity:(options = {})->
      @$el.find('#table-holder li').removeClass('selected')
      @$el.find('#table-holder .no-table-content').remove()
      if facade.portal.getFilterSetting('criticalsOnly')
        @_filterCriticityCriticals(options)
      else
        @_filterCriticityShowAll(options)

    filterEducatedRules: (isSort)->
      @educationModel.getData({async: false}) if isSort?.sorting
      for rule in @educationModel.models
        ruleNameSpan = @$el.find(".rule-name[data-ruleid*='#{rule.get('rulePattern').href.split('/')[2]}']")
        if rule.get('active') then ruleNameSpan?.addClass("educate-icon") else ruleNameSpan?.addClass("educate-icon disabled")

    render: (options)->
      @rendered = true

      rows = @model.asRows({
        selectCriterion:@options.rule
        onlyViolations:true
        criticalViolationsAsResults:facade.portal.getFilterSetting('criticalsOnly')
      })
      row = rows.findWhere({'selected':true})
      if @options.rule?
        panels = facade.portal.getDefaultPanels()
        bookmarked = false
        if 'quality-rules' == row.get('extra').type
          for panel in panels
            if "RuleViolationsModelBookmark" == panel.type
              continue unless @options.rule == panel.parameters.rule
              continue unless @options.technical == panel.parameters.technical
              continue unless @options.business == panel.parameters.business
              bookmarked = true
              break
        else
          bookmarkDisabled = true
      else
        bookmarkDisabled = true

      @$el.html(@template({}))
      that = @
      @table = new facade.bootstrap.Table({
        columns:@_generateColumnHeaders()
        selectOnClick:true
        click:true
        rows:rows
      })
      @$el.find('#table-holder').html(@table.render())
      @filterEducatedRules()
      @filterCriticity(options)
      @table.on('row:clicked', @onTableSelection, @)
      @table.on('sorted', ()=>
        @filterCriticity({sorting:true})
        @filterEducatedRules({sorting:true})
      , @)

      addBookmarkHelpviewOptions = {
        $target:@$el.find('#bookmark-icon'),
        anchor:'left',
        position:'bottom-left',
        title:t('Add Bookmark'),
        content:t('You can click on this button to create a new tile in the homepage for the rule indicator you are looking at.')
      }
      facade.bus.emit('help:createView',addBookmarkHelpviewOptions)
      setTimeout (->
        $(window).resize()
      ), 100
      @$el

    onTableSelection:(item) ->
      return unless item?.extra?.qualityRule?
      facade.bus.emit('navigate', {page:"transactionInvestigation/"+ @options.context + '/' +  @options.transactionId + '/' + @options.business + '/' + @options.technical + '/' + item.extra.qualityRule} )

  })
