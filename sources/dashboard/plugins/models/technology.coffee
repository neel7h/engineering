ListOfTechnologies = (_, BackboneWrapper) ->

  TechnologiesOverview = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @applicationHref + '/results?quality-indicators=('+@business+')&select=(evolutionSummary)&technologies=($all)&snapshot-ids=' + @snapshotId

    initialize:(data, options = {})->
      @applicationHref = options.href
      @snapshotId = options.snapshotId
      @ascending =  options.ascending
      @business = options.business

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    sort: (result) ->
      return result.sort((a,b) =>
        return 1 if a.violationsCount == 'n/a'
        return a.violationsCount - b.violationsCount if @ascending
        return b.violationsCount - a.violationsCount
      )

    computeSummary:(isCritical)->
      technologies = @models[0].attributes.applicationResults[0].technologyResults
      result = []
      for tech in technologies
        value = {}
        value.technologyName = tech.technology
        value.violationsCount = if isCritical then tech.result.evolutionSummary.totalCriticalViolations else tech.result.evolutionSummary.totalViolations
        value.gradeValue = tech.result.grade
        value.violationsCount = 'n/a' if value.gradeValue == undefined
        result.push(value)
      result = @sort(result)
      return  result
  })

  return {
    TechnologiesOverview
  }
