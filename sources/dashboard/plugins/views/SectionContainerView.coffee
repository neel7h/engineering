sections = ($, _, BackboneWrapper, Handlebars) ->

  active = (section, filter)->
    return false unless section?
    return true unless section.filters?
    return true unless filter?
    return section.filters.indexOf(filter) >= 0

  deactivate = (view, section) ->
    view.$el.find('#' + section.id).hide()
    view.$el.find('#' + section.sectionId).hide()
    section.inactiveView = section.inactiveView or section.view
    section.view = null
    section.inactiveClosedView = section.inactiveClosedView or section.closedView
    section.closedView = null

  activate = (view, section) ->
    #view.$el.find('#' + section.id).show()
    view.$el.find('#' + section.id).css({'display':'block'})
    view.$el.find('#' + section.sectionId).show()
    section.view = section.view or section.inactiveView
    section.inactiveView = null
    section.closedView = section.closedView or section.inactiveClosedView
    section.inactiveClosedView = null

  sectionTemplate='<div class="closed-section-content"><h2>{{View.prototype.title}}</h2></div><div id="drill-{{id}}" class="drill-down">
 <div class="loading {{theme}}">
        <div class="square" id="square1"></div>
        <div class="square" id="square2"></div>
        <div class="square" id="square3"></div>
        <div class="square" id="square4"></div>
    </div>
