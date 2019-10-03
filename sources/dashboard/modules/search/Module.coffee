###
  Defines the application search components.
###
define [], ->

  SearchModule = (facade) ->
    Backbone = facade.backbone
    Handlebars = facade.Handlebars
    t = facade.i18n.t

    _Contributors = Backbone.Model.extend({
      url:()->
        REST_URL + @get('snapshot') + '/results?quality-indicators=(nc:60017,cc:60017)&select=(aggregators)'
    })
    _HealthFactors = Backbone.Model.extend({
      url:()->
        if facade.portal.filterHealthFactors()
          return REST_URL + @get('snapshot') + '/results?quality-indicators=(60011,60012,60013,60014,60016,60017)&select=(aggregators)'
        else
          return REST_URL + @get('snapshot') + '/results?quality-indicators=(business-criteria)&select=(aggregators)'

    })
    RulesFinder = Backbone.Model.extend({
      initialize:(options)->
        @contributors = new _Contributors(options)
        @healthFactors = new _HealthFactors(options)
        $('#search-input').find('input').first().focus()

      process:()->
        processed = []
        processedData = {}
        applicationResults = @contributors.get('0').applicationResults
        for result in applicationResults
          processed.push(result.reference.name)
          processedData[result.reference.name] = result
          processedData[result.reference.key] = result
        applicationResults = @healthFactors.get('0').applicationResults
        for result in applicationResults
          processed.push(result.reference.name)
          processedData[result.reference.name] = result
          processedData[result.reference.key] = result
        processed.sort((a, b)->
          return a.toLowerCase().localeCompare(b.toLowerCase());
        )
        @processedData = processedData
        @processed = processed

      getGrade:(name)->
        @processData[name].result.grade

      search:(subString, filterContext)->
        return facade.utils.searchAssessmentModel(@processed, @processedData, subString, filterContext, @get('snapshot').split('/')[4])

      getData:(options)->
        that = @
        if that.fetchStatus?
          return options.success.apply(that, options) if that.fetchStatus == 'ok'
          return options.error.apply(that, options) if that.fetchStatus == 'ko'

        $.when(@contributors.fetch(),@healthFactors.fetch()).then(()->
          that.process()
          that.fetchStatus = 'ok'
          options.success.apply(that, options)
        , ()->
          that.fetchStatus = 'ko'
          options.error.apply(that, options)
        )
    })

    _applicationObjects = Backbone.Model.extend({
      initialize:(options)->
        @options = _.extend({}, options)

      url:()->
        REST_URL + facade.context.get('snapshot').get('href') + '/search-results?items=components&mode=term&word=' + encodeURIComponent(@options.subString) + '&startRow=' + @options.startRow + '&nbRows=' + @options.nbRows
    })

    searchBarTemplate = '{{#if contextual}}<div id="overlay" class="header-search-overlay">{{/if}}<header class="header-search">
            <div id="search-input" class="search-input"><input id="search-content" class="placeholder-content" placeholder="{{t "Search on rules"}} {{placeholder}}" maxlength="100" ></input><div class="close-wrap visible"><div class="close">&#xe62d;</div></div></div>
            <div class="results"><ul class="test"></ul></div>
              <span class="configure"></span>
            </header>
            {{#if contextual}}</div>{{/if}}'

    objectSearchBarTemplate = '<header class="header-search">
            <div id="search-input" class="object-search-input"><input id="search-content" class="placeholder-content" placeholder="{{t "Search on objects"}} {{placeholder}}" maxlength="100" ></input><div class="close-wrap visible"><div class="close">&#xe62d;</div></div></div>
            <div class="results"><ul class="test"></ul></div>
              <span class="configure"></span>
            </header>'

    HomeSearchBarView = Backbone.View.extend({
      template:Handlebars.compile(searchBarTemplate)
      templateSearchResults:Handlebars.compile('
        {{#if samples.length}}
          <li class="information">{{t "The results are contexted to the activated Rules for the current snapshot of the application"}}</li>
        {{else}}
          {{#if hasSearchValue}}
            <li class="information">{{t "No results were found to match your search"}}</li>
          {{/if}}
        {{/if}}
        {{#each samples}}
           <li class="result-item"><div class="label">{{{name}}}</div><ul>
            {{#each links}}
              <li><a href="{{url}}">
                {{#each label}}<span>{{this}}</span>{{/each}}
              </a></li>
            {{/each}}
            </ul></li>
        {{/each}}')

      events:
        'keyup input':'search'
        'click .header-search-overlay':'hideOverlay'
        'focusin input': 'search'
        'focusin header':'focusChange'
        'focusout header':'focusChange'
        'mouseenter header':'mouseState'
        'mouseleave header':'mouseState'
        'click .results':'processClick'
        'keydown input': 'moveFocus'
        'keydown ul>li>a': 'changeFocus'
        'click .close': 'closeSearchBox'

      closeSearchBox:()->
        facade.bus.emit('request:close-search')

      _focusUp:(event)->
        $currentLI = $(event.target).parent()
        $previousLI = $currentLI.prev()
        if !$previousLI.html()? || $previousLI.html() == ""
          $previousLI = $currentLI.parent().parent('li.result-item').prev()
          if !$previousLI? || !$previousLI.html()?
            @$el.find('input').focus()
          else
            $previousLI.find('a:last').focus()
        else
          $previousLI.find('a:last').focus()

      _focusDown:(event)->
        $currentLI = $(event.target).parent()
        $nextLI = $currentLI.next()
        if !$nextLI.html()? || $nextLI.html() == ""
          $nextLI = $currentLI.parent().parent('li.result-item').next()
        $nextLI.find('a:first').focus()

      changeFocus:(event)->
        return if (event.keyCode != 38 || event.which != 38) && (event.keyCode != 40 || event.which != 40)
        @_focusUp(event) if event.keyCode == 38 || event.which == 38
        @_focusDown(event) if event.keyCode == 40 || event.which == 40
        false

      moveFocus:(event)->
        return if event.keyCode != 40 || event.which != 40
        @$el.find('ul>li>a')[0].focus()
        false

      mouseState:(event)->
        if event.type == 'mouseenter'
          @hover = true
          @_cancelCloseSearchResults()
        else
          @hover = false
          @_closeSearchResults(event) unless @focused

      focusChange:(event)->
        if event.type == 'focusin'
          @focused = true
          @_cancelCloseSearchResults()
        else
          @focused = false
          # add for IE9 to identify placeholder
          if 'Search' == $(event.target).val() or '' == $(event.target).val()
            $(event.target).addClass('placeholder-content')
          @_closeSearchResults(event) unless @hover

      _closeSearchResults:(delay = 500)->
        @timeOut = _.delay(()=>
          @$el.find('.results ul').empty()
        , delay)

      _cancelCloseSearchResults:()->
        if @timeOut?
          clearTimeout(@timeOut)
          @timeOut=null

      processClick:(event)->
        localStorage.setItem('selectedTag', 'All Tags')
        $t = $(event.target)
        if $t.hasClass('result-item')
          $t.find('ul li a')[0].focus()
        else
          @_closeSearchResults(0) if 'SPAN' == $t.prop('tagName')

      hideOverlay:(event)->
        return unless event?
        switch event.target.id
          when 'overlay'
            @$el.find('.header-search-overlay').removeClass('display')
          else
            event.stopPropagation()

      search:(event)->
        if event?
          str = $(event.target).val()
          # add for IE9 to identify placeholder
          if event.type == 'focusin'
            if $(event.target).hasClass('placeholder-content')
              $(event.target).removeClass('placeholder-content')
        else
          str = @$el.find('input').val()
        # strip any special characters,
        # if not word characters or space replace with empty string
        str = str?.trim().replace(/[-[\]{}()*+?.,\\^$|#]/g, "\\$&").replace(/\s+/g,'\\s+')
        results = []
        if str != ''
          @$el.find('.search-input').addClass('has-content')
          results = @rules?.search(str, @context)
        else
          @$el.find('.search-input').removeClass('has-content')
        @$el.find('.results>ul').html(@templateSearchResults({samples:results, hasSearchValue:str != ''}))

      initialize:(options)->
        @rules = options.rules

      hide:()->
        @$el.hide()

      getCriteria:(key)->
        name = @rules?.processedData[key]?.reference.name
        return name

      render:()->
        postponeRendering = !@rules.fetchStatus?
        unless postponeRendering
#          if @context.technical? # and !@context.rule?
#            placeholderContent = t('in') + ' ' + @getCriteria(@context.technical)
#          else if @context.business? and !@context.technical?
#            placeholderContent = t('in') + ' ' +@getCriteria(@context.business)
#          else placeholderContent = ''
          @$el.show().html(@template({placeholder:''}))
          @$el.find('.header-search-overlay').addClass('display')
          @$el.find('input').focus()

        if !@rules.fetchStatus?
          @rules.getData({
            success:()=>
              if postponeRendering
#                if @context.technical? # and !@context.rule?
#                  placeholderContent = t('in') + ' ' + @getCriteria(@context.technical)
#                else if @context.business? and !@context.technical?
#                  placeholderContent = t('in') + ' ' +@getCriteria(@context.business)
#                else placeholderContent = ''
                @$el.show().html(@template({placeholder:''}))
                @$el.find('.header-search-overlay').addClass('display')
              @$el.find('input').focus()
              @search(null)
            error:()=>
              @$el.find('input').attr('placeholder',t('Search failed to load. Please try and reload the page'))
          })

        # add for IE9 to identify placeholder
        if(navigator.appVersion.match(/MSIE [\d.]+/))
          facade.polyfill.placeholder(@$el.find('#search-content'))
    })

    TreeNodeCollection = Backbone.Collection.extend({
      url:()->
        REST_URL + @href
      initialize:(nodes,options)->
        @href = options.href
    })

    ObjectSearchBarView = Backbone.View.extend({
      startRow: 1
      nbRows: 50
      template:Handlebars.compile(objectSearchBarTemplate)
      templateSearchResults:Handlebars.compile('
        {{#if searchConfigured}}
          <li class="invalid">{{t "Search is not configured for this application. Please contact your administrator" }}</li>
        {{/if}}
        {{#if samples.length}}
          {{#if showCount}}
            <li class="information">{{t "Number of matching objects"}}&nbsp; &nbsp;<span class="count">{{samples.count}}</span></li>
          {{/if}}
        {{else}}
          {{#if hasSearchValue}}
            <li class="invalid">{{t "No results were found to match your search"}}</li>
          {{/if}}
        {{/if}}
        {{#each samples}}
           <li class="object-search-results-item" id ={{id}}>
            <ul>
              <li><a>
                <span class="shortName">{{{shortName}}} - </span>
                <span class="type">{{type.label}}</span>
                <div class="name">{{name}}</div>
              </a></li>
            </ul>
          </li>
        {{/each}}
        {{#if showMoreMax}}
          <li class="endMessage">{{t "End of search results"}}</li>
        {{/if}}')
      loadingSearchTemplate:Handlebars.compile('
        <li class="loadingMessage">
          <span class="load-icon icon-loading"></span>
          <span>{{t "Loading next items"}}</span>
        </li>')

      events:
        'keyup input':'search'
        'click .header-search-overlay':'hideOverlay'
        'focusin input': 'search'
        'focusin header':'focusChange'
        'focusout header':'focusChange'
        'mouseenter header':'mouseState'
        'mouseleave header':'mouseState'
        'click .results':'processClick'
        'keydown input': 'moveFocus'
        'keydown ul>li>a': 'changeFocus'
        'click .close': 'closeSearchBox'
        'click .object-search-results-item':'goToComponent'

      goToComponent:(event)->
        objectId = $(event.currentTarget).attr('id')
        if objectId?
          treeNodeHref = CENTRAL_DOMAIN + '/components/'
          treeNodeHref += objectId
          treeNodeHref += '/snapshots/' + facade.context.get('snapshot').getId()+ '/tree-nodes'
          treeNodes = new TreeNodeCollection([],{href:treeNodeHref})
          that = @
          treeNodes.getData({
            success:()->
              return if treeNodes.length == 0
              hrefParts = treeNodes.at(0).get('href').split('/')
              facade.context.get('scope').set('businessCriterion', facade.context.get('scope').get('businessCriterion'))
              facade.bus.emit('navigate', {page: "componentsInvestigation/" + hrefParts[2] + "/1"})
          })

      closeSearchBox:()->
        facade.bus.emit('request:close-search')

      _focusUp:(event)->
        $currentLI = $(event.target).parent()
        $previousLI = $currentLI.prev()
        if !$previousLI.html()? || $previousLI.html() == ""
          $previousLI = $currentLI.parent().parent('li.object-search-results-item').prev()
          if !$previousLI? || !$previousLI.html()?
            @$el.find('input').focus()
          else
            $previousLI.find('a:last').focus()
        else
          $previousLI.find('a:last').focus()

      _focusDown:(event)->
        $currentLI = $(event.target).parent()
        $nextLI = $currentLI.next()
        if !$nextLI.html()? || $nextLI.html() == ""
          $nextLI = $currentLI.parent().parent('li.object-search-results-item').next()
        $nextLI.find('a:first').focus()

      changeFocus:(event)->
        return if (event.keyCode != 38 || event.which != 38) && (event.keyCode != 40 || event.which != 40)
        @_focusUp(event) if event.keyCode == 38 || event.which == 38
        @_focusDown(event) if event.keyCode == 40 || event.which == 40
        false

      moveFocus:(event)->
        return if event.keyCode != 40 || event.which != 40
        @$el.find('ul>li>a')[0].focus()
        false

      mouseState:(event)->
        if event.type == 'mouseenter'
          @hover = true
          @_cancelCloseSearchResults()
        else
          @hover = false
          @_closeSearchResults(event) unless @focused

      focusChange:(event)->
        if event.type == 'focusin'
          @focused = true
          @_cancelCloseSearchResults()
          that = this
          @$el.find('.results').on('scroll', () ->
            that.showMoreOnScroll()
          )
        else
          @focused = false
          # add for IE9 to identify placeholder
          if 'Search' == $(event.target).val() or '' == $(event.target).val()
            $(event.target).addClass('placeholder-content')
          @_closeSearchResults(event) unless @hover
          @$el.find('.results').off('scroll')

      _closeSearchResults:(delay = 100)->
        @timeOut = _.delay(()=>
          @$el.find('.results ul').empty()
        , delay)

      _cancelCloseSearchResults:()->
        if @timeOut?
          clearTimeout(@timeOut)
          @timeOut=null

      processClick:(event)->
        $t = $(event.target)
        if $t.hasClass('result-item')
          $t.find('ul li a')[0].focus()
        else
          @_closeSearchResults(0) if 'SPAN' == $t.prop('tagName')

      hideOverlay:(event)->
        return unless event?
        switch event.target.id
          when 'overlay'
            @$el.find('.header-search-overlay').removeClass('display')
          else
            event.stopPropagation()

      process: (str, showMore)->
        data = @objects.get('components')
        str = str?.trim().replace(/[-[\]{}()*+?.,\\^$|#]/g, "\\$&")
        regexp = new RegExp(str,'ig')
        if data?
          for component in data
            if component.shortName.match(regexp)
              component.shortName = component.shortName.replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(regexp,(matching)->
                '<em>' + matching + '</em>')
          data.count = @objects.get('number')
          if @startRow + @nbRows >= data.count and data.count > 0
            showMoreMax = true
          else
            showMoreMax = false
          if showMore
            if @$el.find('.loadingMessage').length == 0
              @$el.find('.results>ul').append(@loadingSearchTemplate())
            setTimeout(()=>
              @$el.find('.loadingMessage').remove()
              @$el.find('.results>ul').append(@templateSearchResults({samples:data, hasSearchValue:str != '', showMoreMax:showMoreMax}))
            , 500)
          else
            @$el.find('.results>ul').html(@templateSearchResults({samples:data, hasSearchValue:str != '', showMoreMax:showMoreMax, showCount: true}))

      search:(event)->
        @startRow = 1
        @nbRows = 50
        $('.results').scrollTop($('.results')[0].offsetTop - 100)
        if event?
          str = $(event.target).val()
          # add for IE9 to identify placeholder
          if event.type == 'focusin'
            if $(event.target).hasClass('placeholder-content')
              $(event.target).removeClass('placeholder-content')
        else
          str = @$el.find('input').val()
        @getMatchingObjects(str)

      getMatchingObjects:(str, showMore)->
        # strip any special characters,
        # if not word characters or space replace with empty string
        # str = str?.trim().replace(/[-[\]{}()*+?.,\\^$|#]/g, "\\$&").replace(/\s+/g,'\\s+')
        str = str?.trim()
        results = []
        if str != ''
          @$el.find('.object-search-input').addClass('has-content')
          @options.subString = str
          @options.startRow = @startRow
          @options.nbRows = @nbRows
          that = this
          @objects = new _applicationObjects(@options)
          @objects.fetch(complete: (xhr, textStatus)->
            if xhr.status == 500
              that.$el.find('.results>ul').html(that.templateSearchResults({ searchConfigured:xhr.status }))
            else
              that.process(str, showMore)
          )
        else
          @$el.find('.object-search-input').removeClass('has-content')
          @_closeSearchResults()

      showMoreOnScroll:()->
        if $('.results').scrollTop() + $('.results').innerHeight() >= $('.results')[0].scrollHeight
          startRow = @startRow + @nbRows
          if startRow <= @objects.get('number')
            @startRow = startRow
            str = @$el.find('input').val()
            @getMatchingObjects(str, true)

      initialize:(options)->
        @options = _.extend({}, options)

      hide:()->
        @$el.hide()

      getCriteria:(key)->
        name = @rules?.processedData[key]?.reference.name
        return name

      render:()->
        @$el.show().html(@template({placeholder:''}))
        @$el.find('.header-search-overlay').addClass('display')
        @$el.find('input').focus()
        # add for IE9 to identify placeholder
        if(navigator.appVersion.match(/MSIE [\d.]+/))
          facade.polyfill.placeholder(@$el.find('#search-content'))
    })

    module = {
      onSearchDialogRequest:(parameters)->
        pageContext = facade.context.get('theme')
        @$el = parameters.$el
        @headerSearchView?.remove()
        if pageContext == 'components-investigation'
          @headerSearchView = new ObjectSearchBarView()
        else
           @headerSearchView = new HomeSearchBarView({rules:@rules})
        @updateSearchDialogContext()
        @$el.html(@headerSearchView.$el)
        @headerSearchView.$el.find('input').focus()

      updateSearchDialogContext:()->
        return unless @$el?
        @headerSearchView.context = @context
        @headerSearchView.render()

      onNavigation:(parameters)->
#        @context = _.extend({},parameters)
        facade.bus.emit('request:close-search',{animate:false}) #if @previousPageId != parameters.pageId
#        @previousPageId = parameters.pageId
#        @updateSearchDialogContext() unless _.isEqual(@context, @headerSearchView?.context)

      initialize: (options) ->
        @options = options
#        @headerSearchView = new HomeSearchBarView({el:@options?.el})
        @options = _.extend({},options)
        @rules = new RulesFinder({snapshot:facade.context.get('snapshot').get('href')})
        facade.bus.on('request:search-dialog', @onSearchDialogRequest, @)
        facade.bus.on('show', @onNavigation, @)

      destroy: () ->
        @headerSearchView?.remove()
    }
    return module

  return SearchModule
