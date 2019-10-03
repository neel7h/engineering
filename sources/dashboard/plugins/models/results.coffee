
results = (_, BackboneWrapper, $) ->

  HEALTH_FACTORS = ["60011", "60012", "60013", "60014", "60016","60017"]

  BusinessCriteriaResults = BackboneWrapper.BaseModel.extend({
    initialize:(options)->
      @lastTwoSnapshots = new _BusinessCriteriaResultsForSnapshots(_.extend({snapshotIds:options.lastTwoSnapshotIds}, options)) # {module:options.module,snapshot:-2, href:options.href})

    getData:(options)->
      that = @
      $.when(@lastTwoSnapshots.fetch()).then(()->
        that.modelResults = that.getBusinessCriteriaResults()
        options.success.apply(that, arguments)

      ,()->
        options.error.apply(that, arguments)
      )

    downloadUrl:(filterHealthFactor)->
      return @lastTwoSnapshots.exportUrl(filterHealthFactor)

    getCriterionWithHigherCriticalViolations:(filterHealthFactors)->
      throw new Error('this function requires explicit definition of health factor filtering') unless filterHealthFactors?
      return @modelResults.results.filter((result)->
        return result if !filterHealthFactors
        return HEALTH_FACTORS.indexOf(result.reference.key) >= 0
      ).reduce((worst, result)->
          return result unless worst?
          return result if worst.result.evolutionSummary.totalCriticalViolations < result.result.evolutionSummary.totalCriticalViolations
          return worst
      ).reference.key


    getCriterionWithLowestGrade:(filterHealthFactors)->
      worst = @modelResults.results[0]
      for measureResult in @modelResults.results
        if (filterHealthFactors)
          continue if HEALTH_FACTORS.indexOf(measureResult.reference.key) == -1
        if measureResult.result.grade < worst.result.grade
          worst = measureResult
      worst.reference.key

    isAvailable:(business, filterHealthFactors )->
      for measureResult in @modelResults.results
        key = measureResult.reference.key
        continue if key != business
        if (filterHealthFactors)
          return false if HEALTH_FACTORS.indexOf(key) == -1
        return true
      return false

    getBusinessCriteriaResults: () ->
      return [] if !@lastTwoSnapshots.get('0')? and !@lastTwoSnapshots.get('1')?
      previousSnapshot = @lastTwoSnapshots.get('1')
      currentSnapshot = @lastTwoSnapshots.get('0')
      hasModule = @get('module')?
      hasTechnology = @get('technology')?

      model = {
        application:currentSnapshot.application
        snapshot:currentSnapshot.applicationSnapshot
        date:currentSnapshot.date
        previousSnapshot:previousSnapshot?.applicationSnapshot
        results:[]
      }
      if hasModule and hasTechnology
        for measureResult in currentSnapshot.applicationResults
          measureResult.result = measureResult.moduleResults[0].technologyResults?[0]?.result
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            previousMeasureResult.result = previousMeasureResult.moduleResults[0].technologyResults?[0]?.result
      if hasModule and !hasTechnology
        for measureResult in currentSnapshot.applicationResults
          measureResult.result = measureResult.moduleResults[0].result
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            previousMeasureResult.result = previousMeasureResult.moduleResults[0]?.result
      if hasTechnology and !hasModule
          for measureResult in currentSnapshot.applicationResults
            measureResult.result = measureResult.technologyResults?[0]?.result
          if previousSnapshot?
            for previousMeasureResult in previousSnapshot.applicationResults
              previousMeasureResult.result = previousMeasureResult.technologyResults?[0]?.result
      for measureResult in currentSnapshot.applicationResults
        continue if measureResult.type != "business-criteria"
        # continue unless measureResult.result.grade?
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            continue unless previousMeasureResult.result?
            if (previousMeasureResult.reference.key == measureResult.reference.key)
              measureResult.result.gradeDelta =  measureResult.result.grade - previousMeasureResult.result.grade
              measureResult.result.gradeVariation =  (measureResult.result.grade - previousMeasureResult.result.grade)/previousMeasureResult.result.grade if previousMeasureResult?.result?.grade?

              measureResult.result.totalCriticalViolationsDelta = measureResult.result.evolutionSummary.totalCriticalViolations - previousMeasureResult.result.evolutionSummary.totalCriticalViolations
              measureResult.result.totalCriticalViolationsVariation =  (measureResult.result.evolutionSummary.totalCriticalViolations - previousMeasureResult.result.evolutionSummary.totalCriticalViolations)/previousMeasureResult.result.evolutionSummary.totalCriticalViolations if previousMeasureResult?.result?.evolutionSummary.totalCriticalViolations?
              measureResult.result.totalViolationsDelta = measureResult.result.evolutionSummary.totalViolations - previousMeasureResult.result.evolutionSummary.totalViolations
              measureResult.result.totalViolationsVariation =  (measureResult.result.evolutionSummary.totalViolations - previousMeasureResult.result.evolutionSummary.totalViolations)/previousMeasureResult.result.evolutionSummary.totalViolations if previousMeasureResult?.result?.evolutionSummary.totalViolations?
              break
        measureResult.result.gradeVariation = 'NaN' unless measureResult.result.gradeVariation?
        measureResult.result.gradeBaselineVariation = 'NaN' unless measureResult.result.gradeBaselineVariation?
        measureResult.result.gradeDelta = 0 unless measureResult.result.gradeDelta?
        measureResult.result.totalCriticalViolationsBaselineVariation = 'NaN' unless measureResult.result.totalCriticalViolationsBaselineVariation?
        measureResult.result.totalCriticalViolationsVariation = 'NaN' unless measureResult.result.totalCriticalViolationsVariation?
        measureResult.result.totalViolationsBaselineVariation = 'NaN' unless measureResult.result.totalViolationsBaselineVariation?
        measureResult.result.totalViolationsVariation = 'NaN' unless measureResult.result.totalViolationsVariation?
        measureResult.result.totalCriticalViolationsDelta = 0 unless measureResult.result.totalCriticalViolationsDelta?
        model.results.push(measureResult)
      model

    getRiskIntroduced:(options = {business:'60017', critical:true})->
      for measureResult in @modelResults?.results
        if measureResult.reference.key == options.business
          if options.critical
            return {
              critical:true
              added:measureResult.result?.evolutionSummary?.addedCriticalViolations
              removed:measureResult.result?.evolutionSummary?.removedCriticalViolations
            }
          else
            return {
              critical:false
              added:measureResult.result?.evolutionSummary?.addedViolations
              removed:measureResult.result?.evolutionSummary?.removedViolations
            }
      return {critical:options.critical, added:'n/a', removed:'n/a'}

    asRows:(options)->
      results = []
      for measureResult in @modelResults.results
        active = true
        if options?.criticalViolationsAsResults
          columns = [
            if measureResult.result.evolutionSummary?.addedCriticalViolations? then measureResult.result.evolutionSummary.addedCriticalViolations else 'n/a',
            if measureResult.result.evolutionSummary?.removedCriticalViolations? then measureResult.result.evolutionSummary.removedCriticalViolations else 'n/a',
            measureResult.result.evolutionSummary.totalCriticalViolations,
            measureResult.result.totalCriticalViolationsVariation,
            #measureResult.result.totalCriticalViolationsBaselineVariation,
            measureResult.reference.name
          ]
          active = false if columns[2] == 0
        else
          columns = [
              if measureResult.result.evolutionSummary?.addedViolations? then measureResult.result.evolutionSummary.addedViolations else 'n/a',
              if measureResult.result.evolutionSummary?.removedViolations? then measureResult.result.evolutionSummary.removedViolations else 'n/a',
              measureResult.result.evolutionSummary.totalViolations,
              measureResult.result.totalViolationsVariation,
              #measureResult.result.totalViolationsBaselineVariation,
              measureResult.reference.name
          ]
          active = false if columns[2] == 0
        results.push({
          columns:columns
          extra:{
            businessCriterion:measureResult.reference.key
            active:active
          }
          selected: options?.selectCriterion == measureResult.reference.key
        })
      @_collection = new BackboneWrapper.BaseCollection(results)
      @_collection.comparator=(left,right)->
        # number of violations first, variation then
        l = left.get('columns')[2]
        ld = left.get('columns')[3]
        r = right.get('columns')[2]
        rd = right.get('columns')[3]
        # if variation is not same, we proceed with variation between values
        return 1 if isNaN(ld) and not isNaN(rd)
        return -1 if isNaN(rd) and not isNaN(ld)
        return r - l if isNaN(rd) and isNaN(ld)
        return ld - rd if r == l
        return r - l

      @_collection.sort()

      filter = if options?.filter? then options?.filter else true
      if filter
        @_filteredCollection = new BackboneWrapper.BaseCollection(@_collection.filter((item)->
          HEALTH_FACTORS.indexOf(item.get('extra').businessCriterion)>= 0
        ))
        return @_filteredCollection
      else
        return @_collection
  })

  _BusinessCriteriaResultsForSnapshots = BackboneWrapper.BaseModel.extend({
    url: ->
      module = @get('module')
      if module?
        rootURL = REST_URL + CENTRAL_DOMAIN + '/modules/' + module.getId() + '/results?quality-indicators=(business-criteria)&select=(evolutionSummary)&snapshot-ids=(' + @get('snapshotIds')+')'
      else
        rootURL = REST_URL + @get('href') + '/results?quality-indicators=(business-criteria)&select=(evolutionSummary)&snapshot-ids=('+ @get('snapshotIds')+')'

      technology = @get('technology')
      if technology?
        rootURL += '&technologies='+technology
      return rootURL

    exportUrl:(filterHealthFactor)->
      bc = 'business-criteria'
      bc =  HEALTH_FACTORS.join(',') if filterHealthFactor
      rootURL = REST_URL +
        @get('href') +
        '/results?quality-indicators=(' + bc + ')&select=(evolutionSummary)' +
        '&snapshot-ids=(' + @get('lastTwoSnapshotIds') + ')'+
        '&modules=($all)' +
        '&technologies=($all)' +
        '&unselect=(grade)&format=(snapshotsAsRows)&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      return rootURL

  })

  TechnicalCriteriaResults = BackboneWrapper.BaseModel.extend({

    initialize:(options)->
      @_technicalCriteria = new _TechnicalCriteriaResultsForBusinessCriterion({
        href:options.href
        businessCriterion:options.businessCriterion
        module:options.module
        technology:options.technology
        lastTwoSnapshotIds:options.lastTwoSnapshotIds
        snapshotId:options.snapshotId
      })

    getData:(options)->
      _arguments = arguments
      that = @
      fullOptions = _.extend({success:@defaultOptions.success, error:@defaultOptions.error}, options)
      $.when(@_technicalCriteria.fetch()).done(()->
        that._contribution = new ContributionCriterion({
          criterion:that._technicalCriteria.getBusinessCriterion()
          snapshotId:that._technicalCriteria.getSnapshotId()
          domain:that._technicalCriteria.getDomain()
        })
        that._contribution.fetch().done(()->
          fullOptions.success.apply(that, _arguments)
        ).fail(()->
          fullOptions.error.apply(that, _arguments)
        )
      )

    fetch:(options)->
      @getData(options)

    getBusinessCriteriaName:()->
      @_contribution.get('name')

    listCriteria:(options)->
      options = _.extend({criticalsOnly:true}, options)
      results = []
      for measureResult in @_technicalCriteria.get('results')
        key = measureResult.reference.key
        if options.criticalsOnly
          criticalViolationsForMetric = measureResult.result.evolutionSummary?.totalCriticalViolations or 0
        else
          criticalViolationsForMetric = measureResult.result.evolutionSummary?.totalViolations or 0
        name = measureResult.reference.name
        result ={
          value:criticalViolationsForMetric
          name:name
          key:key
        }
        if options.filter?
          results.push(result) unless options.filter(result)
        else
          results.push(result)

      results.sort((a,b)->
        if Math.abs(a.value - b.value) < 0.01
          return -1 if a.name < b.name
          return 1

        return a.value - b.value if 'ascending' == options.sortOrder
        return b.value - a.value
      )

      return results

    listContributors:()->
      results = {}
      for contributor in @_contribution.get('gradeContributors')
        results[contributor.key] = contributor
      results

    asRows:(options)->
      contributors = {}
      return new BackboneWrapper.BaseCollection([]) unless @_contribution?

      return new BackboneWrapper.BaseCollection([]) unless @_contribution.get('gradeContributors')?
      for contributor in @_contribution.get('gradeContributors')
        contributors[contributor.key] = contributor
      results = []
      allTechnicalItem = {
        columns:[
          'n/a'
          'n/a'
          'n/a'
          'n/a'
          'All Rules...'
          'n/a'
        ]
        extra:{
          technicalCriterion:'all'
          addedHighestValue: false
          removedHighestValue: false
        }
        selected: options?.selectCriterion == 'all'
        notSelectable:false
      }
      results.push(allTechnicalItem)
      singleSnapshot = !@_technicalCriteria.get('previousSnapshot')
      for measureResult in @_technicalCriteria.get('results')
        contributor = contributors[measureResult.reference.key]
        continue unless contributor?
        if options?.criticalViolationsAsResults
          criticalViolationVariation = measureResult.result.criticalViolationVariation
          columns = [
            if measureResult.result.evolutionSummary?.addedCriticalViolations? then measureResult.result.evolutionSummary.addedCriticalViolations else 'n/a'
            if measureResult.result.evolutionSummary?.removedCriticalViolations? then measureResult.result.evolutionSummary.removedCriticalViolations else 'n/a'
            if measureResult.result.evolutionSummary?.totalCriticalViolations? then measureResult.result.evolutionSummary.totalCriticalViolations else 0
            if criticalViolationVariation? then criticalViolationVariation else if singleSnapshot or criticalViolationVariation == undefined then 'n/a' else 0
            measureResult.reference.name
            contributor.weight
          ]
        else
          violationVariation = measureResult.result.violationVariation
          columns = [
            if measureResult.result.evolutionSummary?.addedViolations? then measureResult.result.evolutionSummary.addedViolations else 'n/a'
            if measureResult.result.evolutionSummary?.removedViolations? then measureResult.result.evolutionSummary.removedViolations else 'n/a'
            if measureResult.result.evolutionSummary?.totalViolations? then measureResult.result.evolutionSummary.totalViolations else 0
            if violationVariation? then violationVariation else if singleSnapshot or violationVariation == undefined then 'n/a' else 0
            measureResult.reference.name
            contributor.weight
          ]
        active = columns[2] != 0
        results.push({
          columns:columns
          extra:{
            technicalCriterion:measureResult.reference.key
            isGone:measureResult.isGone
            active:active
          }
          selected: options?.selectCriterion == measureResult.reference.key
          notSelectable:measureResult.isGone
        })
      @_collection = new BackboneWrapper.BaseCollection(results)
      @_collection.comparator=(left,right)->
        # FIXME rename sorting
        return -1 if left.get('extra').technicalCriterion == 'all'
        return 1 if right.get('extra').technicalCriterion == 'all'
        leftValue = left.get('columns')[5]
        leftVariation = left.get('columns')[3]
        leftScore = left.get('columns')[2]
        rightValue = right.get('columns')[5]
        rightVariation = right.get('columns')[3]
        rightScore = right.get('columns')[2]
        if leftScore == rightScore
          if Math.abs(leftVariation - rightVariation) < 0.0001
            return rightValue - leftValue
          return -1 if isNaN(leftVariation) and not isNaN(rightVariation)
          return 1 if isNaN(rightVariation) and not isNaN(leftVariation)
          return rightVariation - leftVariation
        return -1 if isNaN(leftScore) and not isNaN(rightScore)
        return 1 if isNaN(rightScore) and not isNaN(leftScore)
        return rightScore - leftScore

      @_collection.sort()
      @_collection
  })


  _TechnicalCriteriaResultsForBusinessCriterion = BackboneWrapper.BaseModel.extend({
    url: ->
      module = @get('module')
      snapshotIds = @get('lastTwoSnapshotIds')
      snapshotIds = @get('lastTwoSnapshotIds').join(',') if snapshotIds.length > 1
      if module?
        rootURL = REST_URL + CENTRAL_DOMAIN + '/modules/' + module.getId() + '/results?quality-indicators=(c:'+@get('businessCriterion')+')&select=(evolutionSummary)&snapshot-ids='+ snapshotIds
      else
        rootURL= REST_URL + @get('href')+'/results?quality-indicators=(c:'+@get('businessCriterion')+')&select=(evolutionSummary)&snapshot-ids=' + snapshotIds
      technology = @get('technology')
      rootURL += '&technologies='+technology if technology?
      return rootURL

    exportUrl:()->
      snapshotIds = @get('lastTwoSnapshotIds')
      snapshotIds = @get('lastTwoSnapshotIds').join(',') if snapshotIds.length > 1
      rootURL = REST_URL +
        @get('href') +
        '/results?quality-indicators=(c:'+@get('businessCriterion')+')&select=(evolutionSummary)'+
        '&snapshot-ids=(' + snapshotIds + ')' +
        '&modules=($all)' +
        '&technologies=($all)' +
        '&unselect=(grade)&format=(snapshotsAsRows)&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      return rootURL

    getBusinessCriterion:()->
      @get('businessCriterion')

    getDomain:()->
      @get('href').split('/')?[0] or ''

    getSnapshotId:()->
      @get('snapshotId')

    parse: (response) ->
      return [] if response.length == 0
      currentSnapshot = response[0]
      previousSnapshot = response[1]
      hasModule = @get('module')?
      hasTechnology = @get('technology')?

      model = {
        application:currentSnapshot.application
        snapshot:currentSnapshot.applicationSnapshot
        date:currentSnapshot.date
        previousSnapshot:previousSnapshot?.applicationSnapshot
        results:[]
      }
      # TESTME FIXME can we factorize this piece of code so it is reused everywhere we do this? + add unit tests
      if hasModule and hasTechnology
        for measureResult in currentSnapshot.applicationResults
          if measureResult.moduleResults?[0]?.technologyResults?[0]?.result?
            measureResult.result = measureResult.moduleResults[0].technologyResults[0]?.result
          else
            measureResult.result = {} unless measureResult.result?
            measureResult.result?.grade = undefined
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            if previousMeasureResult.moduleResults?[0]?.technologyResults?[0]?.result?
              previousMeasureResult.result = previousMeasureResult.moduleResults[0].technologyResults[0]?.result
            else
              previousMeasureResult.result = {} unless previousMeasureResult.result?
              previousMeasureResult.result?.grade = undefined
      if hasModule and !hasTechnology
        for measureResult in currentSnapshot.applicationResults
          measureResult.result = measureResult.moduleResults[0].result
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            previousMeasureResult.result = previousMeasureResult.moduleResults[0].result
      if !hasModule and hasTechnology
        for measureResult in currentSnapshot.applicationResults
          if measureResult.technologyResults?[0]?.result
            measureResult.result = measureResult.technologyResults[0]?.result
          else
            measureResult.result.grade = undefined
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            if previousMeasureResult.technologyResults?[0]?.result
              previousMeasureResult.result = previousMeasureResult.technologyResults[0]?.result
            else
              previousMeasureResult.result.grade = undefined

      currentSnapshotCriteria = {}
      for measureResult in currentSnapshot.applicationResults
        continue if measureResult.type != "technical-criteria"
        continue unless measureResult.result.grade?
        currentSnapshotCriteria[measureResult.reference.key] = true
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            if (previousMeasureResult.reference.key == measureResult.reference.key)
              previousVal = previousMeasureResult.result.evolutionSummary?.totalCriticalViolations or 0
              if previousVal == 0
                measureResult.result.criticalViolationVariation = 'NaN'
              else
                currentVal = measureResult.result.evolutionSummary?.totalCriticalViolations or 0
                measureResult.result.criticalViolationVariation = (currentVal - previousVal)/previousVal
              previousVal = previousMeasureResult.result.evolutionSummary?.totalViolations or 0
              if previousVal == 0
                measureResult.result.violationVariation = 'NaN'
              else
                currentVal = measureResult.result.evolutionSummary?.totalViolations or 0
                measureResult.result.violationVariation = (currentVal - previousVal)/previousVal
        model.results.push(measureResult)

      if previousSnapshot?
        for previousMeasureResult in previousSnapshot.applicationResults
          continue if previousMeasureResult.result.grade == 'NaN' or !previousMeasureResult.result.grade?
          unless currentSnapshotCriteria[previousMeasureResult.reference.key]
            previousMeasureResult.isGone = true
            previousMeasureResult.result.grade = 'NaN'
            previousMeasureResult.result.gradeVariation = 'NaN'
            previousMeasureResult.result.criticalViolationVariation = 'NaN'
            previousMeasureResult.result.gradeDelta = 0
            _.keys(previousMeasureResult.result.evolutionSummary).forEach((key)-> previousMeasureResult.result.evolutionSummary[key] = 0)
            currentSnapshot.applicationResults.forEach((qr)->
              if qr.reference.key == previousMeasureResult.reference.key
                previousMeasureResult.result.evolutionSummary = qr.result.evolutionSummary
              )
            model.results.push(previousMeasureResult)
      return model

  })

  ContributionCriterion = BackboneWrapper.BaseModel.extend({
    url: ->
      root = REST_URL+@get('domain')+'/quality-indicators/'+@get('criterion')+'/snapshots/'+@get('snapshotId')
      return root + '/base-quality-indicators' if @get('indirectContributors')
      return root

    parse:(data)->
      return {indirectContributions:data} if Array.isArray(data)
      return data

  })

  _IndirectGradeContributionCriterion = BackboneWrapper.BaseCollection.extend({
    url: ->
      REST_URL+@domain+'/quality-indicators/'+@criterion+'/snapshots/'+@snapshotId+'/base-quality-indicators'

    initialize:(data, options)->
      @criterion=options.criterion
      @snapshotId=options.snapshotId
      @domain=options.domain

  })

  QualityRulesResults = BackboneWrapper.BaseModel.extend({
    initialize:(options)->
      if options.technicalCriterion == 'all'
        @_qualityRules = new _QualityRuleResultsForBusinessCriterion(_.extend({},options))
      else
        @_qualityRules = new _QualityRuleResultsForTechnicalCriterion(_.extend({},options))

    getData:(options)->
      _arguments = arguments
      that = @
      fullOptions = _.extend({success:@defaultOptions.success, error:@defaultOptions.error}, options)
      @_qualityRules.fetch().done(()->
        that._contribution = new ContributionCriterion({
          criterion:that._qualityRules.getTechnicalCriterion()
          snapshotId:that._qualityRules.getSnapshotId()
          domain:that._qualityRules.getDomain()
          indirectContributors:'all' == that.get('technicalCriterion')
        })
        that._contribution.fetch().done(()->
          fullOptions.success.apply(that, _arguments)
        ).fail(()->
          fullOptions.error.apply(that, arguments)
        )
      )

    fetch:(options)->
      @getData(options)

    exportUrl:()->
      return @_qualityRules.exportUrl()

    asRows:(options)->
      return @_collection if @_collection?
      contributors = {}
      return new BackboneWrapper.BaseCollection([]) unless @_contribution?

      if 'all' == @get('technicalCriterion')
        return new BackboneWrapper.BaseCollection([]) unless @_contribution.get('indirectContributions')?
        for contributor in @_contribution.get('indirectContributions')
          contributors[contributor.key] = {
            weight:contributor.compoundedWeight
            key:contributor.key
            critical:contributor.critical
          }
      else
        return new BackboneWrapper.BaseCollection([]) unless @_contribution.get('gradeContributors')?
        for contributor in @_contribution.get('gradeContributors')
          contributors[contributor.key] = contributor

      results = []
      for measureResult, index in @_qualityRules.get('results')
        contributor = contributors[measureResult.reference.key]
        if contributor?
          if options.onlyViolations
            columns = [
              if measureResult.result.evolutionSummary?.addedViolations? then measureResult.result.evolutionSummary.addedViolations else 'n/a'
              if measureResult.result.evolutionSummary?.removedViolations? then measureResult.result.evolutionSummary.removedViolations else 'n/a'
              measureResult.result.violations
              measureResult.result.violationsVariation
              measureResult.reference.name
              contributor.weight
              contributor.critical
            ]
            active = columns[2] != 0
          else
            columns = [
              measureResult.result.grade
              measureResult.result.gradeVariation
              measureResult.reference.name
              measureResult.result.violations
              measureResult.result.violationsVariation
              contributor.weight
              contributor.critical
            ]
            active = columns[2] < 4
          results.push({
            columns:columns
            className:if isNaN(measureResult.result.grade) then "non-clickable" else ''
            extra:{
              qualityRule:measureResult.reference.key
              type:measureResult.type
              isNew:measureResult.isNew
              isGone:measureResult.isGone
              active:active
            }
            data:[
              {label:'criticity', value:if contributor.critical then 1 else 0}
            ]

            selected: options?.selectCriterion == measureResult.reference.key
            notSelectable:measureResult.isGone
          })
      @_collection = new BackboneWrapper.BaseCollection(results)
      @_collection.comparator=(left,right)->
        leftValue = left.get('columns')[5]
        leftVariation = left.get('columns')[3]
        leftScore = left.get('columns')[2]
        rightValue = right.get('columns')[5]
        rightVariation = right.get('columns')[3]
        rightScore = right.get('columns')[2]
        if options == 'rulesWithHighestImprovementOpportunities'
          leftScore = left.get('columns')[1]
          rightScore = right.get('columns')[1]

        if leftScore == rightScore
          if Math.abs(leftVariation - rightVariation) < 0.0001
            return rightValue - leftValue
          return 1 if isNaN(leftVariation) and not isNaN(rightVariation)
          return -1 if isNaN(rightVariation) and not isNaN(leftVariation)
          return rightVariation - leftVariation
        return 1 if isNaN(leftScore) and not isNaN(rightScore)
        return -1 if isNaN(rightScore) and not isNaN(leftScore)
        return rightScore - leftScore
      @_collection.sort()
      @_collection
  })

  _QualityRuleResultsForTechnicalCriterion = BackboneWrapper.BaseModel.extend({
    url: ->
      module = @get('module')
      if module?
        rootURL = REST_URL + CENTRAL_DOMAIN + '/modules/' + module.getId() + '/results?select=(violationRatio,evolutionSummary)&quality-indicators=(c:'+@get('technicalCriterion')+')&snapshot-ids=('+@get('lastTwoSnapshotIds')+')'
      else
        rootURL = REST_URL + @get('href')+'/results?select=(violationRatio,evolutionSummary)&quality-indicators=(c:'+@get('technicalCriterion')+')&snapshot-ids=('+@get('lastTwoSnapshotIds')+')'
      technology = @get('technology')
      if technology?
        rootURL += '&technologies='+technology
      return rootURL

    exportUrl:()->
      rootUrl = REST_URL +
        @get('href')+
        '/results?select=(violationRatio,evolutionSummary)&quality-indicators=(c:'+@get('technicalCriterion')+')'+
        '&snapshot-ids=('+ @get('lastTwoSnapshotIds') + ')' +
        '&modules=($all)' +
        '&technologies=($all)' +
        '&unselect=(grade)&format=(snapshotsAsRows)&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      return rootUrl

    getTechnicalCriterion:()->
      @get('technicalCriterion')

    getDomain:()->
      @get('href').split('/')?[0] or ''

    getSnapshotId:()->
      @get('snapshotId')

    parse: (response) ->
      return [] if response.length == 0
      currentSnapshot = response[0]
      previousSnapshot = response[1]
      hasModule = @get('module')?
      hasTechnology = @get('technology')?
      model = {
        application:currentSnapshot.application
        snapshot:currentSnapshot.applicationSnapshot
        date:currentSnapshot.date
        previousSnapshot:previousSnapshot?.applicationSnapshot
        results:[]
      }
      if hasModule and hasTechnology
        for measureResult in currentSnapshot.applicationResults
          if measureResult.moduleResults?[0]?.technologyResults?[0]?.result?
            measureResult.result = measureResult.moduleResults[0].technologyResults[0]?.result
          else
            measureResult.result = {} unless measureResult.result?
            measureResult.result?.grade = undefined
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            if previousMeasureResult.moduleResults?[0]?.technologyResults?[0]?.result?
              previousMeasureResult.result = previousMeasureResult.moduleResults[0].technologyResults[0]?.result
            else
              previousMeasureResult.result = {} unless previousMeasureResult.result?
              previousMeasureResult.result?.grade = undefined
      if hasModule and !hasTechnology
        for measureResult in currentSnapshot.applicationResults
          measureResult.result = measureResult.moduleResults[0].result
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            previousMeasureResult.result = previousMeasureResult.moduleResults[0].result
      if !hasModule and hasTechnology
        for measureResult in currentSnapshot.applicationResults
          if measureResult.technologyResults?[0]?.result
            measureResult.result = measureResult.technologyResults[0]?.result
          else
            measureResult.result.grade = undefined
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            if previousMeasureResult.technologyResults?[0]?.result
              previousMeasureResult.result = previousMeasureResult.technologyResults[0]?.result
            else
              previousMeasureResult.result.grade = undefined


      currentSnapshotRules = {}
      for measureResult in currentSnapshot.applicationResults
        continue unless measureResult.result.grade?
        currentSnapshotRules[measureResult.reference.key] = true
        if previousSnapshot?
          existRule = false
          for previousMeasureResult in previousSnapshot.applicationResults
            if (previousMeasureResult.reference.key == measureResult.reference.key)
              existRule = true
              measureResult.result.gradeDelta =  measureResult.result.grade - previousMeasureResult.result.grade
              measureResult.result.gradeVariation =  (measureResult.result.grade - previousMeasureResult.result.grade)/previousMeasureResult.result.grade
              if measureResult.result.violationRatio? and previousMeasureResult.result.violationRatio?
                if previousMeasureResult.result.violationRatio.failedChecks != 0
                  measureResult.result.violationsVariation =
                    (measureResult.result.violationRatio.failedChecks - previousMeasureResult.result.violationRatio.failedChecks)/previousMeasureResult.result.violationRatio.failedChecks
              break
          measureResult.isNew = true if !existRule
        measureResult.result.gradeVariation = 'NaN' unless measureResult.result.gradeVariation?
        measureResult.result.violationsVariation = 'NaN' unless measureResult.result.violationsVariation?
        measureResult.result.gradeDelta = 0 unless measureResult.result.gradeDelta?
        if measureResult.result.violationRatio?
          measureResult.result.violations = measureResult.result.violationRatio.failedChecks
        else
          measureResult.result.violations = 'n/a'
        model.results.push(measureResult)
      if previousSnapshot?
        for previousMeasureResult in previousSnapshot.applicationResults
          continue if previousMeasureResult.result.grade == 'NaN' or !previousMeasureResult.result.grade?
          unless currentSnapshotRules[previousMeasureResult.reference.key]
            previousMeasureResult.isGone = true
            previousMeasureResult.result.grade = 'NaN'
            previousMeasureResult.result.gradeVariation = 'NaN'
            previousMeasureResult.result.gradeDelta = 0
            previousMeasureResult.result.violations = 'n/a'
            previousMeasureResult.result.violationsVariation = 'NaN'
            currentSnapshot.applicationResults.forEach((qr)->
              if qr.reference.key == previousMeasureResult.reference.key
                previousMeasureResult.result.evolutionSummary = qr.result.evolutionSummary
              )
            model.results.push(previousMeasureResult)
      return model
  })

  _QualityRuleResultsForBusinessCriterion = BackboneWrapper.BaseModel.extend({
    url: ()->
      if @get('module')?
        rootURL = REST_URL + CENTRAL_DOMAIN + '/modules/' + @get('module').getId() + '/results?select=(violationRatio,evolutionSummary)&quality-indicators=(cc:' + @get('business')+',nc:'+ @get('business')+')&snapshot-ids=('+@get('lastTwoSnapshotIds')+')'
      else
        rootURL = REST_URL + SELECTED_APPLICATION_HREF + '/results?select=(violationRatio,evolutionSummary)&quality-indicators=(cc:' + @get('business')+',nc:'+ @get('business')+')&snapshot-ids=('+@get('lastTwoSnapshotIds')+')'

      technology = @get('technology')
      if technology?
        rootURL += '&technologies='+technology

      return rootURL

    exportUrl:()->
      rootUrl = REST_URL +
        @get('href')+
        '/results?select=(violationRatio,evolutionSummary)&quality-indicators=(cc:' + @get('business')+',nc:'+ @get('business')+')'+
        '&snapshot-ids=(' + @get('lastTwoSnapshotIds') + ')' +
        '&modules=($all)' +
        '&technologies=($all)' +
        '&unselect=(grade)&format=(snapshotsAsRows)&content-type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      return rootUrl


    getTechnicalCriterion:()->
      @get('business')

    getDomain:()->
      @get('href').split('/')?[0] or ''

    getSnapshotId:()->
      @get('snapshotId')

    parse: (response)->
      return [] if response.length == 0
      currentSnapshot = response[0]
      previousSnapshot = response[1]
      hasModule = @get('module')?
      hasTechnology = @get('technology')?
      model = {
        application:currentSnapshot.application
        snapshot:currentSnapshot.applicationSnapshot
        date:currentSnapshot.date
        previousSnapshot:previousSnapshot?.applicationSnapshot
        results:[]
      }
      if hasModule and hasTechnology
        for measureResult in currentSnapshot.applicationResults
          if measureResult.moduleResults?[0]?.technologyResults?[0]?.result?
            measureResult.result = measureResult.moduleResults[0].technologyResults[0]?.result
          else
            measureResult.result = {} unless measureResult.result?
            measureResult.result?.grade = undefined
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            if previousMeasureResult.moduleResults?[0]?.technologyResults?[0]?.result?
              previousMeasureResult.result = previousMeasureResult.moduleResults[0].technologyResults[0]?.result
            else
              previousMeasureResult.result = {} unless previousMeasureResult.result?
              previousMeasureResult.result?.grade = undefined
      if hasModule and !hasTechnology
        for measureResult in currentSnapshot.applicationResults
          measureResult.result = measureResult.moduleResults[0].result
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            previousMeasureResult.result = previousMeasureResult.moduleResults[0].result
      if !hasModule and hasTechnology
        for measureResult in currentSnapshot.applicationResults
          if measureResult.technologyResults?[0]?.result
            measureResult.result = measureResult.technologyResults[0]?.result
          else
            measureResult.result.grade = undefined
        if previousSnapshot?
          for previousMeasureResult in previousSnapshot.applicationResults
            if previousMeasureResult.technologyResults?[0]?.result
              previousMeasureResult.result = previousMeasureResult.technologyResults[0]?.result
            else
              previousMeasureResult.result.grade = undefined

      currentSnapshotRules = {}
      for measureResult in currentSnapshot.applicationResults
        continue unless measureResult.result.grade?
        continue if measureResult.type == 'technical-criteria'
        currentSnapshotRules[measureResult.reference.key] = true
        if previousSnapshot?
          existRule = false
          for previousMeasureResult in previousSnapshot.applicationResults
            if (previousMeasureResult.reference.key == measureResult.reference.key)
              existRule = true
              measureResult.result.gradeDelta =  measureResult.result.grade - previousMeasureResult.result.grade
              measureResult.result.gradeVariation =  (measureResult.result.grade - previousMeasureResult.result.grade)/previousMeasureResult.result.grade
              if measureResult.result.violationRatio? and previousMeasureResult.result.violationRatio?
                if previousMeasureResult.result.violationRatio.failedChecks != 0
                  measureResult.result.violationsVariation =
                    (measureResult.result.violationRatio.failedChecks - previousMeasureResult.result.violationRatio.failedChecks)/previousMeasureResult.result.violationRatio.failedChecks
              break
          measureResult.isNew = true if !existRule
        measureResult.result.gradeVariation = 'NaN' unless measureResult.result.gradeVariation?
        measureResult.result.violationsVariation = 'NaN' unless measureResult.result.violationsVariation?
        measureResult.result.gradeDelta = 0 unless measureResult.result.gradeDelta?
        if measureResult.result.violationRatio?
          measureResult.result.violations = measureResult.result.violationRatio.failedChecks
        else
          measureResult.result.violations = 'n/a'
        model.results.push(measureResult)

      if previousSnapshot?
        for previousMeasureResult in previousSnapshot.applicationResults
          continue if previousMeasureResult.result.grade == 'NaN' or !previousMeasureResult.result.grade?
          unless currentSnapshotRules[previousMeasureResult.reference.key]
            previousMeasureResult.isGone = true
            previousMeasureResult.result.grade = 'NaN'
            previousMeasureResult.result.gradeVariation = 'NaN'
            previousMeasureResult.result.gradeDelta = 0
            previousMeasureResult.result.violations = 'n/a'
            previousMeasureResult.result.violationsVariation = 'NaN'
            currentSnapshot.applicationResults.forEach((qr)->
              if qr.reference.key == previousMeasureResult.reference.key
                previousMeasureResult.result.evolutionSummary = qr.result.evolutionSummary
              )
            model.results.push(previousMeasureResult)
      return model
  })


  _ConfigurationRules = BackboneWrapper.BaseModel.extend({
    url: ()->
      REST_URL + @domain + '/configuration/snapshots/' + @snapshotId + '/quality-' + @type

    initialize:(models, options)->
      @domain = options.domain
      @snapshotId = options.snapshotId
      @type = options.type

    parse:(data)->
      result = {}
      for sample in data
        result[sample.key] = sample.name
      result
  })

  _ComponentDetails = BackboneWrapper.BaseModel.extend({
    url: ()->
      REST_URL + @domain + '/tree-nodes/'+ @node + '/snapshots/' + @snapshotId

    initialize:(models, options)->
      @domain = options.domain
      @snapshotId = options.snapshotId
      @node = options.node

    parse:(data)->
      data
  })

  QualityRuleWithViolationForComponent = BackboneWrapper.BaseCollection.extend({
    url: ()->
      if @rulePattern
        rootURL = @selectedNode + '/violations-summary?rule-pattern=' + @rulePattern
        rootURL += '&status=' + @selectedStatus if @selectedStatus
        return rootURL
      else
        return @selectedNode + '/violated-rule-patterns?business-criterion=' + @businessCriterion

    initialize:(models, options)->
      @selectedNode = options.selectedNode
      @rulePattern = options.rulePattern
      @selectedStatus = options.selectedStatus
      @businessCriterion = options.businessCriterion

  })

  QualityRulesWithViolations = BackboneWrapper.BaseModel.extend({

    initialize:(options)->
      @rules = new _ConfigurationRules([], {
        domain: options.domain
        snapshotId: options.snapshotId
        type: 'rules'
      })
      @measures = new _ConfigurationRules([], {
        domain: options.domain
        snapshotId: options.snapshotId
        type: 'measures'
      })
      @distributions = new _ConfigurationRules([], {
        domain: options.domain
        snapshotId: options.snapshotId
        type: 'distributions'
      })
      @ruleViolations = new QualityRuleWithViolationForComponent([],{
        selectedNode: options.selectedNode
        businessCriterion: options.businessCriterion
      })
      @contribution = new _IndirectGradeContributionCriterion([], {
        criterion:options.businessCriterion
        snapshotId:options.snapshotId
        domain:options.domain
      })

    getData:(options)->
      $.when(@rules.fetch(), @measures.fetch(), @distributions.fetch(), @ruleViolations.fetch(),@contribution.fetch()).then(()->
        options.success.apply(this, arguments)
      ,()->
        options.error.apply(this, arguments)
      )

    asRows:(options)->
      rules = _.extend({}, @rules.attributes, @measures.attributes, @distributions.attributes)
      contributors = {}
      for rule in @contribution.models
        contributors[rule.get('key')] = rule.toJSON()

      results = []
      for ruleViolation in @ruleViolations.models
        grId = ruleViolation.get('rulePattern').href.split('/')[2]
        contributor = contributors[grId]

        continue unless contributor?
        continue if options?.onlyCritical and !contributor.critical
        results.push({
          columns:[
            rules[grId]
            ruleViolation.get('violations').number
            contributor.compoundedWeight
            contributor.critical
          ]
          extra:{
            qualityRule:grId
            critical: contributor.critical
          }
          selected: options?.selectCriterion == grId
          data:[
            {label:'criticity', value:if contributor.critical then 1 else 0}
          ]
        })
      @_collection = new BackboneWrapper.BaseCollection(results)
      @_collection
  })

  TechnicalContext = BackboneWrapper.BaseModel.extend({
    initialize:(options)->
      @context = new _ComponentDetails([], {
        domain: options.domain
        snapshotId: options.snapshotId
        node: options.node
      })

    getData:(options)->
      $.when(@context.fetch()).then(()->
        options.success.apply(this, arguments)
      ,()->
        options.error.apply(this, arguments)
      )

    getContextResult:() ->
      return @context.get('component')

    asRows:(options)->
      contexts = _.extend({}, @context.attributes)
      results = @getContextResult()
      return unless results?
      details = []

      if results.codeLines != null && results.codeLines != undefined
        details.push({
            columns:[
              'Number of code lines',
              results.codeLines
            ]
        })
      if results.commentLines != null && results.commentLines != undefined
        details.push({
          columns:[
            'Number of comment lines',
            results.commentLines
          ]
        })
      if results.commentedCodeLines != null && results.commentedCodeLines != undefined
        details.push({
          columns:[
            'Number of commented code lines',
            results.commentedCodeLines
          ]
        })
      if results.coupling != null && results.coupling != undefined
        details.push({
          columns:[
            'Coupling',
            results.coupling
          ]
        })
      if results.cyclomaticComplexity != null && results.cyclomaticComplexity != undefined
        details.push({
          columns:[
            'Cyclomatic Complexity',
            results.cyclomaticComplexity
          ]
        })
      if results.distinctOperands != null && results.distinctOperands != undefined
        details.push({
          columns:[
            'Distinct Operands',
            results.distinctOperands
          ]
        })
      if results.distinctOperators != null && results.distinctOperators != undefined
        details.push({
          columns:[
            'Distinct Operators',
            results.distinctOperators
          ]
        })
      if results.essentialComplexity != null && results.essentialComplexity != undefined
        details.push({
          columns:[
            'Essential Complexity',
            results.essentialComplexity
          ]
        })
      if results.fanIn != null && results.fanIn != undefined
        details.push({
          columns:[
            'Fan In',
            results.fanIn
          ]
        })
      if results.fanOut != null && results.fanOut != undefined
        details.push({
          columns:[
            'Fan Out',
            results.fanOut
          ]
        })
      if results.halsteadProgramLength != null && results.halsteadProgramLength != undefined
        details.push({
          columns:[
            'Halstead Program Length',
            results.halsteadProgramLength
          ]
        })
      if results.halsteadProgramVocabulary != null && results.halsteadProgramVocabulary != undefined
        details.push({
          columns:[
            'Halstead Program Vocabulary',
            results.halsteadProgramVocabulary
          ]
        })
      if results.halsteadVolume != null && results.halsteadVolume != undefined
        details.push({
          columns:[
            'Halstead Volume',
            results.halsteadVolume
          ]
        })
      if results.integrationComplexity != null && results.integrationComplexity != undefined
        details.push({
          columns:[
            'Integration Complexity',
            results.integrationComplexity
          ]
        })
      if results.ratioCommentLinesCodeLines != null && results.ratioCommentLinesCodeLines != undefined
        details.push({
          columns:[
            'Ratio of CommentLines to CodeLines',
            results.ratioCommentLinesCodeLines
          ]
        })
      @_collection = new BackboneWrapper.BaseCollection(details)
      @_collection
  })

  ComputingDetails = BackboneWrapper.BaseModel.extend({

    initialize:(options)->
      @options = _.extend({},options)
      @_violationRatios = new _ViolationRatios(options)
      @_modules = new _Modules(options)
      @_violationSummary = new _violationSummary(options)

    getData:(options)->
      _arguments = arguments
      that = @
      fullOptions = _.extend({success:@defaultOptions.success, error:@defaultOptions.error}, options)
      $.when(@_violationRatios.fetch(),@_violationSummary.fetch(),@_modules.fetch()).then(()->
        fullOptions.success.apply(that, _arguments)
      , ()->
        fullOptions.error.apply(that, _arguments)
      )

    getViolationRatio:()->
      module = @get('moduleHref')
      unless module?
        return @getApplicationResult().result?.violationRatio
      return @getModuleResult()?.result?.violationRatio

    getViolationSummary:()->
      return @_violationSummary.get('number')

    getApplicationResult:() ->
      return @_violationRatios.get('applicationResults')?[0]

    getModuleResult:()->
      return @_violationRatios.get('applicationResults')?[0].moduleResults?[0]

    asRows:(options = {})->
      details = []
      results = @getApplicationResult()

      return unless results?
      if options.moduleFilter?
        for module in results.moduleResults
          if module.moduleSnapshot.href.indexOf(options.moduleFilter) == 0
            moduleResult = module.result
            details.push({columns:[
              module.moduleSnapshot.name,
              moduleResult.violationRatio?.totalChecks,
              moduleResult.violationRatio?.failedChecks,
              moduleResult.violationRatio?.ratio
            ]})
      else
        # total
        totalResults = results.result
        details.push({columns:[
            'Total',
            totalResults.violationRatio?.totalChecks,
            totalResults.violationRatio?.failedChecks,
            totalResults.violationRatio?.ratio
          ]
          ,className:"computing-total"
        })
        # iterate over modules
        for module in results.moduleResults
          moduleResult = module.result
          details.push({columns:[
            module.moduleSnapshot.name,
            moduleResult.violationRatio?.totalChecks,
            moduleResult.violationRatio?.failedChecks,
            moduleResult.violationRatio?.ratio
          ]})
        for module in @_modules.models
          href = module.get('href')
          found = false
          for resultModule in results.moduleResults
            if href == resultModule.moduleSnapshot.href
              found = true
              break
          details.push({columns:[module.get('name'),-1,-1,-1]}) if !found

      @_collection = new BackboneWrapper.BaseCollection(details)
      @_collection

  })

  _violationSummary = BackboneWrapper.BaseModel.extend({
    url:()->
      if @moduleHref?
        rootURL = REST_URL + @moduleHref + '/snapshots/' + @snapshotId + '/violations-summary?rule-pattern=' + @qualityRuleId
      else
        rootURL = REST_URL + @applicationHref + '/snapshots/' + @snapshotId + '/violations-summary?rule-pattern=' + @qualityRuleId
      rootURL +=  '&technologies=' + @technologies if @technologies
      rootURL +=  '&status=' + @selectedStatus if @selectedStatus
      return rootURL

    initialize:(options)->
      @applicationHref = options.applicationHref
      @moduleHref = options.moduleHref
      @snapshotId = options.snapshotId
      @technologies = options.technology
      @qualityRuleId = options.qualityRuleId
      @selectedStatus = options.selectedStatus

    parse:(data)->
      return data.totalViolations if @selectedStatus == null
      return data.addedViolations if @selectedStatus == "added"
      return data.updatedViolations if @selectedStatus == "updated"
      return data.unchangedViolations if @selectedStatus == "unchanged"
  })

  _Modules = BackboneWrapper.BaseCollection.extend({
    url:()->
      if @moduleHref?
        REST_URL + @moduleHref
      else
        REST_URL + @applicationHref + '/snapshots/' + @snapshotId + '/modules'

    initialize:(options)->
      @applicationHref = options.applicationHref
      @moduleHref = options.moduleHref
      @snapshotId = options.snapshotId

  })

  _ViolationRatios = BackboneWrapper.BaseModel.extend({
    url:() ->
      rootURL = REST_URL + if @get('moduleHref')? then @get('moduleHref') else @get('applicationHref')
      rootURL += '/snapshots/' + @get('snapshotId') + '/results?quality-indicators=' + @get('qualityRuleId') + '&select=violationRatio&modules=($all)'
      rootURL += '&technologies=(' + @get('technology') + ')' if @get('technology')?
      return rootURL

    parse:(data)->
      result = data[0]
      appResults = result.applicationResults[0]
      technologyFilter = @get('technology')
      if (technologyFilter)
        # FIXMe encodeURIComponent could be applied in url methods only (?)
        technologyFilter = decodeURIComponent(technologyFilter)
        appResults.result = {
          grade : -1
          violationRatio: {
            failedChecks: 0
            ratio: 0
            successfulChecks: 0
            totalChecks: 0
          }
        }
        for technologyResult in appResults.technologyResults
          if technologyResult.technology == technologyFilter
            appResults.result = technologyResult.result
            break
        for moduleResult in appResults.moduleResults
          moduleResult.result = {
            grade : -1
            violationRatio: {
              failedChecks: 0
              ratio: 0
              successfulChecks: 0
              totalChecks: 0
            }
          }
          for technologyResult in moduleResult.technologyResults
            if technologyResult.technology == technologyFilter
              moduleResult.result = technologyResult.result
              break
      return result

  })

  Distribution = BackboneWrapper.BaseModel.extend({

    initialize:(options) ->
      @distribution = new ContributionCriterion({
        criterion:options.qualityDistributionId
        snapshotId:options.snapshotId
        domain:options.domain
      })

      @_veryHigh = new _ObjectsDistributionOneCategory({
        applicationHref:options.applicationHref
        moduleHref:options.moduleHref
        snapshotId:options.snapshotId
        categoryRank:1
        qualityDistributionId:options.qualityDistributionId
        businessCriterion:options.businessCriterion
      })

      @_high = new _ObjectsDistributionOneCategory({
        applicationHref:options.applicationHref
        moduleHref:options.moduleHref
        snapshotId:options.snapshotId
        categoryRank:2
        qualityDistributionId:options.qualityDistributionId
        businessCriterion:options.businessCriterion
      })

      @_average = new _ObjectsDistributionOneCategory({
        applicationHref:options.applicationHref
        moduleHref:options.moduleHref
        snapshotId:options.snapshotId
        categoryRank:3
        qualityDistributionId:options.qualityDistributionId
        businessCriterion:options.businessCriterion
      })

      @_low = new _ObjectsDistributionOneCategory({
        applicationHref:options.applicationHref
        moduleHref:options.moduleHref
        snapshotId:options.snapshotId
        categoryRank:4
        qualityDistributionId:options.qualityDistributionId
        businessCriterion:options.businessCriterion
      })

    getData:(options)->
      @distribution.fetch().then(()->
        options.success.apply(this, arguments)
      ,()->
        options.error.apply(this, arguments)
      )

    getCategoryModel:(index)->
      categories = @distribution.get('categories')
      switch(index)
        when 1
          return {title:categories?[0].name, model:@_veryHigh}
        when 2
          return {title:categories?[1].name, model:@_high}
        when 3
          return {title:categories?[2].name, model:@_average}
        when 4
          return {title:categories?[3].name, model:@_low}

    getCategory:(index)->
      categories = @distribution.get('categories')
      switch(index)
        when 1
          return {title:categories?[0].name, rows:@_veryHigh.asRows()}
        when 2
          return {title:categories?[1].name, rows:@_high.asRows()}
        when 3
          return {title:categories?[2].name, rows:@_average.asRows()}
        when 4
          return {title:categories?[3].name, rows:@_low.asRows()}

  })

  _ObjectsDistributionOneCategory = BackboneWrapper.BaseCollection.extend({
    url:() ->
      # TODO add pagination parameters
      @startRow = if @startRow? then @startRow else 1
      @nbRows = if @nbRows? then @nbRows else 10
      if @moduleHref?
        REST_URL + @moduleHref + '/snapshots/'+ @snapshotId + '/components/' + @qualityDistributionId + '/' + @categoryRank + '?business-criterion=' + @businessCriterion + '&startRow='+ @startRow+'&nbRows='+@nbRows
      else
        REST_URL + @applicationHref + '/snapshots/'+ @snapshotId + '/components/' + @qualityDistributionId + '/' + @categoryRank + '?business-criterion=' + @businessCriterion + '&startRow='+ @startRow+'&nbRows='+@nbRows

    initialize:(options)->
      @applicationHref = options.applicationHref
      @moduleHref = options.moduleHref
      @snapshotId = options.snapshotId
      @categoryRank = options.categoryRank
      @qualityDistributionId = options.qualityDistributionId
      @businessCriterion = options.businessCriterion

    asRows:(options)->
      maxRows = options?.nbRows or @models.length
      results = []
      index = 0
      for object in this.models
        break if index++ >= maxRows
        pri = object.get('propagationRiskIndex')
        results.push({columns:[
          object.get('name')
#          if pri? then pri else -1
          object.get('status')
        ]})

      @_collection = new BackboneWrapper.BaseCollection(results)
      @_collection

    parse:(data)->
      allData = []
      if @_collection?
        for model in @models
          allData.push(model.toJSON())
      for d in data
        allData.push(d)
      allData
  })

  RulesViolationsForABusinessCriterion = BackboneWrapper.BaseCollection.extend({

    initialize: (models, options)->
      @options = JSON.parse(JSON.stringify(options))
      @variation = options.variation
      @criticals = new _RulesViolationsForABusinessCriterion([], _.extend({},options,{criticals:true}))
      unless options.criticalsOnly
        @nonCriticals = new _RulesViolationsForABusinessCriterion([], _.extend({},options,{criticals:false}))

    getData:(options)->
      $.when(@criticals.fetch(), @nonCriticals?.fetch()).done(()=>
        for model in @criticals.models
          model.set('critical',true)
          @add(model)
        if @nonCriticals?
          for model in @nonCriticals.models
            model.set('critical',false)
            @add(model)
        options.success()
      ).fail(()->
        options.error?()
      )

    comparator: (a, b)->
      attribute = switch(@variation)
        when 'added' then 'addedViolations'
        when 'removed' then 'removedViolations'
        else 'violationsRatio'
      return b.get(attribute) - a.get(attribute)

    hasPreviousSnapshot:()->
      return @criticals.hasPreviousSnapshot

    getIndicator: ()->
      return @criticals.businessName

    filterRules:()->
      attribute = switch(@variation)
        when 'added' then 'addedViolations'
        when 'removed' then 'removedViolations'
        else 'violationsRatio'
      return @filter((model) ->
        model.get(attribute) > 0
      ).map((model)->
        return model.toJSON();
      )
  })

  _RulesViolationsForABusinessCriterion = BackboneWrapper.BaseCollection.extend({
    url: ()->
      contributors = if @criticals then ',cc:' else ',nc:'
      REST_URL + SELECTED_APPLICATION_HREF + '/results?select=(violationRatio,evolutionSummary)&quality-indicators=(' + @business + contributors + @business + ')&snapshot-ids=(' + @lastTwoSnapshotIds + ')'

    initialize: (models, options)->
      @business = options.business
      @criticals = options.criticals
      @lastTwoSnapshotIds = options.lastTwoSnapshotIds

    _processRules: (snapshot)->
      rules = {}
      return {rules} unless snapshot?
      for sample in snapshot.applicationResults
        switch sample.type
          when 'business-criteria'
            businessCriteria = sample.reference.name
          when 'quality-rules'
            continue unless sample.result.violationRatio? # skipp incomplete elements
            rules[sample.reference.key] = {
              name: sample.reference.name
              key: sample.reference.key
              violations: sample.result.violationRatio.failedChecks
              addedViolations: sample.result.evolutionSummary.addedViolations
              removedViolations: sample.result.evolutionSummary.removedViolations
            }
          else
            continue
      return {rules, businessCriteria}

    parse: (data)->
      currentSnapshotData = @_processRules(data[0])
      previousSnapshotData = @_processRules(data[1])
      @businessName = currentSnapshotData?.businessCriteria
      @hasPreviousSnapshot = data[1]?

      results = []
      for key of currentSnapshotData.rules
        ruleState = currentSnapshotData.rules[key]
        previousRuleState = previousSnapshotData.rules[key]
        continue unless previousRuleState?.violations?
        if previousRuleState.violations == 0
#            dont display the one does not have previous snapshot
          continue
        else
          ruleState.violationsRatio = (ruleState.violations - previousRuleState.violations)/previousRuleState.violations
        ruleState.violations -= previousRuleState.violations
        ruleState.business = @business
        results.push(ruleState)
      return results
  })

  TopRulesViolationsResults = BackboneWrapper.BaseCollection.extend({
    url:()->
      rootURL = REST_URL + SELECTED_APPLICATION_HREF
      rootURL +='/results?select=(violationRatio,evolutionSummary)&quality-indicators=(cc:' + @business + ',nc:' + @business + ')&snapshot-ids=(' + @lastTwoSnapshotIds + ')'
      return rootURL

    initialize: (models, options)->
      @business = options.business
      @lastTwoSnapshotIds = options.lastTwoSnapshotIds

    parse:(snapshotResults)->
      result = []
      if snapshotResults.length > 0
        data = snapshotResults[0].applicationResults.reduce((data, result)=>
          if 'quality-rules' == result.type
            data[result.reference.key] = _.extend({violationsRatio:'NaN', business:@business},result.reference, result.result.violationRatio, result.result.evolutionSummary)
          return data
        ,{})
      if snapshotResults.length > 1
        snapshotResults[1].applicationResults.forEach((previousResult)->
          if 'quality-rules' == previousResult.type
            currentResult = data[previousResult.reference.key]
            return unless currentResult?
            return unless previousResult.result.violationRatio?
            currentResult.violationsRatio = (currentResult.failedChecks - previousResult.result.violationRatio.failedChecks) / previousResult.result.violationRatio.failedChecks
        )
      for key,value of data
        value.hasNoFailedChecks = true unless value.failedChecks?
        result.push(value)
      return result

    hasPreviousSnapshot:()->
      return @model.length > 1

    filterRules:(options)->
        attribute = switch(options.filterCriterion)
          when 'added' then 'addedViolations'
          when 'removed' then 'removedViolations'
          else 'violationsRatio'

        return @models.filter((model)->
          return false if options.onlyCritical and model.get('critical') == false
          if options.reportType == 'rulesWithLargestDecreasePercentageViolations'
            return model.get(attribute) < 0
          else
            return model.get(attribute) > 0
        ).map((model)->
          return model.toJSON();
        ).sort((a, b)->
          if options.reportType == 'rulesWithLargestDecreasePercentageViolations'
            difference = a[attribute] - b[attribute]
            if 0 == difference
              return a.failedChecks - b.failedChecks
            return difference
          else
            difference = b[attribute] - a[attribute]
            if 0 == difference
              return b.failedChecks - a.failedChecks
            return difference
        )

    asRows:(rules, filterCriterion)->
      attribute = switch(filterCriterion)
        when 'added' then 'addedViolations'
        when 'removed' then 'removedViolations'
        else 'violationsRatio'

      results = []
      index = 0
      for model in rules
        continue if model[attribute] == Infinity
        break if index++ > 49
        results.push({
          columns:[
            model.name
            model[attribute]
            model.key
          ]
          extra:{
            model:model
          }
        })
      @_collection = new BackboneWrapper.BaseCollection(results)
  })

  ModuleResultsWithCriticity = BackboneWrapper.BaseCollection.extend({
    url:()->
      REST_URL + @snapshotHref + '/results?modules=$all&select=(evolutionSummary)&quality-indicators=(' + @business + ')'

    initialize:(options)->
      @snapshotHref = options.snapshotHref
      @business = options.business

    getIndicator:()->
      application = @models[0]
      result = application?.get('applicationResults')?[0]
      return result?.reference?.name

    listModules:(options)->
      options = _.extend({criticalsOnly:true}, options);
      results = []
      application = @models[0]
      return result unless application?
      for moduleResult in application.get('applicationResults')[0].moduleResults
        results.push({
          href:moduleResult.moduleSnapshot.href
          name:moduleResult.moduleSnapshot.name
          criticalViolations:moduleResult.result.evolutionSummary?.totalCriticalViolations
          violations:moduleResult.result.evolutionSummary?.totalViolations or 0
        })
      results.sort((a,b)->
        return b.criticalViolations - a.criticalViolations if options.criticalsOnly
        return b.violations - a.violations
      )
      return results

  })

  ListOfBusinessCriteria = BackboneWrapper.BaseCollection.extend({
    initialize:(options)->
      @_businessRules = new _ListOfBusinessCriteria (_.extend({},options))

    getData:(options)->
      that = @
      $.when(@_businessRules.fetch()).then(()->
        options.success.apply(that, arguments)
      ,()->
        options.error.apply(that, arguments)
      )
  })

  _ListOfBusinessCriteria = BackboneWrapper.BaseModel.extend({
    url:()->
      REST_URL + @get('href') + '/business-criteria'
  })

  TagResults = BackboneWrapper.BaseCollection.extend({

    initialize:(options)->
      @_tagResults = new _tagResults (_.extend({},options))

    getData:(options)->
      that = @
      $.when(@_tagResults.fetch()).then(()->
        options.success.apply(that, arguments)
      ,()->
        options.error.apply(that, arguments)
      )
    })

  _tagResults = BackboneWrapper.BaseModel.extend({
    url:()->
      REST_URL + @get('href') + '/results/?quality-standards=('+@get('tags')+')&snapshot-ids=('+@get('snapshotId')+')'
  })

  TagsDetailResults = BackboneWrapper.BaseCollection.extend({
    initialize:(options)->
      @_tagsDetailResults = new _tagsDetailResults (_.extend({},options))

    getData:(options)->
      that = @
      $.when(@_tagsDetailResults.fetch()).then(()->
        options.success.apply(that, arguments)
      ,()->
        options.error.apply(that, arguments)
      )
  })

  _tagsDetailResults = BackboneWrapper.BaseModel.extend({
    url:()->
      REST_URL + @get('href') + '/results/?quality-indicators=(c:'+@get('tags')+')&select=(violationRatio)&snapshot-ids=('+@get('snapshotId')+')'
  })

  ViolationsIndex = BackboneWrapper.BaseModel.extend({

    url:()->
      REST_URL + @href + '/violations-index'

    initialize:(options)->
      @href = options.href.split('/')[0]

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseModel.prototype.fetch.call(this, options)

  })

  return {
    ListOfBusinessCriteria
    BusinessCriteriaResults
    ContributionCriterion
    ComputingDetails
    Distribution
    ModuleResultsWithCriticity
    QualityRulesResults
    QualityRulesWithViolations
    QualityRuleWithViolationForComponent
    RulesViolationsForABusinessCriterion
    TechnicalCriteriaResults
    TopRulesViolationsResults
    TechnicalContext
    TagsDetailResults
    TagResults
    ViolationsIndex
  }
