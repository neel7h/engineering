Controller = (facade) ->

  facade.controllers.InvestigationController.extend({
    pageId: 'components-investigation'
    controlCleanup:()->
      facade.bus.emit('filter',{business:60017})
    states:
      previousIndex: -1
      currentIndex: -1
      parameters:{
        theme:'components-investigation'
      }
      pages:[
        {
          pageView:ComponentBrowserView(facade)
        }
        {
          pageView:QualityRuleWithViolationView(facade)
        }
        {
          pageView:RuleDetails(facade)
        }
        {
          pageView:ViolationDetails(facade)
        }
      ]
      computeIndex:(parameters)->
        return 2 if parameters.ruleComponent?
        return 1 if parameters.rule?
        return 0
  })