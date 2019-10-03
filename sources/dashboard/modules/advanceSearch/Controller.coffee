Controller = (facade) ->

  facade.controllers.InvestigationController.extend({
    pageId: 'advanceSearch'
    states:
      previousIndex:-1
      currentIndex:-1
      parameters:{
        theme:'advance-search'
      }
      pages:[
        {
          pageView:AdvanceSearchView (facade)
        }
        {
          pageView: RuleDetails(facade)
        }
      ]
      computeIndex:(parameters)->
        return 0
  })
