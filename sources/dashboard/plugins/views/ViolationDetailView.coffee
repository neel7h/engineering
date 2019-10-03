###
  Defines the reusable Violation component.
###
ViolationDetailView = ($, _, Backbone, Handlebars) ->
  backbone = Backbone
  plugin = require('plugins/i18n/i18n') #requireing i18n
  t = plugin.Facade.i18n.t

  priorityLevel = (value)->
    switch value
      when 'extreme' then 4
      when 'high' then 3
      when 'moderate' then 2
      when 'low' then 1
      else 0

  _violationsTemplate = Handlebars.compile('<span>
     {{#if href}}
      <em class="short-content" title="{{title}}"><a class="{{state}}" href="{{href}}">&#xe91a;</a></em>
     {{else}}
      <em class="short-content" title="{{title}}"><a class="{{state}}">&#xe91a;</a></em>
     {{/if}}
   </span>')

  templateRuleName = Handlebars.compile(
    '<span class="rule-name" data-ruleid = {{ruleId}}>{{name}}</span>')

  formatRuleName = (value, group, row, model) ->
    templateRuleName({
      ruleId: model.ruleId
      name: value,
    })

  _objectNameTemplate = Handlebars.compile('<span {{#if emphases}}class="emphases"{{/if}}>
    <em class="short-content" title="{{value}}">{{ellipsisMiddle value 15 35}}</em>
    <em class="large-content" title="{{value}}">{{ellipsisMiddle value 30 45}}</em>
    <em class="super-large-content" title="{{value}}">{{value}}</em>
  </span>')

  _componentdrillDownTemplate = Handlebars.compile('<span>
    <a title="{{title}}" class="{{isEnable}}"></a>
  </span>')

  ObjectViolationCloseView = backbone.View.extend({
    title: 'Violations'
    template:Handlebars.compile('<h2 class="close">{{{title}}}</h2><footer></footer>')

    initialize: (options)->
      @facade = options.facade
      @updateModel(options)

    updateModel: (options)->
      @options = _.extend({}, options)
      @model = new @facade.models.QualityRuleComputingDetail({
        applicationHref: SELECTED_APPLICATION_HREF
        snapshotId: @facade.context.get('snapshot').getId()
        qualityRuleId: @options.rule
      })

    updateViewState:(parameters)->
      @updateModel(parameters)
      @table?.select('component', @options.component, true)
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload object violations view', e)
      })
      return

    render:()->
      @$el.html(@template({title:@title}))

  })

  ObjectViolationSectionView = backbone.View.extend({
    _SelectedObjectTemplate: Handlebars.compile('<h2>{{title}}</h2><h3>{{name}}</h3>')
    template: Handlebars.compile('
                  <div class="detail-header">
                    {{#unless advanceSearch}}<div class="close-section"></div>{{/unless}}
                    <div class="priority-drill-down disabled" id="priority-menu"></div>
                    <h2>{{title}}</h2>
                    {{#if advanceSearch}}
                      <div class="object-search">
                        <input id="search-container" placeholder="{{t "Object search"}}" value="{{searchValue}}"/><div class="searchIcon">&#xe600;</div>
                      </div>
                      <div id= "advanceSearch">
                        <div><h3 class = "filterCount"> {{t " Showing "}}{{filteredViolations}}  {{t " out of "}} {{totalViolations}}{{t " violations"}}</h3></div>
                      </div>
                    {{/if}}
                  </div>
                  <div id="table-holder" class="table-violations"></div>
                  <div class="detail-actions">
                    {{#unless advanceSearch}}
                    <div class="educate-action">
                      <a class="educate">
                        <i class="education-icon"></i><span class="education-title">{{t "educate"}}</span>
                      </a>
                    </div>
                    {{/unless}}
                    <a class="export">
                      <i class="download-file pos-2">{{t "Download Excel"}}</i><span class="download-title">{{t "download"}}</span>
                    </a>
                  </div>
                  {{#if showMore}}<div id ="show-more" class="option-selector"></div>{{/if}}
                  {{#unless advanceSearch}}<footer></footer>{{/unless}}')
    startRow: 1
# FIXME pretemplate ? looks like not a regular pattern
    preTemplate: Handlebars.compile('<div class="detail-header">{{#unless advanceSearch}}<div class="close-section"></div>{{/unless}}
                      <h2>{{title}}</h2>
                  </div>
                  <div id="table-holder" class="table-violations"><div class="loading {{theme}}"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div></div>
                  {{#unless advanceSearch}}<footer></footer>{{/unless}}')

    preRender:()->
      @rendered = false
      _.delay(()=>
        return if @rendered
        @downloadLinkUrl = @model.url() + '&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        @$el?.html(@preTemplate({
          title: @title
          theme: @options.theme
          advanceSearch: @options.pageId == 'advanceSearch'
        }))
      , 10)

    initialize: (options)->
      @options = _.extend({}, options)
      @bus = @bus or @options.bus or @options?.facade?.bus
      @facade = options.facade
      @businessCriterion = "60017"
      @businessCriterion = "60016" if @facade.context.get('isSecurity')
      if !options.APDrillDown and @model != undefined then @nbRows = 10 else @nbRows = 1000000
      @nbRows = 20 if options.pageId == 'advanceSearch'
      @isActionPlan = options.APDrillDown
      @status = localStorage.getItem('filterViolationsByStatus')
      @statusValue = switch(@status)
        when 'added' then 1
        when 'updated' then 2
        when 'unchanged' then 3
        else 0
      if options.pageId == 'advanceSearch'
        @callModel(options)
      else
        @updateModel(options)
      @emphaseAddedViolations = JSON.parse(localStorage.getItem('emphasizeAddedViolations'))
      localStorage.removeItem('emphasizeAddedViolations')
      @selectedRows = []
      @exclusionManager = @facade.context.get('user').get('exclusionManager')
      @qualityManager = @facade.context.get('user').get('qualityManager')
      @qualityAutomationManager = @facade.context.get('user').get('qualityAutomationManager')
      if options.pageId == 'advanceSearch'
        @bus.on('filterSearch',@updateViewState ,@)
        @bus.on('clearSearch',@updateViewState, @)

    filterEducation:(el)->
      @educationModel = new @facade.models.education.EducationSummary([],{
        href:@facade.context.get('snapshot').get('href')
      })
      @educationModel.getData({
        success:()=>
          ruleId = @model.params.qualityRuleId
          for model in @educationModel.models
            educatedRuleId = model.get('rulePattern').href.split('/')[2]
            if educatedRuleId == ruleId
              el?.find('.educate').addClass('disabled').parent().attr('title', t('The rule is already added to education'))
              el?.find('.priority-drill-down').find('.educate-violations').closest('li').addClass('disabled')
              if @qualityAutomationManager and !@exclusionManager and !@qualityManager
                el.find('table td:first-child').remove()
                el.find('table thead tr th:first').remove()
      })

    downloadAsExcelFile:()->
      href = @downloadLinkUrl
      $.ajax('url': REST_URL + 'user', 'async': false)
        .success(()->
        window.location = href if href?
      )
      return false

    remove:()->
      @bus.off('action-plan:updated',@updateTable)
      @bus.off('exclusion:updated',@updateTable)
      @bus.off('education:updated',@updateTable)
      @table?.remove()
      @$el.remove()
      @unbind()
      delete @$el
      delete @el;
      @stopListening()
      return @

    updateTable: (options) ->
      @callModel(options)
      if @options.pageId == "advanceSearch"
        $.when(@model.getData().done(), @EducationModel.getData().done()).then(()=> @render({resetRowSelector: true}))
      else
        @model.getData({
          success:()=>
            @render()
          error:(e)->
            console.error('failed trying to reload object violations view', e)
        })

    updateViewState:(parameters)->
      @updateModel(parameters)
      @tableViewState()
      @bus.off('action-plan:updated',@updateTable, @)
      @bus.off('exclusion:updated',@updateTable, @)
      @bus.off('education:updated',@updateTable, @)
      delete @table
      @preRender()
      @model.getData({
        success:()=>
          @render()
        error:(e)->
          console.error('failed trying to reload object violations view', e)
      })
      return

    showMore: (nbRows)->
      @startRow = @startRow + @nbRows
      @nbRows = nbRows - 1 + @startRow
      @updateModel(@options)
      @model.params.startRow = @startRow
      @model.getData({
        success: ()=>
          @render({resetRowSelector:false})
      })

    pushMenuItems:(menuItems, value)->
      item = if isNaN(value) then value else t('+' + value)
      menuItems.push({text: item, action: ()=>
          @preRender()
          if isNaN(value) then @showMore(1000000) else @showMore(value)
        })

    _renderShowMoreSelector:(el, violationRatioValue, nbRows)->
      allText = t('All')
      if violationRatioValue?
        allText = allText + " ("+ violationRatioValue + ")"
      violationsCount = @facade.portal.get('configuration').violationsCount or 5000
      if ((violationRatioValue > violationsCount and violationRatioValue < 100) or  violationRatioValue > violationsCount)
        allTextTemplate = Handlebars.compile('<span title="{{t "You cannot display a high number of violations without big performance issues"}}">'+ allText + '</span>')
      else
        allTextTemplate = Handlebars.compile('<span title="{{t "Depending on the number of violations, this request can take time"}}">'+ allText + '</span>')

      menuItems =[]
      if nbRows < violationsCount
        @pushMenuItems(menuItems, 10) if violationRatioValue > 20
        @pushMenuItems(menuItems, 100) if violationRatioValue > 110 and (violationsCount - nbRows) > 100 and (violationRatioValue - nbRows) > 100
      @pushMenuItems(menuItems,allTextTemplate)

      @showMoreMenu = new @facade.bootstrap.Menu({
        text:t('Show More')
        class: 'light-grey'
        items: menuItems
      });
      if el?
        el.find('#show-more').html(@showMoreMenu.render())
        @showMenuOptionsOnTopOrBottom()
        if nbRows >= violationsCount
          el.find('#show-more li')[0]?.classList.add('inactive')
        if violationRatioValue > violationsCount and (violationRatioValue < 100 or (violationsCount - nbRows) < 100)
          el.find('#show-more li')[1]?.classList.add('inactive')
        else if violationRatioValue > violationsCount
          el.find('#show-more li')[2]?.classList.add('inactive')
        el.find('#show-more li.selectable.no-separator.inactive').prop("disabled", true)

    showMenuOptionsOnTopOrBottom:()->
      menu = $('.cont', '#show-more').first()
      if menu?
        $(menu).removeClass('top')
        menuTop = menu.offset()?.top
        menuHeight = menu.height()
        totalMenuHeight = menuTop + menuHeight
        if totalMenuHeight >= $(window).height()
          $(menu).addClass('top')

    updateSelection:(parameters)->
      @options = {} unless @options?
      @options = _.extend(@options, parameters)
      @updateUrl()
      @tableViewState()

    onActionPlanSelection:(options)->
      if _.find(@table.getSelectedRows(),(model)-> return true if model.get('columns')[0].status == undefined)
        @$el.find('#priority-menu  li[data-ref="0"]').removeClass('disabled') if @qualityManager
        @$el.find('#priority-menu  li[data-ref="1"]').removeClass('disabled') if @exclusionManager
      else
        @$el.find('#priority-menu  li[data-ref="0"]').addClass('disabled') if @qualityManager
        @$el.find('#priority-menu  li[data-ref="1"]').addClass('disabled') if @exclusionManager
      if options.hasChecked
        @$el?.find('#priority-menu').removeClass('disabled')
      else
        @$el?.find('#priority-menu').addClass('disabled')

      isKeyPressed = options.isShift
      rowModels =  @getTableRowModels()
      @selectedRows = [] if(@table.getSelectedRows().length == 0)
      if options.hasChecked && options.row
        options.row.isShift = true if isKeyPressed
        availableIds = _.pluck(@selectedRows, 'id')
        index = availableIds.indexOf(options.row.id)
        if index < 0
          @selectedRows.push(options.row)
          numOfRows = @selectedRows.length
        else
          @selectedRows = @selectedRows.splice(index, 1)

        if isKeyPressed && @selectedRows.length > 1
          previousRow = parseInt( @$el.find('table tbody tr[data-id="' +@selectedRows[@selectedRows.length-2].id  + '"]').attr("data-index"), 10 )
          currentRow = parseInt(@$el.find('table tbody tr[data-id="' +@selectedRows[@selectedRows.length-1].id  + '"]').attr("data-index"), 10 )
          if @selectedRows[@selectedRows.length-1].isShift
            for i in [previousRow .. currentRow]
              @$el.find('table tbody tr[data-index="'+ i + '"] .row-selector input[type="checkbox"]').prop('checked', true)
              rowModels[i].attributes.rowSelected = true

    goToEducation:(event)->
      if @model.length == 0
        educateRules = {}
        educateRules.ruleName = $(".rule-name[data-ruleid*='#{@model.params.qualityRuleId}']")[0].innerText
        educateRules.href = @model.params.applicationHref.split('/')[0] + '/rule-patterns/' + @model.params.qualityRuleId
      else
        educateRules = @table.options.rows.models[0]
        educateRules.ruleName = educateRules.get('extra')?.model.get('rulePattern').name
      @addToEducationDialog(educateRules, t('Educate on rule'), @theme, page: true)

    callRemoveActionPlan:() ->
      @bus.emit('action-plan:remove',{data:@table.getSelectedRows()})

    addToActionPlanDialog:(data) ->
      theme = @theme
      addToActionPlan =  new @facade.backbone.DialogView({
        title: t('Add violations to action plan')
        subTitle: ''
        message: Handlebars.compile('<div><div class="dialogMessage">{{{t "Please, fill information below to"}}} </br>{{{t "Add the selected violations to action plan"}}}</div></div> ')
        comment: t('')
        priority: t('')
        cancel: t('Cancel')
        perform: t('Add')
        theme: theme
        priorityTag : true
        content: true
        image: ''
        tagList: @facade.portal.get('configuration').tag
        commentPlaceholder: t('Comment')
        onPerform: (comment, tag)=>
          @bus.emit('action-plan:save',{priority:tag, comment:comment, data:data})
      })
      addToActionPlan.render()

    scheduleExclusionDialog:(data) ->
      theme = @theme
      scheduleExclusions =  new @facade.backbone.DialogView({
        title: t('Exclude violations')
        subTitle: ''
        message: Handlebars.compile('<div><div class="dialogMessage">{{{t "Please, fill information below to"}}} </br>{{{t "Exclude the selected violations"}}}</div></div> ')
        comment: t('')
        priority: t('')
        cancel: t('Cancel')
        perform: t('Exclude')
        theme: theme
        content: true
        priorityTag: false
        image: ''
        commentPlaceholder: t('Comment')
        onPerform: (comment)=>
          @bus.emit('exclusion:save',{comment:comment, data:data})
      })
      scheduleExclusions.render()

    addToEducationDialog:(educateRules, title, theme, page, multipleRules) ->
      addToEducation =  new @facade.backbone.DialogView({
        title: title
        subTitle: educateRules.ruleName
        message: Handlebars.compile('<div><div class="dialogMessage">{{{t "You are about to track closely related new violations that would be detected on next snapshot. "}}} </br>{{{t "To Share and Promote selected rule documentation, go in the Education tab"}}}</div></div> ')
        shareMessage: t('Share and promote rule documentation with object samples')
        comment: t('')
        priority: t('')
        cancel: t('Cancel')
        perform: t('Educate')
        theme: theme
        actions: @facade.portal.get('configuration').tag.actions[1]
        priorityTag : true
        content: true
        multipleRules: multipleRules
        education: true
        tagList: @facade.portal.get('configuration').tag
        commentPlaceholder: t('Comment for future violations')
        onPerform: (comment, tag, actions)=>
          @bus.emit('education:save',{priority: tag, comment: comment, actions: actions, data: educateRules, page: page})
      })
      addToEducation.render()

    filterQualityRules:(data)->
      filteredRules = []
      educatedRuleIds = _.map(this.EducationModel.models,(rule) -> return rule.get('rulePattern').href.split('/')[2])
      selectedRuleIds = _.unique(_.map(data,(violation) -> return violation.get('ruleId')))
      filteredIds = _.difference(selectedRuleIds, educatedRuleIds)
      for id in filteredIds
        filteredRules.push(_.find(data,(violation)-> return violation if violation.get('ruleId') == id))
      return filteredRules

    showMoreDisplay:()->
      showMore = false
      showMore = true if @nbRows <= @model.size()
      showMore

    _renderTemplate:()->
      @$el?.html(@template({
        title: @title
        showMore: @showMoreDisplay()
        advanceSearch: @options.pageId == 'advanceSearch'
        filteredViolations:if @model.models.length then @model.models.slice(-1)[0]?.get('number') else 0
        totalViolations: @totalViolationsCount
        searchValue: @options.subString
      }))
      @$el?.find('#priority-menu').html(@menu.render())

    getTableExtraModels:(index) ->
      @table.options.rows.models[index]?.get('extra')?.model

    getTableRowModels:() ->
      @table.options.rows.models

    getTableHeader:(index) ->
      @$el?.find('table thead tr th.row-selector')

    updateEducationDetails:()->
      _.each(@EducationModel.models,(rule)=>
        ruleNameSpan = @$el.find(".rule-name[data-ruleid*='#{rule.get('rulePattern').href.split('/')[2]}']")
        if rule.get('active') then ruleNameSpan?.addClass("educate-icon") else ruleNameSpan?.addClass("educate-icon disabled"))

    userRoleCheck:() ->
      el = @$el
      @updateEducationDetails() if @options.pageId == "advanceSearch"
      if @status?
        el.find('#table-holder thead .status').addClass('filtering').attr('title',t('Filtering on violations') + ' ' + @status)
        el.find('#table-holder thead .status .cont .options').attr('data-before',t('Select a filter'))
      else
        el.find('#table-holder thead .status').attr('title', t('Select a filter'))
        el.find('#table-holder thead .status .cont .options').attr('data-before',t('Select a filter'))
      el.find('#table-holder li').removeClass('selected')
      el.find('tr.clickable').addClass('violation-table-row') if @options.pageId == 'components-investigation'
      el.find('#table-holder li[data-ref="' + @statusValue + '"]').addClass('selected')
      if @table.$el.find('tbody tr')?.length == 0
        @getTableHeader()?.addClass('hide-row').attr('title', t('No violations available'))
        return
      ruleDetails = $('#table-holder tbody tr.selected td span.rule-name') if @options.pageId != 'advanced-search'
      _.each(@$el.find('#table-holder tbody tr'),(row)=>
        isActionOrExclusion = $(row).find('td:nth-child(2) span').hasClass('exclusion') or $(row).find('td:nth-child(2) span').hasClass('actionPlan')
        if isActionOrExclusion
          $(row).find('td:first').addClass('hide-row') if $(ruleDetails).hasClass('educate-icon') or $(row).find('td:nth-child(4) span').hasClass('educate-icon'))
      @getTableHeader()?.removeClass('hide-row')
      if @table.$el.find('tbody tr')?.length == @table.$el.find('tbody tr .hide-row')?.length # table header disable
        @getTableHeader().addClass('hide-row').attr('title', t('All violations are already added to actions or scheduled for exclusions'))
      el.find('#table-holder thead th.status').removeAttr('title').attr('title',t('Status')) if @options.pageId == 'advanceSearch'
      $(window).resize()

      el.find('.row-selector.hide-row').on 'click', ->
        return false
      if @getTableRowModels().length == 0
        el.find('.download-file').parent().addClass('disabled')

    disableDropDown:(el)->
      el.find('#priority-menu  li').addClass('disabled')
      el.find('#priority-menu .cont .options').attr('data-before',t('Select an operation'))
      allViolationsNotAdded = false
      _.find(@$el.find('#table-holder tbody tr'),(row)->
        allViolationsNotAdded = true if !($(row).find('td:nth-child(2) span').hasClass('actionPlan') or $(row).find('td:nth-child(2) span').hasClass('exclusion')))
      if @qualityManager
        el.find('.educate').addClass('disabled').parent().attr('title', t('You are not authorized to add Rules to Education feature, please contact your CAST Administrator'))
        if allViolationsNotAdded
          el.find('#priority-menu  li[data-ref="0"]').removeClass('disabled')
      if @exclusionManager
        el.find('.educate').addClass('disabled').parent().attr('title', t('You are not authorized to add Rules to Education feature, please contact your CAST Administrator'))
        if allViolationsNotAdded
          el.find('#priority-menu  li[data-ref="1"]').removeClass('disabled')
      if @qualityAutomationManager
        if _.find(@$el.find('#table-holder tbody tr'),(row)-> return row if $(row).find('td:nth-child(4) span').hasClass('educate-icon')) or @options.pageId != "advanceSearch"
          el.find('.educate').removeClass('disabled').parent().removeAttr('title')
          el.find('#priority-menu  li[data-ref="2"]').removeClass('disabled')

    renderTableElements:(el) ->
      $tableHolder = el.find('#table-holder')
      @updateEducationDetails() if @options.pageId == "advanceSearch"
      if $tableHolder?
        if @status?
          $tableHolder.find('thead .status').addClass('filtering').attr('title',t('Filtering on violations') + ' ' + @status)
          $tableHolder.find('thead .status .cont .options').attr('data-before',t('Select a filter'))
        else
          $tableHolder.find('thead .status').attr('title', t('Select a filter'))
          $tableHolder.find('thead .status .cont .options').attr('data-before',t('Select a filter'))
        $tableHolder.find('li').removeClass('selected')
        $tableHolder.find('tr.clickable').addClass('violation-table-row') if @options.pageId == 'components-investigation'
        $tableHolder.find('li[data-ref="' + @statusValue + '"]').addClass('selected')
        el.find('.educate').addClass('disabled').parent().attr('title', t('You are not authorized to add Rules to Education feature, please contact your CAST Administrator'))
        @disableDropDown(el)
        @userRoleCheck()
        setTimeout (->
          $(window).resize()
        ), 100
        el.find('table tbody tr td.center').last().addClass('violation-body-size')
        el.find('table thead tr:first th.center').last().addClass('violation-header-size')
        @table.on('row:clicked', @onViolationSelection, @)
        @tableViewState()
        @table.on('sorted', @userRoleCheck, @)
        el.find('.row-selector.hide-row').on 'click', ->
          return false
        $tableHolder.find('th.row-selector.disabled').on 'click', ->
          return false
        el.find('.educate').addClass('disabled').parent().attr('title', t('Education feature is not available in past snapshots')) if  !@facade.context.get('snapshot').isLatest()
        if @getTableRowModels().length == 0
          el.find('.download-file').parent().addClass('disabled')
        #      IE and Edge Fix
        isIE = false || !!document.documentMode;
        isEdge = !isIE && !!window.StyleMedia;

        if isIE || isEdge
          el.find('.row-selector').on 'mouseover', ->
            $('html').addClass('noSelect')
          el.find('.row-selector').on 'mouseout', ->
            $('html').removeClass('noSelect')

    onEducationSelection: ()->
      @$el.find('#priority-menu  li:last').removeClass('disabled')
      $tableHolder = @$el?.find('#table-holder')
      selectedRows = $tableHolder.find('tbody input[type="checkbox"]:checked')
      educateRows = _.filter((selectedRows), (row) ->
        rowElement = row.parentElement.parentElement.children[3].firstElementChild.className
        return selectedRows if rowElement == "rule-name educate-icon" or rowElement == "rule-name educate-icon disabled")
      if educateRows.length == @table.getSelectedRows().length
        @$el.find('#priority-menu  li:last').addClass('disabled')

    render: (params = {})->
      el = @$el
      @rendered = true
      options = @options
      @filterEducation(el) if options.pageId != 'advanceSearch'
      @downloadLinkUrl = @model.url() + '&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      items = [
        {text: Handlebars.compile('<span class="add-to-action-plan"></span><span class="text"><span class="bold">{{t "Add"}}</span> {{t "the violations to action plan ..."}} </span>')(),
        action: () =>
          data = @table.getSelectedRows()
          toAddActionsData=[]
          data.map(((item)=>
            if !item.get('extra')?.model.get('remedialAction')?.status? and !item.get('extra')?.model.get('exclusionRequest')?.status?
              toAddActionsData.push(item) if item != undefined
              return item
          ))
          @addToActionPlanDialog(toAddActionsData)
        }
        {text: Handlebars.compile('<span class="exclude-violations"></span><span class="text"><span class="bold">{{t "Schedule Exclusion"}}</span> {{t "of the violations ..."}}</span>')(),
        action: () =>
          data = @table.getSelectedRows()
          toExcludeData= []
          data.map(((item)=>
            if !item.get('extra')?.model.get('remedialAction')?.status? and !item.get('extra')?.model.get('exclusionRequest')?.status?
              toExcludeData.push(item) if item != undefined
              return item
          ))
          @scheduleExclusionDialog(toExcludeData)
        }
        {text: Handlebars.compile('<span class="educate-violations"></span><span class="text"><span class="bold">{{t "Educate"}}</span> {{t "on the related rule ..."}}</span>')(),
        action: () =>
          data = @table.getSelectedRows()
          title = t('Educate on rule')
          if @options.pageId == "advanceSearch"
            filteredRules = @filterQualityRules(data)
            if filteredRules.length > 1
              educateRules = filteredRules
              title = t('Educate on rule(s)')
              educateRules.ruleName = t('Multiple rules are selected')
              multipleRules = true
            else
              educateRules = filteredRules[0]
              educateRules.ruleName = educateRules.get('extra')?.model.get('rulePattern').name
          else
            educateRules = data[0]
            educateRules.ruleName = educateRules.get('extra')?.model.get('rulePattern').name
          @addToEducationDialog(educateRules, title, @theme, page: true if @options.pageId != "advanceSearch", multipleRules)
        }
      ]
      @menu = new @facade.bootstrap.Menu({
        text: Handlebars.compile('<span class="add"></span><span class="text">{{t "Add"}}</span><span class="tooltiptext">{{t "Add your violations to Actions, Exclusions or Education"}}</span>')
        class: 'light-grey right'
        items: items
      });
      that = this
      $('.sections-content').on('scroll', () ->
        that.showMenuOptionsOnTopOrBottom()
      )
      $(window).on('resize', () ->
        that.showMenuOptionsOnTopOrBottom()
      )
      userAuthorized = @exclusionManager or @qualityManager or @qualityAutomationManager if @facade.context.get('snapshot').isLatest()
      emphaseAddedViolations = @emphaseAddedViolations
      model = @model
      nbRows = @startRow - 1 + @nbRows
      if @table? and params?
        @_renderTemplate()
        @table.$el.detach()
        rows = @model.asRows({nbRows: nbRows, selectedComponent: @options.ruleComponent})
        if @options.pageId == 'advanceSearch'
          _.each(rows.models, (row, index)->
            rows.models[index].set('id', rows.models[index].get('componentId') + '_' + rows.models[index].get('ruleId'))
          )
        @table.update({rows:rows, resetRowSelector: if params.resetRowSelector then params.resetRowSelector else true})
        el?.find('#table-holder').append(@table.render())
        @table.delegateEvents()
      else
        if @options.pageId != 'advanceSearch'
          data = _.find(@model.models, (model, index)=>
            return model.get('component').href.split('/')[2] == (@options.ruleComponent or @options.component) and !options.APDrillDown and index < 10
            )
          if data or !@component? then @nbRows = 10 else @nbRows = 1000000
        @nbRows = 20 if options.pageId == 'advanceSearch'
        @_renderTemplate()
        tagType = 'Priority'
        if @facade.portal.get('configuration').tag?.tagType
          tagType = @facade.portal.get('configuration').tag.tagType
        tagType = tagType + ' '
        that = @
        columns = [
          {header: '<label>&#xe92e;</label>',  headerMin:'#xe92e;', title:t('Actions or Exclusions'), align: 'center',length:2,
          format: (value)->
            if value.status == 'added' and value.userName
              title = t('Excluded on next snapshot, with the comment ')+value.comment?.replace(/\s+/g, " ")
              name = 'exclusion'
            else if value.status?
              title = t('Added to Action Plan, with the ')+t(tagType)+t(value.tag)+t(' and comment ')+value.comment?.replace(/\s+/g, " ")
              name = 'actionPlan'
            else
              name = ""
              title = t('')
            return '<span title="'+title+'" class="'+name+'"></span>'
          }
          {header: t('Object name location'), title:t('Object Name Location'), align:'left stretch', format: (value, columnId, rowId, item)->
            if emphaseAddedViolations
              status = item.columns[3]
              emphases = status == 'added'
            return _objectNameTemplate({value:value, emphases:emphases})
          }
          {header: t('risk'), align:'left', headerMin:'#xe61b;', title:t('Risk is based on number of other violations for the object for the selected health measure linked to the level of use of the object in the application.'), length:4, format: (value)->
            return ('<div title="Risk value is based on propagated risk index which is calculated regarding health measures. Please select a health measure other than TQI.">' + 'n/a' + '</div>') if isNaN(value) or value < 0
            max = model.maxRisk()
            # ratio = value / max
            length = parseInt(value / max * 100)
            # width = parseInt(ratio * 100)
            # height = parseInt(ratio * 20)
            # console.log max, ratio
            length = Math.max(1, length) if value > 0
            bar = '<div class="bar " title="' + that.facade.numeral(value).format('0,000') + '"><div class="weight object-pri" style="width:' + length + '%">' + that.facade.numeral(value).format('0,000') + '</div></div>'
            return bar
            # triangle = '<div class="triangle-container"><div class="triangle-shadow" style=" border-width: 0px 0px 20px 100px;"></div><div class="triangle" style=" border-width: 0px 0px ' + height + 'px ' + width + 'px;"></div></div>'
            # return triangle
            return 'n/a' if value < 0
            return @facade.numeral(value).format('0,00') #if value < 1000
          # return '<span title="' + facade.numeral(value).format('0,00') + '">' + facade.numeral(value).format('0,0.0a') + '<span>' if value < 10000
          # return '<span title="' + facade.numeral(value).format('0,00') + '">' + facade.numeral(value).format('0.0a') + '<span>'
          }
          {header: t('status'), headerMin:'#xe61a;', title:t('status'), align:'left status', format: (value)->
            return '<span class="fixed-font-grey">' + value + '</span>' if value == 'unchanged'
            return '<span class="fixed-font"><em>' + value + '</em></span>'
          selector:{
            data: [
              {label: t('All statuses'), value:0},
              {label: t('Added'), value: 1},
              {label: t('Updated'), value: 2},
              {label: t('Unchanged'), value: 3}
            ],
            onSelection:(value)=>
              switch(value)
                when 0 then status = null
                when 1 then status = 'added'
                when 2 then status = 'updated'
                when 3 then status = 'unchanged'
              return if that.status == status
              that.status = status
              that.statusValue = value
              if that.status
                localStorage.setItem('filterViolationsByStatus',that.status)
              else
                localStorage.removeItem('filterViolationsByStatus')
              that.updateViewState(that.options)
          } if options.pageId != 'advanceSearch'
          }
        ]
        if that.options.pageId != 'components-investigation' and that.options.pageId != 'advanceSearch'
          columns.push({header: t(''), align:'center link-to-component-browser', format: (value)->
            if that.facade.context.get('snapshot').isLatest()
              title = t('Investigate object in module drill-down')
              isEnable = ''
            else
              title = t('Module drill-down, not available in past snapshots')
              isEnable = 'disable-component-drilldown'
            return _componentdrillDownTemplate({title: title, isEnable: isEnable})
          })
        else if that.options.pageId == 'advanceSearch'
          columns.splice(2,0,{header: t('Rule'), title:t('Rule'),align:'left stretch', format:(value, group, row, model) -> return formatRuleName(value, group, row, model)})
          columns.splice(3,1)
          columns.push({header: t(''), align:'center', format: (value)->
            title = t('Access the violation source code')
            state = 'showViolation'
            href = '#' + SELECTED_APPLICATION_HREF + '/snapshots/' + that.facade.context.get('snapshot').getId() + '/qualityInvestigation/0/' + that.options.filterBusinessCriterion + '/all/' + value + '/' + '_ap' ;
            return  _violationsTemplate({href: href, title: title, state: state})
          })
        nbRows = @startRow - 1 + @nbRows
        rows = @model.asRows({nbRows: nbRows, selectedComponent: @options.component})
        if @options.pageId == 'advanceSearch'
          _.each(rows.models, (row, index)->
            rows.models[index].set('id', rows.models[index].get('componentId') + '_' + rows.models[index].get('ruleId'))
          )
        @table = new @facade.bootstrap.Table({
          columns: columns
          rows : rows
          selectOnClick: true
          rowSelector: if userAuthorized then true else false
          click: true if @options.pageId != 'advanceSearch'
        })
        el?.find('#table-holder').html(@table.render())
      @getViolationAndRenderShowMore(options)
      if options.pageId == "advanceSearch"
        searchObjects = new @objectSearch(@)
        el?.find('#search-container').keyup(_.debounce(_.bind(searchObjects.fetchData, searchObjects), 1500))
      input = el?.find('#search-container')
      if @options.subString? and @options.subString != ''
        strLength = input?.val()?.length
        input.focus()
        input[0]?.setSelectionRange(strLength, strLength)
      @renderTableElements(el) if el?
      @table.on('update:row-selector', @onActionPlanSelection, @)
      @table.on('update:row-selector', @onEducationSelection, @) if @options.pageId == 'advanceSearch' and @qualityAutomationManager
      hasSelection = false
      for row in @getTableRowModels()
        row = row.toJSON()
        if row.selected
          hasSelection = true
          @onViolationSelection(row)
      el?.find('#table-holder thead th.status').removeAttr('title').attr('title',t('Status')) if @options.pageId == 'advanceSearch'
      if @model.length == 0 and !$("#search-container").is(":focus")
        input?.css('pointer-events','none') and el?.find('.object-search').attr('title',t('No objects to search'))
      if @component and !hasSelection
        @table.selectRow(0)
      if @model.length == 0
        if @status? and @options.pageId != 'advanceSearch'
          el?.find('#table-holder').append('<div class="no-violations">' + t('No Violations when filtering on') + ' ' + @status + '</div>')
        else
          el?.find('#table-holder').append('<div class="no-violations">' + t('No Violations found') + '</div>')
        # no selections, do something
        if @component?
          @componentSelection()
      if @options.pageId != 'advanceSearch'
        if @options.pageId != 'components-investigation'
          qualityRuleHelpviewOptions = {
            $target:el.find('th:nth-child(4)')
            isVisible:()=>
              el.width() != 0
            useHelpDialog:true
            image:'risk'
            title:t('risk column is defined by the propagated risk index(PRI)')
            content:Handlebars.compile('<p>{{t "This is a measurement of the riskiest objects of the application along with the Health Measures of Robustness, Performance, Security, Changeability and Transferability."}}</p>
              <p>{{t "The PRI formula takes into account the intrinsic risks of the component regarding a selected health measure coupled with the level of use of the given object in the application."}}</p>
              <p>{{t "PRI finds objects that threaten the application usage. Regarding risk identified, it should help you to determine if you need to decide to correct it or not and to correctly anticipate a test planning"}}</p>
              <div><div>{{t "The first RISKIEST(128) object in this illustration has higher PRI because"}}
                <ul><li>1. {{t "More objects depend on it."}}</li>
                <li>2. {{t "...regarding the weight of its violations"}}</li></ul></div>
              </div>')()
          }
          @bus.emit('help:createView',qualityRuleHelpviewOptions)
        else
          qualityRuleHelpApplicationviewOptions = {
            $target:el.find('th:nth-child(4)')
            isVisible:()=>
              el.width() != 0
            position:'bottom-left'
            title:t('Risk')
            content: '<p>' + t('This is a measurement of the riskiest artifacts or objects of the application along with the Health Measures of Robustness, Performance, Security, Changeability and Transferability.') + '</p>' +
              '<p>' + t('PRI takes into account the intrinsic risk of the component coupled with the level of use of the given object in the transaction. It systematically helps the aggregate risk of the application in a relative manner, allowing for identification, prioritization, and ultimately remediation of the riskiest objects.') + '</p>' +
              '<p>' + t('The PRI number reflects the cumulative risk of the object based on its relationships and interdependencies. The PRI is calculated as a function of the rules violated, their weight/criticality, and the frequency of the violation.') + '</p>'
          }
          @bus.emit('help:createView',qualityRuleHelpApplicationviewOptions)
      @bus.on('action-plan:updated',@updateTable,@)
      @bus.on('exclusion:updated',@updateTable,@)
      @bus.on('education:updated',@updateTable,@)
      el
  })
  return{
    ObjectViolationCloseView
    ObjectViolationSectionView
  }