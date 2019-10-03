# FIXME this helpers pattern is source of issues, we should think about a rework here
TableHelpers = ($,numeral, Handlebars) ->

  isGreyScore4 = (model)->
    if model?.extra?.active?
      return if model.extra.active then '' else 'grey'
    return 'grey' if model?.columns[0] >= 4
    return ''

  classifyScore = (value)->
    return 'bad' if value <2
    return 'warn' if value <3
    return 'empty'

  classifyScoreRange = (value) ->
    return 'score between 1 and 2 (high risk)' if value <2
    return 'score between 2 and 3 (medium risk)' if value <3

  variationFormat = (value, format = '0.00%', model)->
    return 'new' if model? and model.extra.isNew
    return 'n/a' if (isNaN(value) or !isFinite(value))
    varFormat = numeral(Math.abs(value)).format(format)
    return varFormat if value == 0
    return '~+ '+varFormat if varFormat == format and value>0
    return '~- '+varFormat if varFormat == format and value<0
    return '+'+ varFormat if value>0
    return '-'+ varFormat if value<0
    return varFormat

  scoreFormat = (value)->
    return 'n/a' if value=='n/a'
    return numeral(value).format('000')

  variationScore = (value)->
    return 'var-grey' if value==0
    return ''

  variationTitle = (value, reportType)->
    return 'Variation is not available' if isNaN(value)
    return 'We did not find violations in previous snapshot' if not isFinite(value)
    return 'No variation' if value==0
    return numeral(value).format('0.00%') if reportType
    return numeral(value).format('0.0000000000000000000%')

  technicalNameFormat = (value) ->
    separatedValues = value.split('-')
    if separatedValues.length >= 2
      separatedValues[0] = '<em>' + separatedValues[0] + '</em> '
      return separatedValues.join('-')
    if separatedValues.length == 2
      return '<em>' + separatedValues[0] + '</em> - ' + separatedValues[1]
    else
      return '<em>' + value + '</em>'

  scoreNotAvailable=(value)->
    return true if value=='NaN'
    return false

  templateScore=Handlebars.compile(
    '<span class="{{scoreType}}" title="{{scoreRange}}"/><span class="score {{grey}}" title="{{value}}">{{format}}</span>'
  )

  templateRuleScore=Handlebars.compile(
    '<span class="{{scoreType}}" title="{{scoreRange}}" /><span class="score {{grey}}" title="{{#if scoreNotAvailable}}This rule is no more activated for this snapshot. it can be due to Risk Model configuration or modification in the source code that remove the scope of object identified by the rule.{{else}}{{value}}{{/if}}">{{format}}</span>'
  )

  templateTechnicalScore=Handlebars.compile(
    '<span class="{{scoreType}}" title="{{scoreRange}}"/><span class="score {{grey}}" {{#if scoreNotAvailable}} title="This technical criteria is no more activated for this snapshot. it can be due to Risk Model configuration or modification in the source code that remove the scope of object identified by the rules included into the technical criteria."{{else}}title="{{value}}"{{/if}}>{{format}}</span>'
  )

  templateVar = Handlebars.compile(
    '<span class="{{grey}} {{var}}" title="{{title}}">{{format}}</span>'
  )

  templateName = Handlebars.compile(
    '<span class="{{grey}}">{{title}}</span>'
  )

  templateWeight = Handlebars.compile(
    '<span class="{{grey}}">{{format}}</span>'
  )

  templateTechnicalName = Handlebars.compile(
    '<span class="fixed-font {{grey}}" {{#if deactiveRuleInfo}}title="This technical criteria is no more activated for this snapshot. it can be due to Risk Model configuration or modification in the source code that remove the scope of object identified by the rules included into the technical criteria."{{/if}}>{{{technicalName}}}</span>'
  )
  templateRuleName = Handlebars.compile(
    '<span class="{{grey}}" {{#if deactiveRuleInfo}}title="This rule is no more activated for this snapshot. it can be due to Risk Model configuration or modification in the source code that remove the scope of object identified by the rule."{{/if}}>{{name}}</span>
    {{#if informationTitle}}<span title="{{informationTitle}}" class="information-icon {{grey}}"></span>{{/if}}
    {{#if addNewSymbol}}<span class="new-label">new</span>{{/if}}'
  )
  templateCritical = Handlebars.compile(
    '<span class="{{grey}} {{#if value}}critical{{/if}}"></span>'
  )


  formatName = (value, model)->
    templateName({title:value,grey:isGreyScore4(model)})

  formatTechnicalName = (value, model)->
    templateTechnicalName({grey:isGreyScore4(model), technicalName:technicalNameFormat(value),deactiveRuleInfo:model.extra.isGone})


  templateFormatViolation = Handlebars.compile('<span class="score {{grey}}" title="{{formatNumber value "0,000"}}">{{formatNumber value "0,000"}}</span>')
  formatViolation=(value, model)->
    extra = model.extra;
    templateFormatViolation({
      value:value
      grey:isGreyScore4(model)
      })

  formatScore=(value, model)->
    templateScore({
      scoreType:classifyScore(value)
      scoreRange:classifyScoreRange(value)
      grey:isGreyScore4(model)
      format:scoreFormat(value)
      value:value
    })

  formatRuleScore=(value, model)->
    templateRuleScore({
      scoreType:classifyScore(value)
      scoreRange:classifyScoreRange(value)
      grey:isGreyScore4(model)
      format:scoreFormat(value)
      value:value
      scoreNotAvailable:scoreNotAvailable(value)
    })

  formatTechnicalScore=(value, model)->
    templateTechnicalScore({
      scoreType:classifyScore(value)
      scoreRange:classifyScoreRange(value)
      grey:isGreyScore4(model)
      format:scoreFormat(value)
      value:value
      scoreNotAvailable:scoreNotAvailable(value)
    })

  formatVariation = (value, model, reportType)->
    format = '0%'
    if value? and !isNaN(value)
      if Math.abs(value) < 0.01
        format = '0.00%'
    templateVar({
      grey:isGreyScore4(model)
      var:variationScore(value)
      title:variationTitle(value, reportType)
      format:variationFormat(value, format)
    })

  formatGeneralVariation = (percentage, value, format, model, reportType)->
    templateVar({
      grey: isGreyScore4(model)
      var: variationScore(value)
      title: variationTitle(value, reportType)
      format: variationFormat(percentage, format,model)
    })


  formatWeight = (value, model) ->
    if value == 'n/a' or isNaN(value)
      return templateWeight({grey:isGreyScore4(model), format:value})
    return templateWeight({grey:isGreyScore4(model), format:numeral(value).format('0,000')})

  formatRuleName = (value, model) ->
    templateRuleName({grey:isGreyScore4(model), name:value,informationTitle:loadTitle(model.extra.type), addNewSymbol:model.extra.isNew, deactiveRuleInfo:model.extra.isGone})

  formatCritical = (value, model) ->
    templateCritical({grey:isGreyScore4(model), value:value})

  helpers = {
    isGreyScore4:isGreyScore4
    formatVariation:formatVariation
    formatGeneralVariation:formatGeneralVariation
    formatScore:formatScore
    formatRuleScore:formatRuleScore
    formatTechnicalScore:formatTechnicalScore
    formatName:formatName
    formatWeight:formatWeight
    formatTechnicalName:formatTechnicalName
    formatRuleName:formatRuleName
    formatCritical:formatCritical
    formatViolation:formatViolation
  }
