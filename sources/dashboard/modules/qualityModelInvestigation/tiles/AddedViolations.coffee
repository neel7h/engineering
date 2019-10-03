AddedViolations = (facade) ->

  Handlebars = facade.Handlebars
  t = facade.i18n.t
  return facade.backbone.View.extend({
    className:'tile-content'
    template:Handlebars.compile('
        <div class="business-criteria icon-{{business}}">
          <h2>{{t "Risk introduced"}}</h2>
          <h3 class="">{{t "for"}}</h3><div id="business-selector" class="business-selector"></div>
        </div>
        <div class="added-violations-container"></div>')

    loadingTemplate:'<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    valuesTemplate:Handlebars.compile('
      {{#if critical}}
          <div class="added-violations"><div class="value {{#if isLarge}}large-value{{/if}}">{{#if added}}+ {{/if}}{{formatNumber added "0,000"}}</div><div class="label">{{t "Added critical violations"}}</div></div>
          <div class="removed-violations"><div class="value">{{#if removed}}- {{/if}}{{formatNumber removed "0,000"}}</div><div class="label">{{t "Removed critical violations"}}</div></div>
      {{else}}
        <div class="added-violations"><div class="value {{#if isLarge}}large-value{{/if}}">{{#if added}}+ {{/if}}{{formatNumber added "0,000"}}</div><div class="label">{{t "Added violations"}}</div></div>
        <div class="removed-violations"><div class="value">{{#if removed}}- {{/if}}{{formatNumber removed "0,000"}}</div><div class="label">{{t "Removed violations"}}</div></div>
      {{/if}}')

    noRiskTemplate:Handlebars.compile('
      {{#if critical}}
          <div class="disable-tile" >{{t "No added and removed critical violations"}}</div>
      {{else}}
          <div class="disable-tile" >{{t "No added and removed violations"}}</div>
      {{/if}}')

    events:
      'mousedown':'clicking'
      'click .added-violations-container':'drillInQualityModel'
      'widget:resize':'updateRendering'

    updateRendering:() ->
      if @$el.width() < 260
        @$el.addClass('compact-col') unless @$el.hasClass('compact-col')
      else
        @$el.removeClass('compact-col') if @$el.hasClass('compact-col')
      @$el

    clicking:(event)->
      @clicked = {
        x: event.pageX
        y: event.pageY
      }
      return true

    drillInQualityModel:(event)->
      if @clicked? and Math.abs(event.pageX - @clicked.x) < 15 and Math.abs(event.pageY - @clicked.y) < 15
        @clicked = null
        facade.bus.emit('navigate', {page:'qualityInvestigation/risk/' + @business })
        return
      @clicked = null

    initialize:(options)->
      @options = _.extend({},options)
      @business = @options.tile.get('parameters').business or '60017'
      @business = "60016" if facade.context.get('isSecurity')
      filterHealthFactor = facade.portal.get('configuration').filterHealthFactor or false
      snapshot = facade.context.get('snapshot')
      module = facade.context.get('module')
      lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds()
      if module
        prevSnapshotModules = facade.context.get('modulesInPreviousSnapshot').pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(module.get('name'))
        lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds().splice('1') if isModuleAvailable < 0
      @model = new facade.models.BusinessCriteriaResults({
          href:SELECTED_APPLICATION_HREF
          snapshotId: snapshot.getId()
          lastTwoSnapshotIds: lastTwoSnapshotIds
      })
      @businessCriteriaModels = facade.context.get('snapshot').createBusinessCriteriaConfiguration({
        filterHealthFactor:filterHealthFactor
      })
      facade.bus.on('global-filter-change:criticalsOnly', this._dataRender, this)

    _dataRender:()->
      criticalsOnly =  facade.portal.getFilterSetting('criticalsOnly')
      modelDataTemp = @model.getRiskIntroduced({business:@business, critical:criticalsOnly})
      addedViolationsCount = modelDataTemp.added
      removedViolationsCount = modelDataTemp.removed
      modelDataTemp.isLarge = addedViolationsCount> 10000
      if addedViolationsCount == 0 and removedViolationsCount == 0
       @$el.find('.violations-container').remove()
       @$el.find('.added-violations-container').remove()
       @$el.append('<div class="violations-container violations-container-empty"></div>')
       $vc = @$el.find('.violations-container')
       $vc.html(@noRiskTemplate({
         critical: criticalsOnly
       }))
      else
       @$el.find('.violations-container').remove()
       @$el.append('<div class="added-violations-container risk-intro-evt"></div>')
       @$el.find('.added-violations-container').html(this.valuesTemplate(modelDataTemp))
      return

    render:()->
      facade.ui.spinner(@$el)
      @$el.addClass('compact-col') if @options.tile.get('sizex') == 1

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
            @_dataRender(item)
            @options.tile.get('parameters').business = item
            @options.tile.collection.trigger('grid-update')
          )
          showCriticalsOnly = facade.portal.getFilterSetting('criticalsOnly')
          @$el.html(@template({
            showCriticalsOnly:showCriticalsOnly
            business:@business
          }))
          @$el.find('#business-selector').html(@businessCriteriaSelector.render())
          @$el.find('.added-violations-container').html(@loadingTemplate)
          @$el?.find('#business-selector .cont .options').attr('data-before',t('Select health measure'))
          @model.getData({
            success:()=>
              @businessCriteriaSelector.selectValue(@business)
          })
      })
      @$el
  })
