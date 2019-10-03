ActionPlanView = (facade) ->

  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  _objectNameTemplate = Handlebars.compile('<span>
          <em class="short-content" title="{{value}}">{{ellipsisMiddle value 15 35}}</em>
          <em class="large-content" title="{{value}}">{{ellipsisMiddle value 25 45}}</em>
          <em class="super-large-content wrappable " title="{{value}}">{{value}}</em>
         </span>')

  _violationsTemplate = Handlebars.compile('<span>
         {{#if href}}
          <em class="short-content" title="{{title}}"><a class="{{state}}" href="{{href}}">&#xe91a;</a></em>
         {{else}}
          <em class="short-content" title="{{title}}"><a class="{{state}}">&#xe91a;</a></em>
         {{/if}}
         </span>')

  resizeTableCol=(data)->
    data = data.data if data.data?

# respWidth = $('#gizmo').width()
# Proceed to the resize for each table that can be found here, as we have sections
    data.$el?.find('table').each (index) ->
        table = $(this)
        # minWidth = 0

        table.removeClass('contract compact large super-large')
        table.addClass('test')

        # ---------------------------------------------------------------------------------- #
        # Get the stretching column... !!! CODE OK FOR JUST ONE STRETCHING COLUMN !!!
        # ---------------------------------------------------------------------------------- #
        currentHeight = table.outerHeight()
        table.css({'white-space':'nowrap'})
        newHeight = table.outerHeight()
        table.css({'white-space':''})
        table.addClass('contract') if newHeight != currentHeight

        # ---------------------------------------------------------------------------------- #
        # Get the stretching column... !!! Loop it again for the contract mode
        # ---------------------------------------------------------------------------------- #
        currentHeight = table.outerHeight()
        table.css({'white-space':'nowrap'})
        newHeight = table.outerHeight()
        table.css({'white-space':''})
        table.addClass('compact') if newHeight != currentHeight

        return @ if table.hasClass('compact')
        return @ if table.hasClass('contract')

        # TODO optimize
        currentHeight = table.outerHeight()
        table.addClass('large')
        table.css({'white-space':'nowrap'})
        newHeight = table.outerHeight()
        table.css({'white-space':''})
        table.removeClass('large') if newHeight != currentHeight

        if screen.width > 1280 and screen.height > 720
          currentHeight = table.outerHeight()
          table.addClass('super-large')
          table.css({'white-space':'nowrap'})
          newHeight = table.outerHeight()
          table.css({'white-space':''})
          table.removeClass('super-large') if newHeight != currentHeight

        return @

  ActionPlanDetailView = facade.backbone.View.extend({
    template:Handlebars.compile('<div class="action-plan-overview">
            <div class="action-plan-summary">
              <div class="priority-drill-down disabled" id="priority-menu"></div>
                    <div class="summary-issues solved-issues" title="{{t "solved"}}">
                       <span class="solved-issues-title"></span>
                       <span class="solved-issues-count"></span>
                    </div>
                    <div class="summary-issues pending-issues" title="{{t "pending"}}">
                      <span class="pending-issues-title"></span>
                      <span class="pending-issues-count"></span>
                      <span class="dotted-summary">&#9679</span>
                    </div>
                    <div class="summary-issues added-issues" title="{{t "added"}}">
                      <span class="added-issues-count"></span>
                      <span class="dotted-summary">&#9679</span>
                    </div>
                    <a title="{{t "download data as excel file"}}" class="download-file pos">{{t "Download Excel"}}</a>
                  </div>
                <article>
                  <div class="action-plan-issues-listing"></div>
                  <div id="show-more"></div>
                </article>
              </div>')

    loadingTemplate: '<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    events:
      'click .download-file':'downloadAsExcelFile'

    preRender:()->
      @$el.find('.action-plan-issues-listing').html(@loadingTemplate)
      $('#show-more').css('display', 'none')

    downloadAsExcelFile:()->
      href = @downloadLinkUrl
      $.ajax('url': REST_URL + 'user', 'async': false)
        .success(()->
        window.location = href if href?
      )
      return false

    initialize:()->
      globalOptions = facade.portal.get('configuration').parameters or {nbRows:10}
      @businessCriterion = "60017"
      @businessCriterion = "60016" if facade.context.get('isSecurity')
      @model = new facade.models.actionPlan.ActionPlanSummary([], {href:facade.context.get('snapshot').get('href')})
      @startRow=1
      @nbRows= globalOptions.nbRows
      @selectedRows = []

      @tableModel = new facade.models.actionPlan.ActionPlanIssues([],{
        href:facade.context.get('snapshot').get('href')
        startRow:@startRow
        nbRows:@nbRows
      })
      facade.bus.on('action-plan:updated',@updateTable,@)
      @exclusionManager = facade.context.get('user').get('exclusionManager')
      @qualityManager = facade.context.get('user').get('qualityManager')
      $(window).on('resize', {$el:@$el}, resizeTableCol)

    showMore: (nbRows)->
      el = @$el
      @nbRows = nbRows
      @startRow = @tableModel.size() + 1
      @tableModel.startRow = @startRow
      @tableModel.nbRows = @nbRows
      @tableModel.getData({
        success: ()=>
          @_updateTableRender(el)
          @onActionPlanSelection()
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
      violationsCount = facade.portal.get('configuration').violationsCount or 5000
      if ((violationRatioValue > violationsCount and violationRatioValue < 100) or  violationRatioValue > violationsCount)
        allTextTemplate = Handlebars.compile('<span title="{{t "You cannot display a high number of violations without big performance issues"}}">'+ allText + '</span>')
      else
        allTextTemplate = Handlebars.compile('<span title="{{t "Depending on the number of violations, this request can take time"}}">'+ allText + '</span>')

      menuItems =[]
      if nbRows < violationsCount
        @pushMenuItems(menuItems, 10) if violationRatioValue > 30
        @pushMenuItems(menuItems, 100) if violationRatioValue > 120 and (violationsCount - nbRows) > 100 and (violationRatioValue - nbRows) > 100
      @pushMenuItems(menuItems,allTextTemplate)

      @showMoreMenu = new facade.bootstrap.Menu({
        text:t('Show More')
        class: 'light-grey'
        items: menuItems
      });
      el.find('#show-more').html(@showMoreMenu.render())
      @showOptionsOnTopOrBottomForActionPlan()
      if nbRows >= violationsCount
        el.find('#show-more li')[0]?.classList.add('inactive')
      if violationRatioValue > violationsCount and (violationRatioValue < 100 or (violationsCount - nbRows) < 100)
        el.find('#show-more li')[1]?.classList.add('inactive')
      else if violationRatioValue > violationsCount
        el.find('#show-more li')[2]?.classList.add('inactive')
      el.find('#show-more li.selectable.no-separator.inactive').prop("disabled", true)

    getViolationAndRenderShowMore:(el)->
      that = this
      @model.getData({
        success:()=>
          data = @model.computeSummary()
          violationRatio = data.totalIssues
          if violationRatio?
            that._renderShowMoreSelector(el, violationRatio, that.startRow - 1 + that.nbRows)
          else
            that._renderShowMoreSelector()
      })

    showOptionsOnTopOrBottomForActionPlan:()->
      menu = $('.cont', '.action-plan-overview #show-more').first()
      if menu?
        $(menu).removeClass('top')
        menuTop = menu.offset()?.top
        menuHeight = menu.height()
        totalMenuHeight = menuTop + menuHeight
        if totalMenuHeight >= $(window).height()
          $(menu).addClass('top')

    updateTable:()->
      el = @$el
      @_renderSummary(el)
      @tableModel = new facade.models.actionPlan.ActionPlanIssues([],{
        href:facade.context.get('snapshot').get('href')
        startRow:1
        nbRows:@tableModel.size()
      })
      @tableModel.getData({
        success:()=>
          @_updateTableRender(el)
          @getViolationAndRenderShowMore(el)
          @onActionPlanSelection()
      })

    onActionPlanSelection:(options)->
      el = @$el
      if options?.hasChecked
        el.find('#priority-menu').removeClass('disabled')
        el.find('.added-issues').css('margin-left','9.5em')
      else
        el.find('#priority-menu').addClass('disabled')
        el.find('.added-issues').css('margin-left','0em')
      isKeyPressed = options?.isShift
      rowModels =  @table.options.rows.models
      @selectedRows = [] if(@table.getSelectedRows().length == 0)
      if options?.hasChecked && options?.row
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
              el.find('table tbody tr[data-index="'+ i + '"] .row-selector input[type="checkbox"]').prop('checked', true)
              rowModels[i].attributes.rowSelected = true

    callActionPlan : (item) ->
      facade.bus.emit('action-plan:save',{priority:item.value, data:@table.getSelectedRows()})

    callRemoveActionPlan : () ->
      facade.bus.emit('action-plan:remove',{data:@table.getSelectedRows()})

    addToActionPlanDialog:(items, sameComments, samePriority) ->
      item = items[0].get('extra').model.get('remedialAction')
      comment = item?.comment
      priority = item?.tag
      if items.length >1 and !sameComments
        comment = ""
      if items.length >1 and !samePriority
        priority = ""
      addToActionPlan =  new facade.backbone.DialogView({
        title: t('Update Actions')
        subTitle: ''
        message: Handlebars.compile('<div><div class="dialogMessage">{{{t "Please, fill information below to"}}} </br>{{{t "update the selected Actions"}}}</div></div> ')
        comment: comment
        priority: t(priority)
        cancel: t('Cancel')
        perform: t('Update')
        content: true
        theme: 'background-blue'
        image: ''
        priorityTag: true
        tagList: facade.portal.get('configuration').tag
        commentPlaceholder: t('Comment')
        onPerform: (comment, tag)->
          facade.bus.emit('action-plan:save',{priority:tag, comment:comment, data:items})
      })
      addToActionPlan.render()

    _allValuesSame :(arr)->
      return true if arr.length == 0
      return true if arr.length == 1 && arr[0] == 'solved'
      for i in [1 .. arr.length-1]
        if(arr[i] != arr[0])
          return false
      return true

    _renderSummary:(el)->
      @model.getData({
        success:()=>
          data = @model.computeSummary()
          el.find('.solved-issues-count').html(data.solvedIssues)
          el.find('.pending-issues-count').html(data.pendingIssues)
          el.find('.added-issues-count').html(data.addedIssues)
      })

    resizeHeader:(el)->
      if @tableModel.length == 0
        el.find('.download-file').addClass('disabled')
        el.find('table th.hide-row').removeAttr('title')
        el.find('table tbody').append('<div class="no-violations">' + t('No Violations found') + '</div>')
      el.find('table thead tr:first th.center').addClass('violation-header-size')

    _updateTableRender:(el)->
      rows = @tableModel.asRows({nbRows: @startRow - 1 + @nbRows})
      @table.$el.detach()
      @table.update({rows: rows, resetRowSelector:true})
      el.find('.action-plan-issues-listing .loading').remove()
      el.find('.action-plan-issues-listing').append(@table.render())
      el.find('.table .status').attr('summary-data',t('added'))
      @table.delegateEvents()
      @resizeHeader(el)
      for i in[0 .. rows.length-1]
        if el.find('table tbody tr td:nth-child(3) span')[i]?.className.includes('solved')
          el.find('table tbody tr[data-index="' + i  + '"]').addClass('disabled-row')
          el.find('table tbody tr[data-index="'+ i + '"] .row-selector').addClass('hide-row')
      status = rows.map(((item)=>
        return item.get('extra').model.get('remedialAction')?.status
      ))
      if @_allValuesSame(status) == true and (status[0] == 'solved' or status.length == 0)
        el.find('table thead tr th.row-selector ').addClass('disabled hide-row')
      else
        el.find('table thead tr th.row-selector ').removeClass('disabled hide-row')
      el.find('th.row-selector.disabled').on 'click', ->
        return false
      el.find('.row-selector.hide-row').on 'click', ->
        return false
      @getViolationAndRenderShowMore(el)
      @_hideOrShowShowMoreButton()
      resizeTableCol({$el:@$el})

    _hideOrShowShowMoreButton:()->
      tableSize = @tableModel.length
      $('#show-more').css('display', 'table') if tableSize >= 20
      @model.getData({
        success:()=>
          data = @model.computeSummary()
          $('#show-more').css('display', 'none') if tableSize == data.totalIssues
      })

    scheduleExclusionDialog:(data) ->
      scheduleExclusions =  new facade.backbone.DialogView({
        title: t('Exclude violations')
        subTitle: ''
        message: Handlebars.compile('<div><div class="dialogMessage">{{{t "Please, fill information below to"}}}</br>{{{t "Exclude the selected violations"}}}</div></div> ')
        comment: t('')
        cancel: t('Cancel')
        perform: t('Exclude')
        theme: 'background-blue'
        content: true
        priorityTag: false
        image: ''
        commentPlaceholder: t('Comment')
        onPerform: (comment)->
          facade.bus.emit('exclusion:save',{comment:comment, data:data})
      })
      scheduleExclusions.render()

    render:()->
      el = @$el
      @downloadLinkUrl = @tableModel.url() + '&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      el.html(@template())
      el.find('.added-issues').attr('summary-data',t('added'))
      el.find('.pending-issues .pending-issues-title').attr('summary-data',t('pending'))
      el.find('.solved-issues .solved-issues-title').attr('summary-data',t('solved'))
      @menu = new facade.bootstrap.Menu({
        text: Handlebars.compile('<span class="add"></span><span class="text">{{t "Manage"}}</span><span class="tooltiptext">{{t "Manage your violations through Actions or Exclusions"}}</span>')
        class: 'light-grey right'
        items:[
          {text: Handlebars.compile('<span class="add-to-action-plan"></span><span class="text"><span class="bold">{{t "Update"}}</span> {{t " Actions ..."}}</span>')(),
          action: () =>
            data = @table.getSelectedRows()
            comments = data.map(((item)=>
              return item.get('extra').model.get('remedialAction')?.comment
            ))
            priorities = data.map(((item)=>
              return item.get('extra').model.get('remedialAction')?.tag
            ))
            @addToActionPlanDialog(data, @_allValuesSame(comments) , @_allValuesSame(priorities) )
          }
          {text: Handlebars.compile('<span class="exclude-violations"></span><span class="text"><span class="bold">{{t "Schedule Exclusions"}}</span> {{t "for related violations ..."}} </span>')(),
          action: () =>
            @scheduleExclusionDialog(@table.getSelectedRows())
          }
          {text: Handlebars.compile('<span class="remove-violations"></span><span class="text"><span class="bold">{{t "Remove"}}</span> {{t "from Action list ..."}} </span>')(),
          action: () =>
            confirm =  new facade.backbone.DialogView({
              title:t('Remove')
              subTitle: ''
              message:t('Are you sure you want to remove violation(s) from action list ?')
              cancel:t('Cancel')
              perform:t('Remove')
              button : true
              action: 'remove'
              image: ''
              theme: 'background-blue'
              data: @table.getSelectedRows()
              onPerform:()->
                facade.bus.emit('action-plan:remove',{data:@data})
            })
            confirm.render()
          }]
      })
      userAuthorized = @exclusionManager or @qualityManager if facade.context.get('snapshot').isLatest()
      el.find('#priority-menu').html(@menu.render())
      el.find('#priority-menu .cont .options').attr('data-before',t('Select an operation'))
      @getViolationAndRenderShowMore(el)
      that = this
      $('.action-plan-overview').on('scroll', () ->
        that.showOptionsOnTopOrBottomForActionPlan()
      )
      $(window).on('resize', () ->
        that.showOptionsOnTopOrBottomForActionPlan()
      )
      @_renderSummary(el)
      $tableHolder = @$el.find('.action-plan-issues-listing')
      facade.ui.spinner($tableHolder)
      @tableModel.getData({
        success:()=>
          @_hideOrShowShowMoreButton()
          rows = @tableModel.asRows({nbRows: @startRow - 1 + @nbRows})
          tagType = 'Priority'
          if facade.portal.get('configuration').tag?.tagType
            tagType = facade.portal.get('configuration').tag.tagType
          that = @
          @table = new facade.bootstrap.Table({
            columns:[
              {header: t(tagType), title:t(tagType), align: 'left', length:4, format: (value)->
                tag = value.charAt(0).toUpperCase() + value.slice(1);
                return '<span>'+tag+'</span>'
              },
              {header: t('status'), headerMin:'#xe61a;',title:t('Status'), align: 'center', length:4, format: (value)->
                return '<span class="status ' + value + '"></span>'
              },
              {header: t('Comment'),title:t('Comment'), align:'left stretch'}
              {header: t('Rule'), title:t('Rule'),align:'left stretch'}
              {header: t('Object name location'), title:t('Object name location'),align:'left stretch', format: (value)->
                return _objectNameTemplate({value})
              },
              {header: t('Last update'),title:t('Last update'), align:'left stretch date', format: (time)->
                return moment.utc(time).format('MM-DD-YYYY')
              },
              {header: t(''), align:'center', format: (value)->
                title = t('Access the violation source code')
                state = 'showViolation'
                status = value.split('_')[0]
                href = '#'+ SELECTED_APPLICATION_HREF + '/snapshots/' + facade.context.get('snapshot').getId() + '/qualityInvestigation/0/' +that.businessCriterion+'/all/'+ value.split('_')[1] + '/' + '_ap' ;
                if status == 'solved'
                  title = t('The violation is not anymore visible')
                  state = 'hideViolation'
                  href = ''
                return  _violationsTemplate({href: href, title: title, state: state})
              }
            ]
            rows:rows
            rowSelector: if userAuthorized then true else false
          })
          $tableHolder.html(@table.render())
          @table.on('update:row-selector', @onActionPlanSelection, @)
          for i in[0 .. rows.length-1]
            if rows.models[i]?.get('columns')[1] == "solved"
              el.find('table tbody tr[data-index="' + i  + '"]').addClass('disabled-row')
              el.find('table tbody tr[data-index="'+ i + '"] .row-selector').addClass('hide-row')
          status = rows.map(((item)=>
            return item.get('extra').model.get('remedialAction')?.status
          ))
          el.find('.table .status').attr('summary-data',t('added'))
          if @_allValuesSame(status) == true and (status[0] == 'solved' or status.length == 0)
            el.find('table thead tr th.row-selector ').addClass('hide-row')
          else
            el.find('table thead tr th.row-selector ').removeClass('hide-row')
          @resizeHeader(el)
          el.find('table tbody tr td.center').last().addClass('violation-body-size')
          @table.on('sorted', @sortColumn, @)
          el.find('.row-selector.hide-row').on 'click', ->
            return false
          el.find('th.row-selector.disabled').on 'click', ->
            return false
          #      IE and Edge Fix
          isIE = false || !!document.documentMode;
          isEdge = !isIE && !!window.StyleMedia;

          el.find('#priority-menu div div ul li').addClass('disabled')
          if @qualityManager
            el.find('#priority-menu div div ul li[data-ref="0"]').removeClass('disabled')
            el.find('#priority-menu div div ul li[data-ref="2"]').removeClass('disabled')
          if @exclusionManager
            el.find('#priority-menu div div ul li[data-ref="1"]').removeClass('disabled')

          if isIE || isEdge
            el.find('.row-selector').on 'mouseover', ->
              $('html').addClass('noSelect')
            el.find('.row-selector').on 'mouseout', ->
              $('html').removeClass('noSelect')
          resizeTableCol({$el:@$el})
      })

    sortColumn:() ->
      actionStatus = @table.options.rows.models.map(((items)=>
        return items.get('extra').model.get('remedialAction')?.status
      ))
      @$el.find('.table .status').attr('summary-data',t('added'))
      if @tableModel.length == 0
        @$el.find('table th.hide-row').removeAttr('title')
        @$el.find('table tbody').append('<div class="no-violations">' + t('No Violations found') + '</div>')
      @$el.find('table thead tr:first th.center').addClass('violation-header-size')
      if @_allValuesSame(actionStatus) and (actionStatus[0] == 'solved' or actionStatus.length == 0)
        @$el.find('table thead tr th.row-selector ').addClass('disabled hide-row')
      else
        @$el.find('table thead tr th.row-selector ').removeClass('disabled hide-row')
      for i in[0 .. @table.options.rows.models.length-1]
        if @table.options.rows.models[i]?.get('columns')[1] == "solved"
          @$el.find('table tbody tr[data-index="' + i + '"]').addClass('disabled-row')
          @$el.find('table tbody tr[data-index="' + i + '"] .row-selector').addClass('hide-row')
      resizeTableCol({$el:@$el})

    remove:()->
      facade.bus.off('action-plan:updated',@updateTable)
      @table?.remove()
      @$el.remove()
      @unbind()
      delete @$el
      delete @el
      @stopListening()
      @

  })
  return ActionPlanDetailView