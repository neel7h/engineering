NewViolationsForQualityRules = (facade)->

  backbone = facade.backbone
  Handlebars = facade.Handlebars
  _ = facade._
  t = facade.i18n.t
  INCREASE_VIOLATIONS_BUSINESS = 'increase-violations-business'

  formatPercentage = (value, format)->
    return t('new') if value == Infinity
    absValue = Math.abs(value*100)
    return '~0%' if absValue>0 and absValue<1
    return facade.numeral(value).format(format)

  Tile = backbone.View.extend({
    className:'new-violations-for-quality-rules-tile'
    template:Handlebars.compile('
      <div class="business-criteria icon-{{parameters.business}}">
        <h2>{{#if increasing}}{{t "Top rules increasing violations"}}{{else}}{{t "Top rules decreasing violations"}}{{/if}}</h2>
        <h3 class="">{{t "for"}}</h3><div id="business-selector" class="business-selector"></div>
      </div>
      <div class="new-violations-rules-container"></div>
      </div>')
    loadingTemplate:'<div class="loading white"><div class="square" id="square1"></div><div class="square" id="square2"></div><div class="square" id="square3"></div><div class="square" id="square4"></div></div>'

    rulesWithAddedViolations:Handlebars.compile('
      {{#unless data.length}}<div><span class="rule-name no-added" >{{t "No added violations" }}</span></div>{{/unless}}
        {{#each data}}
          <div class="link-to-rule" data-business="{{business}}"  data-key="{{key}}" title="{{name}} : {{formatNumber addedViolations "0,000"}} {{#if ../hasPreviousSnapshot}}{{t "more violations since previous snapshot"}}{{else}}{{t "added"}}{{/if}}">
            <span class="rule-name" >{{ellipsisMiddle name ../charBefore ../charAfter}}</span>
            <span class="added-violations {{#if critical}}critical {{/if}}">
              <span>+ {{formatNumber addedViolations "0,000"}}</span>
            </span>
          </div>
        {{/each}}')

    rulesWithRemovedViolations:Handlebars.compile('
      {{#unless data.length}}<div><span class="rule-name no-added" >{{t "No removed violations" }}</span></div>{{/unless}}
        {{#each data}}
          <div class="link-to-rule {{#if hasNoFailedChecks}}non-clickable{{/if}}" data-business="{{business}}"  data-key="{{key}}" title="{{#if hasNoFailedChecks}}{{t "This rule is not available for investigation as it does not apply anymore"}}{{else}}{{name}} : {{formatNumber removedViolations "0,000"}} {{#if ../hasPreviousSnapshot}}{{t "less violations since previous snapshot"}}{{else}}{{t "removed"}}{{/if}}{{/if}}">
            <span class="rule-name" >{{ellipsisMiddle name ../charBefore ../charAfter}}</span>
            <span class="removed-violations {{#if critical}}critical {{/if}}">
              <span>- {{formatNumber removedViolations "0,000"}}</span>
            </span>
          </div>
        {{/each}}')


    rulesWithNewViolationsTemplate:Handlebars.compile('{{#unless data.length}}<div><span class="rule-name no-added" >{{ellipsisMiddle "No increasing violations" ../charBefore ../charAfter}}</span></div>{{/unless}}
      {{#each data}}
      <div class="link-to-rule" data-business="{{business}}"  data-key="{{key}}" title="{{name}} : {{formatNumber violations "0,000"}} {{#if ../hasPreviousSnapshot}}{{t "more violations since previous snapshot"}}{{else}}{{t "added"}}{{/if}}">
        <span class="rule-name" >{{ellipsisMiddle name ../charBefore ../charAfter}}</span>
        <span class="violation-ratio {{#if critical}}critical {{/if}}" title="{{violations}}">
          <span>{{formatPercentageNumber violationsRatio "0%"}}</span>
      </div>
    {{/each}}')

    initialize:(options)->
      snapshot = facade.context.get('snapshot')
      businessCriterion = options.tile.get('parameters').business or '60013'
      businessCriterion = "60016" if facade.context.get('isSecurity')
      @options = _.extend({},options,{
        business: businessCriterion
        onlyCritical: facade.portal.getFilterSetting('criticalsOnly')
      })

      @model =  new facade.models.TopRulesViolationsResults([],{
        business:@options.business
        lastTwoSnapshotIds: snapshot.getLastTwoSnapshotIds()
      });

      filterHealthFactor = facade.portal.get('configuration').filterHealthFactor or false
      @businessCriteriaModels = facade.context.get('snapshot').createBusinessCriteriaConfiguration({
        filterHealthFactor:filterHealthFactor
      })
      this.isCritical = facade.portal.getFilterSetting('criticalsOnly');
      facade.bus.on('global-filter-change:criticalsOnly',this.updateFilterState,this)

    remove:()->
      facade.bus.off('global-filter-change:criticalsOnly',this.updateFilterState)

    events:
      'widget:resize':'updateRendering'
      'mouseup .link-to-rule:not(.non-clickable)':'clicking'
      'mousedown':'mouseDown' # deactivate drag'n drop on tile when clicking span
      'click .critical-control>div':'displayOnlyCritical'

    applyToTemplate:(data, templateHelpers) ->
      if data.addedViolations
        return @rulesWithAddedViolations(data, templateHelpers)
      if data.removedViolations
        return @rulesWithRemovedViolations(data, templateHelpers)
      return @rulesWithNewViolationsTemplate(data, templateHelpers)

    updateRendering:(event) ->
      large = @large
      newData = @_setupData(@$el.width())
      if large != @large
        @$el.find('.new-violations-rules-container').html(@applyToTemplate(newData,{
          helpers:{
            formatPercentageNumber:formatPercentage
          }
        }))

    updateFilterState:(options)->
      selectCritical = facade.portal.getFilterSetting('criticalsOnly');
      @options.onlyCritical = selectCritical
      @_dataRender(@options.business)

    clicking:(event)->
      return true unless @onLink
      @onLink = false
      $t = @_isLink(event.target)
      return true unless $t?

      ruleId  = $t.attr('data-key')
      businessId = $t.attr('data-business')
      linkModel = new facade.models.ContributionCriterion({
        domain:CENTRAL_DOMAIN
        criterion:ruleId
        snapshotId:facade.context.get('snapshot').getId()
      })
      linkModel.getData({
        success:()->
          firstAggregator = linkModel.get('gradeAggregators')[0]
          technicalCriteriaId = firstAggregator.key
          localStorage.setItem("emphasizeAddedViolations", 'true')
          facade.bus.emit('navigate', {page:'qualityInvestigation/0/' + businessId + '/' + technicalCriteriaId + '/' + ruleId})
        error:()->
          facade.bus.emit('notification:message',{message: t('We were not able to gather data required to build link. If the issue reproduces, please contact your administrator.'), type:'error', 'title':t('An error occurred')})
      })

      return false

    mouseDown:(event)->
      if @_isLink(event.target)
        @onLink = true
        return false
      @onLink = false
      return true



    _isLink:(target)->
      $t = $(target)
      return $t if $t.hasClass('link-to-rule')
      $t = $t.parents('.link-to-rule')
      return $t  if $t.hasClass('link-to-rule')
      return undefined

    _setupData:(width)->
      variation = this.options.tile.get('parameters').variation
      isViolationRatio = ['added', 'removed'].indexOf(variation) == -1
      data = {
        increasing: 'removed' != variation
        addedViolations: 'added' == variation
        removedViolations:'removed' == variation
        violationsRatio: isViolationRatio
        hasPreviousSnapshot:if isViolationRatio then @model.hasPreviousSnapshot() else true
        data:@model.filterRules({filterCriterion:variation, onlyCritical:@options.onlyCritical})
      }
      if width < 400
        @large='min'
        return _.extend(data, { charBefore : 28, charAfter : 10})
      if width < 520
        @large='medium'
        return _.extend(data,  { charBefore : 60, charAfter : 30})

      @large='max'
      return _.extend(data,  { charBefore : 60, charAfter : 50})

    _dataRender:(businessItem)->
      snapshot = facade.context.get('snapshot')
      @model = new facade.models.TopRulesViolationsResults([],{
        business:businessItem
        lastTwoSnapshotIds: snapshot.getLastTwoSnapshotIds()
      });
      @model.getData({
        success:()=>
          @$el.find('.new-violations-rules-container').html(@applyToTemplate(@_setupData(@$el.width()),{
            helpers:{
              formatPercentageNumber:formatPercentage
              }
            }))
          localStorage.setItem(INCREASE_VIOLATIONS_BUSINESS, businessItem)
        error:()=>
          @$el.find('.new-violations-rules-container').html('<p class="error">' + t('An error occurred. Please try and reload the page or contact your administrator.') + '</p>')
      })

    render:()->
      tileConfiguration = _.extend({
        increasing:'removed' != @options.tile.get('parameters').variation
      }, @options.tile.toJSON())
      @$el.html(@template(tileConfiguration))
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
            oldBusiness = @options.business
            @options.business = item
            if oldBusiness? and oldBusiness != @options.business
              @$el.find('.business-criteria').addClass('icon-'+@options.business).removeClass('icon-'+oldBusiness)
            @$el.find('.new-violations-rules-container').html(@loadingTemplate)
            @_dataRender(item)
            @options.tile.get('parameters').business = item
            @options.tile.collection.trigger('grid-update')
          )
          @$el.find('#business-selector').html(@businessCriteriaSelector.render())
          @$el?.find('#business-selector .cont .options').attr('data-before',t('Select health measure'))
          @businessCriteriaSelector.selectValue(@options.business)
      })

      @$el

  })

  return Tile
