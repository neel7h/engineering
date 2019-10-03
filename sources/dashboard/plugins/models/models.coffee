plugin = (_, Backbone, $) ->

  # TODO factorize technical criterion & quality rules as much as possible to reduce code duplicates
  # TODO add tests

  # TODO : model for breadcrumb ? ADG7018/applications/15/results?quality-indicators=(60017,61009,7388)

  error = (model, xhr, options) ->
    if xhr?.status!=0 # status 0 means that the page reloading cancelled the request
      alert("Unexpected error")
      console.info "-----------------"
      console.info "Unexpected error:"
      console.info model
      console.info xhr
      console.info options

  BackboneWrapper =
    BaseModel : Backbone.Model.extend({
        defaultOptions:
          success: ()=>
            @success?.apply(this, arguments)
          error: ()=>
            @error?.apply(this, Array.prototype.slice.call(arguments))

        getData: (options) ->
          fullOptions = _.extend({success:@success, error:@error}, options)
          return @fetch(fullOptions)
    })
    BaseCollection : Backbone.Collection.extend({
      defaultOptions:
        success: ()=>
          @success?.apply(this, arguments)
        error: ()=>
          @error?.apply(this, Array.prototype.slice.call(arguments))

      getData: (options)->
        fullOptions = _.extend({success:@defaultOptions.success, error:@defaultOptions.error}, options)
        return @fetch(fullOptions)
    })

  Scope = BackboneWrapper.BaseModel.extend({

  })

  Server = BackboneWrapper.BaseModel.extend({
    url: REST_URL + 'server'

    licenseStatus:()->
      @get('license')?.status
  })


  results = results(_,BackboneWrapper,$)

  models =
    id:'models'
    Facade:
      backbone:
        Model:BackboneWrapper.BaseModel
        Collection:BackboneWrapper.BaseCollection
      models:
        actionPlan:actionPlan(_, BackboneWrapper)
        advancedSearch:advancedSearch(_, BackboneWrapper)
        applications:new applications(_, BackboneWrapper)
        breadcrumb:breadcrumb(_,BackboneWrapper)
        BusinessCriteriaResults:results.BusinessCriteriaResults
        Collection:BackboneWrapper.BaseCollection
        componentBrowserTree: new componentBrowser(_, BackboneWrapper)
        configuration:new configuration(_, BackboneWrapper)
        ContributionCriterion:results.ContributionCriterion
        Distribution: results.Distribution
        education:education(_,BackboneWrapper)
        exclusion:exclusion(_, BackboneWrapper)
        reportGenerator: reportGenerator(_,BackboneWrapper)
        documentationPattern: new documentationPattern(_, BackboneWrapper)
        Model:BackboneWrapper.BaseModel
        ModuleResultsWithCriticity : results.ModuleResultsWithCriticity        
        QualityRuleComputingDetail:results.ComputingDetails
        QualityRulesResults:results.QualityRulesResults
        QualityRuleWithViolationForComponent:results.QualityRuleWithViolationForComponent
        QualityRulesResultsForAllTechnicalCriterion:results.QualityRulesResultsForAllTechnicalCriterion
        QualityRulesWithViolations:results.QualityRulesWithViolations
        TechnicalContext:results.TechnicalContext
        RulesViolationsForABusinessCriterion:results.RulesViolationsForABusinessCriterion
        ListOfBusinessCriteria:results.ListOfBusinessCriteria
        technology: ListOfTechnologies(_,BackboneWrapper)
        Server:Server
        ViolationsIndex: results.ViolationsIndex
        Scope:Scope
        TagResults: results.TagResults
        TagsDetailResults:results.TagsDetailResults
        snapshots:new snapshots(_, BackboneWrapper)
        sourceCodes: new sourceCodes(_, BackboneWrapper)
        TechnicalCriteriaResults:results.TechnicalCriteriaResults
        technologies:technologies(_, BackboneWrapper)
        transactions:transactions(_, $, BackboneWrapper)
        TopRulesViolationsResults:results.TopRulesViolationsResults
        user:users(_, BackboneWrapper)
        violations:new violations(_, BackboneWrapper)

  models

# AMD support (use in require)
if define?.amd?
  define(['underscore', 'backbone', 'jquery'], (_, Backbone, $) ->
    return plugin(_,Backbone, $)
  )
# direct browser integration (src include)
else if window?
  window.stem = window.stem or {}
  window.stem.plugins = window.stem.plugins or {}
  window.stem.plugins.models = plugin(_,Backbone, $)
else if module?.exports?
  module.exports = plugin(_,Backbone, $)
