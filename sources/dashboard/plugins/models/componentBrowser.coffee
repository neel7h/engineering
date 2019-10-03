###
  Component browser provides the models to access the application information by hierarchy
###

componentBrowser = (_, BackboneWrapper) ->

  ComponentRoot = BackboneWrapper.BaseModel.extend({
    url:()->
      REST_URL + SELECTED_APPLICATION_HREF + '/snapshots/' + @get('snapshotId') + '/tree-node'

    getChildrenHref:()->
      @get('children')?.href

    getDefectsSummaryHref:()->
      @get('defectsSummary')?.href

    getHref:()->
      @get('href')

    getComponent:()->
      @get('component')

    getAncestors:()->
      @get('ancestors')
  })

  DefectsSummary = BackboneWrapper.BaseModel.extend({
    url:()->
      url = REST_URL + @get('href')
      url += '?business-criterion=' + @get('businessCriterion') if @get('businessCriterion')?
      url

    getViolations:()->
      @get('violations')

    getDefectiveComponents:()->
      @get('defectiveComponents')

    getViolatedRulePatterns:()->
      @get('violatedRulePatterns')
  })

  TreeNodes = BackboneWrapper.BaseCollection.extend({
    url:()->
      REST_URL + @options.href

    initialize:(options)->
      @options = _.extend({},options)

    getFirstNodeId:()->
      href = @at(0)?.get('href')
      id = href?.split('/')?[2] or ''
      return id
  })

  return {
    ComponentRoot
    DefectsSummary
    TreeNodes
  }