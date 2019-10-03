TechnologyTile = (facade) ->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t

  Tile = backbone.View.extend({
    className:'tile-technologies'
    template:Handlebars.compile('
          <div class="business-criteria icon-{{business}}">
            <h2>{{t "TECHNOLOGIES OVERVIEW"}}</h2>
            <h3 class="">{{t "for"}}</h3><div id="business-selector" class="business-selector"></div>
          </div>
          <div class="technology-container"></div>')
    loadingTemplate:'<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    templateTechnologies:Handlebars.compile('
          <table class="technology-view">
            <thead>
              <tr><th title="{{t "Technologies"}}" class="technology">{{t "Technologies"}}</th>
                  <th title="{{t "Critical Violations"}}" class="violations-count">{{#if isCritical}} {{t "Critical Violations"}} {{else}} {{t "Violations"}} {{/if}}</th>
              </tr>
            </thead>
            <tbody>
              {{#each data}}
                <tr class="technologySelector {{#isUndefined gradeValue}}disabled{{/isUndefined}}">
                  <td class="technology-name" >{{ellipsisMiddle technologyName ../charBefore ../charAfter}}</td>
                  <td class="critical-violations-count"><span>{{violationsCount}}</span></td>
                </tr>
              {{/each}}
            </tbody>
          </table>')

    events:
      'mousedown':'clicking'
      'click .technologySelector':'drillInQualityModel'

    initialize:(options)->
      @options = _.extend({},options)
      @business = @options.tile.get('parameters').business or "60017"
      @ascending = true if options.order == "ascending"
      @model = new facade.models.technology.TechnologiesOverview([], {href:facade.context.get('href'),snapshotId:facade.context.get('snapshot').getId(), ascending: @ascending, business: @business})
      @onlyCritical = facade.portal.getFilterSetting('criticalsOnly')
      filterHealthFactor = facade.portal.get('configuration').filterHealthFactor or false
      @businessCriteriaModels = facade.context.get('snapshot').createBusinessCriteriaConfiguration({
        filterHealthFactor:filterHealthFactor
      })
      facade.bus.on('global-filter-change:criticalsOnly',this.updateFilterState,this)

    clicking:(event)->
      @clicked = {
        x: event.pageX
        y: event.pageY
      }
      return true

    _dataRender:(business)->
      @model = new facade.models.technology.TechnologiesOverview([],{
        href:facade.context.get('href'),
        snapshotId:facade.context.get('snapshot').getId()
        business:business
        ascending: @ascending
      })
      @model.getData({
        success:()=>
          data = @model.computeSummary(@onlyCritical)
          @$el.find('.technology-container').html(this.templateTechnologies({data: data, isCritical: @onlyCritical}))
      })

    drillInQualityModel:(event)->
      technology = event.currentTarget.cells[0].innerText
      facade.bus.emit('filter', {technology:technology});
      if @clicked? and Math.abs(event.pageX - @clicked.x) < 15 and Math.abs(event.pageY - @clicked.y) < 15
        @clicked = null
        facade.bus.emit('navigate', {page:'qualityInvestigation/0/' + @business, technology:technology})
        return
      @clicked = null

    updateFilterState:()->
      this.onlyCritical = facade.portal.getFilterSetting('criticalsOnly')
      this.renderDetails()

    renderDetails:()->
      @model.getData({
        success:()=>
          data = @model.computeSummary(@onlyCritical)
          $ul = @$el.find('.technology-container')
          $ul.html(@templateTechnologies({
            data: data,
            isCritical: @onlyCritical
          }))
      })

    render:()->
      @$el.html(@template(business:@business))
      @$el.find('.technology-container').html(@loadingTemplate)
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
            @$el.find('.technology-container').html(@loadingTemplate)
            @_dataRender(item)
            @options.tile.get('parameters').business = item
            @options.tile.collection.trigger('grid-update')
          )
          @$el.find('#business-selector').html(@businessCriteriaSelector.render())
          @$el?.find('#business-selector .cont .options').attr('data-before',t('Select health measure'))
          @businessCriteriaSelector.selectValue(@business)
          that = @
      })
      @$el
  })
  return Tile
