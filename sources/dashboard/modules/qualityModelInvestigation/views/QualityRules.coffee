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
    template: Handlebars.compile('<div class="metric-page" id="quality-rules">
          <div class="content-header">
            <h1>{{t "Rules..."}}</h1>
          </div>
          <div class="tag-drill-down" id="tag"></div>
          <div class="content-actions">
            <a title="{{t "download all data as excel file"}}" class="download-file">{{t "Download Excel"}}</a>
            <a id="bookmark-icon" title="{{t "add bookmark to the homepage"}}" class="{{#if bookmarkDisabled}}inactive{{/if}}
                {{#if bookmarked}}icon-bookmark-on{{else}}icon-bookmark-off{{/if}}"></a>
          </div>
          <div id="table-holder" class="table-holder"></div>
        </div>')

    preTemplate:'<div class="loading"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    preRender:()->
      @rendered = false
      _.delay(()=>
        return if @rendered
        @$el.html(@preTemplate)
      , 500)

    events:
      'click #bookmark-icon.icon-bookmark-off': 'addBookmark'
      'click #bookmark-icon.icon-bookmark-on': 'removeBookmark'
      'click .download-file':'downloadAsExcelFile'

    initialize: (options)->
      @options = _.extend({}, options)
      @options.business = facade.portal.getTQIifBCisFiltered(@options.business)
      @tags = facade.portal.get('configuration')?.ruleTag
      snapshot = facade.context.get('snapshot')
      lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds()
      @tagModel = new facade.models.TagResults({tags:@tags, href:SELECTED_APPLICATION_HREF, snapshotId: snapshot.getId()})
      if facade.context.get('module')
        modulesInPreviousSnapshot = facade.context.get('modulesInPreviousSnapshot')
        prevSnapshotModules = modulesInPreviousSnapshot.pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(facade.context.get('module').get('name'))
        lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds().splice('1') if isModuleAvailable < 0

      @model = new facade.models.QualityRulesResults({
        href:SELECTED_APPLICATION_HREF,
        technicalCriterion: @options.technical
        business:@options.business
        module:facade.context.get('module')
        technology:facade.context.get('technologies').getSelectedEncoded()
        snapshotId: snapshot.getId()
        lastTwoSnapshotIds: lastTwoSnapshotIds
        risk: @options.risk
      })
      @educationModel = new facade.models.education.EducationSummary([],{
        href:facade.context.get('snapshot').get('href')
      })
      @tagsAvailable = false
      @tagModel.getData({
        success:(results)=>
          if results.length != 0
            @tagsAvailable = true
      })
      @educationModel.getData({async: false})
      facade.bus.on('global-filter-change:criticalsOnly', this.onFilterUpdate, this)

    downloadAsExcelFile:()->
      href = @downloadLinkUrl
      $.ajax('url': REST_URL + 'user', 'async': false)
        .success(()->
          window.location = href if href?
        )
      return false

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

    adjustScroll:(rowIndex)->
      setTimeout(()=>
        selected = @$el.find('#table-holder table tbody tr[data-index="' + rowIndex + '"]')
        selected.closest('.content').scrollTop(selected[0]?.offsetTop);
      , 500)

    updateRiskModel:(parameters)->
      snapshot = facade.context.get('snapshot')
      module = facade.context.get('module')
      lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds()
      if module
        prevSnapshotModules = facade.context.get('modulesInPreviousSnapshot').pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(module.get('name'))
        lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds().splice('1') if isModuleAvailable < 0

      @model = new facade.models.QualityRulesResults({
        href:SELECTED_APPLICATION_HREF,
        technicalCriterion: @options.technical
        business:@options.business
        module:facade.context.get('module')
        technology:facade.context.get('technologies').getSelectedEncoded()
        snapshotId: snapshot.getId()
        lastTwoSnapshotIds: lastTwoSnapshotIds
        risk: @options.risk
      })
      @preRender()
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload technical criteria view', e)
      })

    updateViewState:(parameters)->
      sameModule = @model.get('module')?.getId() == facade.context.get('module')?.getId()
      sameTechnology = @model.get('technology') == facade.context.get('technologies').getSelectedEncoded()
      if sameModule and sameTechnology
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
      @options.business = parameters.business
      @options.technical = parameters.technical
      @options.risk = parameters.risk
      @options.rule = parameters.rule
      return unless @options.technical?
      @updateRiskModel(parameters)
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
        violationsVariation: {header:'<label>&#xe618;&#xe63a;</label>', headerMin:'#xe618;#xe63a;', title:t('Violation evolution since previous snapshot'), align: 'right', length: 3, sort:(a, b, increasing)->
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
      return [headers.addedCriticalViolationCount, headers.removedCriticalViolatioCount,headers.violationsCount, headers.violationsVariation, headers.qualityRuleName, headers.weight, headers.critical]

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
        @$el.find('#table-holder').append('<div class="no-table-content">' + t('No Rules found when filtering on critical violations') + '</div>')
        @$el.find('#bookmark-icon').addClass('inactive')
      @$el.find('#table-holder li[data-ref="1"]').addClass('selected')
      if selectedItemBecomesInvisible and @selectionChanged
        if 0 == @$el.find('tr[data-criticity="1"] td').length
          facade.bus.emit('navigate', {page:"qualityInvestigation/#{@options.risk}/" + @options.business + "/" + @options.technical})
        $(@$el.find('tr[data-criticity="1"] td')[0]).closest('.content').scrollTop(0);
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

    filterCriticity:(options = {})->
      @$el.find('#table-holder tbody tr').hide() if @$el.find('#tag li.selected').text() != "All Tags"
      @$el.find('#table-holder li').removeClass('selected')
      @$el.find('#table-holder .no-table-content').remove()
      if @$el.find('#tag li').hasClass('selected') and @$el.find('#tag li.selected').text() != 'All Tags'
        @filterTagRules($('#tag li.selected').text())
      else
        if facade.portal.getFilterSetting('criticalsOnly')
          @_filterCriticityCriticals(options)
        else
          @_filterCriticityShowAll(options)

    filterEducatedRules: (isSort)->
      @educationModel.getData({async: false}) if isSort?.sorting
      for rule in @educationModel.models
        ruleNameSpan = @$el.find(".rule-name[data-ruleid*='#{rule.get('rulePattern').href.split('/')[2]}']")
        if rule.get('active') then ruleNameSpan?.addClass("educate-icon") else ruleNameSpan?.addClass("educate-icon disabled")

    filterRows: (rows, risk) ->
      return rows if risk != 'risk'
      filteredResults = []
      for row in rows.models
        if((row.attributes.columns[0] or row.attributes.columns[1]) and (row.attributes.columns[0] != 'n/a' and row.attributes.columns[1] != 'n/a'))
          filteredResults.push(row)
      rows.models = filteredResults
      return rows

    filterRules:()->
      @$el.find('#table-holder tbody tr').removeClass('selected')
      _.first(_.filter(_.map(@$el.find('#table-holder tbody tr'), (row)=>
        return $(row) if $(row).attr('style') == '' or $(row).attr('style') == undefined
      ), (data) => data))?.addClass('selected')
      $(@$el.find('#table-holder tbody tr.selected td')[0]).click()

    noTableContent: (options)->
      @$el.find('#table-holder').append('<div class="no-table-content">' + t('No Rules found when filtering on Tag') + '</div>')
      facade.bus.emit('navigate', {page:"qualityInvestigation/#{@options.risk}/" + @options.business + "/" + @options.technical})

    filterTagRules: (parameter)->
      @$el.find('#table-holder .no-table-content').remove()
      @tagRulesModel = new facade.models.TagsDetailResults({
        tags: parameter,
        href: SELECTED_APPLICATION_HREF,
        snapshotId: @options.snapshotId
      })
      @tagRulesModel.getData({
        success: (results)=>
          @$el.find('#table-holder tbody tr').hide()
          if results.length == 0
            @noTableContent()
            return
          tagIDs = _.map(results[0].applicationResults, (item)=> return item.reference.key)
          rows = _.filter(@$el.find('#table-holder tbody tr *[data-ruleid]'), (row) => return row if _.contains(tagIDs,$(row).attr('data-ruleid')))
          if facade.portal.getFilterSetting('criticalsOnly')
            _.each(rows,(row)=> $(row).parents('tr').show() if $(row).parents('tr').attr('data-criticity') == "1")
          else
            _.each(rows,(row)=> $(row).parents('tr').show())
          if @$el.find('#table-holder tbody tr:visible').length == 0
            @noTableContent()
          if @$el.find('#table-holder tbody tr.selected').attr('style')
            @filterRules()
      })

    updateRules: (parameter)->
      return if $('#tag li .label').hasClass('disabled') and parameter != "All Tags"
      localStorage.setItem('selectedTag',parameter)
      @$el.find('#tag li').removeClass('selected')
      @$el.find('#tag li:has(.text:contains("' + parameter + '"))').addClass('selected')
      @$el.find('#tag .selector .text').text(parameter)
      if parameter != "All Tags"
        @filterTagRules(parameter)
      else
        @filterCriticity({sorting:true})

    renderTable: (options, row, rowIndex)->
      @$el.find('#table-holder').html(@table.render())
      @filterEducatedRules()
      @$el.find('#table-holder').after("<div class='risk-table-message'><i>" + t('This displayed information is restricted to metrics with added and removed violations only linked to the Risk Introduced tile') + "</i></div>") if @options.risk == 'risk'
      @filterCriticity(options)
      @table.on('row:clicked', @onTableSelection, @)
      @onTableSelection(row,rowIndex)
      @table.on('sorted', ()=>
        @filterCriticity({sorting:true})
        @filterEducatedRules({sorting:true})
      , @)

    menuItems:(tag)->
      {text: Handlebars.compile('<span class="text">'+ t(tag)+'</span>')(),
      tagName: tag
      action: (options)=>
        @updateRules(options.tagName)
      }
    updateMenu:(parameter)->
      @$el?.find('#tag li:not(:first-child) .label').addClass('disabled').parent().attr('title','This Tag is not available for this application')
      localStorage.setItem('selectedTag','All Tags')
      @updateRules(parameter)

    render: (options)->
      @rendered = true
      rows = @model.asRows({
        selectCriterion:@options.rule
        onlyViolations:true
      })
      items = []
      items.push(@menuItems("All Tags"))
      if @tags?
        for tag in @tags
          items.push(@menuItems(tag))
        @menu = new facade.bootstrap.Menu({
          text: Handlebars.compile('<span class="add"></span><span class="text">{{t "All Tags"}}</span><span class="tooltiptext">{{t "Filter Rules based on Tag"}}</span>')
          class: 'light-grey right'
          items: items
        });
      else
        localStorage.setItem('selectedTag','')
      rows = @filterRows(rows, @options.risk)
      row = rows.findWhere({'selected':true})
      rowIndex = -1
      for row, key in rows.models
        if rows.models[key].get('selected')
          rowIndex = key
          break
      if @options.rule? and row?
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

      @downloadLinkUrl = @model.exportUrl()
      @$el.html(@template({
        bookmarkDisabled:bookmarkDisabled
        bookmarked: bookmarked
      }))

      @table = new facade.bootstrap.Table({
        columns:@_generateColumnHeaders()
        selectOnClick:true
        click:true
        rows:rows
      })
      @renderTable(options, row, rowIndex)
      if @tags?
        @$el.find('#tag').html(@menu.render())
      @$el.find('#tag .cont .options').attr('data-before', t('Select a Tag'))
      if @tagsAvailable == false
        @$el?.find('#tag li:not(:first-child) .label').addClass('disabled').parent().attr('title','This Tag is not available for this application')
        @updateRules('All Tags')
      if _.contains(@tags,localStorage.getItem('selectedTag'))
        @$el.find('#table-holder tbody tr').hide()
        @updateRules(localStorage.getItem('selectedTag'))
      else
        @$el.find('#tag li:first').addClass('selected')
      addBookmarkHelpviewOptions = {
        $target:@$el.find('#bookmark-icon'),
        anchor:'left',
        position:'bottom-left',
        title:t('Add Bookmark'),
        content:t('You can click on this button to create a new tile in the homepage for the current rule you are looking at.')
      }
      facade.bus.emit('help:createView',addBookmarkHelpviewOptions)
      setTimeout (->
        $(window).resize()
        ), 100
      @$el

    onTableSelection:(item,rowIndex) ->
      @adjustScroll(rowIndex) if rowIndex?
      return unless item?.extra?.qualityRule?
      if item.extra.qualityRule != @options.rule
        @options.rule = item.extra.qualityRule
        panels = facade.portal.getDefaultPanels()
        bookmarked = false
        if 'quality-rules' == item.extra.type
          for panel in panels
            if "RuleViolationsModelBookmark" == panel.type
              continue unless @options.rule == panel.parameters.rule
              continue unless @options.technical == panel.parameters.technical
              continue unless @options.business == panel.parameters.business
              bookmarked = true
              break
        else
          disabled = true

        $bookmarkEle = @$el.find('#bookmark-icon')
        if disabled? and disabled
          $bookmarkEle.addClass('inactive')
          $bookmarkEle.removeClass('icon-bookmark-on')
          $bookmarkEle.addClass('icon-bookmark-off')
        else
          $bookmarkEle.removeClass('inactive')
          if bookmarked
            $bookmarkEle.removeClass('icon-bookmark-off')
            $bookmarkEle.addClass('icon-bookmark-on')
          else
            $bookmarkEle.removeClass('icon-bookmark-on')
            $bookmarkEle.addClass('icon-bookmark-off')
      facade.bus.emit('navigate', {page:"qualityInvestigation/#{@options.risk}/" + @options.business + "/" + @options.technical + '/' + item.extra.qualityRule})

  })
