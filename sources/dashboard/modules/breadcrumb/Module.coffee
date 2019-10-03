###
  Defines the application header components.
###
define [], ->

  BreadcrumbModule = (facade) ->

    _ = facade._
    t = facade.i18n.t

    BreadcrumbView = facade.backbone.View.extend({
      template:facade.Handlebars.compile('<div><header class="breadcrumb hide">
        <div id="module-selector" class="option-selector hidden"></div>
        <div id="business-criteria-selector" class="option-selector hidden"></div>
        <div id="breadcrumb-path" class="breadcrumb-path">
            <ul></ul>
        </div>
      </header></div>')
      # FIXME having two templates is usually a sign that views are not well structured, could create an embedded view
      itemTemplate:facade.Handlebars.compile('<li class="animated {{#if className}}{{className}}{{/if}}">
              <a href="{{href}}" class="long" ><span class="{{breadcrumbClass}}"></span>{{name}}
                {{#if value}}
                  <span class="score">{{formatNumber value "0.00"}}</span>
                {{/if}}
              </a>
              <a href="{{href}}" title="{{name}}" class="short"><span class="{{breadcrumbClass}}"></span>
                {{#unless isHealthFactor}}
                {{#if shortName}}{{shortName}}{{else}}{{ellipsisMiddle name 10 20}}{{/if}}{{/unless}}
                {{#if value}}
                  <span class="score">{{formatNumber value "0.00"}}</span>
                {{/if}}
              </a>
              <a href="{{href}}" title="{{name}}" class="shorter"><span class="{{breadcrumbClass}}"></span>
                {{#unless isHealthFactor}}
                  {{#if shortName}}{{shortName}}{{else}}{{ellipsisMiddle name 5 5}}{{/if}}
                {{/unless}}
                {{#if value}}
                  <span class="score">{{formatNumber value "0.00"}}</span>
                {{/if}}
              </a>
          </li>')
      defaultTemplate:facade.Handlebars.compile(' <li><span class="{{breadcrumbClass}}"></span>{{name}}</li>')

      events:
        'click li':'addSelectionState'

      initialize:(options)->
        $(window).on('resize', _.debounce(
          ()=> @resize()
        ,10))

      addSelectionState:(event)->
        $target = $(event.target)
        if event.target.tagName == 'A'
          $target = $(event.target).parent()
        @$el.find('.breadcrumb-path li').removeClass('selected')
        $target.addClass('selected')

      hideOrShow:(options)->
        @latestPageId = options.pageId
        switch (options.pageId)
          when 'home'
            @$el.find('.breadcrumb').addClass('hide') unless @$el.find('.breadcrumb').hasClass('hide')
          else
            @$el.find('.breadcrumb').removeClass('hide') if @$el.find('.breadcrumb').hasClass('hide')

      # FIXME Avoid copy paste code
      _processModuleSelector:(options)->
        activateModuleSelector = options.activateModuleSelector or false
        if activateModuleSelector
          @$moduleSelector.show()
          if (options.availableModules?.length == 0)
            @moduleSelector.disable()
          else
            @moduleSelector.enable()
          @moduleSelector.enableOptions(options.availableModules,t("The module is not available for the selected criteria."))
        else
          @$moduleSelector.hide()

      _processBusinessCriterionSelector:(options)->
        activateBusinessCriteriaSelector = options.activateBusinessCriteriaSelector or false
        @$el.find('#business-criteria-selector .cont .options').attr('data-before',t('Select a health measure'))
        if activateBusinessCriteriaSelector
          @$businessCriteriaSelector.show()
          @businessCriteriaSelector?.enableOptions(options.availableHealthFactors,t("The criteria is not available for the selected metric."))
        else
          @$businessCriteriaSelector.hide()

      display:(options = {})->
        return if options.pageId? and options.pageId != @latestPageId
        @_processModuleSelector(options)
        @_processBusinessCriterionSelector(options)

        fullPath = options.path
        return @replace(fullPath) if !@currentFullPath? or fullPath.length == 0 or options.pageId  == 'actionPlanOverview' or options.pageId == 'educationOverview'

        fullPath = [] unless fullPath?
        i = -1
        while ++i < @currentFullPath.length
          oldItem = @currentFullPath[i]
          if i>= fullPath.length
            if @currentFullPath.length == fullPath.length + 1
              return @drillUp(fullPath)
            return @replace(fullPath)
          newItem = fullPath[i]
          if !(newItem.name == oldItem.name and newItem.value == oldItem.value and newItem.href == oldItem.href)
            return @replace(fullPath)

        if @currentFullPath.length == fullPath.length
          return
        if @currentFullPath.length + 1 == fullPath.length
          return @drillDown(fullPath)
        return @replace(fullPath)

      resize:()->
        dropDownsWidth = 0
        @$el.find('.drop-down').each(()->
          $dropDown = $(this)
          if ($dropDown).is(':visible')
            dropDownsWidth += $dropDown.width()
        )

        W = @$el.find('.breadcrumb').width() - dropDownsWidth - 30
        if @$el.find('#add-bookmark').width()
          W -= @$el.find('#add-bookmark').width()
        w = @$el.find('.breadcrumb-path').width()
        $ul = @$el.find('ul')
        if $ul.hasClass('short')
          if W < w
            $ul.addClass('shorter')
            # special heuristics, short is not enough
          else
            if $ul.hasClass('shorter')
              $ul.removeClass('shorter')
            else
              $ul.removeClass('short')
            @resize()
        else
          if W < w
            $ul.addClass('short')

      addIcon:(breadItem)->
        if breadItem.type == 'business-criteria'
          breadItem.breadcrumbClass = 'bread-icon icon-' + breadItem.key if breadItem.key?

      replace:(pathComponents)->
        @currentFullPath = pathComponents
        breadItems = ''
        for field in @currentFullPath
          field.isHealthFactor = field.type == 'business-criteria'
          @addIcon(field)
          field.name = t("All Rules...") if field.name == "All Rules..."
          if field.href?
            breadItems += @itemTemplate({name: field.name, className:field.className, href:field.href, shortName:field.shortName, value:field.value, breadcrumbClass:field.breadcrumbClass, isHealthFactor:field.type == "business-criteria"})
          else
            breadItems += @defaultTemplate(field)
        @$el.find('.breadcrumb-path ul').html(breadItems)
        @resize()

      drillDown:(pathComponents)->
        @currentFullPath = pathComponents
        addItem = @currentFullPath[pathComponents.length - 1]
        @addIcon(addItem)
        addItem.name = t("All Rules...") if addItem.name == "All Rules..."
        @$el.find('.breadcrumb-path ul').append(@itemTemplate(
          {name: addItem.name, href:addItem.href, shortName:addItem.shortName, value:addItem.value, breadcrumbClass:addItem.breadcrumbClass, isHealthFactor:addItem.type == "business-criteria"}))
        $el = @$el.find('.breadcrumb-path ul li').not(".fadeOutDown").last()
        $el.animo( { animation: 'fadeInUp', duration: 0.5 })
        @resize()

      drillUp:(pathComponents)->
        @currentFullPath = pathComponents
        $el = @$el.find('.breadcrumb-path ul li').not(".fadeOutDown").last()
        if $('html').hasClass('keyframe')
          $el.animo( { animation: 'fadeOutDown', duration: 0.8 }, ()=>
            $el.remove()
            @resize()
          )
        else
          $el.remove()
          @resize()

      updatetheme:(parameters)->
        @$el.removeClass().addClass(parameters.theme)

      updateModuleSelector:(options)->
        selectedModule = facade.context.get('module')
        if selectedModule?
          @moduleSelector.selectValue(selectedModule.get('href'))
          @moduleSelector.$el.removeClass('default')
        else
          @moduleSelector.selectValue(-1)
          @moduleSelector.$el.addClass('default')

      _renderModuleSelector:()->
        name = ''
        selectedModule = facade.context.get('module')
        data = [{
          label:t('All Modules')
          value:-1
          selected:if selectedModule? then false else true
        }];
        for module in facade.context.get('modules').list()
          data.push({
            label:module.get('name')
            value:module.get('href')
            selected: selectedModule?.get('href') == module.get('href')
          })
        @moduleSelector = new facade.bootstrap.Selector({name: name, data: data, class: 'right breadrumb-selector module-selector', maxCharacters:20});
        @moduleSelector.on('selection', (item)=>
          facade.bus.emit('filter', {module:item})
          if '-1' == item
            @moduleSelector.$el.addClass('default')
          else
            @moduleSelector.$el.removeClass('default')
        )
        @moduleSelector.$el.addClass('default') unless selectedModule?
        @$moduleSelector = @$el.find('#module-selector').html(@moduleSelector.render());

      updateCriterionSelector:()->
        businessFilter = facade.context.get('scope').get('businessCriterion')
        if '60017' == businessFilter.toString()
          @businessCriteriaSelector?.selectValue(businessFilter)
          @businessCriteriaSelector?.$el.addClass('default')
        else
          @businessCriteriaSelector?.selectValue(businessFilter)
          @businessCriteriaSelector?.$el.removeClass('default')


      _renderCriterionSelector:()->
        filterHealthFactor = facade.portal.get('configuration').filterHealthFactor or false
        businessCriteriaModels = facade.context.get('snapshot').createBusinessCriteriaConfiguration({
          filterHealthFactor:filterHealthFactor
        })
        @$businessCriteriaSelector = @$el.find('#business-criteria-selector')
        that = @
        businessCriteriaModels.getData({
          success:()->
            result = []
            businessFilter = facade.context.get('scope').get('businessCriterion')
            businessCriteriaModels.each((model)->
              result.push({
                label:model.get('name')
                value:model.get('key')
                selected: parseInt(model.get('key')) == parseInt(businessFilter)
              })
            )
            that.businessCriteriaSelector = new facade.bootstrap.Selector({name: '', data: result, class: 'right breadrumb-selector business-selector', maxCharacters:20});
            that.businessCriteriaSelector.on('selection', (item)=>
              if '60017' == item?.toString()
                that.businessCriteriaSelector.$el.addClass('default')
              else
                that.businessCriteriaSelector.$el.removeClass('default')
              facade.bus.emit('filter', {business:item})
            )
            that.businessCriteriaSelector.$el.addClass('default') if (!businessFilter? or '60017' == businessFilter)
            facade.context.get('scope').businessCriterionList = result
            that.$businessCriteriaSelector.html(that.businessCriteriaSelector.render());
        })

      render:()->
        @$el.html(@template())
        # FIXME have technologies module register to module so it can be added
        @$el.find('header').append('<div id="technology-filter" class="option-selector"></div>')
        facade.bus.emit('render:technologyFilter',{$el:@$el.find('#technology-filter')})
        @_renderModuleSelector()
        @_renderCriterionSelector()

        that = @
        breadcrumbHelpviewOptions = {
          $target:@$el.find('#breadcrumb-path')
          title:t('Breadcrumb') ,
          content:t('You can click on one of the link into the breadcrumb if you want to come back to a previous situation.')
        }
        facade.bus.emit('help:createView',breadcrumbHelpviewOptions)
        @$el
        @$el.find('#module-selector .cont .options').attr('data-before',t('Select a module'))
    })

    module = {
      initialize: (options) ->
        @view = new BreadcrumbView({el:options?.el})
        @view.render()

        facade.bus.on('theme', @view.updatetheme, @view)
        facade.bus.on('breadcrumb', @view.display, @view)
        facade.bus.on('breadcrumb', @view.updateCriterionSelector, @view) # TODO add function in bootstrap to select an item based on data-value
        facade.bus.on('breadcrumb', @view.updateModuleSelector, @view)
        facade.bus.on('show', @view.hideOrShow, @view)
      destroy: () ->
        @view.remove()
    }
    return module

  return BreadcrumbModule
