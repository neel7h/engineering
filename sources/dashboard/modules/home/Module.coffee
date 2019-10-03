###
  Defines the home page content -> Home page module.
###
define [], ->
  HomeModule = (facade) ->

    # FIXME make this part of plugin utilities
    # FIXME create a persistence plugin
    LOCAL_STORAGE_WAR_IDENTIFIER = facade.base64.encode(window.location.pathname) + '_'
    LOCAL_STORAGE_KEY = LOCAL_STORAGE_WAR_IDENTIFIER + 'profiles'

    backbone = facade.backbone
    Handlebars = facade.Handlebars
    _ = facade._
    t = facade.i18n.t

    Tile = backbone.Model.extend({
      initialize:(options)->
        @set('id',@cid)
    })

    Tiles = backbone.Collection.extend({
      model:Tile
    })

    # FIXME make all tiles part of dedicated modules (and create new if needed) then register programatically
    # FIXME do not add new tiles here !! We NEED to remove all of them and register them instead
    CoreTiles = CoreTiles(facade)
    TileViews = {
      QualityModelOverview:QualityModelOverview(facade)
      ComponentInvestigationOverview:ComponentInvestigationOverview(facade)
      QualityModelBookmark:QualityModelBookmark(facade)
      RuleViolationsModelBookmark:RuleViolationsModelBookmark(facade)
      RiskiestComponents:RiskiestComponents(facade)
      BusinessCriteria:BusinessCriteria(facade)
      ExternalLink:ExternalLink(facade)
      ExternalLinkWithImage: ExternalLinkWithImage(facade)
      MockTile:MockTile(facade)
    }

    getTileView = (tile)->
        lastSnapshot = facade.context.get('snapshot').isLatest()
        TileView = TileViews[tile.get('type')]
        TileView = TileViews['NotFound'] unless TileView?
        if !lastSnapshot and TileView.requiresLastSnapshot
          originalTitle = TileView?.title
          TileView = TileViews['Inactive']
          TileView.title = originalTitle
        return TileView

    TilesSettingsContainer = backbone.View.extend({
      className:'tile-settings-content'
      template: Handlebars.compile('
        <ul class="color-container">
          {{#each colors}}
            <li class="color-selector {{color}} {{#if selected}}selected{{/if}}" title="{{color}}" color="{{color}}" style="background-color:{{hex}}"></li>
          {{/each}}
        </ul>
      ')
      events:
          'click .color-selector': 'chooseColor'

      initialize:(options)->
        this.tile = options.tile
        this.data = {
          colors: [
            {color:'red',hex:'#f00041'}
            {color:'mauve',hex:'#c3a5af'}
            {color:'magenta',hex:'#4b233c'}
            {color:'black',hex:'#0f0019'}
            {color:'green',hex:'#1ebeb4'}
            {color:'orchid',hex:'#785ac8'}
            {color:'yellow',hex:'#ffa200'}
            {color:'blue',hex:'#017eff'}
            {color:'blue-dark',hex:'#194155'}
            {color:'violet-light',hex:'#9a95ab'}
            {color:'grey-dark',hex:'#2d323c'}
            {color:'eco-green',hex:'#b9e100'}
            {color:'grey-light',hex:'#c8c8c8'}
            {color:'purple',hex:'#32234b'}
            {color:'orange',hex:'#ff8100'}
          ]
        }

      chooseColor:(event)->
        selectedTileColor = $(event.target).attr('color')
        return if this.model.get('color') == selectedTileColor
        this.model.set('color', selectedTileColor)
        this.model.collection.trigger('grid-update')
        this.tile.refresh()
        this.render()

      render:()->
        this.data.colors.forEach((color)=>
          color.selected = color.color == this.model.get('color')
        )
        @$el.html(@template(this.data))
        @$el
    });

    TileContainer = backbone.View.extend({
      template:Handlebars.compile('<li id="{{id}}" class="{{color}} {{type}}"
        {{#if row}}data-row="{{row}}"{{/if}}
        {{#if col}}data-col="{{col}}"{{/if}}
         data-sizex="{{sizex}}" data-sizey="{{sizey}}"
        {{#if max-sizex}} data-max-sizex="{{max-sizex}}" {{/if}}
        {{#if max-sizey}} data-max-sizey="{{max-sizey}}" {{/if}}
        {{#if min-sizex}} data-min-sizex="{{min-sizex}}" {{/if}}
        {{#if min-sizey}} data-min-sizey="{{min-sizey}}" {{/if}}
      ><span class="tile-settings" title="Tile settings"></span><span class="close"></span></li>')

      events:
        'click .close':'remove',
        'click .tile-settings':'changeTileSettings'

      initialize:(options)->
        @options = _.extend({},options)
        @model = options.model
        facade.bus.on('custom:toggle-delete', @toggleDelete, @)

      toggleDelete:(options)->
        if options.active
          @$el.find('.close').removeClass('off').addClass('on')
        else
          @$el.find('.close').removeClass('on').addClass('off')

      changeTileSettings:()->
        this.$el.find('.tile-settings').addClass('active-settings-icon')
        tileSettingsModal =  new facade.backbone.DropDownDialogView({
          $attach: this.$el.find('.tile-settings'),
          title:t('Set your favorite color for the tile')
          height:100
          width:300 ## desired width
        })
        tileSettingsModal.once('closing-dropdown',()=>
          this.$el.find('.tile-settings').removeClass('active-settings-icon')
        )
        tileSettingsModal.render()
        tileSettingsModal.addContent(new TilesSettingsContainer({
          tile:this
          model:this.model
        }).render())

      remove:()->
        facade.bus.emit('bookmark:remove',{index:@model.get('id')})

      refresh:()->
        newState = this.model.toJSON()
        this.$el.addClass(newState.color).removeClass(this.state.color)
        this.state = newState

      render:()->
        this.state = @model.toJSON()
        @$el.html($(@template(this.state)))
        @$el.find('li').append(this.options.view.render())
        @setElement(@$el.find('li')) # hack
        @$el
    })

    TilesContainer = backbone.View.extend({
      tagName:'ul'
      template:Handlebars.compile('')

      render:()->
        @$el.html(@template())

        @collection.each((tile)=>
          TileView = getTileView(tile)
          tileView = new TileView(_.extend({color:tile.get('color')}, tile.get('parameters'), tile:tile))
          tileContainer = new TileContainer({
            model:tile
            view:tileView
          })
          @$el.append(tileContainer.render())
        )
        @$el
    })

    HomeView = backbone.View.extend({
      template:Handlebars.compile('<div class="gridster"></div><div class="editor-view-container"></div>')

      onResize:(event)->
        return
        $gridster = @$el.find('.gridster')
        $ul = @$el.find('.gridster > ul')
        ratio = $gridster.width() / $ul.width()
        ratio= 0.9 if ratio < 0.9
        ratio= 1.1 if ratio > 1.1
        $ul.css('transform', 'scale3d('+ratio+','+ratio+',1)')
        $ul.css('transform-origin','0px 0px 0px')

      _removeTile:(tile,index)->
        $li = @$el.find('li#'+index)
        @gridster.remove_widget($li,()=>
          @tiles.remove(tile)
          @gridster.serialize()
          @tiles.trigger('grid-update')
        )

      removeTile:(parameters)->
        @render() unless @rendered
        index = parameters.index
        if index?
          tile = @tiles.where({id:parameters.index})
          @_removeTile(tile,index)
        else
          type = parameters.type
          tilesOfType = @tiles.where({type:type})
          tiles = parameters.findInTiles(tilesOfType)
          for tile in tiles
            index = tile.get('id')
            @_removeTile(tile,index)

      addTile:(parameters)->
        @render() unless @rendered
        newTileParameters = {
          "type": parameters.type
          "color": if parameters.color? then parameters.color else "grey"
          "parameters": TileViews[parameters.type].processParameters?(parameters)
          "sizex": 1
          "sizey": 1
        }
        newModel = new Tile(newTileParameters)
        TileView = getTileView(newModel)
        tileView = new TileView(_.extend({color:newModel.get('color')}, newModel.get('parameters'), tile:newModel))
        @tiles.add(newModel)
        newTile = new TileContainer({
          model:newModel
          view:tileView
        })
        $tile = @gridster.add_widget(newTile.render())
        newModel.set('row',parseInt($tile.attr('data-row')))
        newModel.set('col', parseInt($tile.attr('data-col')))
        @tiles.trigger('grid-update')

      render:()->
        $(window).off('resize',@onResize)
        that = @
        panels = facade.portal.getDefaultPanels()
        profiles = facade.portal.getDefaultProfiles()
        for panel in panels
          # to avoid merging of object in backbone
          panel.id = ''
        @tiles = new Tiles(panels)
        @tiles.on('grid-update', ()->
          newPanels = that.tiles.toJSON()
          profiles = JSON.parse(JSON.stringify(profiles)) # to make a full clone and avoid side effects
          profiles[0].areas[0].panels = newPanels
          localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(profiles))
        )
        @$el.html(@template())
        @$el.find('.gridster').append(new TilesContainer({collection:@tiles}).render())

        gridster = @$el.find("ul").gridster({
          widget_base_dimensions: [168, 168]
          widget_margins: [10, 10]
          extra_cols:20
          extra_rows:20
          cols:8
          serialize_params: ($widget, wgd)->
            tile = that.tiles.findWhere({id:$widget.attr('id')})
            return {} unless tile?
            tile.set('col', wgd.col)
            tile.set('row', wgd.row)
            tile.set('sizex', wgd.size_x)
            tile.set('sizey', wgd.size_y)
            return tile.toJSON()
          resize:
            resize:_.debounce((e, ui, $widget)->
              $widget.find('>div').trigger('widget:resize')
            , 40)
            stop:(e, ui, $widget)->
              $widget.find('>div').trigger('widget:resize')
              gridster.serialize()
              that.tiles.trigger('grid-update')
            enabled: true,
            max_size: [6, 4],
            min_size: [1, 1]
          draggable:
            stop: ()->
              gridster.serialize()
              that.tiles.trigger('grid-update')
        }).data('gridster');
        $(window).on('resize', _.debounce(()=>
          @onResize()
        , 10, true))
        @gridster = gridster
        @rendered = true

        tilesAreaHelpviewOptions = {
          $target:@$el.find('.gridster'),
          anchor:'right',
          position:'bottom-left',
          title:t('Tiles area'),
          content:t('Each tile can be moved or resized in your homepage. Favorite tiles are another type of tile that can be added to the homepage when you will drill-down into the risk model. These tiles can be removed by clicking on the top right icon.')
        }
        facade.bus.emit('help:createView',tilesAreaHelpviewOptions)
        return @
    })

    module = {
      initialize: (options) ->
        facade.bus.emit('menu:add-item',{
          "className": "home",
          "text": t('Home'),
          "route": "home"
        })
        @homeView = new HomeView(options)
        facade.bus.on('show', @control, @)
        facade.bus.on('data:store:reset', @resetHomePage, @)
        facade.bus.on('tile:register', @registerTile, @)
        facade.bus.on('bookmark:add', @addBookmark,@)
        facade.bus.on('bookmark:remove', @removeBookmark,@)
        facade.bus.on('data:updated', @forceRendering,@)

        # register core tiles
        facade.bus.emit('tile:register',{type:'Inactive',TileView:CoreTiles.InactiveTileView})
        facade.bus.emit('tile:register',{type:'NotFound',TileView:CoreTiles.TileNotFoundView})

        $(window).resize()


      registerTile:(parameters)->
        TileViews[parameters.type] = parameters.TileView

      removeBookmark:(parameters)->
        @homeView.removeTile(parameters)
        facade.bus.emit('notification:message',{
          message:t('Tile removed from your homepage')
          title:t('Bookmark')
          type:'log'
        })

      addBookmark:(parameters)->
        @homeView.addTile(parameters)
        @rendered = true
        facade.bus.emit('notification:message',{
          message:t('New tile added to your homepage')
          title:t('Bookmark')
          type:'log'
        })

      resetHomePage:(parameters)->
        if parameters.key == 'profiles'
          localStorage.removeItem(LOCAL_STORAGE_WAR_IDENTIFIER + parameters.key) if parameters.key?
          @homeView.render()
          @rendered = true

      forceRendering:()->
        @rendered = false

      processBreadcrumb:(parameters)->
        switch parameters.pageId
          when 'home' then facade.bus.emit("breadcrumb", [])
          else return

      control:(parameters)->
        switch parameters.pageId
          when 'home'
            @homeView?.$el.show()
            $(window).trigger('resize')
            unless @rendered
              @homeView.render()
              @rendered = true
            @homeView?.$el.show()
            $('#content-container #drill-page').hide()

          else
            @homeView?.$el.hide()
            $('#content-container #drill-page').show()

      destroy:() ->

    }
    return module

  return HomeModule
