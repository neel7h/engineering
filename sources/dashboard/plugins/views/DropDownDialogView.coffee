DropDownDialogView = ($, _, Backbone, Handlebars, Highcharts, moment)->

  ## Manages the overlay for the drop down
  Overlay = Backbone.View.extend({
      className:'overlay'
      events:
        'click':'closeDropDown'
      initialize:(options)->
        this.dropDown = options.dropDown
      closeDropDown:(event)->
        this.dropDown.trigger('close') if 'overlay' == event.target.className

      render:()->
        @$el.html('')
        return @$el
  })

  # The drop down is just a container here.
  DropDownView = Backbone.View.extend({
    className:'drop-down-container'
    template:Handlebars.compile('<div><h2>{{title}}</h2><button class="close-button">Close</button></div><div id="container"></div>')
    events:
      'click .close-button': 'closeDropDown'

    initialize:(options)->
      @options = _.extend({},options)
      this.on('close', this.closeDropDown, this)

    removeOverlay:()->
      @$overlay?.remove();

    closeDropDown:()->
      this.remove()
      @removeOverlay()
      this.trigger('closing-dropdown')

    positionDialog:()->
      $attach = @options.$attach;
      top = $attach.offset().top + $attach.height() + 40
      right = @$overlay.width() -  $attach.offset().left - (@options.width + $attach.width()) / 2
      if @options.isHeader
        @$el.addClass('align-header')
      @$el
        .css('top',top)
        .css('right',right)
        .css('min-width',@options.width)
        .css('min-height',@options.height)

    render:()->
      @removeOverlay()
      @$overlay = new Overlay({dropDown:this, $el:$('<div></div>')}).render()
      $('body').append(@$overlay)
      @$el.html(@template({title:@options.title}))
      @positionDialog()
      @$overlay.html(@$el)
      setTimeout(()=>
        @$el.addClass('visible')
      , 20 )
      return @$el

    addContent:($el)->
      @$el.find('#container').html($el)

  })

  ModalView = DropDownView.extend({
    className:'drop-down-container modal-container'
    closeDropDown:()->
      DropDownView.prototype.closeDropDown.apply(this, arguments)
      $('#container').removeClass('content-blur');

    positionDialog:()->
      $('#container').addClass('content-blur');
      $body = $('body')
      top = $body.offset().top + $body.height() + 20
      right = @$overlay.width() -  $body.offset().left - (@options.width + $body.width()) / 2
      @$el
        .css('position','absolute')
        .css('top','50%')
        .css('left','50%')
        .css('min-width', @options.width)
        .css('min-height',@options.height)
        .css('margin-left',-@options.width/2 + 'px')
        .css('margin-top',-@options.height/2 + 'px')

  })

  return {
    DropDownView
    ModalView
  }
