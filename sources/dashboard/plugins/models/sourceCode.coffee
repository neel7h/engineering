sourceCodes = (_, BackboneWrapper) ->

  escape = (string)->
    tagsToReplace = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;'
    };
    string.replace(/[&<>]/g, (tag) ->
      tagsToReplace[tag] || tag;
    )

  DiagnosisFindings = BackboneWrapper.BaseModel.extend({
    url: ()->
      REST_URL + CENTRAL_DOMAIN + '/components/' + @get('componentId') + '/snapshots/' + @get('snapshotId') + '/findings/' + @get('ruleId')

    hasBookmarks: ()->
      bookmarks = @get('bookmarks')
      return false unless bookmarks?
      return bookmarks.length != 0

    parse:(data)->
      if !data.values?.length
        @findings = []
      else
        @findings = data.values[0]
      return data

    asRows:(options)->
      results = []
      for object in @findings
        results.push({
            columns:[
              object.component.name
            ]
            extra:{
              componentId: object.component.href?.split('/')[2]
            }
        })
      @_collection = new BackboneWrapper.BaseCollection(results)
  })

  _Violation = BackboneWrapper.BaseModel.extend({
    url: ()->
      REST_URL + CENTRAL_DOMAIN + '/components/' + @get('componentId') + '/snapshots/' + @get('snapshotId') + '/violations?rule-pattern=' + @get('ruleId')

    parse:(data)->
      return data[0]

  })

  _RulePattern = BackboneWrapper.BaseModel.extend({
    url:() ->
      REST_URL + CENTRAL_DOMAIN + '/rule-patterns/' + @get('ruleId')
  })

  _TechnicalRuleSummary = BackboneWrapper.BaseModel.extend({
      url: ()->
        REST_URL + CENTRAL_DOMAIN + '/quality-indicators/' + @get('technicalId') + '/snapshots/' + @get('snapshotId')

      isCritical:(ruleId)->
        rule = _.findWhere(@get('gradeContributors'), {key:ruleId})
        return true if rule?.critical
        return false
  })

  _RuleSummary = BackboneWrapper.BaseModel.extend({
    url:()->
      REST_URL + CENTRAL_DOMAIN + '/quality-indicators/' + @get('ruleId') + '/snapshots/' + @get('snapshotId')

    getTechnicalAggregatorId:()->
      return @get('gradeAggregators')?[0].key

  })

  ViolationDetails = BackboneWrapper.BaseModel.extend({

    getData:()->
      deferred = $.Deferred()
      @ruleSummary = new _RuleSummary({
        snapshotId:@get('snapshotId')
        ruleId:@get('ruleId')
      })
      @rulePattern = new _RulePattern({
        ruleId:@get('ruleId')
      })
      @violation = new _Violation({
        snapshotId:@get('snapshotId')
        ruleId:@get('ruleId')
        componentId:@get('componentId')
      })
      @findings = new DiagnosisFindings({
        snapshotId:@get('snapshotId')
        ruleId:@get('ruleId')
        componentId:@get('componentId')
      })

      $.when(@violation.fetch(), @ruleSummary.fetch(), @rulePattern.fetch(), @findings.fetch()).done(()=>
        @technicalRuleSummary = new _TechnicalRuleSummary({
          snapshotId:@get('snapshotId')
          technicalId:@ruleSummary.getTechnicalAggregatorId()
        })
        @technicalRuleSummary.fetch().done(()=>
          deferred.resolve()
        ).fail(()->
          deferred.reject()
        )
      ).fail(()=>
          deferred.reject()
      )
      return deferred

    isCritical:()->
      @technicalRuleSummary.isCritical(@get('ruleId'))

    getFindings:()->
      return @findings.toJSON()

    getRulePattern:()->
      return @rulePattern.toJSON()

    getViolationStatus: ()->
      ### Return the violation information between the rule and object on given snapshot ###
      return @violation.toJSON()

    getType:()->
      bookmarks = @findings.get('bookmarks')
      return 'violationBookmarks' if bookmarks? and bookmarks.length > 0
      return 'path' if @findings.get('type') == 'path'
      return 'object' if @findings.get('type') == 'object'

    toJSON:()->
      return {
      rule: {
        name: @ruleSummary.get('name')
        rationale: @rulePattern.get('rationale')
      }
      component:{
        status:@violation.get('component').status
      }
      violation:{
        status:@violation.get('diagnosis').status
      }
      }

  })

  SourceCodes = BackboneWrapper.BaseCollection.extend({
    url: () ->
      return REST_URL + CENTRAL_DOMAIN + '/components/' + @componentId + '/snapshots/' + @snapshotId + '/source-codes'

    initialize: (models, options)->
      @componentId = options.componentId
      @snapshotId = options.snapshotId
  })

  SourceCode = BackboneWrapper.BaseModel.extend({
    url:()->
      queryParameters = []
      queryParameters.push('start-line=' + @get('startLine')) if @get('startLine')?
      queryParameters.push('end-line=' + @get('endLine')) if @get('endLine')?
      root = REST_URL + @get('href')
      if queryParameters.length != 0
        root += '?' + queryParameters.join('&')
      return root

    defaults:
      spread:1
      blockSize:10
      content:''
      linesOfCode:[]

    createFileLink:()->
      rootURL = '#' + @get('currentSnapshotHref')
      rootURL += '/components/' + @get('componentId') + '/'
      rootURL += @get('href').split('/').splice(1).join('/')
      return rootURL

    initialize:()->
      @set('href', @get('file').href) if @get('file')?.href?
      @set('objectStartLine',@get('startLine'))
      @set('startLine', Math.max(1,  @get('startLine') - @get('spread')))
      @set('objectEndLine', @get('endLine'))
      if @get('fetchAllBookmark')
        @set('endLine', @get('endLine') + @get('spread'))
      else
        @set('endLine', Math.max(1,Math.min(@get('objectEndLine'), @get('objectStartLine') + @get('blockSize'))))
        @set('endLine', @get('endLine') + @get('spread')) if @get('endLine') == @get('objectEndLine')
        @set('endLine', @get('objectEndLine') + @get('spread')) if  @get('objectEndLine') - @get('endLine') < @get('blockSize')
      @set('viewFile', @createFileLink())

    fetchMore:()->
      @set('startLine', @get('endLine') + 1)
      @set('endLine',Math.min(@get('objectEndLine'), @get('startLine') +  @get('blockSize')))
      @set('endLine', @get('endLine') + @get('spread')) if @get('endLine') == @get('objectEndLine')
      @set('endLine', @get('objectEndLine') + @get('spread')) if  @get('objectEndLine') - @get('endLine') < @get('blockSize')
      return @fetch()

    canShowMore:()->
      return @get('endLine') < @get('objectEndLine')

    fetch: (options)->
      options = _.extend(options || {}, {
        dataType: 'text'
        contentType:'text/plain; charset=UTF-8'
      })
      this.constructor.__super__.fetch.call(this, options);

    parse: (response, options)->
      linesOfCode = response?.split('\n')
      linesOfCode = linesOfCode.slice(0, linesOfCode.length - 1)  if linesOfCode[linesOfCode.length - 1] == ''
      result = @toJSON()
      result.content = response
      result.linesOfCode = linesOfCode
      return result

  })

  return {
    SourceCode
    SourceCodes
    DiagnosisFindings
    ViolationDetails
  }
