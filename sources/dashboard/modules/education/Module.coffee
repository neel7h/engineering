###
  Defines the education manipulation component.
###
define [], ->
  EducationModule = (facade) ->
    EducationView = EducationView (facade)
    ImprovementSection = ImprovementSection (facade)
    ViolationsSection = ViolationsSection (facade)

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

    education =

      save: (parameters)->
        return unless parameters?
        return unless parameters.data?
        comment = parameters.comment
        tag = parameters.priority
        active = parameters.actions
        putData = []
        postData = []
        if !parameters.data.length
          item = {
            rulePattern:
              href: parameters.data.href or parameters.data.get('extra').model.get('rulePattern').href
            remedialActionPattern:
              comment: comment
              tag: tag
            active: active
          }
          postData.push(item)
        else
          for sample in parameters.data
            model = sample.get('extra').model
            item = {
              rulePattern:
                href: model.get('rulePattern').href
              remedialActionPattern:
                comment: comment
                tag: tag
              active: active
            }
            if model.get('remedialActionPattern') then putData.push(item) else postData.push(item)
        postDeferred = _processData('POST', postData, '/action-plan/triggers')
        putDeferred = _processData('PUT', putData, '/action-plan/triggers')
        href = SELECTED_APPLICATION_HREF + '/educationOverview/education'
        $.when(postDeferred, putDeferred).done(()->
          if postData.length != 0
            facade.bus.emit('notification:message',{
              message:Handlebars.compile('<a class="link" href="#{{href}}">{{t "Education"}}</a>')({href:href})
              title: '<em>'+postData.length+'</em> '+ t(' rule successfully added to Education')
              type:'log'
            })
            if parameters.page
              ruleNameSpan = $(".rule-name[data-ruleid*='#{parameters.data.href?.split('/')[2] or parameters.data.get('extra').model.get('rulePattern').href.split('/')[2]}']")
              if parameters.actions then ruleNameSpan?.addClass("educate-icon") else ruleNameSpan?.addClass("educate-icon disabled")
          if putData.length != 0
            facade.bus.emit('notification:message',{
              title:'<em>'+putData.length+'</em>'+ t(' rule(s) successfully updated to Education')
              message:Handlebars.compile('<a class="link" href="#{{href}}">{{t "Education"}}</a>')({href:href})
              type:'log'
            })
          facade.bus.emit('education:updated')
          if $('.action-plan .breadcrumb .breadcrumb-path [title="EDUCATION"]').parent().hasClass('selected')
            $('.notification-popup .link').hide()
          facade.bus.emit('data:updated')
        ).fail(()->
          facade.bus.emit('notification:message',{
            message:t('Failed to update education.')
            title:t('Education')
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
            rulePattern:
              href: model.get('rulePattern').href
          }
          if model.get('remedialActionPattern')?
            deleteData.push(item)
        href = SELECTED_APPLICATION_HREF + '/educationOverview/education'
        if deleteData.length == 0
          facade.bus.emit('notification:message',{
            message:Handlebars.compile('<a href="#{{href}}">{{t "Education"}}</a>')({href:href})
            title:t('No data to remove from education')
            type:'warn'
          })
        else
        deleteDeferred = _processData('DELETE', deleteData, '/action-plan/triggers')
        $.when(deleteDeferred).done(()->
          facade.bus.emit('notification:message',{
            message:''
            title:'<em>'+deleteData.length+'</em>' + ' ' + t('rule(s) successfully removed from education')
            type:'log'
          })
          facade.bus.emit('education:updated')
          facade.bus.emit('data:updated')
        ).fail(()->
          facade.bus.emit('notification:message',{
            message:t('Failed to remove Education.')
            title:t('Education')
            type:'error'
          })
        )

    ExtendedRoute = facade.navigation.Router.extend(
      routes:
        ':domain/applications/:id(/modules/:moduleId)(/technology/:technology)(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)/educationOverview/(:education)':'gotoEducation'
        ':domain/applications/:id(/modules/:moduleId)(/technology/:technology)(/snapshots/:snapshotId)(/business/:filterBusinessCriterion)/educationOverview/(:improvement)/(:violationType)':'gotoEducation'

      gotoEducation: (domain, id, moduleId, technology, snapshotId, filterBusinessCriterion, education, violationType)->
        facade.bus.emit('show', {
          pageId:'educationOverview'
          filterBusinessCriterion:filterBusinessCriterion
          education: education
          tab:'remediation'
          violationType: violationType
        })
    )

    module = {
      initialize: (options) ->
        @options = _.extend({}, options)
        facade.bus.on('education:save', education.save, education)
        facade.bus.on('education:remove', education.remove, education)
        facade.bus.on('show', @control ,@)
        facade.bus.on('show', @processBreadcrumb, @)

        facade.bus.emit('menu:add-item',{
          "className": "education-overview",
          "text": t('Education and Continuous improvement'),
          "route": "educationOverview/education",
        })

        facade.bus.emit('tile:register',{
          type:'ContinuousImprovement'
          TileView:ContinuousImprovementTile(facade)
        })
        
      postInitialize:(options)->
        router = new ExtendedRoute() # in the post initialize to make sure *other route still comes last

      control:(options) ->
        return unless 'educationOverview' == options?.pageId
        if @view?
          @view.remove()
          delete @view
        if options.education == 'education'
          $(@options.el).html('<div id="education-holder"></div>')
          @view = new EducationView({el:'#education-holder'})
        else
          $(@options.el).html('<div id="improvement-holder"></div>')
          @view = new ImprovementSection({el:'#improvement-holder', violationType: options.violationType, ViolationsSection: ViolationsSection})
        @view.$el.show()
        @view.render()

      processBreadcrumb:(parameters)->
        return unless 'educationOverview' == parameters.pageId
        facade.bus.emit('theme', {theme:'education'})
        snapshotId = facade.context.get('snapshot').getId()
        moduleId = facade.context.get('module')?.getId()
        rootHREF = '#' + SELECTED_APPLICATION_HREF
        rootHREF += '/modules/' + moduleId if moduleId?
        rootHREF += '/snapshots/' + snapshotId
        rootHREF += '/business/' + parameters.filterBusinessCriterion if parameters.filterBusinessCriterion?
        rootHREF += '/educationOverview'
        path = [{
          name:t('EDUCATION')
          type:''
          href:rootHREF + '/education'
          className: ''
        },{
          name:t('IMPROVEMENT')
          type:''
          href:rootHREF + '/improvement'
          className: ''
        }
        ]
        facade.bus.emit('header', {criticalFilter:'disable'})
        if parameters.education == 'education'
          path[0].className = 'selected'
        else
          path[1].className = 'selected'
        facade.bus.emit('breadcrumb', {
          pageId:parameters.pageId
          path:path
        })

      destroy: () ->
    }
    return module

  return EducationModule
