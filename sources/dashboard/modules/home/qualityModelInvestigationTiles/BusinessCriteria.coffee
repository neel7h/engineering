BusinessCriteria = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t
  BUSINESS_CRITERIA_STRENGTH = 'strength'
  STRENGTH_BUSINESS = 'strength-business'
  WEAKNESS_BUSINESS = 'weakness-business'

  classifyScore = (grade)->
    return 'bad' if grade < 2
    return 'warn' if grade < 3
    return 'good' if grade <4
    return 'very-good'

  TechnicalCriteriaView = backbone.View.extend({
    className: 'business-criteria-strength-tile'
    template:Handlebars.compile('
      <div class="business-criteria icon-{{business}}">
        <h2 class="">{{#if strength}} {{t "strengths"}} {{else}} {{t "weaknesses"}} {{/if}}</h2>
        <h3 class="">{{t "for"}}</h3><div id="business-selector" class="business-selector"></div>
      </div>
      <ul class="technical-criteria-list"></ul>
    ')
    loadingTemplate:'<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'
    technicalCriteriaTemplate:Handlebars.compile('
      {{#unless data.length}}<div><span class="empty-technical-criteria" >{{t "No technical criteria present" }}</span></div>{{/unless}}
      {{#each data}}<li title="{{name}}" data-key="{{key}}">{{ellipsisMiddle name ../charBefore ../charAfter}}</li>{{/each}}
    ')

    events:
      'mousedown':'clicking'
      'click ul>li':'drillInBusinessCriteria'
      'widget:resize':'updateRendering'

    updateRendering:(event) ->
      $t = $(event.target)
      if $t.width() < 350
        charBefore = 7
        charAfter = 35
      else
        charBefore = 60
        charAfter = 60
      if $t.height() < 170
        showData = @data.slice(0,4)
      else if $t.height() > 170 and $t.height() < 360
        showData = @data.slice(0,11)
      else
        showData = @data

      $ul = @$el.find('.technical-criteria-list')
      $ul.html(@technicalCriteriaTemplate({data:showData, charBefore:charBefore, charAfter:charAfter},{
        helpers:{
          classifyScore:classifyScore
        }
      }))
      @$el

    clicking:(event)->
      @clicked = {
        x: event.pageX
        y: event.pageY
      }
      true

    drillInBusinessCriteria:(event)->
      $target = $(event.target)
      localStorage.setItem(BUSINESS_CRITERIA_STRENGTH, @strength)
      if @clicked? and Math.abs(event.pageX - @clicked.x) < 15 and Math.abs(event.pageY - @clicked.y) < 15
        @clicked = null
        if @data? and @data.length > 0
          facade.bus.emit('navigate', {page:'qualityInvestigation/0/' + @business + '/' + $target.attr('data-key')})
        return
      @clicked = null

    initialize:(options)->
      @options = _.extend({},options)
      @strength = @options.tile.get('parameters').orderBy == "strength"
      @business = @options.tile.get('parameters').business or '60017'
      @business = "60016" if facade.context.get('isSecurity')
      @threshold = @options.tile.get('parameters').threshold or [2,3,3.99]
      this.onlyCritical = facade.portal.getFilterSetting('criticalsOnly');
      filterHealthFactor = facade.portal.get('configuration').filterHealthFactor or false
      @businessCriteriaModels = facade.context.get('snapshot').createBusinessCriteriaConfiguration({
        filterHealthFactor:filterHealthFactor
      })
      module = facade.context.get('module')
      snapshot = facade.context.get('snapshot')
      lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds()
      if module
        prevSnapshotModules = facade.context.get('modulesInPreviousSnapshot').pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(module.get('name'))
        lastTwoSnapshotIds = snapshot.getLastTwoSnapshotIds().splice('1') if isModuleAvailable < 0
      @model = new facade.models.TechnicalCriteriaResults({
        href:SELECTED_APPLICATION_HREF
        businessCriterion:@business
        snapshotId:snapshot.getId()
        lastTwoSnapshotIds:lastTwoSnapshotIds
      })
      facade.bus.on('global-filter-change:criticalsOnly',this.updateFilterState,this)

    updateFilterState:(options)->
      this.onlyCritical = facade.portal.getFilterSetting('criticalsOnly');
      this.renderTechnicalCriteria(@options.business)

    renderTechnicalCriteria:(businessItem)->
      orderByStrength = @strength
      @data = @model.listCriteria({
        criticalsOnly:this.onlyCritical
        sortOrder:if orderByStrength then 'ascending' else 'descending'
        filter:(line)->
          return line.value != 0 if orderByStrength
          return line.value == 0
      })
      $ul = @$el.find('.technical-criteria-list')
      $ul.html(@technicalCriteriaTemplate({
        data:@data,
        charBefore:7,
        charAfter:35
        }
      ))

      if orderByStrength
        localStorage.setItem(STRENGTH_BUSINESS, businessItem)
      else
        localStorage.setItem(WEAKNESS_BUSINESS, businessItem)

    _dataRender:(businessItem)->
      snapshot = facade.context.get('snapshot')
      lastTwoSnapshotIds = facade.context.get('snapshot').getLastTwoSnapshotIds()
      module = facade.context.get('module')
      if module
        modulesInPreviousSnapshot = facade.context.get('modulesInPreviousSnapshot')
        prevSnapshotModules = modulesInPreviousSnapshot.pluck('name')
        isModuleAvailable = prevSnapshotModules.indexOf(module.get('name'))
        lastTwoSnapshotIds = facade.context.get('snapshot').getLastTwoSnapshotIds().splice('1') if isModuleAvailable < 0

      @model = new facade.models.TechnicalCriteriaResults({
        href:SELECTED_APPLICATION_HREF
        businessCriterion:businessItem
        snapshotId:snapshot.getId()
        lastTwoSnapshotIds:lastTwoSnapshotIds
      })
      @model.getData({
        success:()=>
          this.renderTechnicalCriteria(businessItem);
      })

    render:()->
      strength = @strength
      className = if strength then 'strength' else 'weaknesses'
      @$el.addClass(className)
      @$el.html(@template({
        businessCriteria:''
        business:@business
        strength:strength
        isTQI:@business == '60017'
      }))

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
            @$el.find('.technical-criteria-list').html(@loadingTemplate)
            @_dataRender(item)
            @options.tile.get('parameters').business = item
            @options.tile.collection.trigger('grid-update')
          )
          @$el.find('#business-selector').html(@businessCriteriaSelector.render())
          @$el?.find('#business-selector .cont .options').attr('data-before',t('Select health measure'))
          @businessCriteriaSelector.selectValue(@business)
      })

      return @$el
  })

  return TechnicalCriteriaView
