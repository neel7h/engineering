EducationView = (facade) ->

  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t
  _violationsTemplate = Handlebars.compile('<span>
             {{#if href}}
                 <em class="short-content" title="{{title}}"><a class="{{state}}" href="{{href}}">&#xe93e;</a></em>
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

  EducationDetailView = facade.backbone.View.extend({
    template:Handlebars.compile('<div class="education-overview">
              <header>
                <div id="education-selector"><span>{{t "Rules with triggered education"}}</span></div>
                <div class="priority-drill-down disabled" id="priority-menu"></div>
                <a title="{{t "download data as excel file"}}" class="download-file pos">{{t "Download Excel"}}</a>
              </header>
              <article>
                <div class="education-issues-listing"></div>
              </article>
            </div>')

    loadingTemplate: '<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    unavailableTemplate: Handlebars.compile('<div class="investigation-not-available"><h1>{{{t "Education not available in past snapshot"}}}</h1><p>{{{t "You may only be able to investigate this data in the latest snapshot."}}}</p></div>')

    events:
      'click .active': 'shareRuleDetails'
      'click .download-file': 'downloadAsExcelFile'

    preRender:()->
      @$el.find('.education-issues-listing').html(@loadingTemplate)

    downloadAsExcelFile:()->
      href = @downloadLinkUrl
      $.ajax('url': REST_URL + 'user', 'async': false)
        .success(()->
        window.location = href if href?
      )
      return false

    initialize:()->
      @tableModel = new facade.models.education.EducationSummary([],{
        href:facade.context.get('snapshot').get('href')
      })
      @businessCriterion = "60017"
      @businessCriterion = "60016" if facade.context.get('isSecurity')
      @selectedRows = []
      @qualityAutomationManager= facade.context.get('user').get('qualityAutomationManager')
      facade.bus.on('education:updated', @updateTable, @)
      $(window).on('resize', {$el:@$el}, resizeTableCol)

    shareRuleDetails: (event) ->
      that = @
      UrlModel = Backbone.Model.extend(
        makeUrl: (tags) ->
          urlStr=@get('url')
          urlSep='?'
          params = @get('params')
          for paramKey, paramVal of @get('params')
            for tagKey, tagVal of tags
              tagVal = '"' + tagVal + '"' if paramKey == "body" and tagKey == "ruleName"
              paramVal = paramVal.replace( new RegExp('\\$'+tagKey,'g'), tagVal)
            urlStr+= urlSep + paramKey + '=' + encodeURIComponent(paramVal)
            urlSep="&"
          return urlStr
      )

      UrlCollection = Backbone.Collection.extend(
        url: 'resources/urls.json'
        model: UrlModel

        makeUrl: (mailToId, tags) ->
          return @get(mailToId).makeUrl(tags)
      )
      urlsStore = new UrlCollection()
      urlsStore.fetch().done(()->
        ruleId = event.currentTarget.dataset['ruleid']
        ruleName = decodeURIComponent(event.currentTarget.dataset['rulename'])
        actionText = event.currentTarget.dataset['actiontext']
        ruleDocumentationUrl = window.location.href.split('#')[0] + '#'+ SELECTED_APPLICATION_HREF + "/snapshots/" + facade.context.get('snapshot').getId() + "/qualityInvestigation/0/#{that.businessCriterion}/all/#{ruleId}/0/_edu"
        ViolationsUrl = window.location.href.split('#')[0] + '#'+ SELECTED_APPLICATION_HREF + "/snapshots/" + facade.context.get('snapshot').getId() + "/qualityInvestigation/0/#{that.businessCriterion}/all/#{ruleId}/0"
        tags = {ruleName: ruleName, ruleDocumentationUrl: ruleDocumentationUrl, violationsUrl: ViolationsUrl, actionText: actionText}
        window.location.href = urlsStore.makeUrl("share-rule-details", tags)
      )

    onEducationSelection:(options)->
      el = @$el
      if options?.hasChecked
        el.find('#priority-menu').removeClass('disabled')
        el.find('#education-selector').css('margin-left','9em')
      else
        el.find('#priority-menu').addClass('disabled')
        el.find('#education-selector').css('margin-left','0em')
      isKeyPressed = options?.isShift
      rowModels =  @table.options.rows.models
      @selectedRows = [] if(@table.getSelectedRows().length == 0)
      if options?.hasChecked && options?.row
        options.row.isShift = true if isKeyPressed
        availableIds = _.pluck(@selectedRows, 'cid')
        index = availableIds.indexOf(options.row.cid)
        if index < 0
          @selectedRows.push(options.row)
          numOfRows = @selectedRows.length
        else
          @selectedRows = @selectedRows.splice(index, 1)

        if isKeyPressed && @selectedRows.length > 1
          previousRow = parseInt(el.find('table tbody tr[data-id="' +@selectedRows[@selectedRows.length-2].id  + '"]').attr("data-index"), 10 )
          currentRow = parseInt(el.find('table tbody tr[data-id="' +@selectedRows[@selectedRows.length-1].id  + '"]').attr("data-index"), 10 )
          if @selectedRows[@selectedRows.length-1].isShift
            for i in [previousRow .. currentRow]
              el.find('table tbody tr[data-index="'+ i + '"] .row-selector input[type="checkbox"]').prop('checked', true)
              rowModels[i].attributes.rowSelected = true

    _allValuesSame :(arr)->
      return true if arr.length == 0
      for i in [1 .. arr.length-1]
        if(arr[i] != arr[0])
          return false
      return true

    updateEducationDialog:(items, sameComments, samePriority, sameActive) ->
      item = items[0].get('extra').model
      comment = item.get('remedialActionPattern').comment
      priority = item.get('remedialActionPattern').tag or item.get('remedialActionPattern').priority
      if item.get('active') == true then actions = facade.portal.get('configuration').tag.actions[0] else actions = facade.portal.get('configuration').tag.actions[1]
      if items.length >1 and !sameComments
        comment = ""
      if items.length >1 and !samePriority
        priority = ""
      if items.length >1 and !sameActive
        actions = facade.portal.get('configuration').tag.actions[1]
      addToEducation =  new facade.backbone.DialogView({
        title: t('Update Scheduled Education')
        subTitle: ''
        message: Handlebars.compile('<div><div class="dialogMessage">{{{t "Please, fill information below to update the scheduled Education"}}} </br>{{{t "related to new violations detectable on the next snapshot"}}}</div></div> ')
        comment: comment
        priority: t(priority)
        actions: actions
        cancel: t('Cancel')
        perform: t('Update')
        content: true
        education: true
        theme: 'background-blue'
        image: ''
        priorityTag: true
        tagList: facade.portal.get('configuration').tag
        commentPlaceholder: t('Comment for future violations')
        onPerform: (comment, tag, actions)->
          facade.bus.emit('education:save',{priority:tag, comment:comment, actions:actions, data:items})
      })
      addToEducation.render()

    updateTable:()->
      el = @$el
      @tableModel = new facade.models.education.EducationSummary([],{
        href:facade.context.get('snapshot').get('href')
      })
      @tableModel.getData({
        success:()=>
          @table.$el.detach()
          @_updateTableRender(el)
          @onEducationSelection()
      })

    _updateTableRender:(el)->
      rows = @tableModel.asRows()
      @table.update({rows: rows, resetRowSelector:true})
      el.find('.education-issues-listing .loading').remove()
      el.find('.education-issues-listing').append(@table.render())
      @table.delegateEvents()
      @sortColumn()
      el.find('.row-selector.hide-row').on 'click', ->
        return false

    render:()->
      el = @$el
      @downloadLinkUrl = @tableModel.url()+ '?startRow=0&nbRows=100001'+ '&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      userAuthorized = @qualityAutomationManager if facade.context.get('snapshot').isLatest()
      el.html(@template())
      @menu = new facade.bootstrap.Menu({
        text: Handlebars.compile('<span class="add"></span><span class="text">{{t "Manage"}}</span><span class="tooltiptext">{{t "Manage your rules through Education"}}</span>')
        class: 'light-grey right'
        items:[
          {text: Handlebars.compile('<span class="update"></span><span class="text"><span class="bold">{{t "Update"}}</span> {{t " scheduled education ..."}}</span>')(),
          action: () =>
            data = @table.getSelectedRows()
            comments = data.map(((item)=>
              return item.get('extra').model.get('remedialActionPattern').comment
            ))
            priorities = data.map(((item)=>
              return item.get('extra').model.get('remedialActionPattern').tag or item.get('extra').model.get('remedialActionPattern').priority
            ))
            active =  data.map(((item)=>
              return item.get('extra').model.get('active')
            ))
            @updateEducationDialog(data, @_allValuesSame(comments) , @_allValuesSame(priorities) ,@_allValuesSame(active))
          }
#          {text: Handlebars.compile('<span class="share-rules"></span><span class="text"><span class="bold">{{t "Share and Promote"}}</span> {{t "selected diagnostics"}} </span>')()
##          action: () =>
#          }
          {text: Handlebars.compile('<span class="remove-violations"></span><span class="text"><span class="bold">{{t "Remove"}}</span> {{t "from Education"}} </span>')(),
          action: () =>
            confirm =  new facade.backbone.DialogView({
              title:t('Remove')
              subTitle: ''
              message:t('Are you sure you want to remove rule(s) from Education list ?')
              cancel:t('Cancel')
              perform:t('Remove')
              button : true
              image: ''
              theme: 'background-blue'
              data: @table.getSelectedRows()
              onPerform:()->
                facade.bus.emit('education:remove',{data:@data})
            })
            confirm.render()
          }]
      })
      el.find('#priority-menu').html(@menu.render())
      el.find('#priority-menu .cont .options').attr('data-before',t('Select an operation'))
      $tableHolder = el.find('.education-issues-listing')
      facade.ui.spinner($tableHolder)
      that = @
      @tableModel.getData({
        success:()=>
          rows = @tableModel.asRows()
          @table = new facade.bootstrap.Table({
            columns:[
              {header: t('Rule'), title:t('Rule'),align:'left stretch'}
              {header: t('Tag'), title:t('Tag'), align: 'left', length:4, format: (value)->
                tag = value.charAt(0).toUpperCase() + value.slice(1);
                return '<span>'+tag+'</span>'
              },
              {header: t('Comment'),title:t('Comment'), align:'left stretch'}
              {header: t('Action'),title:t('Action'), align:'left stretch', format: (value)->
                if value then return "Mark for action" else return "Mark for continuous improvement"
              }
              {header: t('Last update'),title:t('Last update'), align:'left stretch noBorder', format: (time)->
                return moment.utc(time).format('MM-DD-YYYY')
              },
              {header: t(''), align: 'center noBorder', format: (value)->
                name ='active'
                title = t('Share the rule and object with violation')
                if value.active then actionText = t('We would like to inform you that all new violations will be automatically added to the action plan for the next scan done with CAST.') else actionText = t('Please note that this rule has been selected as a measure for continuous improvement and henceforth, we would be monitoring this rule. Our goal is that we would not create any new violation for this rules and fix the existing violation, wherever possible.')
                return '<span title="'+t(title)+'" class="'+name+'" data-ruleid= "'+value.ruleId+'" data-actiontext="'+actionText+'" data-rulename= "'+encodeURIComponent(value.ruleName)+'">&#xe940;</span>'
              },
              {header: t(''), align:'center', format: (value)->
                title = t('Access the rule documentation')
                state = 'showRuleDocumentation'
                education = true
                href = '#'+ SELECTED_APPLICATION_HREF + '/snapshots/' + facade.context.get('snapshot').getId() + '/qualityInvestigation/0/' +that.businessCriterion+'/all/'+ value+'/0/_edu'
                return  _violationsTemplate({href: href, title: title, state: state, education: education})
              }
            ]
            rows:rows
            rowSelector:userAuthorized
          })
          $tableHolder.html(@table.render())
          @table.on('update:row-selector', @onEducationSelection, @)
          @sortColumn()
          @table.on('sorted', @sortColumn, @)
          el.find('a.showRuleDocumentation').on 'click', -> return localStorage.setItem('filterViolationsByStatus','added')
          el.find('.row-selector.hide-row').on 'click', ->
            return false
        error:() =>
          if !facade.context.get('snapshot').isLatest()
            el.find('.education-issues-listing').html(@unavailableTemplate)
            @$el.find('.download-file').addClass('disabled')
      })
    sortColumn:() ->
      if @tableModel.length == 0
        @$el.find('.download-file').addClass('disabled')
        @$el.find('table thead th').addClass('hide-row')
        @$el.find('table th.hide-row').removeAttr('title')
        @$el.find('table tbody').append('<div class="no-rules">' + t('No Rules found') + '</div>')
      @$el?.find('table thead tr:first th.center').addClass('violation-header-size')
      resizeTableCol({$el:@$el})

    remove:()->
      facade.bus.off('education:updated', @updateTable)
      @table?.remove()
      @$el.remove()
      @unbind()
      delete @$el
      delete @el
      @stopListening()
      @
  })
  return EducationDetailView
