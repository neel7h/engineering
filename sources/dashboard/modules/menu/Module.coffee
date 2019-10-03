###
  Defines the application navigation menu and possible interactions.
###
define [], ->

  MenuModule = (facade) ->

    configuration = facade.portal.get('configuration')
    pages = configuration.navigation.pages

    MenuView = facade.backbone.View.extend({
      template:facade.Handlebars.compile('<nav class="menu">
      {{#each pages}}
        <div id = "{{id}}" class="button"><div class="menu-cursor"><a {{#if route}}href="{{../rootHref}}{{route}}" {{/if}} title="{{text}}" id="{{@index}}" class="icon {{className}}"></a></div></div>
      {{/each}}
      </nav>')
      events:
        'click .icon':'clickOnMenu'

      initialize:(options)->
        facade.bus.on('menu:add-item', @addMenuItem, @)
        facade.bus.on('filter:updated', @updateUrls, @)

      addMenuItem: (data)->
        pages.push(data)
        @render()

      clickOnMenu:(event)->
        $currentIcon = $(event.target).parent().parent()
        item = pages[event.target.id]
        if item.event?
          facade.bus.emit(item.event)
          if $currentIcon.hasClass('help-mode') # TODO we should define a general non-url action property rather than specific one.
            $currentIcon.removeClass('help-mode')
            @$el.find('#' + @context?.route).addClass('selected')
          else
            $currentIcon.addClass('help-mode')
        facade.bus.emit('header',{criticalFilter:'enable'}) if item.id == "home"

      setContext:(parameters)->
        @context = _.extend({},parameters)

      selectMenuItem:(parameters)->
        @$el.find('.button').removeClass('selected')
        if parameters.route?
          if parameters.route == 'home'
            facade.bus.emit('theme', {theme:''})
          @$el.find('#' + parameters.route).addClass('selected')
        else  
          @$el.find('#' + parameters.pageId).addClass('selected')

      generateHref:()->
        rootURL = '#' + SELECTED_APPLICATION_HREF
        snapshotId = facade.context.get('snapshot').getId()
        rootURL +=  '/snapshots/' + snapshotId if snapshotId?
        businessFilter = facade.context.get('scope').get('businessCriterion')
        rootURL +=  '/business/' + businessFilter if businessFilter?
        return rootURL + '/'

      updateUrls:()->
        rootHref = @generateHref()
        for page in pages
          @$el.find('#' + page.id).find('a').attr('href', rootHref + page.route)

      render:()->
        for page in pages
          if page.route == 'actionPlanOverview/0'
            page.id = 'actionPlanOverview'
          else if page.route == 'qualityInvestigation/0'
            page.id = 'qualityInvestigation'
          else if page.route == 'educationOverview/education'
            page.id = 'educationOverview'
          else
            page.id = page.route
        @$el.html(@template({
          rootHref:@generateHref()
          pages:pages
        }))
        @$el
    })

    module = {
      initialize: (options) ->
        @view = new MenuView({el:options?.el})
        @view.render()
        facade.bus.on('show', @view.selectMenuItem, @view)
        facade.bus.on('show', @view.setContext, @view)
      destroy: () ->
        @view.remove()
    }
    return module

  return MenuModule

