ExclusionsView = (facade) ->

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

  ExclusionDetailView = facade.backbone.View.extend({
    template:Handlebars.compile('<div class="exclusion-overview">
            <header>
              <div id="exclusion-selector"></div>
              <div class="priority-drill-down disabled" id="priority-menu"></div>
              <div class="exclusion-summary">
                <a title="{{t "download data as excel file"}}" class="download-file pos">{{t "Download Excel"}}</a>
               </div>
            </header>
            <article>
              <div class="exclusion-issues-listing"></div>
              <div id="show-more"></div>
            </article>
          </div>')

    loadingTemplate: '<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    unavailableTemplate: Handlebars.compile('<div class="investigation-not-available"><h1>{{{t "Not available for past snapshot"}}}</h1><p>{{{t "You may only be able to investigate this data in the latest snapshot."}}}</p></div>')

    events:
      'click .download-file':'downloadAsExcelFile'

    preRender:()->
      @$el?.find('.exclusion-issues-listing').html(@loadingTemplate)
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
      @activeModel = new facade.models.exclusion.ActiveExclusionsSummary([], {href:facade.context.get('snapshot').get('href')})
      @scheduleModel = new facade.models.exclusion.ScheduledExclusionsSummary([], {href:facade.context.get('snapshot').get('href')})
      @startRow=1
      @nbRows= globalOptions.nbRows
      @selectedRows = []
      @tableModel = new facade.models.exclusion.ActiveExclusions([],{
        href:facade.context.get('snapshot').get('href')
        startRow:@startRow
        nbRows:@nbRows
      })
      facade.bus.on('exclusion:updated',@updateTable,@)
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
          @onExclusionSelection()
          @startRow = 1
          @nbRows = 20
      })

    sortColumn:() ->
      el = @$el
      @manageRemovedExclusions(el, @table.options.rows, true, false)
      if @tableModel.length == 0
        el.find('table th.hide-row').removeAttr('title')
        el.find('table tbody').append('<div class="no-violations">' + t('No Violations found') + '</div>')
      el.find('table thead tr:first th.center').addClass('violation-header-size')
      resizeTableCol({$el:@$el})

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
      el?.find('#show-more').html(@showMoreMenu.render())
      @showOptionsOnTopOrBottomForExclusion()
      if nbRows >= violationsCount
        el.find('#show-more li')[0]?.classList.add('inactive')
      if violationRatioValue > violationsCount and (violationRatioValue < 100 or (violationsCount - nbRows) < 100)
        el.find('#show-more li')[1]?.classList.add('inactive')
      else if violationRatioValue > violationsCount
        el.find('#show-more li')[2]?.classList.add('inactive')
      el.find('#show-more li.selectable.no-separator.inactive').prop("disabled", true)

    getViolationAndRenderShowMore:(el)->
      that = this
      if $('#drill-page #exclusion-selector .selector span.label').first().html() != t("Scheduled")
        @activeModel.getData({
          success:()=>
            data = @activeModel.computeSummary()
            if @getSelectedExclusionType() != t("Scheduled")
              @$el?.find('.exclusion-count').html(@activeModel.computeSummary())
            violationRatio = data
            if violationRatio?
              that._renderShowMoreSelector(el, violationRatio, that.tableModel.startRow - 1 + that.tableModel.nbRows)
            else
              that._renderShowMoreSelector()
        })
      else
        @activeModel.getData({
          success:()=>
            el.find('.exclusion-count').html(@activeModel.computeSummary()) #update exclusion count in scheduled view

        })
        @scheduleModel.getData({
          success:()=>
            data = @scheduleModel.computeSummary()
            if @getSelectedExclusionType() != t("Scheduled")
              el.find('.exclusion-count').html(@scheduleModel.computeSummary())
            violationRatio = data
            if violationRatio?
              that._renderShowMoreSelector(el, violationRatio, that.tableModel.startRow - 1 + that.tableModel.nbRows)
            else
              that._renderShowMoreSelector()
        })

    showOptionsOnTopOrBottomForExclusion:()->
      menu = $('.cont', '.exclusion-overview #show-more').first()
      if menu?
        $(menu).removeClass('top')
        menuTop = menu.offset()?.top
        menuHeight = menu.height()
        totalMenuHeight = menuTop + menuHeight
        if totalMenuHeight >= $(window).height()
          $(menu).addClass('top')

    updateTable:(type)->
      el = @$el
      if type == "ScheduledExclusions"
        @tableModel = new facade.models.exclusion.ScheduledExclusions([],{
          href:facade.context.get('snapshot').get('href')
          startRow:1
          nbRows:@tableModel.size()
        })
      else
        @tableModel = new facade.models.exclusion.ActiveExclusions([],{
          href:facade.context.get('snapshot').get('href')
          startRow:1
          nbRows:@tableModel.size()
        })
      @tableModel.getData({
        success:()=>
          @_updateTableRender(el)
          @onExclusionSelection()
          @getViolationAndRenderShowMore(el)
      })

    onExclusionSelection:(options)->
      el = @$el
      if options?.hasChecked
        el.find('#priority-menu').removeClass('disabled')
        el.find('#exclusion-selector').css('margin-left','9em')
      else
        el.find('#priority-menu').addClass('disabled')
        el.find('#exclusion-selector').css('margin-left','0em')
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

    _updateTableRender:(el)->
      @table.$el.detach()
      rows = @tableModel.asRows({nbRows: @startRow - 1 + @tableModel.length})
      @table.update({rows: rows, resetRowSelector:true})
      el.find('.exclusion-issues-listing .loading').remove()
      el.find('.exclusion-issues-listing').append(@table.render())
      for i in[0 .. rows.length-1]
        if el.find('table tbody tr td:nth-child(2) span')[i]?.className == "status remove"
          el.find('table tbody tr[data-index="' + i + '"] .showViolation').closest('span').css('visibility','hidden')
          el.find('table tbody tr[data-index="' + i + '"] .showViolation').closest('.center').addClass('hide-violation')
          $(el.find('table tbody tr .row-selector')[i]).addClass('hide-row').attr('title', t('This exclusion is scheduled for removal'))
      el.find('table tbody tr td:nth-child(5) .removed').parent().parent().find('input').closest('td').addClass('hide-row').attr('title', t('This exclusion is scheduled for removal'))
      el.find('table thead tr:first th.center').addClass('violation-header-size')
      @manageRemovedExclusions(el, rows, false, true)
      if @tableModel.length == 0
        el.find('.download-file').addClass('disabled')
        el.find('table th.hide-row').removeAttr('title')
        el.find('table tbody').append('<div class="no-violations">' + t('No Violations found') + '</div>')
      el.find('th.row-selector.disabled').on 'click', ->
        return false
      el.find('.row-selector.hide-row').on 'click', ->
        return false
      @getViolationAndRenderShowMore(el)
      @table.delegateEvents()
      @_hideOrShowShowMoreButton()
      resizeTableCol({$el:@$el})

    _hideOrShowShowMoreButton:()->
      tableSize = @tableModel.length
      $('#show-more').css('display', 'table') if tableSize >= 20
      if $('#drill-page #exclusion-selector .selector span.label').first().html() != t("Scheduled")
        @activeModel.getData({
          success:()=>
            data = @activeModel.computeSummary()
            if tableSize == data
              $('#show-more').css('display', 'none')
        })
      else
        @scheduleModel.getData({
          success:()=>
            data = @scheduleModel.computeSummary()
            if tableSize == data
              $('#show-more').css('display', 'none')
        })

    _allValuesSame :(arr)->
      if arr.length == 1 and arr[0] == 'added'
        return true
      nullCheck = _.filter(arr,(val) -> return val)
      if(nullCheck?.length == 0)
        return true
      for i in [1 .. arr.length-1]
        if(arr[i] != arr[0])
          return false
      if(arr[0] == 'added')
        return true
      return true

    scheduleExclusionDialog:(items, sameComments) ->
      item = items[0].get('extra').model.get('exclusionRequest')
      comment = item?.comment
      if items.length >1 and !sameComments
        comment = ""
      scheduleExclusions =  new facade.backbone.DialogView({
        title: t('Update Exclusions')
        subTitle: ''
        message: Handlebars.compile('<div><div class="dialogMessage">{{{t "Please, fill information below to"}}} </br>{{{t "update the selected Exclusions"}}}</div></div> ')
        comment: comment
        cancel: t('Cancel')
        perform: t('Update')
        theme: 'background-blue'
        content: true
        priorityTag: false
        image: ''
        type:'scheduleExclusions'
        commentPlaceholder: t('Comment')
        onPerform: (comment)->
          facade.bus.emit('exclusion:save',{comment:comment, data:items,type:@type})
      })
      scheduleExclusions.render()

    getSelectedExclusionType : ()->
      return @$el?.find('#exclusion-selector .selector .label').html()

    getHeaderRowSelector : ()->
      return @$el?.find('table thead tr th.row-selector ')

    manageRemovedExclusions : (el, rows, isSort, isUpdateTable)->
      isExclusionsRemoved = rows.map(((item)=>
        return item.get('extra').model.get('exclusionRequest')
      ))
      @getHeaderRowSelector()?.addClass('hide-row').attr('title', t('All exclusions are scheduled for removal')) if @_allValuesSame(isExclusionsRemoved)
      if !isUpdateTable
        for i in[0 .. rows.length-1]
          if rows.models[i]?.get('extra').model.get('exclusionRequest') == null
            el.find('table tbody tr[data-index="'+ i + '"] .row-selector input').prop('checked', false) if isSort
            el.find('table tbody tr[data-index="'+ i + '"] .row-selector').addClass('hide-row').attr('title', t('This exclusion is scheduled for removal'))
            el.find('table tbody tr[data-index="' + i + '"] .showViolation').closest('span').css('visibility','hidden')
            el.find('table tbody tr[data-index="' + i + '"] .showViolation').closest('.center').addClass('hide-violation')
        el.find('.row-selector.hide-row').on 'click', ->
          return false

    addToActionPlanDialog:(data) ->
      addToActionPlan =  new facade.backbone.DialogView({
        title: t('Add violations to action plan')
        subTitle: ''
        message: Handlebars.compile('<div><div class="dialogMessage">{{{t "Please, fill information below to"}}} </br>{{{t "Add the selected violations to action plan"}}}</div></div> ')
        comment: t('')
        priority: t('')
        cancel: t('Cancel')
        perform: t('Add')
        theme: 'background-blue'
        content: true
        priorityTag : true
        image: ''
        data:data
        tagList: facade.portal.get('configuration').tag
        commentPlaceholder: t('Comment')
        onPerform: (comment, tag)->
          facade.bus.emit('action-plan:save',{priority:tag, comment:comment, data:@data})
      })
      addToActionPlan.render()

    userRoleCheck:(el) ->
      el.find('#priority-menu').html(@menu.render());
      el.find('#priority-menu div div ul li').addClass('disabled')
      if @qualityManager
        el.find('#priority-menu div div ul li[data-ref="2"]').removeClass('disabled')
        el.find('#priority-menu .cont .options').attr('data-before',t('Select an operation'))
      if @exclusionManager
        el.find('#priority-menu div div ul li[data-ref="0"]').removeClass('disabled')
        el.find('#priority-menu div div ul li[data-ref="1"]').removeClass('disabled')
        el.find('#priority-menu .cont .options').attr('data-before',t('Select an operation'))

    render:()->
      el = @$el
      userAuthorized = @exclusionManager or @qualityManager if facade.context.get('snapshot').isLatest()
      el.html(@template())
      that = this
      $('.exclusion-overview').on('scroll', () ->
        that.showOptionsOnTopOrBottomForExclusion()
      )
      $(window).on('resize', () ->
        that.showOptionsOnTopOrBottomForExclusion()
      )
      $tableHolder = el.find('.exclusion-issues-listing')
      facade.ui.spinner($tableHolder)
      ActiveLabel = t('Active on current snapshot')
      data = [{
        label: ActiveLabel + '[<span class="exclusion-count"></span>]'
        value: 'ActiveExclusions'
        selected: true
      },{
        label: t('Scheduled')
        value: 'ScheduledExclusions'
        selected: ''
      }]
      exclusionSelector = new facade.bootstrap.Selector({name:null, data: data, class: 'light-grey', maxCharacters:80})
      el.find('#exclusion-selector').html(exclusionSelector.render())
      el.find('#exclusion-selector .cont .options').attr('data-before',t('Select exclusion type'))
      exclusionSelector.on('selection', (exclusionType)=>
        @preRender()
        that = this
        el.find('.cont .options li').removeClass('selected')
        el.find('.cont .options [data-value="'+exclusionType+'"]').addClass('selected')
        if exclusionType == "ScheduledExclusions"
          el.find('#exclusion-selector .cont').css('min-width','310px')
          facade.bus.emit('navigate', {page: "actionPlanOverview/" + "exclusions/scheduled"})
        else
          facade.bus.emit('navigate', {page: "actionPlanOverview/" + "exclusions"})
        el.find('.priority-drill-down').addClass('disabled')
        el.find('#exclusion-selector').css('margin-left','0em')
        if exclusionType == 'ActiveExclusions'
          @menu = new facade.bootstrap.Menu({
            text: Handlebars.compile('<span class="add"></span><span class="text">{{t "Manage"}}</span><span class="tooltiptext">{{t "Manage your violations through Actions or Exclusions"}}</span>')
            class: 'light-grey right'
            items:[
              {text: Handlebars.compile('<span class="remove-violations"></span><span class="text"><span class="bold">{{t "Remove"}}</span> {{t "Active Exclusions ..."}} </span>')(),
              action: () =>
                confirm =  new facade.backbone.DialogView({
                  title:t('Remove')
                  subTitle: ''
                  message:t('Are you sure you want to remove active exclusion(s) ?')
                  cancel:t('Cancel')
                  perform:t('Remove')
                  button : true
                  action: 'remove'
                  image: ''
                  theme: 'background-blue'
                  data: @table.getSelectedRows()
                  onPerform:()->
                    facade.bus.emit('exclusion:remove',{data:@data})
                })
                confirm.render()
              }
            ]
          });
          @tableModel = new facade.models.exclusion.ActiveExclusions([],{
            href:facade.context.get('snapshot').get('href')
            startRow:@startRow
            nbRows:@nbRows
          })
        else
          @menu = new facade.bootstrap.Menu({
            text: Handlebars.compile('<span class="add"></span><span class="text">{{t "Manage"}}</span><span class="tooltiptext">{{t "Manage your violations through Actions or Exclusions"}}</span>')
            class: 'light-grey right'
            items: [
              {text: Handlebars.compile('<span class="update-violations"></span><span class="text"><span class="bold">{{t "Update"}}</span> {{t "Scheduled Exclusions "}}...</span></span>')(),
              action: () =>
                data = @table.getSelectedRows()
                data  =_.filter(data,(mod) ->
                  mod.get('extra').model.get('exclusionRequest')
                )
                comments = data.map(((item)=>
                  return item.get('extra')?.model.get('exclusionRequest')?.comment
                ))
                @scheduleExclusionDialog(data, @_allValuesSame(comments))
              }
              {text: Handlebars.compile('<span class="remove-violations"></span><span class="text"><span class="bold">{{t "Remove"}}</span> {{t "from Scheduled list "}}...</span>')(),
              action: () =>
                data = @table.getSelectedRows()
                data  =_.filter(data,(mod) ->
                  mod.get('extra').model.get('exclusionRequest')
                )
                confirm =  new facade.backbone.DialogView({
                  title:t('Remove')
                  subTitle: ''
                  message:t('Are you sure you want to remove scheduled exclusion(s) ?')
                  cancel:t('Cancel')
                  perform:t('Remove')
                  image: 'logout'
                  button: true
                  action: 'remove'
                  theme: 'background-blue'
                  data: data
                  type: exclusionType
                  onPerform:()->
                    facade.bus.emit('exclusion:remove',{data:@data,type:@type})
                })
                confirm.render()
              }
              {
                text: Handlebars.compile('<span class="related-violations"></span><span class="text"><span class="bold">{{t "Add"}}</span> {{t "the related violations to action plan "}}...')(),
                action: () =>
                  data = @table.getSelectedRows()
                  data  =_.filter(data,(mod) ->
                    mod.get('extra').model.get('exclusionRequest')
                  )
                  @addToActionPlanDialog(data)

              }
            ]
          });
          @tableModel = new facade.models.exclusion.ScheduledExclusions([],{
            href:facade.context.get('snapshot').get('href')
            startRow:@startRow
            nbRows:@nbRows
          })
        @downloadLinkUrl = @tableModel.url() + '&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        @userRoleCheck(el)
        #        @$el?.find('.priority-drill-down .selector').click ->
        #          updateRemoveCount = 0
        #          toAddRemoveCount = 0
        #          countdom = $(this).closest('#drill-page')
        #          updateRemoveInputElements = $(this).closest('#drill-page').find('.exclusion-issues-listing table tbody tr input')
        #          elements=countdom.find('.exclusion-issues-listing table tbody tr .added').closest('tr').find('input')
        #
        #          _.each(updateRemoveInputElements,(element)->
        #            if $(element).prop('checked')
        #              ++updateRemoveCount
        #          )
        #          _.each(elements,(element)->
        #            if $(element).prop('checked')
        #              ++toAddRemoveCount
        #          )
        #          if updateRemoveCount > 0
        #            countdom.find('.update-count').html(updateRemoveCount)
        #            countdom.find('.remove-count').html(updateRemoveCount)
        #            countdom.find('.related-count').html(updateRemoveCount)
        that = @
        @tableModel.getData({
          success:()=>
            el.find('show-more').remove()
            @getViolationAndRenderShowMore(el)
            @_hideOrShowShowMoreButton()
            rows = @tableModel.asRows({nbRows: @startRow - 1 + @nbRows})
            @table = new facade.bootstrap.Table({
              columns:[
                {header: t('status'), headerMin:'#xe61a;',title:t('Status'), align: 'center', length:4, format: (value)->
                  value = 'remove' if value == ''
                  return '<span class="status ' + value + '"></span>'
                },
                {header: t('Comment'),title:t('Comment'), align:'left stretch'}
                {header: t('Rule'), title:t('Rule'),align:'left stretch'}
                {header: t('Object name location'), title:t('Object name location'),align:'left stretch', format: (value)->
                  return _objectNameTemplate({value})
                },
                {header: t('Last update'),title:t('Last update'), align:'left stretch date', format: (time)->
                  return moment.utc(time).format('MM-DD-YYYY') if time
                  return '<span class="removed"></span>'
                },
                {header: t(''), align:'center', format: (value)->
                  title = t('Access the violation source code')
                  state = 'showViolation'
                  status = value.split('_')[0]
                  href = '#'+ SELECTED_APPLICATION_HREF + '/snapshots/' + facade.context.get('snapshot').getId() + '/qualityInvestigation/0/' +that.businessCriterion+'/all/'+ value.split('_')[1] + '/' + '_ap' ;
                  return  _violationsTemplate({href: href, title: title, state: state})
                }
              ]
              rows:rows
              rowSelector:  if userAuthorized then true else false
            })
            if @getSelectedExclusionType() != t("Scheduled")
              @table.options.columns.pop()
              @table.options.columns.shift()
            $tableHolder.html(@table.render())
            el.find('.table').addClass('drill-down-column') if @getSelectedExclusionType() == t("Scheduled")
            @table.on('update:row-selector', @onExclusionSelection, @)
            @manageRemovedExclusions(el, rows, false, false)
            if @tableModel.length == 0
              el.find('.download-file').addClass('disabled')
              el.find('table th.hide-row').removeAttr('title')
              el.find('table tbody').append('<div class="no-violations">' + t('No Violations found') + '</div>')
            el.find('table tbody tr td.center').last().addClass('violation-body-size')
            el.find('table thead tr:first th.center').addClass('violation-header-size')
            @table.on('sorted', @sortColumn, @)
            el.find('th.row-selector.disabled').on 'click', ->
              return false
            #      IE and Edge Fix
            isIE = false || !!document.documentMode;
            isEdge = !isIE && !!window.StyleMedia;

            if isIE || isEdge
              el.find('.row-selector').on 'mouseover', ->
                $('html').addClass('noSelect')
              el.find('.row-selector').on 'mouseout', ->
                $('html').removeClass('noSelect')
            resizeTableCol({$el:@$el})
          error:() =>
            @activeModel.getData({
              success:()=>
                el.find('.exclusion-count').html(@activeModel.computeSummary())
                el.find('.exclusion-issues-listing').html(@unavailableTemplate)
                if !facade.context.get('snapshot').isLatest() and exclusionType == "ScheduledExclusions"
                  el.find('.download-file').addClass('disabled')
            })
        },exclusionType)
      )
      if window.location.href.indexOf("actionPlanOverview/exclusions/scheduled") >-1
        $('#exclusion-selector .selector .label').text(t("Scheduled"))
        exclusionSelector.trigger('selection','ScheduledExclusions')
      else
        exclusionSelector.trigger('selection','ActiveExclusions')

    remove:()->
      facade.bus.off('exclusion:updated',@updateTable)
      @table?.remove()
      @$el.remove()
      @unbind()
      delete @$el
      delete @el;
      @stopListening()
      @
  })
  return ExclusionDetailView