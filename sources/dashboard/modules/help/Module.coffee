###
  Defines the application help and possible interactions.
###
define [], ->

  HelpModule = (facade) ->

    backbone = facade.backbone
    Handlebars = facade.Handlebars
    _ = facade._
    $ = facade.$
    t = facade.i18n.t

    HelpContainerView = facade.backbone.View.extend({
      initialize:() ->
        facade.bus.on('toggle:help-buttons',@toggleHelpMode,@)

      toggleHelpMode:()->
        if @$el.hasClass('help-disable-view')
          @$el.removeClass('help-disable-view')
        else
          @$el.addClass('help-disable-view')
    })

    HelpView = facade.backbone.View.extend({
      tagName:'div'
      className:'help-point'
      template:Handlebars.compile('
          <div id="help-button" class="help-button closed disabled">&#xe621;</div>
          <div class="help-description closed">
              <h2>{{title}}</h2>
              {{{content}}}
          </div>')

      events:
        'click #help-button':'toggleHelpDescription'

      toggleHelpDescription:(event)->
        $button = @$el.find('.help-button')
        $description = @$el.find('.help-description')
        if $button.hasClass('closed')
          facade.bus.emit('close:help-messages')
          this.$el.addClass('active')
          $button.addClass('visited') unless $button.hasClass('visited')
          $button.removeClass('closed')
          $description.removeClass('closed')
        else
          this.$el.removeClass('active')
          $button.addClass('closed')
          $description.addClass('closed')
        position = @options.position
        if position?
          $description.addClass(position) unless $description.hasClass(position)
        else
          $description.addClass('bottom-right') unless $description.hasClass('bottom-right')


      toggleHelp:()->
        $button = @$el.find('.help-button')
        $description = @$el.find('.help-description')
        $description.addClass('closed')
        $button.addClass('closed')
        targetVisible = @options.$target.is(":visible")
        targetVisible = @options.isVisible?() if targetVisible and @options.isVisible?

        if $button.hasClass('disabled') and targetVisible
          @positionHelpButton()
          $button.removeClass('disabled')
        else
          $button.addClass('disabled')

      closeHelp:()->
        $button = @$el.find('.help-button')
        $description = @$el.find('.help-description')
        $description.addClass('closed')
        $button.addClass('closed')
        this.$el.removeClass('active')

      initialize:(options)->
        @options = _.extend({},options)
        @on('toggle:help-buttons', @toggleHelp, @)
        $(window).on('resize', _.debounce(
          () =>
            @positionHelpButton()
        ,100))

      positionHelpButton:()->
        $p = @options.$target

        offset = $p.offset()
        if offset?
          @$el.css('top', offset.top + $p.outerHeight(true)/3)
          anchor = @options.anchor
          if anchor == 'left'
            @$el.css('left', offset.left - 1 * $p.outerWidth(true)/4)
          else
            @$el.css('left', offset.left + 2 * $p.outerWidth(true)/3)

      render:()->
        @$el.html(@template(@options))

    })

    HelpDialogueView = HelpView.extend({
      dialogTemplate:Handlebars.compile('
          <div id="help-button" class="help-button closed disabled">&#xe621;</div>
          <div class="dialog-help-description closed"></div>')

      toggleHelpDescription:(event)->
        helpDialog = new facade.backbone.HelpDialogView({
          title:'Help'
          image:@options.image
          contentTitle:@options.title
          contentBody:@options.content
        })
        $button = @$el.find('.help-button')
        $description = @$el.find('.dialog-help-description')
        $description.html(helpDialog.render())
        if $button.hasClass('closed')
          $button.addClass('visited') unless $button.hasClass('visited')
          $description.removeClass('closed')
        else
          $description.addClass('closed')
        position = @options.position
        if position?
          $description.addClass(position) unless $description.hasClass(position)
        else
          $description.addClass('bottom-right') unless $description.hasClass('bottom-right')

      render:()->
        @$el.html(@dialogTemplate(@options))
    })

    module = {
      initialize: (options) ->
        @$el= $(options.el)
        containerView = new HelpContainerView({el:@$el})
        facade.bus.on('help:createView',@createHelpView,@)
        facade.bus.on('close:helpViews', @closeHelpViews, @)

      postInitialize:()->
        facade.bus.emit('menu:add-item',{
          "className": "help",
          "text": t('Help'),
          "event": "toggle:help-buttons"
        })

      createHelpView:(options)->
        if options.useHelpDialog
          view = new HelpDialogueView(options)
        else
          view = new HelpView(options)
        @$el.append(view.render())
        facade.bus.on('toggle:help-buttons', view.toggleHelp, view)
        facade.bus.on('close:help-messages', view.closeHelp, view)
    }
    return module

  return HelpModule
