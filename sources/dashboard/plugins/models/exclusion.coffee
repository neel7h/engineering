exclusion = (_, BackboneWrapper) ->

  ExclusionSummary = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @href + '/exclusions/summary'

    initialize:(data, options = {})->
      @href = options.href

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    computeSummary:()->
      result = {
        addedExclusionRequests:0
        unboundExclusionRequests:0
        processedExclusionRequests:0
      }
      @each((item)->
        result.addedExclusionRequests += item.get('addedExclusionRequests')
        result.unboundExclusionRequests += item.get('unboundExclusionRequests')
        result.processedExclusionRequests += item.get('processedExclusionRequests')
      )
      result.totalIssues = result.addedExclusionRequests + result.unboundExclusionRequests + result.processedExclusionRequests
      result

  })

  ScheduledExclusionsSummary = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @href + '/exclusions/scheduled-summary'

    initialize:(data, options = {})->
      @href = options.href

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    computeSummary:()->
      @models[0].get('scheduledExclusions').number

  })

  ActiveExclusionsSummary = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @href + '/excluded-violations-summary'

    initialize:(data, options = {})->
      @href = options.href

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    computeSummary:()->
      @models[0].get('excludedViolations').number

  })

  ExclusionIssue = BackboneWrapper.BaseModel.extend({

    getObjectId:()->
      component = @get('component')
      componentId = component?.href.split('/')[2]
      #date = @get('remedialAction').dates.updated.time
      date = 'yo'
      rule = @get('rulePattern').href.split('/')[2]
      return componentId + '-' + date + '-' + rule

    getComponentId:()->
      return @get('component')?.href.split('/')[2]

    getRuleId:()->
      return @get('rulePattern').href.split('/')[2]
  })

  ActiveExclusions = BackboneWrapper.BaseCollection.extend({
    model:ExclusionIssue
    url:()->
      suffix = '?startRow=' + @startRow
      suffix += '&nbRows=' + @nbRows
      REST_URL + @href + '/excluded-violations' + suffix

    initialize:(models, options)->
      @href = options.href
      @startRow = options.startRow or 1
      @nbRows = options.nbRows or 10

    parse:(data)->
      allData = []
      for model in @models
        allData.push model.toJSON()
      for d in data
        allData.push(d)
      allData

    asRows:(options)->
      maxRows = options?.nbRows or @models.length
      results = []
      index = 0
      for model in @models
        break if index++ >= maxRows
        results.push({
          columns:[
            model.get('exclusionRequest')?.comment or ''
            model.get('rulePattern').name
            model.get('component').name
            model.get('exclusionRequest')?.dates?.updated.time or ''
          ]
          extra:{
            model:model
          }
          id:model.getObjectId()
          componentId:model.getComponentId()
          ruleId:model.getRuleId()
        })
      @_collection = new BackboneWrapper.BaseCollection(results)

  })

  ScheduledExclusions = BackboneWrapper.BaseCollection.extend({
    model:ExclusionIssue
    url:()->
      suffix = '?startRow=' + @startRow
      suffix += '&nbRows=' + @nbRows
      REST_URL + @href + '/exclusions/scheduled' + suffix

    initialize:(models, options)->
      @href = options.href
      @startRow = options.startRow or 1
      @nbRows = options.nbRows or 10

    parse:(data)->
      allData = []
      for model in @models
        allData.push model.toJSON()
      for d in data
        allData.push(d)
      allData

    asRows:(options)->
      maxRows = options?.nbRows or @models.length
      results = []
      index = 0
      for model in @models
        break if index++ >= maxRows
        results.push({
          columns:[
            model.get('exclusionRequest')?.status or ''
            model.get('exclusionRequest')?.comment or ''
            model.get('rulePattern').name
            model.get('component').name
            model.get('exclusionRequest')?.dates.updated.time or ''
            model.get('exclusionRequest')?.status + '_'  + model.getRuleId() + '/' + model.getComponentId()
          ]
          extra:{
            model:model
          }
          id:model.getObjectId()
          componentId:model.getComponentId()
          ruleId:model.getRuleId()
        })
      @_collection = new BackboneWrapper.BaseCollection(results)

  })

  return {
    ExclusionSummary
    ScheduledExclusionsSummary
    ActiveExclusionsSummary
    ActiveExclusions
    ScheduledExclusions
  }
