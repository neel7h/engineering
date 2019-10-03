reportGenerator = (_, BackboneWrapper) ->

  IndustryComplianceReports = BackboneWrapper.BaseCollection.extend({

    url:()->
      REST_URL + @domainId + '/reports?template=' +  @templateId + '.docx&snapshot-id=' + @snapshotId

    initialize:(data, options = {})->
      @domainId = options.domainId
      @snapshotId = options.snapshotId
      @templateId = options.templateId

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

  })

  ComplexityFanOutReports = BackboneWrapper.BaseCollection.extend({

    url:()->
      suffix = '&startRow=' + @startRow
      suffix += '&nbRows=' + 50
      REST_URL + @href + '/snapshots/' + @snapshotId + '/components/' + @componentId + '?properties=(cyclomaticComplexity,fanOut)' + suffix + '&order=(desc(cyclomaticComplexity),desc(fanOut))'

    initialize:(models, options)->
      @href = options.href
      @status = options.status
      @snapshotId = options.snapshotId
      @componentId = options.business if options.business?
      @startRow = options.startRow or 1
      @nbRows = options.nbRows or 50

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
            model.get('name')
            model.get('cyclomaticComplexity')
            model.get('fanOut')
          ]
          extra:{
            model:model
          }
        })
      @_collection = new BackboneWrapper.BaseCollection(results)
  })

  LowDocumentationReports = ComplexityFanOutReports.extend(

    url:()->
      suffix = '&startRow=' + @startRow
      suffix += '&nbRows=' + 50
      REST_URL + @href + '/snapshots/' + @snapshotId + '/components/' + @componentId + '?properties=(cyclomaticComplexity,ratioCommentLinesCodeLines)' + suffix + '&order=(desc(cyclomaticComplexity),desc(ratioCommentLinesCodeLines))'

    asRows:(options)->
      maxRows = options?.nbRows or @models.length
      results = []
      index = 0
      for model in @models
        break if index++ >= maxRows
        results.push({
          columns:[
            model.get('name')
            model.get('cyclomaticComplexity')
            model.get('ratioCommentLinesCodeLines')
          ]
          extra:{
            model:model
          }
        })
      @_collection = new BackboneWrapper.BaseCollection(results)
  )

  CorrectedViolationsReport = ComplexityFanOutReports.extend(

    url:()->
      suffix = '?startRow=' + @startRow
      suffix += '&nbRows=' + @nbRows
      if @status == 'added'
        REST_URL + @href + '/snapshots/' + @snapshotId + '/violations' + suffix + '&status=added'
      else
        REST_URL + @href + '/snapshots/' + @snapshotId + '/removed-violations' + suffix

    asRows:(options)->
      maxRows = options?.nbRows or @models.length
      results = []
      index = 0
      for model in @models
        break if index++ >= maxRows
        results.push({
          columns:[
            model.get('rulePattern').name
            model.get('component').name
            model.get('diagnosis').status
            model.get('rulePattern').href.split('/')[2] + '/' + model.get('component').href.split('/')[2]
          ]
          extra:{
            model:model
          }
        })
      @_collection = new BackboneWrapper.BaseCollection(results)
  )

  CorrectedAndRemovedViolationCount = ComplexityFanOutReports.extend(
    url:()->
      REST_URL + @href + '/snapshots/' + @snapshotId + '/results?select=evolutionSummary&quality-indicators=' + @componentId

    parse:(data)->
      results = [
        addedViolation: data[0].applicationResults[0].result.evolutionSummary.addedViolations,
        removedViolation: data[0].applicationResults[0].result.evolutionSummary.removedViolations
      ]
      return results
  )

  ImprovementGap = ComplexityFanOutReports.extend(

    url:()->
      REST_URL + @href + '/snapshots/' + @snapshotId + '/results?quality-indicators=(quality-rules)&unselect=(grade)&select=(improvementGap)&order=(desc(improvementGap),asc(rule-pattern-name))'

    asRows:(options)->
      results = []
      index = 0
      for model in @models[0].get('applicationResults')
        break if index++ >= 50
        continue if Math.round(model.result.improvementGap) == 0
        results.push({
          columns:[
            model.reference.name
            model.result.improvementGap
            model.reference.key
          ]
          extra:{
            model:model
          }
        })
      @_collection = new BackboneWrapper.BaseCollection(results)
  )

  return {
    IndustryComplianceReports
    ComplexityFanOutReports
    LowDocumentationReports
    CorrectedViolationsReport
    CorrectedAndRemovedViolationCount
    ImprovementGap
  }