actionPlan = (_, BackboneWrapper) ->

  ActionPlanSummary = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @href + '/action-plan/summary'

    initialize:(data, options = {})->
      @href = options.href

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    computeSummary:()->
      result = {
        addedIssues:0
        pendingIssues:0
        solvedIssues:0
      }
      @each((item)->
        result.addedIssues += item.get('addedIssues')
        result.pendingIssues += item.get('pendingIssues')
        result.solvedIssues += item.get('solvedIssues')
      )
      result.totalIssues = result.addedIssues + result.pendingIssues + result.solvedIssues
      result

  })

  ActionPlanIssue = BackboneWrapper.BaseModel.extend({

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

  ActionPlanIssues = BackboneWrapper.BaseCollection.extend({
    model:ActionPlanIssue
    url:()->
      suffix = '?startRow=' + @startRow
      suffix += '&nbRows=' + @nbRows
      REST_URL + @href + '/action-plan/issues' + suffix

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
            model.get('remedialAction').tag
            model.get('remedialAction').status
            model.get('remedialAction')?.comment or ''
            model.get('rulePattern').name
            model.get('component').name
            model.get('remedialAction').dates.updated.time
            model.get('remedialAction').status + '_'  + model.getRuleId() + '/' + model.getComponentId()

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
    ActionPlanSummary
    ActionPlanIssues
  }
