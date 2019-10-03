
ExpandableViewPlugin = (bus, _, BackboneWrapper, Handlebars) ->

  resizeTableCol=(data)->
    data = data.data if data.data?

    # respWidth = $('#gizmo').width()
    # Proceed to the resize for each table that can be found here, as we have sections

    # adjust table headers
    # data.$el.find('.table').each((index) ->
    #   # does not work for section based tables, scroll event to be raised after
    #   $(this).data('bootstrap-table')?.adjustStickyHeader?($(this).parent())
    # )
    # data.$el.find('.sections-content').trigger('scroll')
    that = data
    data.$el.find('.table').each (index) ->
      table = $(this)

      # minWidth = 0

      table.removeClass('contract compact large super-large')
      table.addClass('test')
      $actualTable = table.find('table')

      # ---------------------------------------------------------------------------------- #
      # Get the stretching column... !!! CODE OK FOR JUST ONE STRETCHING COLUMN !!!
      # ---------------------------------------------------------------------------------- #
      currentHeight = table.outerHeight()
      table.css({'white-space':'nowrap'})
      newHeight = table.outerHeight()
      table.css({'white-space':''})
      table.addClass('contract') if newHeight != currentHeight
      table.addClass('contract') if $actualTable.width() > table.width()

      # ---------------------------------------------------------------------------------- #
      # Get the stretching column... !!! Loop it again for the contract mode
      # ---------------------------------------------------------------------------------- #
      if (table.width()/screen.width * 100) < 22 || $('#detail-page-3').width() < 420
        currentHeight = table.outerHeight()
        table.css({'white-space':'nowrap'})
        newHeight = table.outerHeight()
        table.css({'white-space':''})
        table.addClass('compact') if newHeight != currentHeight
        table.addClass('compact') if $actualTable.width() > table.width()
        return @

