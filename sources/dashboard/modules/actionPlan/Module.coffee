###
  Defines the action plan manipulation component.
###
define [], ->
  ActionPlanModule = (facade) ->
    ActionPlanView = ActionPlanView (facade)
    ExclusionsView = ExclusionsView (facade)

    Handlebars = facade.Handlebars
    $ = facade.$
    _ = facade._
    t = facade.i18n.t

    _processData = (httpVerb, data, suffixUrl) ->
      if data.length == 0
        deferred = $.Deferred()
        deferred.resolve()
      else
        deferred = $.ajax(
          REST_URL + SELECTED_APPLICATION_HREF + suffixUrl
        , {
            type:httpVerb
            headers:
              "accept":'application/json'
              "content-type":'application/json'

            data:JSON.stringify(data)
          })
      return deferred

    actions =
      save: (parameters)->
        return unless parameters?
        return unless parameters.data?
        tag = parameters.priority
        comment = parameters.comment
        putData = []
        postData = []
        if parameters.data[0].get('extra').model.get('remedialAction')?.tag == tag and parameters.data[0].get('extra').model.get('remedialAction')?.comment == comment
          facade.bus.emit('notification:message',{
            message:t('Please update priority and comment. Failed to update action plan.')
            title:t('Action plan')
            type:'error'
          })
        else
          for sample in parameters.data
            model = sample.get('extra').model
            item = {
              component:
                href: model.get('component').href
              rulePattern:
                href: model.get('rulePattern').href
              remedialAction:
                tag: tag
                comment: comment
            }
            if model.get('remedialAction')?
              putData.push(item)
            else
              postData.push(item)

          postDeferred = _processData('POST', postData, '/action-plan/issues')
          putDeferred = _processData('PUT', putData, '/action-plan/issues')
          href = SELECTED_APPLICATION_HREF + '/actionPlanOverview/0'
          $.when(postDeferred, putDeferred).done(()->
            if postData.length != 0
              facade.bus.emit('notification:message',{
                message:Handlebars.compile('<span class="toast-message">{{t "To edit or remove action plan, you can also go to the"}} <a class="link" href="#{{href}}">{{t "Action Plan View"}}</a></span>')({href:href})
                title: '<em>'+postData.length+'</em> '+ ' ' + t('violation(s) successfully added to action plan')
                type:'log'
              })
            if putData.length != 0
              facade.bus.emit('notification:message',{
                message:Handlebars.compile('<span class="toast-message">{{t "To edit or remove action plan, you can also go to the"}} <a class="link" href="#{{href}}">{{t "Action Plan View"}}</a></span>')({href:href})
                title:'<em>'+putData.length+'</em>'+ ' ' + t('violation(s) successfully modified in action plan')
                type:'log'
              })
            if $('.exclusion-overview #exclusion-selector .selector .label').text() == "Scheduled"
              facade.bus.emit('exclusion:updated',"ScheduledExclusions")
            else
              facade.bus.emit('action-plan:updated')
            if $('.action-plan .breadcrumb .breadcrumb-path [title="ACTIONS"]').parent().hasClass('selected')
              $('.notification-popup .toast-message').hide()
            facade.bus.emit('data:updated')
          ).fail(()->
            facade.bus.emit('notification:message',{
              message:t('Failed to update action plan.')
              title:t('Action plan')
              type:'error'
            })
          )

      remove: (parameters)->
        return unless parameters?
        return unless parameters.data?

        deleteData = []
        for sample in parameters.data
          model = sample.get('extra').model
          item = {
            component:
              href: model.get('component').href
            rulePattern:
              href: model.get('rulePattern').href
          }
          # to avoid trying to remove items that are not in action plan, which will lead to an error
          if model.get('remedialAction')?
            deleteData.push(item)
        href = SELECTED_APPLICATION_HREF + '/actionPlanOverview/0'
        if deleteData.length == 0
          facade.bus.emit('notification:message',{
            message:Handlebars.compile('{{t "To edit or remove action plan, you can also go to the"}} <a href="#{{href}}">{{t "Action Plan View"}}</a>')({href:href})
            title:t('No data to remove from action plan')
            type:'warn'
          })
        else
          deleteDeferred = _processData('DELETE', deleteData, '/action-plan/issues')
          $.when(deleteDeferred).done(()->
            facade.bus.emit('notification:message',{
              message:Handlebars.compile('<span class="toast-message">{{t "To edit or remove action plan, you can also go to the"}} <a href="#{{href}}">{{t "Action Plan View"}}</a></span>')({href:href})
              title:'<em>'+deleteData.length+'</em>' + ' ' + t('violation(s) successfully removed from action plan')
              type:'log'
            })
            facade.bus.emit('action-plan:updated')
            facade.bus.emit('data:updated')
            if $('.action-plan .breadcrumb .breadcrumb-path [title="ACTIONS"]').parent().hasClass('selected')
              $('.notification-popup .toast-message').hide()
          ).fail(()->
            facade.bus.emit('notification:message',{
              message:t('Please select priority. Failed to update action plan.')
              title:t('Action plan')
              type:'error'
            })
          )

    exclusions =

      save: (parameters)->
        return unless parameters?
        return unless parameters.data?
        comment = parameters.comment
        putData = []
        postData = []
        if parameters.data[0].get('extra').model.get('exclusionRequest')?.comment == comment
          facade.bus.emit('notification:message',{
            message:t('Please update comment. Failed to schedule exclusions.')
            title:t('Exclusions')
            type:'error'
          })
        else
          for sample in parameters.data
            model = sample.get('extra').model
            item = {
              rulePattern:
                href: model.get('rulePattern').href
              component:
                href: model.get('component').href
              exclusionRequest:
                comment: comment
            }
            if model.get('exclusionRequest')?
              putData.push(item)
            else
              postData.push(item)

          postDeferred = _processData('POST', postData, '/exclusions/requests')
          putDeferred = _processData('PUT', putData, '/exclusions/requests')
          href = SELECTED_APPLICATION_HREF + '/actionPlanOverview/exclusions/scheduled'
          $.when(postDeferred, putDeferred).done(()->
            if postData.length != 0
              facade.bus.emit('notification:message',{
                message:Handlebars.compile('<a class="link" href="#{{href}}">{{t "Exclusion"}}</a>')({href:href})
                title: '<em>'+postData.length+'</em> '+ t(' violation(s) successfully Excluded on next snapshot')
                type:'log'
              })
            if putData.length != 0
              facade.bus.emit('notification:message',{
                message:Handlebars.compile('<a class="link" href="#{{href}}">{{t "Exclusion"}}</a>')({href:href})
                title:'<em>'+putData.length+'</em>'+ t(' violation(s) successfully updated for Exclusion on next snapshot')
                type:'log'
              })
            if $('.exclusion-overview #exclusion-selector .selector .label').text() == "Scheduled"
              facade.bus.emit('exclusion:updated',"ScheduledExclusions")
            else
              facade.bus.emit('action-plan:updated')
            if $('.action-plan .breadcrumb .breadcrumb-path [title="EXCLUSIONS"]').parent().hasClass('selected')
              $('.notification-popup .link').hide()
            facade.bus.emit('data:updated')
          ).fail(()->
            facade.bus.emit('notification:message',{
              message:t('Failed to schedule exclusions.')
              title:t('Exclusion')
              type:'error'
            })
          )

      remove: (parameters)->
        return unless parameters?
        return unless parameters.data?

        deleteData = []
        for sample in parameters.data
          model = sample.get('extra').model
          item = {
            component:
              href: model.get('component').href
            rulePattern:
              href: model.get('rulePattern').href
          }
          # to avoid trying to remove items that are not in exclusions, which will lead to an error
          if model.get('exclusionRequest')?
            deleteData.push(item)
        href = SELECTED_APPLICATION_HREF + '/actionPlanOverview/exclusions'
        if deleteData.length == 0
          facade.bus.emit('notification:message',{
            message:Handlebars.compile('<a href="#{{href}}">{{t "Exclusions"}}</a>')({href:href})
            title:t('No data to remove from exclusion')
            type:'warn'
          })
        else
          deleteDeferred = _processData('DELETE', deleteData, '/exclusions/requests')
          $.when(deleteDeferred).done(()->
            Scheduledtitle = t('violation(s) successfully removed from Scheduled Exclusions')
            Activetitle = t('violation(s) successfully removed from Active Exclusions on the next snapshot or a snapshot reconsolidation')
            title = Scheduledtitle if deleteData.length > 1
            if window.location.href.indexOf('actionPlanOverview/exclusions/scheduled') != -1
              title = Scheduledtitle
            else
              title = Activetitle
            facade.bus.emit('notification:message',{
              message:''
              title:'<em>'+deleteData.length+'</em>' + ' ' + title
              type:'log'
            })
            facade.bus.emit('exclusion:updated',parameters.type)
            facade.bus.emit('data:updated')
          ).fail(()->
            facade.bus.emit('notification:message',{
              message:t('Failed to update exclusion.')
              title:t('Exclusion')
              type:'error'
            })
          )

    ExtendedRoute = facade.navigation.Router.extend(
      routes:
        ':domain/applications/:id(/modules/:moduleId)(/technology/:technology)(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)/actionPlanOverview/(:exclusions)':'gotoActionPlan'
        ':domain/applications/:id(/modules/:moduleId)(/technology/:technology)(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)/actionPlanOverview/(:exclusions)/(:scheduled)':'gotoActionPlan'

      gotoActionPlan: (domain, id, moduleId, technology, snapshotId, filterBusinessCriterion, exclusions)->
        facade.bus.emit('show', {
          pageId:'actionPlanOverview'
          filterBusinessCriterion:filterBusinessCriterion
          exclusions: exclusions
          tab:'remediation'
        })
    )

    module = {
      initialize: (options) ->
        @options = _.extend({}, options)
        facade.bus.on('action-plan:save', actions.save, actions)
        facade.bus.on('action-plan:remove', actions.remove, actions)
        facade.bus.on('exclusion:save', exclusions.save, exclusions)
        facade.bus.on('exclusion:remove', exclusions.remove, exclusions)
        facade.bus.on('show', @control ,@)
        facade.bus.on('show', @processBreadcrumb, @)

        facade.bus.emit('tile:register',{
          type:'ActionPlanSummary'
          TileView:ActionPlanSummaryTile(facade)
        })

        facade.bus.emit('tile:register',{
          type:'ExclusionSummary'
          TileView:ExclusionSummaryTile(facade)
        })


        facade.bus.emit('menu:add-item',{
          "className": "action-plan-overview",
          "text": t('Monitor Actions and Exclusions'),
          "route": "actionPlanOverview/0",
        })

      postInitialize:(options)->
        router = new ExtendedRoute() # in the post initialize to make sure *other route still comes last

      control:(options) ->
        return unless 'actionPlanOverview' == options?.pageId
        if @view?
          @view.remove()
          delete @view

        if options.exclusions == 'exclusions'
          $(@options.el).html('<div id="exclusion-holder"></div>')
          @view = new ExclusionsView({el:'#exclusion-holder'})
        else
          $(@options.el).html('<div id="action-plan-holder"></div>')
          @view = new ActionPlanView({el:'#action-plan-holder'})
        @view.$el.show()
        @view.render()

      processBreadcrumb:(parameters)->
        return unless 'actionPlanOverview' == parameters.pageId
        facade.bus.emit('theme', {theme:'action-plan'})
        snapshotId = facade.context.get('snapshot').getId()
        moduleId = facade.context.get('module')?.getId()
        rootHREF = '#' + SELECTED_APPLICATION_HREF
        rootHREF += '/modules/' + moduleId if moduleId?
        rootHREF += '/snapshots/' + snapshotId
        rootHREF += '/business/' + parameters.filterBusinessCriterion if parameters.filterBusinessCriterion?
        rootHREF += '/actionPlanOverview'
        path = [{
          name:t('ACTIONS')
          type:''
          href:rootHREF + '/0'
          className: ''
        },{
          name:t('EXCLUSIONS')
          type:''
          href:rootHREF + '/exclusions'
          className: ''
        }]
        facade.bus.emit('header', {criticalFilter:'disable'})
        if parameters.exclusions =='exclusions'
          path[1].className = 'selected'
        else
          path[0].className = 'selected'
        facade.bus.emit('breadcrumb', {
          pageId:parameters.pageId
          path:path
        })

      destroy: () ->
    }
    return module

  return ActionPlanModule
