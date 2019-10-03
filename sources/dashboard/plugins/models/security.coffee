security = (_, BackboneWrapper) ->

  SecurityOverview = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @applicationHref + '/results?quality-indicators=60016&snapshot-ids=' + @snapshotId

    initialize:(data, options)->
      @applicationHref = options.href
      @snapshotId = options.snapshotId[0]

  fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    computeSummary:(data)->
      return @models[0].get('applicationResults')[0].result.grade
  })

  SecurityTechnologies = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @applicationHref + '/results?quality-indicators=(60016)&select=(evolutionSummary)&technologies=($all)&snapshot-ids=' + @snapshotId

    initialize:(data, options = {})->
      @applicationHref = options.href
      @snapshotId = options.snapshotId[0]

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    computeSummary:()->
      technologies = @models[0].attributes.applicationResults[0].technologyResults
      result = []
      for tech in technologies
        value = {}
        value.technologyName = tech.technology
        value.grade = tech.result.grade
        value.totalCriticalViolations = tech.result.evolutionSummary.totalCriticalViolations
        result.push(value)
      return  result
  })

  return {
    SecurityOverview
    SecurityTechnologies
  }