#      return @ if table.hasClass('compact')
#      return @ if table.hasClass('contract')

      #large and superlarge classes not required as of now.
      # TODO optimize
      if (table.width()/screen.width * 100) > 35
        currentHeight = table.outerHeight()
        table.addClass('large')
        table.css({'white-space':'nowrap'})
        newHeight = table.outerHeight()
        table.css({'white-space':''})
        table.removeClass('large') if newHeight != currentHeight

      if (table.width()/screen.width * 100) > 65
        currentHeight = table.outerHeight()
        table.addClass('super-large')
        table.css({'white-space':'nowrap'})
        newHeight = table.outerHeight()
        table.css({'white-space':''})
        table.removeClass('super-large') if newHeight != currentHeight
      return @


  ###
    ExpandableView proposes a view with a splitter mechanism. The splitter mechanism require the view to
    be associated to another view (event splitter:resize)
    The expandable view hosts a backbone view and will getData on the inner view model if available before
    rendering.

    Exposed fields:
      - minSize: minimal size in number of pixels (default to 300)
    Exposed methods
      - resize
      - transition methods : moveOut, moveDownIn, moveRightOut, move(left), moveRight, moveIn
  ###
  return BackboneWrapper.View.extend({
    minSize:250
    template: Handlebars.compile('<div id="dragger" class="dragger"></div><div id="content" class="content {{theme}}">
      <div class="loading {{theme}}">
        <div class="square" id="square1"></div>
        <div class="square" id="square2"></div>
        <div class="square" id="square3"></div>
        <div class="square" id="square4"></div>
    </div></div>')

    events:
      'mousedown #dragger':'acquireResize'

    scroll:(event)->
      $(event.target).find('.table').each((index, item)->
        $(item).data('bootstrap-table')?.adjustStickyHeader($(event.target))
      )

    initialize:(options)->
      @$el.addClass(options.className) if options.className
      @options = _.extend({}, options)
      @resizeTableColDebounced([$el:@$el])
      $(window).on('resize', {$el:@$el}, $.proxy(@resizeTableColDebounced, @))


    remove:()->
      @innerView?.remove?()
      BackboneWrapper.View.prototype.remove.apply(this, arguments)

    # ---------------------------------------------------------------------------------- #
    # -----------------------------TABLE SIZE MANAGEMENT-------------------------------- #
    # ---------------------------------------------------------------------------------- #
    # Slight optimization, large/super-large started to add extra calculation cost
    # and caused loss of responsiveness
    resizeTableColDebounced:()->
      resizeTableCol({$el:@$el})


    triggerResponsivePanelDebounced:(data) ->
      #DOES NOT WORKING WITH PASSED VARIABLE. A GLOBAL ONE COULD BE CREATED, BUT SEEMS MESS COMPARED TO THE SMALL BENEFITS IT BRINGS
      @triggerResponsivePanelDebounced = _.debounce(
          ->
            @triggerResponsivePanel(data)
            return
        ,10)

    triggerResponsivePanel:(data) ->
      bus.emit('responsive-panel', data)

    resize:(newWidth)->
      @triggerResponsivePanel({leftView:@$el, leftWidth:newWidth})
      @$el.css('width', newWidth + 'px')
      resizeTableCol({$el:@$el})

    acquireResize:(event)->
      return @leaveZoomMode() if @$el.hasClass('zoom')
      @$el.parent().find('.draggable').css('transition','')
      $('html').addClass('noSelect')
      $(window)
      .on('mousemove', @, @resizeView)
      .on('mouseup', @releaseResize)

    releaseResize:(event)->
      $('html').removeClass('noSelect')
      $(window).off('mousemove', @resizeView)
      .off('mouseup', @releaseResize)

    enterZoomMode:()->
      @$el.addClass('zoom')
      $(window).off('mousemove', @resizeView)
      @trigger('zoom',{inZoom:true})

    leaveZoomMode:()->
      $draggable = @$el #$target.parent('.draggable')
      $draggable.removeClass('zoom')
      totalWidth = $draggable.parent('.drag-container').width()
      newWidth = totalWidth / 3 # not full half presentation

      @_saveHandleLocation(newWidth, totalWidth )
      @$el.css('left', newWidth + 'px')
      @$el.css('width', totalWidth  - newWidth  + 'px')
      resizeTableCol({$el:@$el})
      @trigger('splitter:resize', newWidth)
      @trigger('zoom',{inZoom:false})

    setZoom:()->
      @$el.addClass('zoom')
      return @

    cleanSelection:()->
      @$el.find('#table-holder').find('.selected').removeClass('selected')
      return @

    resetZoom:()->
      @$el.removeClass('zoom')
      return @

    _saveHandleLocation:(left, width)->
      localStorage.setItem('investigationHandle', left / width)

    resizeView:(event)->
      view = event.data
      pageX = event.pageX - 60 # lateral menu size. TODO get the actual value as the menu may be removed/closed at some point
      left = parseInt(view.unPx(view.$el.offsetParent().css('left')))
      width = parseInt(view.unPx(view.$el.offsetParent().css('width')))
      newLeft = pageX - left
      newWidth = width - pageX + left
      if newWidth < view.minSize
        newWidth = view.minSize
        newLeft = width - newWidth
      otherWidth = width - newWidth
      if otherWidth < view.minSize
        otherWidth = 0
        newWidth = width - otherWidth
        newLeft = width - newWidth
        view.enterZoomMode()
      view._saveHandleLocation(newLeft, width)
      view.$el.css('left',newLeft + 'px').css('width',newWidth + 'px')
      view.resizeTableColDebounced({$el:view.$el})
      view.trigger('splitter:resize', otherWidth)
      view.triggerResponsivePanel({rightView:view.$el, rightWidth:newWidth})

    unPx:(value)->
      value.replace('px','')

    updateViewState:(parameters)->
      @innerView?.updateViewState?(parameters)

    reload:(options)->
      @innerView.updateModel?(options)
      innerView = @innerView
      if innerView.model?
        innerView.model.getData({
          success:()=>
            innerView.render()
          error:()=>
            console.error arguments
#            alert('failure')
        })
      else innerView.render()

    innerContentScrollRequest:(top)->
      $content = @$el.find('.content')
      height = $content.height()
      return if (top < 2*height/3) # basic heuristic, only scroll a bit if it is already in page but at the bototm
      if (top < height)
        $content.animate({scrollTop:100}, '500')
      else
        $content.animate({scrollTop:top - 50}, '500')

    render:(innerView)->
      if @innerView?
        @innerView.off('scroll',@innerContentScrollRequest)
      @innerView = innerView
      @innerView.on('scroll',@innerContentScrollRequest, @)
      @$el.html(@template(@options))
      if innerView.model?
        innerView.model.getData({
          success:()=>
            @$el.find('#content').html(innerView.render())
          error:()=>
            console.error arguments
        })
      else
        @$el.find('#content').html(innerView.render())
      # @$el.find('div').on('scroll', (event)=>
      #   @scroll(event)
      # )
      @$el

    moveOut:(time)->
      return @$el.hide() if !Modernizr?.cssanimations
      if time == 0
        @$el.animo({animation: 'fadeOutUp', duration: time, timing: 'ease-in-out'})
        @$el.hide()
      else
        time = time or 0.8
        @$el.animo({animation: 'fadeOutUp', duration: time, timing: 'ease-in-out'}, ()=>
          @$el.hide()
        )

    moveDownIn:(width)->
      @$el.show()
      @$el.css('width', width)
      @$el.animo({animation: 'fadeInDown', duration: 0.8, timing: 'ease-in-out'}, ()=>
#        @$el.find('#dragger').css("opacity", "0").css('display','none')
      )

    moveRightOut:()->
      @$el.animo({animation: 'fadeOutRight', duration: 0.8, timing: 'ease-in-out'}, ()=>
        @$el.hide()
      )

    move:(shift, newWidth)->
      change('moveLeft',-shift)
      @$el.show()
      @$el.addClass('left')
      @$el.animo({animation: 'moveLeft', duration: 0.8, timing: 'ease-in-out'}, ()=>
        @$el.css('left', '0').css('width', newWidth)
        @$el.find('#dragger').css('opacity', '0').css('display','none')
      )

    moveRight:(shift)->
      change('moveRight',shift)
      @$el.show()
      @$el.find('tr.selected').removeClass('selected')
      @$el.animo({animation: 'moveRight', duration: 0.8, timing: 'ease-in-out'}, ()=>
        @$el.removeClass('left').addClass('right')
        @$el.css('left', shift)
        @$el.find('#dragger').css('opacity', '1').css('display','block')
      )

    moveIn:(shift, width)->
      @$el.show()
      @$el.css('left', shift)
      @$el.css('width', width)
      @$el.removeClass('left')
      @$el.animo({animation: 'fadeInRight', duration: 0.8, timing: 'ease-in-out'}, ()=>
        @$el.find('#dragger').css("opacity", "1").css('display','block')
      )
  })
