controller = (bus, _, BackboneWrapper,ExpandableView, Handlebars) ->

  transition = 'all 0.8s'
  
  InvestigationController = BackboneWrapper.View.extend({
    pageId:''
    states:{}
    template: Handlebars.compile('<div class="drag-container">
            {{#each pages}}<div class="draggable" id="detail-page-{{@index}}"></div>{{/each}}
          </div>
          <div class="selected-object-info"></div>')

    initialize:(options) ->
      @options = _.extend({}, options)
      @pageId = @pageId or options.pageId
      bus.on('responsive-panel', @responsivePanel, @)


    control:(parameters)->
      return @exit() if @pageId != parameters.pageId
      @render() unless @rendered
      # update panels content
      candidateIndex = @states.computeIndex(parameters)
      @parameters = _.extend({}, @states.parameters, parameters, {inZoom:@inZoom and candidateIndex!=0})

      index = 0
      for page in @states.pages
        break if index++ > candidateIndex + 1
        newUrl = page.instance?.updateViewState(@parameters)
        return bus.emit('navigate', {page:newUrl} ) if newUrl?

      @states.previousIndex = @states.currentIndex
      @states.currentIndex = candidateIndex
      # update navigation state
      return @enter() if @states.previousIndex == -1

      queryStringToUpdate = {}
      for parameter of @parameters.queryString
        if @states.pages[@states.currentIndex].queryString?
          queryStringToUpdate[parameter] = 0 if @states.pages[@states.currentIndex].queryString.indexOf(parameter) == -1
          continue
        queryStringToUpdate[parameter] = 0
      bus.emit('update:url', queryStringToUpdate)

      direction = @states.currentIndex - @states.previousIndex
      return @dontMove() if 0 == direction
      return @drillUp(direction) if direction < 0
      return @drillDown(direction)

    exit:()->
      return unless @rendered
      bus.off('leave:zoom', @leaveZoomMode)
      @controlCleanup?()
      for page in @states.pages
        if page.instance?
          page.instance.remove()
          delete page.instance
      @rendered = false
      @states.currentIndex = -1
      @states.previousIndex = -1
      return

    enter:()->
      bus.on('leave:zoom', @leaveZoomMode, @)
      leftPage = @states.pages[@states.currentIndex]
      leftPage.instance = new ExpandableView({el: '#detail-page-' + @states.currentIndex, className:'left', theme:@states.parameters?.theme})
      leftPage.instance.render(new leftPage.pageView(@parameters))


      rightPage = @states.pages[@states.currentIndex+1]
      rightPage.instance = new ExpandableView({el: '#detail-page-' +(@states.currentIndex+1), className:'right', theme:@states.parameters?.theme})
      rightPage.instance.render(new rightPage.pageView(@parameters))
      zooming = false
      try
        handleRatio = localStorage.getItem('investigationHandle')
        if !isNaN(handleRatio) and parseFloat(handleRatio) == 0
          zooming = true
          rightPage.instance.$el.addClass('zoom')
      rightPage.instance.on('splitter:resize', leftPage.instance.resize, leftPage.instance)
      rightPage.instance.on('zoom', @setZoom, @)

      @setZoom({inZoom:zooming})

    dontMove:()->
      if @states.currentIndex == 0 and @inZoom
        @states.pages[1].instance.leaveZoomMode()
        @setZoom({inZoom:false})

    drillDown:(steps)->
      return @setZoom({inZoom:@inZoom}) if steps < 1
      index = @states.currentIndex - steps
      page0 = @states.pages[index]
      page1 = @states.pages[index+1]
      page2 = @states.pages[index+2]
      unless page2.instance?
        page2.instance = new ExpandableView({el: '#detail-page-' + (index+2), className:'out-of-view', theme:@states.parameters?.theme})
        page2.instance.render(new page2.pageView(@parameters))
      @drillDownTransition(page0.instance, page1.instance, page2.instance)
      @drillDown(steps-1)

    drillUp:(steps)->
      if steps > -1
        return @setZoom({inZoom:@inZoom})

      index = @states.currentIndex - steps
      page0 = @states.pages[index-1]
      unless page0.instance?
        page0.instance = new ExpandableView({el: '#detail-page-' + (index-1), className:'left', theme:@states.parameters?.theme})
        page0.instance.render(new page0.pageView(@parameters))
      page1 = @states.pages[index]
      page2 = @states.pages[index+1]

      @drillUpTransition(page0.instance, page1.instance, page2.instance)
      if @states.currentIndex == 0 and @inZoom
        page1.instance.leaveZoomMode()
        @inZoom = false
      return @drillUp(steps+1)

    leaveZoomMode:()->
      return unless @inZoom
      @states.pages[@states.currentIndex+1].instance.leaveZoomMode()
      @setZoom({inZoom:false})

    setZoom:(data)->
      @inZoom = data.inZoom
#      bus.emit('zoom', _.extend({}, @parameters, {inZoom:@inZoom}))

    render:()->
      $(window).off('resize', @resize)
      @$el.html(@template(@states))
      if @options.hasSelectedObjectInfo? and @options.hasSelectedObjectInfo
        @$el.find('.selected-object-info').show()
      @$el
      $(window).on('resize',{controller:@},@resize)
      @rendered = true

    responsivePanel:(data)->
      if data.rightView?
        @manageResponsivePanel(data.rightView, data.rightWidth)
      if data.leftView?
        @manageResponsivePanel(data.leftView, data.leftWidth)

    manageResponsivePanel:(theView, theSize)->
      if theSize <= 430
        theView.addClass('compact')
      else
        theView.removeClass('compact')

    resize:(event)->
      controller = event.data.controller
      states = controller.states
      return if states.currentIndex < 0
      leftView = states.pages?[states.currentIndex].instance
      rightView = states.pages?[states.currentIndex+1].instance
      globalWidth = controller.$el.find('.drag-container').width()

      handleRatio = localStorage.getItem('investigationHandle')
      if handleRatio?
        handleRatio = parseFloat(handleRatio)
      else
        handleRatio = .33

      leftWidth = Math.round(globalWidth*handleRatio)
      rightWidth = globalWidth - leftWidth
      leftView?.$el.width(leftWidth)
      rightView?.$el.width(rightWidth)
      rightView?.$el.css('left', leftWidth)
      controller.responsivePanel({leftView:leftView?.$el, leftWidth:leftWidth, rightView:rightView?.$el, rightWidth:rightWidth})


    drillDownTransition:(view0, view1, view2)->
      gW = @$el.find('.drag-container').width()
      widthL = view0.$el.width()
      if @inZoom and widthL == gW
        widthL = 0
      widthR = gW - widthL

      view0.moveOut()
      view1.$el.removeClass('right').removeClass('out-of-view').addClass('left')
      view1.$el.find('.dragger').css({'display':'none', 'opacity':'0'})
      view1.$el.css('transition',transition).show()
      view1.$el.css('left',0)
      view1.$el.css('width',widthL)

      view2.$el.find('.dragger').css({'display':'', 'opacity':'1'})
      view2.$el.css('transition',transition).show()
      view2.$el.css('left', widthL)
      view2.$el.css('width', widthR)

      view1.$el.removeClass('zoom')
      view0.$el.removeClass('zoom')

      if @inZoom
        view2.$el.addClass('zoom')
        view1.$el.removeClass('zoom')
      else
        view2.$el.removeClass('zoom')
      view2.$el.removeClass('left').removeClass('out-of-view').addClass('right')

      view1.off('splitter:resize', view0.resize)
      view1.off('zoom', @setZoom)
      view2.on('splitter:resize', view1.resize, view1)
      view2.on('zoom', @setZoom, @)
      @responsivePanel({leftView:view1.$el, leftWidth:widthL, rightView:view2.$el, rightWidth:widthR})

    drillUpTransition:(hiddenView, leftView, rightView)->
      gW = @$el.find('.drag-container').width()
      widthL = leftView.$el.width()
      widthR = gW - widthL
      rightView.$el.find('.dragger').css({'display':'none', 'opacity':'0'})
      rightView.$el.css('transition',transition).show()
      rightView.$el.css('left','100%')

      rightView.$el.addClass('out-of-view').removeClass('right')
      leftView.$el.find('.dragger').css({'display':'', 'opacity':'1'})
      leftView.$el.css('transition',transition).show()
      leftView.$el.css('left', widthL)
      leftView.$el.css('width',widthR)

      if @inZoom
        leftView.$el.addClass('zoom')
        hiddenView.$el.removeClass('zoom')
      else
        leftView.$el.removeClass('zoom')
      leftView.$el.addClass('right').removeClass('left')

      hiddenView.resetZoom().moveDownIn(widthL)
      hiddenView.$el.find('.dragger').css({'display':'none', 'opacity':'0'})
      rightView.off('splitter:resize', leftView.resize)
      rightView.off('zoom', @setZoom)
      leftView.on('splitter:resize', hiddenView.resize, hiddenView)
      leftView.on('zoom', @setZoom, @)
      @responsivePanel({leftView:leftView.$el, leftWidth:widthL, rightView:rightView.$el, rightWidth:widthR})

    selectComponent:(parameters)->
      @$el.find('.selected-object-info').html(parameters?.name)
  })