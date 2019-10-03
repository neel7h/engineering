Controller = (facade) ->

  facade.controllers.InvestigationController.extend({
    pageId: 'transaction-investigation'
    # controlCleanup:()->
      # facade.bus.emit('filter',{module:-1, technology:-1})
    states:
      previousIndex:-1
      currentIndex:-1
      parameters:{
        theme:'transaction-investigation'
      }
      pages:[
        {
          pageView:TransactionView(facade)
        }
        {
          pageView:BusinessCriteriaView(facade)#facade.backbone.View.extend({})
        }
        {
          pageView:TechnicalCriteriaView(facade)
        }
        {
          pageView:QualityRulesView(facade)#facade.backbone.View.extend({})
          queryString:['qi_violations','qi_documentation','qi_scroll']
        }
        # {
        #   pageView:facade.backbone.View.extend({})
        # }
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
        return 4 if parameters.component?
        return 3 if parameters.rule?
        return 2 if parameters.technical?
        return 1 if parameters.business?
        return 0
  })
