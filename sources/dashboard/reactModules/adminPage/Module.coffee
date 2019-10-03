define [], ->

  ConfigurationModule = (facade) ->

    View = facade.backbone.View.extend({
     template: facade.Handlebars.compile('<div id ="component"></div>')

     render:()->
       @$el.html(@template)
     })

    ExtendedRoute = facade.navigation.Router.extend(
      routes: '/admin' : 'goToAdmin'

      goToAdmin: ()->
        facade.bus.emit('show')
    )

    module = {
      initialize: (options) ->
        @options = _.extend({}, options)
        facade.bus.on('show', @control, @)

      postInitialize:(options)->
        router = new ExtendedRoute()

      control:(options)->
        require ['dashboard/reactModules/adminPage/app'], (app) =>
          console.log('app', app)
        $(@options.el).html('<div id="configuration-container"></div>')
        @admin_configuration = new View(el:'#configuration-container')
        @admin_configuration.$el.show()
        @admin_configuration.render()

      destroy: () ->
        @admin_configuration.remove()
    }
    return module

  return ConfigurationModule