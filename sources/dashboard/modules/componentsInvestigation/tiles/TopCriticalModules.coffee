TopCriticalModules = (facade)->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  CRITICAL_MODULES_BUSINESS = 'critical-modules-business'

  Tile = backbone.View.extend({
    className:'top-critical-modules-tile'
    template:Handlebars.compile('
      <div class="business-criteria icon-{{parameters.business}}">
        <h2>{{title}}</h2>
        <h3 class="">{{t "for"}}</h3><div id="business-selector" class="business-selector"></div>
      </div>
      <div class="critical-violations-scale-grid"></div>
      <div class="critical-modules-container"></div>
      <div class="critical-violations-scale" >



      </div>')
    # FIXME use general loader instead of manual one
    loadingTemplate:'<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    modulesTemplate:Handlebars.compile('
    {{#if onlyCritical}}
      {{#each data}}
        <div class="link-to-module" data-href="{{href}}" title="{{name}}: {{formatNumber criticalViolations "0,000"}} {{t "critical violations"}}"><span class="module-name" >{{ellipsis name 22}}</span><span class="critical-violation-count"><span style="width:{{width}}%" /></div>
      {{/each}}
    {{else}}
      {{#each data}}
        <div class="link-to-module" data-href="{{href}}" title="{{name}}: {{formatNumber violations "0,000"}} {{t "violations"}}"><span class="module-name" >{{ellipsis name 22}}</span><span class="critical-violation-count"><span style="width:{{width}}%" /></div>
      {{/each}}
    {{/if}}')

    scaleTemplate:Handlebars.compile('
        <span class="legend">{{#if onlyCritical}}{{t "# Crit. violations"}}{{else}}{{t "# violations"}}{{/if}}</span>
        <span class="scale-ranges">
          <span class="min-value">0</span><span class="median-value">{{formatNumber median "0,000"}}</span><span class="max-value">{{formatNumber max "0,000"}}</span>
        </span>')

    initialize:(options)->
      @options = _.extend({},options)
      @business = @options.tile.get('parameters').business or '60013'
      @business = "60016" if facade.context.get('isSecurity')
      filterHealthFactor = facade.portal.get('configuration').filterHealthFactor or false
      @businessCriteriaModels = facade.context.get('snapshot').createBusinessCriteriaConfiguration({
        filterHealthFactor:filterHealthFactor
      })
      @onlyCritical = facade.portal.getFilterSetting('criticalsOnly');
      @model = new facade.models.ModuleResultsWithCriticity({
        snapshotHref:facade.context.get('snapshot').get('href')
        business:@business
      })
      facade.bus.on('global-filter-change:criticalsOnly',this.updateFilterState,this)

    updateFilterState:(options)->
      @onlyCritical = facade.portal.getFilterSetting('criticalsOnly');
      @_dataRender(@options.business)

    events:
      'widget:resize':'updateRendering'
      'mouseup .link-to-module':'clicking'
      'mousedown':'mouseDown'

    updateRendering:(event) ->
      $(window).trigger('resize')

    mouseDown:(event)->
      if @_isLink(event.target)
        @onLink = true
        return false
      @onLink = false
      return true

    _isLink:(target)->
      $t = $(target)
      return $t if $t.hasClass('link-to-module')
      $t = $t.parents('.link-to-module')
      return $t  if $t.hasClass('link-to-module')
      return undefined

    clicking:(event)->
      moduleHref = @_isLink(event.target)?.attr('data-href')
      return true unless moduleHref?
      return true unless @onLink
      @onLink = false
      treeNodes = new facade.models.componentBrowserTree.TreeNodes({href:moduleHref + '/tree-node'})
      business = @business
      treeNodes.getData({
        success:()->
          node = treeNodes.getFirstNodeId()
          facade.context.get('scope').set('businessCriterion',business)
          localStorage.setItem("criticalSorting", 'true')
          if node == ''
            facade.bus.emit('navigate', {page:'componentsInvestigation'})
          else
            facade.bus.emit('navigate', {page:'componentsInvestigation/' + node})
      })

      return false

    _dataRender:(business)->
        data = @model.listModules({
          criticalsOnly:@onlyCritical
        })
        attribute = if @onlyCritical then 'criticalViolations'  else 'violations'
        max = 0
        if data.length >= 0 # Check necessity
          max = data[0][attribute]
          for sample in data
            sample.width = 100 * sample[attribute] / max
        median = max / 2
        @$el.find('.critical-violations-scale-grid').show()
        @$el.find('.critical-violations-scale').show()
        @$el.find('.critical-modules-container').html(@modulesTemplate({data:data, onlyCritical:@onlyCritical}))
        @$el.find('.critical-violations-scale').html(@scaleTemplate({median:median, max:max, onlyCritical:@onlyCritical}))
        localStorage.setItem(CRITICAL_MODULES_BUSINESS, business)


    render:()->
      @$el.html(@template(_.extend({
          title: this.constructor.title
        }, @options.tile.toJSON())))

      @businessCriteriaModels.getData({
        success:()=>
          result = []
          @businessCriteriaModels.each((model)->
            result.push({
              label:model.get('name')
              value:model.get('key')
              selected: parseInt(model.get('key')) == parseInt(@business)
            })
          )
          @businessCriteriaSelector = new facade.bootstrap.Selector({name: '', data: result, class: 'left', maxCharacters:20});
          @businessCriteriaSelector.on('selection', (item)=>
            oldBusiness = @business
            @business = item
            if oldBusiness? and oldBusiness != @business
              @$el.find('.business-criteria').addClass('icon-'+@business).removeClass('icon-'+oldBusiness)
            @$el.find('.critical-modules-container').html(@loadingTemplate)
            @$el.find('.critical-violations-scale-grid').hide()
            @$el.find('.critical-violations-scale').hide()
            @model = new facade.models.ModuleResultsWithCriticity({
              snapshotHref:facade.context.get('snapshot').get('href')
              business:@business
            })
            @model.getData({
              success:()=>
                @_dataRender(item)
              error:()=>
                @$el.find('.critical-modules-container').html(t('no modules'))
            })
            @options.tile.get('parameters').business = item
            @options.tile.collection.trigger('grid-update')
          )
          @$el.find('#business-selector').html(@businessCriteriaSelector.render())
          @$el?.find('#business-selector .cont .options').attr('data-before',t('Select health measure'))
          @businessCriteriaSelector.selectValue(@business)
      })
      @$el
  },{
    requiresLastSnapshot:true
    title:t('Top modules with violations')
  })

  return Tile
