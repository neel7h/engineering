###
  Provide the models to access the object violations

  REST-API documentation : http://confluence/display/PdtInt/Portfolio+API
###
violations = (_, BackboneWrapper) ->


  Violation = BackboneWrapper.BaseModel.extend({

    getObjectId:()->
      component = @get('component')
      console.warn 'no component associated to violation, your database may not be up to date' unless component?
      component?.href.split('/')[2]

    getRuleId:()->
      return @get('rulePattern').href.split('/')[2]

  })

  Violations = BackboneWrapper.BaseCollection.extend({
    model:Violation
    url:() ->
      startRow = if @params?.startRow? then '&startRow=' + @params.startRow else ''
      nbRows = if @params?.nbRows? then '&nbRows=' + @params.nbRows else ''
      status = if @params?.status? then '&status=' + @params.status else ''
      rootURL = REST_URL  + if @params.moduleHref? then @params?.moduleHref  else @params?.applicationHref
      rootURL += '/snapshots/' + @params?.snapshotId + '/violations?rule-pattern=' + @params?.qualityRuleId + '&business-criterion=' + @params?.businessCriterionId
      technology = @params?.technology
      if technology?
        rootURL += '&technologies='+technology
      rootURL += startRow + nbRows + status

    initialize:(models, options)->
      @params = options

    size:()->
      @models.length

    parse:(data)->
      allData = []
      for model in @models
        allData.push model.toJSON()
      for d in data
        allData.push(d)
      allData

    asRows:(options)->
      maxRows = options?.nbRows or @models.length
      view = options?.view
      violations = []
      index = 0
      for violation in @models
        break if index++ >= maxRows
        componentId = violation.getObjectId()
        pri = violation.get('component')?.propagationRiskIndex
        columns = [
          if violation.get('exclusionRequest')? then violation.get('exclusionRequest') else if violation.get('remedialAction')? then violation.get('remedialAction')  else '-'
          violation.get('component')?.name,
          if pri? then pri else -1
          violation.get('diagnosis')?.status
          100
        ]
        if view == 'applicationInvestigation'
          columns.pop()

        violations.push({
          columns:columns
          extra:{
            componentId: componentId
            model:violation
          }
          id: componentId
          selected: componentId? and options?.selectedComponent == componentId
        })
      @_collection = new BackboneWrapper.BaseCollection(violations)

    maxRisk:()->
      return @_maxRisk if @_maxRisk
      max = 0
      for violation in @models
        pri = violation.get('component')?.propagationRiskIndex or -1
        max = pri if max < pri
      @_maxRisk = max
      return max
  })

  ComponentViolations = Violations.extend({
    url:() ->
      startRow = if @params?.startRow? then '&startRow=' + @params.startRow else ''
      # startRow += 1
      nbRows = if @params?.nbRows? then '&nbRows=' + @params.nbRows else ''
      status = if @params?.status? then '&status=' + @params.status else ''
      REST_URL + CENTRAL_DOMAIN + '/tree-nodes/' + @params.component + '/snapshots/' + @params?.snapshotId + '/violations?rule-pattern=' + @params?.qualityRuleId + '&business-criterion=' + @params?.businessCriterionId + startRow + nbRows + status
  })

  TotalViolations = Violations.extend({
    model:Violation
    url:()->
      return REST_URL  + @params?.applicationHref + '/snapshots/' + @params?.snapshotId + '/results?select=(evolutionSummary)'

    parse:(data)->
      {totalViolationsCount: data[0].applicationResults[0].result.evolutionSummary.totalViolations}
  })

  AdvanceSearchViolations = Violations.extend({
    model:Violation
    url:()->
      startRow = if @params?.startRow? then '&startRow=' + @params.startRow else ''
      nbRows = if @params?.nbRows? then '&nbRows=' + @params.nbRows else ''
      rootURL = REST_URL  + @params?.applicationHref + '/snapshots/' + @params?.snapshotId + '/indexed-violations?'
      if @params.subString?
        rootURL += if @params.subString == "" then '' else 'object-fullname=' + encodeURIComponent(@params.subString) + '&mode=term'
      else ''

      if @params.filterSearch? and (@params.filterSearch['business-criteria'].length or @params.filterSearch['technical-criteria'].length or @params.filterSearch['quality-rules'].length)
        rootURL+= '&rule-pattern=('
        for bc in @params.filterSearch['business-criteria']
          rootURL += "bqi:#{bc},"
        for tc in @params.filterSearch['technical-criteria']
          rootURL += "c:#{tc},"
        for qr in @params.filterSearch['quality-rules']
          rootURL += "#{qr},"
        rootURL += ')'

      if @params.filterSearch? and @params.filterSearch['critical'].length
        if @params.filterSearch['critical'].length < 2
          rootURL+= '&critical='
          if @params.filterSearch['critical'][0] == 'critical' then rootURL += "true" else rootURL += "false"

      filters = [
        {filterName: 'technology', urlKey: 'technologies' },
        {filterName: 'name', urlKey: 'modules'},
        {filterName: 'weight', urlKey: 'weight'},
        {filterName: 'status', urlKey: 'status'},
        {filterName: 'transactions', urlKey: 'transactions'}
      ]

      filters.map((filter)=> rootURL += @filterSearchData(filter))

      rootURL += startRow + nbRows
      return rootURL

    initialize:(models, options)->
      @params = options

    filterSearchData:(filter)->
      rootURL = ''
      if @params.filterSearch? and @params.filterSearch[filter.filterName].length
        rootURL+= "&#{filter.urlKey}=("
        for value,index in @params.filterSearch[filter.filterName]
          if index == 0 then rootURL += "#{value}" else rootURL += ",#{value}"
        rootURL += ')'
        return rootURL
      return rootURL

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    parse:(data)->
      allData = []
      for d in data.violations
        allData.push(d)
      allData.push({number:data.number}) if data.violations.length
      return allData

    asRows:(options)->
      maxRows = options?.nbRows or @models.length
      violations = []
      index = 0
      for violation in @models
        break if index++ >= maxRows or violation.get('number')?
        componentId = violation.getObjectId()
        ruleId = violation.getRuleId()
        columns = [
          if violation.get('exclusionRequest')? then violation.get('exclusionRequest') else if violation.get('remedialAction')? then violation.get('remedialAction')  else '-'
          violation.get('component')?.name,
          if violation.get('rulePattern')?.name then violation.get('rulePattern').name
          violation.get('diagnosis')?.status
          violation.getRuleId() + '/' + componentId
        ]

        violations.push({
          columns:columns
          extra:{
            componentId:componentId
            model:violation
          }
          componentId:componentId
          ruleId: ruleId
          selected: componentId? and options?.selectedComponent == componentId
        })
      @_collection = new BackboneWrapper.BaseCollection(violations)
  })

  TransactionViolations = Violations.extend({
    url:()->
      startRow = if @params?.startRow? then '&startRow=' + @params.startRow else ''
      nbRows = if @params?.nbRows? then '&nbRows=' + @params.nbRows else ''
      status = if @params?.status? then '&status=' + @params.status else ''
      # 	{Domain}/transactions/{TransactionID}/snapshots/{SnapshotID}/violations{?Parameters}

      rootURL = REST_URL  + CENTRAL_DOMAIN + '/transactions/' + @params.transactionId
      rootURL += '/snapshots/' + @params?.snapshotId + '/violations?rule-pattern=' + @params?.qualityRuleId + '&business-criterion=' + @params?.businessCriterionId
      rootURL += startRow + nbRows + status
      return rootURL
  })

  TransactionViolationsRatio = Violations.extend({
    initialize:(@params,options)->
      @_violationRatio = new _violationRatio(options)
      @_totalViolationsCount = new _totalViolationsCount(options)

    getData:(options)->
      $.when(@_violationRatio.fetch(),@_totalViolationsCount.fetch()).then(()->
        options.success.apply(this, arguments)
      ,()->
        options.error.apply(this, arguments)
      )
    getViolationSummary:()->
      return @_violationRatio.get('number')

    getAllViolationsCount:()->
      return @_totalViolationsCount.get('failedChecks')

  })

  _violationRatio = BackboneWrapper.BaseModel.extend({
    url:()->
      rootURL = REST_URL  + CENTRAL_DOMAIN + '/transactions/' + @transactionId + '/snapshots/' + @snapshotId + '/violations-summary?rule-pattern=' + @qualityRuleId
      rootURL += '&status=' + @selectedStatus if @selectedStatus
      return rootURL

    initialize:(options)->
      @transactionId = options.transactionId
      @snapshotId = options.snapshotId
      @qualityRuleId = options.qualityRuleId
      @selectedStatus = options.selectedStatus

    parse:(data)->
      return data.totalViolations if @selectedStatus == null
      return data.addedViolations if @selectedStatus == "added"
      return data.updatedViolations if @selectedStatus == "updated"
      return data.unchangedViolations if @selectedStatus == "unchanged"

  })

  _totalViolationsCount = BackboneWrapper.BaseModel.extend({
    url:()->
      rootURL = REST_URL  + CENTRAL_DOMAIN + '/transactions/' + @transactionId + '/results/?snapshot-ids=(' + @snapshotId + ')' + '&quality-indicators=' + @qualityRuleId + '&select=violationRatio'

    initialize:(options)->
      @transactionId = options.transactionId
      @snapshotId = options.snapshotId
      @qualityRuleId = options.qualityRuleId

    parse:(data)->
      return data[0].applicationResults[0].transactionResults[0].result?.violationRatio

  })

  AddedRemovedViolations = BackboneWrapper.BaseCollection.extend({
    model:Violation
    url:()->
      REST_URL + @href + '/violations?rule-pattern=('+@ruleIds+')&status=(added,deleted)&startRow=1&nbRows=100001'

    initialize:(models, options)->
      @params = options
      @ruleIds = options.ruleIds
      @href = options.href

    fetch:(options)->
      options = options || {}
      options.cache = true
      return BackboneWrapper.BaseCollection.prototype.fetch.call(this, options)

    parse:(data)->
      allData = []
      for model in @models
        allData.push model.toJSON()
      for d in data
        allData.push(d)
      allData

    asRows:()->
      violations = []
      for violation in @models
        componentId = violation.getObjectId()
        columns = [
          violation.get('rulePattern').name,
          violation.get('component').name,
          violation.get('diagnosis').status
          violation.getRuleId()+'/'+violation.getObjectId()
        ]

        violations.push({
          columns:columns
          extra:{
            componentId: componentId
            model:violation
          }
          id: violation.cid
          selected: componentId? and options?.selectedComponent == componentId
        })
      @_collection = new BackboneWrapper.BaseCollection(violations)
  })

  return{
    Violation
    Violations
    AdvanceSearchViolations
    ComponentViolations
    TransactionViolations
    TransactionViolationsRatio
    TotalViolations
    AddedRemovedViolations
  }
