advancedSearch = (_, BackboneWrapper) ->

  CriteriaResult = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @href + '/results?quality-indicators=(business-criteria,technical-criteria,quality-rules)'

    initialize:(models, options)->
      @href = options.href

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    asRows: ()->
      results = []
      for model in @models[0].get('applicationResults')
        results.push({
          columns: [model.reference.name]
          extra: {
            model: model
          }
          id: model.reference.key
        })

      results_bc = _.filter(results, (result) ->
        if result.extra.model.type == 'business-criteria'
          result.type = "business-criteria"
          return result
      )
      results_tc =  _.filter(results, (result) ->
        if result.extra.model.type == 'technical-criteria'
          result.type = "technical-criteria"
          return result
      )
      results_qr = _.filter(results, (result) ->
        if result.extra.model.type == 'quality-rules'
          result.type = "quality-rules"
          return result
      )
      results = _.union(_.sortBy(results_bc, (criteria) => criteria.extra.model.reference.name)
      ,_.sortBy(results_tc, (criteria) => criteria.extra.model.reference.name)
      ,_.sortBy(results_qr, (criteria) => criteria.extra.model.reference.name)
      )
      @_collection = new BackboneWrapper.BaseCollection(results)
  })

  TechnologiesResult = CriteriaResult.extend({

    url:()->
      REST_URL + @href + '/results?&technologies=$all'

    asRows: ()->
      results = []
      for model in @models[0].get('applicationResults')[0].technologyResults
        results.push({
          columns: [model.technology]
          type: "technology"
          extra: {
            model: model
          }
        })
      @_collection = new BackboneWrapper.BaseCollection(results)

  })

  ModulesResult = CriteriaResult.extend({

    url:()->
      REST_URL + @href + '/results?&modules=$all'

    asRows: ()->
      results = []
      for model in @models[0].get('applicationResults')[0].moduleResults
        results.push({
          columns: [model.moduleSnapshot.name]
          type: "name"
          extra: {
            model: model
          }
        })
      @_collection = new BackboneWrapper.BaseCollection(results)

  })

  return{
    CriteriaResult
    TechnologiesResult
    ModulesResult
  }