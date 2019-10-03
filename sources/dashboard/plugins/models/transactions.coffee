transactions = (_, $, BackboneWrapper) ->

  Transaction = BackboneWrapper.BaseModel.extend({
    url:()->
      REST_URL + CENTRAL_DOMAIN + '/transactions/' + this.get('transactionId') + '/snapshots/' + this.get('snapshotId')

    initialize:(options = {})->
      if options.transactionId
        @set('id', options.transactionId)
        return @
      @set('id', options.href?.split('/')[2])
      return @
  })

  TransactionsListing = BackboneWrapper.BaseCollection.extend({
    model:Transaction
    url:()->
      REST_URL +  this.href + '/snapshots/' + this.snapshotId + '/transactions/' + this.context + '?startRow=' + this.startRow + '&nbRows=' + (this.nbRows + 1)

    initialize:(data, options = {})->
      this.href = options.href
      this.snapshotId = options.snapshotId;
      this.context = options.context or 60013
      this.nbRows = parseInt(options.nbRows) or 400
      this.startRow = options.startRow or 1

    parse:(data)->
      this.hasMore = data.length > this.nbRows;
      data.pop() if this.hasMore
      allData = []
      for model in @models
        allData.push model.toJSON()
      for d in data
        allData.push(d)
      return allData

    maxRisk:()->
      return @_maxRisk if @_maxRisk
      @_maxRisk = this.toJSON().reduce((max, transaction)->
        return transaction.transactionRiskIndex if transaction.transactionRiskIndex > max
        return max
      , 0)
      return @_maxRisk

    asCloud:()->
      return this.toJSON().map((transaction, index)->
        return {
          text:transaction.shortName or transaction.name
          weight:transaction.transactionRiskIndex or 0
          fullName:transaction.name
        }
      )

    asRows:(options = {})->
      maxRisk = @maxRisk()
      results =  this.toJSON().map((transaction, index)->
        return {
          columns:[
            transaction.name,
            transaction.transactionRiskIndex or 'n/a'
          ],
          type:"transactions"
          extra:{
            shortName:transaction.shortName
            longName:transaction.name
            transaction:transaction.id
            maxRisk:maxRisk
          }
          id:transaction.id
          selected:if options.transactionId then transaction.id == options.transactionId else index == 0
        }
      )
      return new BackboneWrapper.BaseCollection(results)
  })

  HEALTH_FACTORS = ["60011", "60012", "60013", "60014", "60016","60017"]
  TransactionResultsForBusinessCriteria = BackboneWrapper.BaseCollection.extend({
    url:()->
      # Domain/transactions/transactionId/results?quality-indicators=(...)&select=(violationRatio,evolutionSummary)&snapshot-ids=(...)
      rootURL = REST_URL + CENTRAL_DOMAIN +
        '/transactions/' + this.transactionId +
        '/results?quality-indicators=(business-criteria)' +
        '&select=(violationRatio,evolutionSummary)' +
        '&snapshot-ids=(' + this.snapshotId + ')'
      return rootURL

    initialize:(data, options)->
      this.transactionId = options.transactionId
      this.snapshotId = options.snapshotId

    asRows:(options)->
      options = _.extend({
          filter:true
          criticalViolationsAsResults:true
        }, options)

      results = this.toJSON()[0]?.applicationResults.map((measureResult)->
        summary = measureResult.transactionResults[0].result.evolutionSummary
        if options.criticalViolationsAsResults
          columns = [summary.addedCriticalViolations, summary.removedCriticalViolations, summary.totalCriticalViolations, measureResult.reference.name]
        else
          columns = [summary.addedViolations, summary.removedViolations, summary.totalViolations, measureResult.reference.name]
        return {
          columns:columns
          extra:
            businessCriterion:measureResult.reference.key
            active:columns[2] != 0
          selected:options.selectCriterion == measureResult.reference.key
        }
      ).filter((item)->
        return true unless options.filter
        return HEALTH_FACTORS.indexOf(item.extra.businessCriterion)>= 0
      ).sort((a, b)->
        diff = b.columns[2] - a.columns[2]
        return diff if diff != 0
        diff = b.columns[1] - a.columns[1]
        return diff if diff != 0
        return b.columns[0] - a.columns[0]
      )
      return new BackboneWrapper.BaseCollection(results)

  })

  ContributionCriterion = BackboneWrapper.BaseModel.extend({
    url: ->
      rootURL = REST_URL + CENTRAL_DOMAIN +
        '/quality-indicators/' + @get('criterion') +
        '/snapshots/' + @get('snapshotId')
      rootURL += '/base-quality-indicators' if @get('indirectContributors')
      return rootURL


    parse:(data)->
      if Array.isArray(data)
        data = {gradeContributors:data.map((item)->
          item.weight=item.compoundedWeight
          return item

        )}
      data.rules = data.gradeContributors.reduce((result, contributor)->
        result[contributor.key] = contributor
        return result
      , {})

      return data
  })

  TransactionResultsForTechnicalCriteria = BackboneWrapper.BaseCollection.extend({
    url:()->
      # Domain/transactions/transactionId/results?quality-indicators=(...)&select=(violationRatio,evolutionSummary)&snapshot-ids=(...)
      rootURL = REST_URL + CENTRAL_DOMAIN +
        '/transactions/' + this.transactionId +
        '/results?quality-indicators=(c:' + this.businessCriterion + ')' +
        '&select=(violationRatio,evolutionSummary)' +
        '&snapshot-ids=(' + this.snapshotId + ')'
      return rootURL

    initialize:(data, options)->
      this.transactionId = options.transactionId
      this.businessCriterion = options.businessCriterion
      this.snapshotId = options.snapshotId
      this.options = _.extend({
        criterion:options.businessCriterion
      }, options)
      this._contribution = new ContributionCriterion(this.options)

    getData:(options)->
      promise = $.when(this._contribution.fetch(), this.fetch());
      promise.done(options.success)
      promise.fail(options.error)
      return promise;

    asRows:(options)->
      options = _.extend({
          criticalViolationsAsResults:true
        }, options)
      ruleContributions = this._contribution.get('rules')
      results = this.toJSON()[0].applicationResults.map((measureResult)->
        summary = measureResult.transactionResults[0].result.evolutionSummary
        weight = ruleContributions[measureResult.reference.key].weight
        if options.criticalViolationsAsResults
          columns = [summary.addedCriticalViolations, summary.removedCriticalViolations, summary.totalCriticalViolations, measureResult.reference.name, weight]
        else
          columns = [summary.addedViolations, summary.removedViolations, summary.totalViolations, measureResult.reference.name, weight]
        return {
          columns:columns
          extra:
            technicalCriterion:measureResult.reference.key
            active:columns[2] != 0
          selected:options.selectCriterion == measureResult.reference.key
        }
      ).sort((a, b)->
        diff = b.columns[2] - a.columns[2]
        return diff if diff != 0
        diff = b.columns[1] - a.columns[1]
        return diff if diff != 0
        return b.columns[0] - a.columns[0]
      )
      results.unshift({
        columns:[
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
        selected: options.selectCriterion == 'all'
        notSelectable:false
      })
      return new BackboneWrapper.BaseCollection(results)

  })

  TransactionResultsForQualityRules = TransactionResultsForTechnicalCriteria.extend({

    url:()->
        # Domain/transactions/transactionId/results?quality-indicators=(...)&select=(violationRatio,evolutionSummary)&snapshot-ids=(...)
        rootURL = REST_URL + CENTRAL_DOMAIN + '/transactions/' + this.transactionId
        if 'all' == this.technicalCriterion
          rootURL += '/results?quality-indicators=(nc:' + this.businessCriterion + ',cc:' + this.businessCriterion + ')'
        else
          rootURL += '/results?quality-indicators=(c:' + this.technicalCriterion + ')'
        rootURL += '&select=(violationRatio,evolutionSummary)' +
          '&snapshot-ids=(' + this.snapshotId + ')'
        return rootURL

    initialize:(data, options)->
      this.transactionId = options.transactionId
      this.businessCriterion = options.businessCriterion
      this.technicalCriterion = options.technicalCriterion
      this.snapshotId = options.snapshotId
      indirect = 'all' == options.technicalCriterion
      this.options = _.extend({
        criterion:if indirect then options.businessCriterion else options.technicalCriterion
        indirectContributors:indirect
      }, options)
      this._contribution = new ContributionCriterion(this.options)

    asRows:(options)->
      options = _.extend({
          criticalViolationsAsResults:true
        }, options)
      ruleContributions = this._contribution.get('rules')
      appResults = this.toJSON()?[0]?.applicationResults
      return new BackboneWrapper.BaseCollection([]) unless appResults?
      results = appResults.filter((measureResult)->
          return 'technical-criteria' != measureResult.type
      ).map((measureResult)->
        summary = measureResult.transactionResults[0].result.evolutionSummary
        violationRatio = measureResult.transactionResults[0].result.violationRatio
        weight = ruleContributions[measureResult.reference.key].weight
        critical = ruleContributions[measureResult.reference.key].critical
        columns = [summary.addedViolations, summary.removedViolations, violationRatio.failedChecks, measureResult.reference.name, weight, critical]
        return {
          columns:columns
          extra:
            qualityRule:measureResult.reference.key
            type: measureResult.type
            active:columns[2] != 0
          data:[{
            label:'criticity'
            value: if critical then 1 else 0
            }]
          selected:options.selectCriterion == measureResult.reference.key
        }
      ).filter((a)->
        return a.columns[4] if options.criticalViolationsAsResults
        return true
      ).sort((a, b)->
        diff = b.columns[2] - a.columns[2]
        return diff if diff != 0
        diff = b.columns[1] - a.columns[1]
        return diff if diff != 0
        return b.columns[0] - a.columns[0]
      )
      return new BackboneWrapper.BaseCollection(results)
  })

  return {
    Transaction
    TransactionsListing
    TransactionResultsForBusinessCriteria
    TransactionResultsForTechnicalCriteria
    TransactionResultsForQualityRules
  }
