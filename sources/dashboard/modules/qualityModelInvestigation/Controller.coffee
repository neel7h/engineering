Controller = (facade) ->

  facade.controllers.InvestigationController.extend({
    pageId: 'quality-investigation'
    controlCleanup:()->
      facade.bus.emit('filter',{module:-1, technology:-1})
    states:
      previousIndex:-1
      currentIndex:-1
      pages:[
        {
          pageView:BusinessCriteriaView(facade)
        }
        {
          pageView:TechnicalCriteriaView(facade)
        }
        {
          pageView:QualityRulesView(facade)
          queryString:['qi_violations', 'qi_computing-details','qi_documentation', 'qi_notes', 'qi_scroll']
        }
        {
          pageView:RuleDetails(facade)
          queryString:['qi_violations', 'qi_computing-details','qi_documentation', 'qi_notes', 'qi_scroll','qivi_source-code', 'qivi_violation-status', 'qivi_notes', 'qivi_scroll']
        }
        {
          pageView:ViolationDetails(facade)
          queryString:['qi_violations', 'qi_computing-details','qi_documentation', 'qi_notes', 'qi_scroll','qivi_source-code', 'qivi_violation-status', 'qivi_notes', 'qivi_scroll']
        }
      ]
      computeIndex:(parameters)->
        return 3 if parameters.component?
        return 2 if parameters.rule?
        return 1 if parameters.technical?
        return 0
  })
