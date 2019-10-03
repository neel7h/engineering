###
  Defines the notification popup messaging system.
###
define [], ->

  NotificationModule = (facade) ->

    ###
      Notification popup view.
      Expected behavior: the message displays on the bottom right of the page. Message will disappear after a few
      seconds, unless the user take focus with the mouse (popup do not close while mouse is hovering) or explicitly
      removes the popup via the remove button.
    ###
    Notification = facade.backbone.View.extend({
      tagName:'div'
      className:'notification-popup'
      template:facade.Handlebars.compile('<div class="message {{type}}"><span class="remove-notification"></span><h3>{{{title}}}</h3>{{{message}}}</div>')
      removalDelay:5000
      events:
        'click .remove-notification':'terminate'
        'mouseover':'postponeTermination'
        'mouseout':'proceedWithTermination'

      initialize:(options)->
        @options = facade._.extend({},options)

      postponeTermination:()->
        return if @options.persistent
        clearTimeout(@timerId)
        @$el.css('opacity', 1)
        @timerId = null

      proceedWithTermination:()->
        return if @options.persistent
        return if timerId?
        @timerId = facade._.delay(()=>
          @terminate()
        , @removalDelay)

      terminate:()->
        @$el.css('opacity',0)
        @timerId = facade._.delay(()=>
          @remove()
        , 1000)

      render:()->
        @$el.html(@template(@options))
        if @options.persistent
          @$el.addClass('on-top')
        else
          @timerId = facade._.delay(()=>
            @terminate()
          , @removalDelay)
        @$el
    })

    ###
      Module definition.
    ###
    module = {
      initialize: (options) ->
        @$notifications = facade.$('body')
          .append('<div class="notification-container"></div>')
          .find('.notification-container')
        @$topNotifications = facade.$('body')
          .append('<div class="notification-container on-top"></div>')
          .find('.notification-container.on-top')
        facade.bus.on('notification:message', @displayNotification, @)
        facade.bus.on('notification:persistent-message', @displayPersistentNotification, @)

      displayPersistentNotification:(data = {})->
        options = facade._.extend({message:'',title:'information',type:'log', persistent:true},data)
        notificationView = new Notification(options)
        @$topNotifications.append(notificationView.render())

      displayNotification:(data = {})->
        options = facade._.extend({message:'',title:'information',type:'log'},data)
        notificationView = new Notification(options)
        @$notifications.append(notificationView.render())

      destroy: () ->
        @$notifications.remove()
        @$topNotifications.remove()
    }
    return module

  return NotificationModule
