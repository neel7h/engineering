education = (_, BackboneWrapper) ->

  EducationIssue = BackboneWrapper.BaseModel.extend({
    getRuleId:()->
      return @get('rulePattern').href.split('/')[2]
  })

  EducationSummary = BackboneWrapper.BaseCollection.extend({
    model: EducationIssue
    url:()->
      REST_URL + @href + '/action-plan/triggers'

    initialize:(models, options)->
      @href = options.href

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    totalCount:()->
      return @models.length

    parse:(data)->
      allData = []
      for model in @models
        allData.push model.toJSON()
      for d in data
        allData.push(d)
      allData

    asRows:(options)->
      results = []
      if options?.improvementSection
        for model in @models
          if !model.get('active')
            results.push({
              columns:[
                model.get('rulePattern').name
              ]
              extra:{
                model:model
              }
              id:model.getRuleId()
              ruleId:model.getRuleId()
            })
      else
        for model in @models
          results.push({
            columns:[
              model.get('rulePattern').name
              model.get('remedialActionPattern').tag or model.get('remedialActionPattern').priority
              model.get('remedialActionPattern')?.comment or ''
              model.get('active')
              model.get('remedialActionPattern').dates.updated.time
              {active: model.get('active'), ruleId: model.getRuleId(), ruleName: model.get('rulePattern').name }
              model.getRuleId()
            ]
            extra:{
              model:model
            }
            id:model.getRuleId()
            ruleId:model.getRuleId()
          })
      @_collection = new BackboneWrapper.BaseCollection(results)

  })

  EducationTotalViolationsCount = BackboneWrapper.BaseModel.extend({
    url:()->
      url = REST_URL + @href + '/results?quality-indicators=('+@rules+')&select=(violationRatio)'
      if @snapshotId then url += '&snapshot-id=' + @snapshotId else  url += '&snapshots=$all'

    initialize:(models, options)->
      @href = options.href
      @rules = options.ruleIds
      @snapshotId = options.snapshotId

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseModel.prototype.fetch.call(this, options)

    getSnapshotsData:(data)->
      snapshotsData = []
      for index of data.attributes
        snapshotsData.push({
          time: data.get(index).date.time,
          date: data.get(index).date.isoDate,
          violations: @getViolationsCount(data, index)
        })
      return snapshotsData

    getViolationsCount:(data, index)->
      violationsCount = 0
      for rule in data.get(index).applicationResults
        violationsCount += rule.result.violationRatio.failedChecks
      return violationsCount

    getInitialViolationsCount:(data)->
      initialViolationsCount = 0
      for rule in data.get(Object.keys(data.attributes).length - 1).applicationResults
        initialViolationsCount += rule.result.violationRatio.failedChecks
      return initialViolationsCount

    getViolationsDifference:(currentViolations, previousViolations, initialViolations)->
      result = {}

      result.currentViolations = currentViolations
      initialCountDifference =  currentViolations - initialViolations
      result.initialCountDifferenceWithSign = initialCountDifference
      result.initialCountDifference = Math.abs(initialCountDifference)
      result.initialViolationsPercentage = if initialViolations == 0 then initialCountDifference else (result.initialCountDifference / initialViolations * 100).toFixed(2)

      previousCountDifference =  currentViolations - previousViolations
      result.previousCountDifferenceWithSign = previousCountDifference
      result.previousCountDifference = Math.abs(previousCountDifference)
      result.previousViolationsPercentage = if previousViolations == 0 then previousCountDifference else (result.previousCountDifference / previousViolations * 100).toFixed(2)
      return result

    getViolations: (data) ->
      currentViolations = @getViolationsCount(data, '0')
      previousViolations = @getViolationsCount(data, '1')
      initialViolations = @getInitialViolationsCount(data)
      return @getViolationsDifference(currentViolations, previousViolations, initialViolations)

  })

  EducationViolationsCount = BackboneWrapper.BaseModel.extend({

    url:()->
      @rules = 0 if @rules.length == 0
      url = REST_URL + @href + '/results?quality-indicators=('+@rules+')&select=(evolutionSummary)'
      if @snapshotId then url += '&snapshot-id=' + @snapshotId else url += '&snapshots=$all'

    initialize:(models, options)->
      @href = options.href
      @rules = options.ruleIds
      @snapshotId = options.snapshotId
      @type = options.type

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseModel.prototype.fetch.call(this, options)

    addedRemovedViolationsCount:(data)->
      result = []
      result.removedViolationsCount = 0
      result.addedViolationsCount = 0
      if @rules != 0
        for rule in data.get('0').applicationResults
          result.removedViolationsCount += rule.result.evolutionSummary.removedViolations
          result.addedViolationsCount += rule.result.evolutionSummary.addedViolations
      return result

    getSnapshotsData:(data)->
      snapshotsData = []
      for index of data.attributes
        snapshotsData.push({
          time: data.get(index).date.time,
          date: data.get(index).date.isoDate,
          violations: @getViolationsCount(data, index)
        })
      return snapshotsData

    getViolationsCount:(data, index)->
      violationsCount = 0
      if @type == 'added'
        for rule in data.get(index).applicationResults
          violationsCount += rule.result.evolutionSummary.addedViolations
      else
        for rule in data.get(index).applicationResults
          violationsCount += rule.result.evolutionSummary.removedViolations
      return violationsCount

    getInitialViolationsCount:(data)->
      initialViolationsCount = 0
      if @type == 'added'
        for index of data.attributes
          for rule in data.get(index).applicationResults
            initialViolationsCount += rule.result.evolutionSummary.addedViolations
      else
        for snapshot of data.attributes
          for rule in data.get(snapshot).applicationResults
            initialViolationsCount += rule.result.evolutionSummary.removedViolations
      return initialViolationsCount

    })

  return{
    EducationSummary
    EducationIssue
    EducationViolationsCount
    EducationTotalViolationsCount
  }

