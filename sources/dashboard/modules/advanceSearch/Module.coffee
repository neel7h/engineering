define [], ->

  AdvanceSearchModule = (facade) ->

    $ = facade.$
    t = facade.i18n.t
    _ = facade._
    Handlebars = facade.Handlebars

    Controller = Controller(facade)

    UnavailableView = facade.backbone.View.extend({
      template: Handlebars.compile('<div class="unavailable-view">
          <h1>{{t "Content not available in past snapshot"}}</h1>
          <p>{{t "Advanced search is not available in this snapshot."}}</p>
          <p>{{t "You may only be able to use this feature in the latest snapshot."}}</p>
        </div>')
      render:()->
        @$el.html(@template)
    })

    UnavailableIndexView = facade.backbone.View.extend({
      template: Handlebars.compile('<div class="unavailable-index-view"><h1>{{t "No index created for Advanced search"}}</h1><h2>{{t "Please contact system administrator"}}</h2></div>')
      render:()->
        @$el.html(@template)
    })

    module = {
      initialize: (options) ->
        @options = _.extend({}, options)
        facade.bus.emit('menu:add-item',{
          "className": "advance-search",
          "text": t('Advanced search'),
          "route": "search",
        })
        if localStorage.getItem('violationIndexStatus') != 'upToDate'
          @initializeOnNoIndex(options)
          return
        if facade.context.get('snapshot').isLatest()
          @initializeOnCurrentSnapshots(options)
        else
          @initializeOnPastSnapshots(options)

      initializeOnNoIndex:(options)->
        facade.bus.on('show', (parameters)->
          if 'advanceSearch' == parameters.pageId
            view = new UnavailableIndexView({el:options.el})
            view.render()
            facade.bus.emit('theme', {theme:'advance-search'})
            facade.bus.emit('header', {criticalFilter:'disable'})
            facade.bus.emit('breadcrumb', {
              path:[{name:t('Advanced search'), type: '', href: null, className: ''}],
              pageId:parameters.pageId
            })
        , @)

      initializeOnCurrentSnapshots:(options)->
        controller = new Controller({el: options.el})
        facade.bus.on('show', controller.control, controller)
        facade.bus.on('show', @processBreadcrumb, @)

      initializeOnPastSnapshots:(options)->
        facade.bus.on('show', (parameters)->
          if 'advanceSearch' == parameters.pageId
            view = new UnavailableView({el:options.el});
            view.render();
            facade.bus.emit('theme', {theme:'advance-search'})
            facade.bus.emit('header', {criticalFilter:'disable'})
            facade.bus.emit('breadcrumb', {
              path:[{name:t('Advanced search'), type: '', href: null, className: ''}],
              pageId:parameters.pageId
            })
        , this)

      processBreadcrumb:(parameters)->
        return unless 'advanceSearch' == parameters.pageId
        facade.bus.emit('theme', {theme:'advance-search'})
        path =[{
          name:t('Advanced search')
          type: ''
          href: null
          className: ''
        }]
        facade.bus.emit('breadcrumb', {
          pageId:parameters.pageId
          path :path
        })
        facade.bus.emit('header', {criticalFilter:'disable'})
      destroy: () ->
        @view.remove()
    }
    return module

  return AdvanceSearchModule