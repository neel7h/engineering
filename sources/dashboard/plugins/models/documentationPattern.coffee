###
  Documentation patterns provide the models to access the rules' documentation

  REST-API documentation : http://confluence/display/PdtInt/Portfolio+API
###
documentationPattern = (_, BackboneWrapper) ->


  RulePattern = BackboneWrapper.BaseModel.extend({
    url: ->
      REST_URL + CENTRAL_DOMAIN + '/rule-patterns/' + @get('qualityRuleId')

    getName:()->
      @get('name')

    getRationale:()->
      @get('rationale')

    getDescription:()->
      @get('description')

    getRemediation:()->
      @get('remediation')

    getReference:()->
      @get('reference')

    getTechnologies:()->
      @get('technologies')

    getOutput: ()->
      @get('output')

    getTotal: ()->
      @get('total')

    getSample: ()->
      @get('sample')

    getRemediationSample: ()->
      @get('remediationSample')

  })

  return{
    RulePattern
  }