</div><footer></footer>'

  BackboneWrapper.View.extend({
    localId:'nop_'
    sections:[]
    sectionTemplate:Handlebars.compile(sectionTemplate)
    template: Handlebars.compile(' <div id="section" class="sections">
      {{#if view}}
      <nav>
      {{#each sections}}
      <a {{#if selected}}class="selected"{{/if}} title="{{title}}" id="{{id}}">{{#ifDef notifications}}<span class="notification"></span>{{/ifDef}}</a>
      {{/each}}
      </nav>
      {{/if}}
      <div id="section-hidden-block" class="section-hidden-block"></div>
      <div class="sections-content">
      {{#each sections}}
      <section id="{{sectionId}}">' + sectionTemplate + '</section>
      {{/each}}
      </div>
    </div>')
    notificationValueTemplate:Handlebars.compile('{{#if value}}{{formatNumber value "0,000"}} {{/if}}{{title}}')

    events:
      'click .drill-down':'_openSection'
      'click section':'_openSection'
      'click nav>a':'navigateInSections'
      'click .close-section':'closeSection'

    closeSection:(event)->
      $section = $(event.target).parents('section.open')
      $section.find('.drill-down').removeClass('opening').find('.loading').hide()
      id = $section.attr('id')
      data = {}
      data[id] = 0
      @bus?.emit('update:url',data)
      that = @
      for section in @sections
        filterOptions = _.extend({filter:that.filter}, that.options)
        if section.sectionId == id
          $section.html(@sectionTemplate(section)).removeClass('open')
          if section.ClosedView?
            closedView = new section.ClosedView(filterOptions)
            section.closedView = closedView
            if closedView.model?
              closedView.model.getData({
                success:()->
                  that.$el.find('section#' + section.sectionId + ' .closed-section-content').html(closedView.render())
              })
            else
              that.$el.find('section#' + section.sectionId + ' .closed-section-content').html(closedView.render())
          return

    initialize: (options)->
      @options = _.extend({}, options)
      @bus = @bus or @options.bus or @options?.facade?.bus
      @locaIds = []
      for section in @sections
        section.theme = @options.theme
        section.sectionId = @localId + section.id
        @locaIds.push(section.sectionId)

    remove:()->
      for section in @sections
        section.view?.remove?()
      BackboneWrapper.View.prototype.remove.apply(this, arguments)

    loadFilter:(parameters)->
      deferred = $.Deferred()
      deferred.resolve(null)
      deferred

    updateModel:(options)->
      _.extend(@options, @options, options)

    updateViewState:(options)->
      differences = false

      for field of options
        if options[field] != @options[field]
          differences = true
          break
      return unless differences
      that = @
      @loadFilter?(options).done((filter)=>
        @filter = filter
        filterOptions = _.extend({filter:filter}, options)
        for section in @sections
          ((section)->
            if active(section, filter)
              activate(that, section)
              section.notifications?.value?(filterOptions, (value)=>
                originalValue = value
                value = '99+' if value > 99
                that.$el.find('a#' + section.id + ' .notification').html(value).attr('title',that.notificationValueTemplate({value:originalValue, title:section.title}))
              )
            else
              deactivate(that, section)
          )(section)
        @updateSubviewState?(filterOptions)
      )
      return

    updateMenuOnScroll:(event)->
      view = event.data
      $container = view.$el.find('.sections-content')
      $sections = $container.find('section')
      scrollData = {}
      scrollData[view.localId + 'scroll'] = $container.scrollTop()
      view.bus?.emit('update:url',scrollData)
      selected = null
      # heuristic: find the one who's top position in scroll is smaller (nearest to the top)
      $sections.each((i, item)->
        $section = $(item)
        top = Math.abs($section.position().top)
        if !$section.is(':visible')  #skip invisible section
          return true
        unless selected?
          return selected = {$item:$section, top:top}
        selected = {$item:$section, top:top} if selected.top > top
      )
      $sections.each((i, item)->
        $section = $(item)
        $item = $section.find('tr.clickable.selected')
        if $item.length
          containerTop = $container.offset().top
          itemTop = $item.offset().top + $item.outerHeight(true)
          visible = (containerTop - itemTop) < 0
          if visible
            view.$el.find('#section-hidden-block').html('')
            $container.css('top', '')
          else
            #message = view.sections[i]?.view.generateMessage?()
            messageSection = view.$el.find('#section-hidden-block')
            messageSection.html('')
            #messageSection.html(message)
            height = 0
            #height = messageSection.outerHeight(true)
            $container.css('top', height + 'px')
      )
      navId = selected.$item.attr('id').replace(view.localId,'')
      view.$el.find('nav a').removeClass('selected')
      view.$el.find('nav a#'+navId).addClass('selected')

    navigateToSection:(sectionId)->
      $menuItem = @$el.find('a#'+sectionId)
      $section = @$el.find('#' + @localId + sectionId)
      $sectionContainer =@$el.find('.sections-content')
      $lastSection = @$el.find('section:last-child')
      @$el.find('nav a').removeClass('selected')
      $menuItem.addClass('selected')
      previousScrollOffset = $sectionContainer.scrollTop()
      $sectionContainer.scrollTop(0)
      scrollOffset = $section.position()?.top
      $lastSection.css('height',$sectionContainer.height() + scrollOffset?)
      $sectionContainer.scrollTop(previousScrollOffset)
      $sectionContainer.animate({scrollTop:scrollOffset}, '500')
      scrollData = {}
      scrollData[@localId + 'scroll'] =scrollOffset
      @bus?.emit('update:url',scrollData)
      $section.animo({animation:'pulse', duration:0.5})

    navigateInSections:(event)->
      $menu = $(event.target)
      $section = @$el.find('#' + @localId + event.target.id)
      $sectionContainer =@$el.find('.sections-content')
      $lastSection = @$el.find('section:last-child')
      @$el.find('nav a').removeClass('selected')
      if $menu.prop('tagName') != 'A'
        $menu.parent().addClass('selected')
      else
        $menu.addClass('selected')
      previousScrollOffset = $sectionContainer.scrollTop()
      $sectionContainer.scrollTop(0)
      scrollOffset = $section.position()?.top
      $lastSection.css('height',$sectionContainer.height() + scrollOffset?)
      $sectionContainer.scrollTop(previousScrollOffset)
      $sectionContainer.animate({scrollTop:scrollOffset}, '500')
      scrollData = {}
      scrollData[@localId + 'scroll'] =scrollOffset
      @bus?.emit('update:url',scrollData)
      $section.animo({animation:'pulse', duration:0.5})

    _openSection:(event)->
      $section = $(event.target)
      $section = $section.parents('section') unless $section.is('section')
      @openSection($section.attr('id'))

    openSection:(sectionId)->
      $section = @$el.find('#' + sectionId)
      return if $section.length == 0
      return if $section.hasClass('open')
      return if $section.find('.drill-down').hasClass('opening')
      $section.find('.drill-down').addClass('opening').find('.loading').show()
      data = {}
      data[sectionId] = 1
      @bus?.emit('update:url',data)
      for section in @sections
        filterOptions = _.extend({filter:@filter}, @options)
        if section.sectionId == sectionId
          view = new section.View(filterOptions)
          section.view = view
          if active(section, @filter) and view.model?
            if view.options?.pageId == "advanceSearch"
              $.when(view.model.getData().done(), view.EducationModel.getData().done(), view.totalViolationsModel.getData().done()).then(()->
                view.totalViolationsCount = view.totalViolationsModel.models[0].get('totalViolationsCount')
                $section.html(view.render()).addClass('open')
              )
            else
              view.model.getData({
                success:()->
                  $section.html(view.render()).addClass('open')
              })
          else
            $section.html(view.render()).addClass('open')
          return

    render: ()->
      @$el.find('.sections-content').unbind('scroll')
      html = @$el.html(@template({sections:@sections, theme:@options?.theme, view:@options?.pageId != 'advanceSearch'}))
      that = @
      @loadFilter(@options).done((filter)=>
        that.filter = filter
        for section in @sections
          ((section)->
            filterOptions = _.extend({filter:filter}, that.options)
            section.notifications?.value?(filterOptions, (value)=>
              originalValue = value
              value = '99+' if value > 99
              that.$el.find('a#' + section.id + ' .notification').html(value).attr('title',that.notificationValueTemplate({value:originalValue, title:section.title}))
            )

            if section.ClosedView?
              closedView = new section.ClosedView(filterOptions)
              section.closedView = closedView
              if active(section, filter) and closedView.model?
                closedView.model.getData({
                  success:()->
                    that.$el.find('section#' + section.sectionId + ' .closed-section-content').html(closedView.render())
                })
              else
                that.$el.find('section#' + section.sectionId + ' .closed-section-content').html(closedView.render())
          )(section)

        @$el.find('.sections-content').bind('scroll', @, @updateMenuOnScroll)

        for parameter of @options.queryString
          if @locaIds.indexOf(parameter) >= 0
            @openSection(parameter) if @options.queryString[parameter]

        for section in @sections
          if section.openedByDefault
            @openSection(section.sectionId)

        for section in @sections
          if active(section, filter)
            activate(that, section)
          else
            deactivate(that, section)

        if @options.queryString[@localId + 'scroll']?
          setTimeout(()=>
            @$el.find('.sections-content').animate({scrollTop:@options.queryString[@localId + 'scroll']},'500')
          ,100)
      )



      html
  })
